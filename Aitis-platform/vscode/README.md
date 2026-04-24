# VS Code Setup Pack for AI Test Intelligence Platform

Copy the `.vscode` folder and `ai-test-intelligence-platform.code-workspace` file into the **root of your project repository**.

## What is included
- `.vscode/settings.json`
- `.vscode/launch.json`
- `.vscode/tasks.json`
- `.vscode/extensions.json`
- `ai-test-intelligence-platform.code-workspace`

## First-time setup
### Backend
```bash
cd apps/api
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend
```bash
cd apps/web
npm install
```

## Environment files
Copy these files before running:
- `apps/api/.env.example` → `apps/api/.env`
- `apps/web/.env.example` → `apps/web/.env.local`

## Run from VS Code
- Open **Run and Debug**
- Choose **Run Full Stack**
- Or run tasks manually from **Terminal → Run Task**

## Useful URLs
- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/health
