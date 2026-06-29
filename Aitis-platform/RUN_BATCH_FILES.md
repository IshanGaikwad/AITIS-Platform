# 🚀 AITIS Phase 1 - Quick Start Batch Files

Simple Windows batch files to run and manage the AITIS Phase 1 system.

## 📋 Available Batch Files

### **setup.bat** 🔧
**Install all dependencies and run migrations**
- Installs Python dependencies
- Installs Alembic for database migrations
- Runs database migrations
- Installs Node.js dependencies

**Run once** before starting servers for the first time.

```bash
double-click setup.bat
```

---

### **start-both.bat** ⚡
**Start Backend AND Frontend servers simultaneously**
- Backend API on port 8000
- Frontend on port 3000
- Opens in 2 new windows

**Most common choice** for full development setup.

```bash
double-click start-both.bat
```

---

### **start-backend.bat** 🔌
**Start Backend server only**
- FastAPI on port 8000
- API Docs at http://localhost:8000/docs

Use when you only need the API.

```bash
double-click start-backend.bat
```

---

### **start-frontend.bat** 🎨
**Start Frontend server only**
- Next.js dev server on port 3000

Use when backend is already running elsewhere.

```bash
double-click start-frontend.bat
```

---

### **run-phase1.bat** 🎯
**Interactive menu with all options**
- Full setup and run
- Component-by-component setup
- Individual server startup
- Run tests
- More granular control

Use for advanced workflows.

```bash
double-click run-phase1.bat
```

---

### **run-tests.bat** 🧪
**Run integration and E2E tests**
- Backend integration tests (pytest)
- Frontend E2E tests (Playwright)
- Run both

Use to validate the system.

```bash
double-click run-tests.bat
```

---

## 🎯 Quick Start Workflows

### **First Time Setup**
```
1. double-click setup.bat
   (installs everything)
2. double-click start-both.bat
   (runs both servers)
```

### **Daily Development**
```
double-click start-both.bat
```

### **Backend Only**
```
double-click start-backend.bat
```

### **Run Tests**
```
double-click run-tests.bat
```

---

## 🌐 Access Points

Once running:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

---

## ⚙️ Prerequisites

Make sure you have installed:

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Node.js 20+** - [Download](https://nodejs.org/)
- **Git** (optional, for version control) - [Download](https://git-scm.com/)

**Optional (for PostgreSQL support):**
- **PostgreSQL 16** - [Download](https://www.postgresql.org/download/)

---

## 🔍 System Requirements

| Requirement | Minimum | Recommended |
|------------|---------|-------------|
| RAM | 4 GB | 8 GB |
| Disk | 2 GB | 5 GB |
| Python | 3.11 | 3.12+ |
| Node.js | 20 | 22+ |

---

## 🆘 Troubleshooting

### Port Already in Use
If you get "Address already in use" error:
```powershell
# Find and kill process on port 8000 (backend)
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Find and kill process on port 3000 (frontend)
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

### Python Not Found
```bash
# Add Python to PATH in System Environment Variables
# Or use full path: C:\Python312\python.exe
```

### Node/npm Not Found
```bash
# Reinstall Node.js and ensure it's added to PATH
# Verify: npm --version
```

### Dependencies Won't Install
```bash
# Clear cache and retry
pip cache purge
npm cache clean --force

# Then run setup.bat again
```

### Database Migration Fails
```bash
# Check alembic.ini for correct database URL
# For SQLite (default), it creates app.db automatically
```

---

## 📝 Batch File Locations

All batch files are in the root directory:
```
Aitis-platform/
├── setup.bat
├── start-both.bat
├── start-backend.bat
├── start-frontend.bat
├── start-frontend.bat
├── run-phase1.bat
├── run-tests.bat
└── RUN_BATCH_FILES.md (this file)
```

---

## 📖 For More Information

- **API Docs:** See [PHASE1_API_DOCS.md](./PHASE1_API_DOCS.md)
- **Setup Guide:** See [DEVELOPER_QUICK_REF.md](./DEVELOPER_QUICK_REF.md)
- **Full Overview:** See [PHASE1_COMPLETION_SUMMARY.md](./PHASE1_COMPLETION_SUMMARY.md)
- **All Docs:** See [DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md)

---

## 🎓 What Each Batch File Does (Technical)

### setup.bat
```batch
1. cd backend
2. pip install -r requirements.txt
3. pip install alembic
4. alembic upgrade head
5. cd frontend\apps\web
6. npm install
```

### start-both.bat
```batch
1. start "Backend" cmd /k "cd backend && uvicorn app.main:app --reload"
2. start "Frontend" cmd /k "cd frontend\apps\web && npm run dev"
```

### run-tests.bat
```batch
1. pytest tests/test_phase1_integration.py -v
2. npx playwright test tests/e2e/phase1.spec.ts --headed
```

---

## ✅ Verification Checklist

After running the batch files, verify:

- [ ] Backend server running (http://localhost:8000)
- [ ] Frontend server running (http://localhost:3000)
- [ ] API Docs accessible (http://localhost:8000/docs)
- [ ] No error messages in terminal windows
- [ ] Ports 3000 and 8000 are available

---

## 🐛 Getting Help

If issues persist:

1. Check error messages in the terminal window
2. Ensure all prerequisites are installed
3. Try running setup.bat again
4. Check system PATH variables
5. Consult [DEVELOPER_QUICK_REF.md](./DEVELOPER_QUICK_REF.md) for detailed help

---

**Happy coding! 🚀**
