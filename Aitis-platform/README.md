# AI Test Intelligence Platform (AITIS)

Full-stack application for intelligent test generation with FastAPI backend and Next.js frontend.

## 📋 Quick Start

### Prerequisites
- Docker & Docker Compose (for containerized deployment)
- Python 3.11+ (for local development)
- Node.js 20+ (for local development)

### 1️⃣ Initial Setup
```bash
# Run the setup script
bash setup.sh

# This will:
# - Verify Docker installation
# - Create .env files from examples
# - Guide you through configuration
```

### 2️⃣ Configure Environment
Edit the following files with your configuration:
- `.env` - Main configuration
- `backend/.env` - Jira credentials
- `frontend/apps/web/.env.local` - Frontend API endpoint

### 3️⃣ Start Services

**Using Docker Compose (Recommended)**
```bash
docker-compose up --build
```

**Using Make**
```bash
make up
```

**Local Development**
```bash
# Terminal 1 - Backend
make dev-backend

# Terminal 2 - Frontend
make dev-frontend
```

## 🌐 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | Web UI |
| Backend API | http://localhost:8000 | REST API |
| API Documentation | http://localhost:8000/docs | Interactive API docs |
| Health Check | http://localhost:8000/health | Backend health |

## 📁 Project Structure

```
Aitis-platform/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── main.py      # App entry point
│   │   ├── api/         # API routes
│   │   ├── core/        # Configuration
│   │   ├── db/          # Database
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   └── services/    # Business logic
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
│
├── frontend/            # Next.js application
│   └── apps/web/
│       ├── app/         # Next.js pages
│       ├── components/  # React components
│       ├── lib/         # Utilities & API client
│       ├── Dockerfile
│       ├── package.json
│       └── .env.local
│
├── docker-compose.yml   # Docker Compose config
├── .env.example         # Environment template
├── .env.production      # Production template
├── Makefile             # Build commands
├── setup.sh             # Initial setup script
└── DEPLOYMENT.md        # Detailed deployment guide
```

## 🚀 Available Commands

```bash
make help              # Show all available commands
make install          # Install dependencies locally
make build            # Build Docker images
make up               # Start services
make down             # Stop services
make logs             # View all logs
make logs-backend     # View backend logs
make logs-frontend    # View frontend logs
make clean            # Remove containers and volumes
make dev-backend      # Start backend locally
make dev-frontend     # Start frontend locally
make test-backend     # Run backend tests
make status           # Show container status
```

## 🔧 Configuration

### Backend Environment Variables
```env
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
ENV=development
DATABASE_URL=sqlite:///./app.db
```

### Frontend Environment Variables
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

## 📦 Backend Stack
- **FastAPI** - Modern async web framework
- **SQLAlchemy** - ORM
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **Python-dotenv** - Environment management

## 🎨 Frontend Stack
- **Next.js 15** - React framework
- **React 19** - UI library
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling

## 🐳 Docker Deployment

### Development
```bash
docker-compose up --build
```

### Production
1. Update `.env.production` with your settings
2. Update `docker-compose.yml` to use `.env.production`
3. Build and push images:
```bash
docker-compose build
docker-compose -f docker-compose.yml up -d
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
source .venv/bin/activate
pytest
```

### Frontend Tests
```bash
cd frontend/apps/web
npm test
```

## 📚 API Endpoints

### Stories
- `GET /api/stories/sample` - Get sample story

### Intents
- `POST /api/intents/generate` - Generate intents from story

### Test Cases
- `POST /api/tests/generate` - Generate test cases

### Scenarios
- `POST /api/scenarios/generate` - Generate Gherkin scenarios

### Automation
- `POST /api/automation/generate` - Generate automation code

See http://localhost:8000/docs for interactive documentation.

## 🐛 Troubleshooting

### Services won't start
```bash
# Check Docker
docker --version
docker-compose --version

# Clean up
make clean

# Try again
make up
```

### Port conflicts
```bash
# Find process using port
lsof -i :8000        # Backend
lsof -i :3000        # Frontend

# Kill process
kill -9 <PID>
```

### Frontend can't reach backend
1. Check `.env.local` has correct `NEXT_PUBLIC_API_BASE_URL`
2. Verify backend is running: `curl http://localhost:8000/health`
3. Check browser console for CORS errors

### Backend database errors
```bash
cd backend
rm -f app.db
docker-compose restart backend
```

## 📖 Additional Resources

- [Deployment Guide](./DEPLOYMENT.md)
- [Backend README](./backend/README.md)
- [Frontend README](./frontend/README.md)
- [API Documentation](http://localhost:8000/docs) (when running)

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests
4. Submit a pull request

## 📄 License

[Add your license here]

## ❓ Support

[Add support information here]
