.PHONY: help install build up down logs clean dev-backend dev-frontend test-backend status

# Cross-platform venv python (Windows uses .venv/Scripts, Unix uses .venv/bin).
# Paths are relative to backend/ since each recipe cds there first.
ifeq ($(OS),Windows_NT)
VENV_PY := .venv/Scripts/python
else
VENV_PY := .venv/bin/python
endif

help:
	@echo "AITIS Platform - Available Commands"
	@echo "===================================="
	@echo "make install         - Install dependencies locally"
	@echo "make build          - Build Docker images"
	@echo "make up             - Start services with Docker Compose"
	@echo "make down           - Stop services"
	@echo "make logs           - View container logs"
	@echo "make logs-backend   - View backend logs"
	@echo "make logs-frontend  - View frontend logs"
	@echo "make clean          - Remove containers and volumes"
	@echo "make dev-backend    - Start backend locally"
	@echo "make dev-frontend   - Start frontend locally"
	@echo "make test-backend   - Run backend tests"

install:
	@echo "Installing backend dependencies..."
	cd backend && python -m venv .venv && $(VENV_PY) -m pip install --upgrade pip && $(VENV_PY) -m pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend/apps/web && npm install

build:
	@echo "Building Docker images..."
	docker-compose build

up:
	@echo "Starting services..."
	docker-compose up -d
	@echo "Services started!"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

down:
	@echo "Stopping services..."
	docker-compose down

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v
	@echo "Cleaned!"

dev-backend:
	cd backend && $(VENV_PY) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

dev-frontend:
	cd frontend/apps/web && npm run dev

test-backend:
	cd backend && $(VENV_PY) -m pytest

status:
	docker-compose ps
