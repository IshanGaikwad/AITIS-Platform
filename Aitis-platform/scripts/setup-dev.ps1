param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$PG_VERSION = "16"
$PG_BIN     = "C:\Program Files\PostgreSQL\$PG_VERSION\bin"
$DB_NAME    = "aitis"
$DB_USER    = "aitis"
$DB_PASS    = "aitis_dev_password"
$SECRET     = "dev-secret-key-change-in-production-32chars"
$ROOT       = Split-Path $PSScriptRoot -Parent
$BACKEND    = Join-Path $ROOT "backend"

Write-Host ""
Write-Host "==> Step 1: Check PostgreSQL $PG_VERSION" -ForegroundColor Cyan
if (Test-Path "$PG_BIN\psql.exe") {
    Write-Host "    Already installed at $PG_BIN" -ForegroundColor Green
} else {
    Write-Host "    Installing PostgreSQL $PG_VERSION via winget..."
    winget install --id "PostgreSQL.PostgreSQL.$PG_VERSION" --silent --accept-package-agreements --accept-source-agreements
    Start-Sleep -Seconds 5
    if (-not (Test-Path "$PG_BIN\psql.exe")) {
        $found = Get-ChildItem "C:\Program Files\PostgreSQL" -Directory -ErrorAction SilentlyContinue |
                 Sort-Object Name -Descending |
                 Select-Object -First 1
        if ($found) { $PG_BIN = "$($found.FullName)\bin" }
    }
    Write-Host "    Done. Using: $PG_BIN" -ForegroundColor Green
}

$env:PATH = "$PG_BIN;" + $env:PATH

Write-Host ""
Write-Host "==> Step 2: Start PostgreSQL service" -ForegroundColor Cyan
$svcName = "postgresql-x64-$PG_VERSION"
$svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
if ($null -eq $svc) {
    $svc = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
}
if ($null -eq $svc) {
    Write-Host "    No PostgreSQL service found — skipping." -ForegroundColor Yellow
} elseif ($svc.Status -eq "Running") {
    Write-Host "    Service '$($svc.Name)' already running." -ForegroundColor Green
} else {
    try {
        Start-Service -Name $svc.Name -ErrorAction Stop
        Write-Host "    Service '$($svc.Name)' started." -ForegroundColor Green
    } catch {
        Write-Host "    Could not start service (needs admin). Start PostgreSQL manually then re-run." -ForegroundColor Yellow
    }
}
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "==> Step 3: Create database and user" -ForegroundColor Cyan
$psql = Join-Path $PG_BIN "psql.exe"
if (-not (Test-Path $psql)) {
    Write-Host "    psql.exe not found -- skipping. Install PostgreSQL first." -ForegroundColor Yellow
} else {
    $sql1 = "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'"
    $exists = (& $psql -U postgres -t -c $sql1 2>$null) -match "1"
    if (-not $exists) {
        & $psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
    }
    $dbExists = (& $psql -U postgres -t -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>$null) -match "1"
    if (-not $dbExists) {
        & $psql -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    }
    & $psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    Database and user ready." -ForegroundColor Green
    } else {
        Write-Host "    psql failed. Manually create: CREATE USER $DB_USER WITH PASSWORD '$DB_PASS'; CREATE DATABASE $DB_NAME OWNER $DB_USER;" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "==> Step 4: Create backend/.env" -ForegroundColor Cyan
$envFile = Join-Path $BACKEND ".env"
if (Test-Path $envFile) {
    Write-Host "    .env already exists -- skipping." -ForegroundColor Green
} else {
    $content = "APP_NAME=AI Test Intelligence API`nAPP_ENV=development`n`nDATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}`n`nREDIS_URL=redis://localhost:6379/0`n`nSECRET_KEY=${SECRET}`nALGORITHM=HS256`nACCESS_TOKEN_EXPIRE_MINUTES=60`nREFRESH_TOKEN_EXPIRE_DAYS=7`n`nOAUTH2_PROVIDER=atlassian`nOAUTH2_CLIENT_ID=`nOAUTH2_CLIENT_SECRET=`nOAUTH2_AUDIENCE=api.atlassian.com`nOAUTH2_SCOPES=read:jira-work read:confluence-content.all`nOAUTH2_REDIRECT_URI=http://localhost:3000/auth/callback`n`nJIRA_BASE_URL=`nJIRA_EMAIL=`nJIRA_API_TOKEN="
    [System.IO.File]::WriteAllText($envFile, $content, [System.Text.Encoding]::UTF8)
    Write-Host "    Created: $envFile" -ForegroundColor Green
}

Write-Host ""
Write-Host "==> Step 5: Run Alembic migrations" -ForegroundColor Cyan
Push-Location $BACKEND
python -m alembic upgrade head
if ($LASTEXITCODE -eq 0) {
    Write-Host "    Migrations applied." -ForegroundColor Green
} else {
    Write-Host "    Alembic failed -- backend will auto-create tables on first start." -ForegroundColor Yellow
}
Pop-Location

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "  Start backend:  cd backend && uvicorn app.main:app --reload --port 8000"
Write-Host "  Start frontend: cd frontend/apps/web && npm run dev"
Write-Host ""
