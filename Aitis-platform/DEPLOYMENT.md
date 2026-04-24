# AITIS Deployment Guide

## Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 20+ (for local development)

## Initial Setup

### 1. Environment Configuration
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

Make sure to set:
- `JIRA_BASE_URL` - Your Jira domain
- `JIRA_EMAIL` - Your Jira email
- `JIRA_API_TOKEN` - Your Jira API token

### 2. Backend Setup (Local Development)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend Setup (Local Development)
```bash
cd frontend/apps/web
npm install
```

## Running with Docker Compose

### Development
```bash
docker-compose up --build
```

Access:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Production
```bash
docker-compose -f docker-compose.yml up -d
```

## Local Development

### Start Backend
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

### Start Frontend
```bash
cd frontend/apps/web
npm run dev
```

The frontend should connect to `http://localhost:8000/api` by default.

## Deployment Checklist

- [ ] Environment variables configured (`.env` file)
- [ ] Docker images built successfully
- [ ] Backend database initialized
- [ ] Frontend environment configured
- [ ] Jira API credentials validated
- [ ] All endpoints tested with API docs (http://localhost:8000/docs)
- [ ] Frontend can connect to backend API

## Troubleshooting

### Backend won't start
1. Check Python version: `python --version` (should be 3.11+)
2. Verify all dependencies: `pip install -r requirements.txt`
3. Check `.env` file configuration

### Frontend can't reach backend
1. Ensure `NEXT_PUBLIC_API_BASE_URL` is set correctly in `.env.local`
2. Check backend is running: `curl http://localhost:8000/docs`
3. Check Docker network if using compose

### Port conflicts
Change ports in `docker-compose.yml` or use:
```bash
docker ps  # See running containers
docker kill <container-id>  # Stop conflicting container
```
