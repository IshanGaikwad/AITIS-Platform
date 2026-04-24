.PHONY: help install build up down logs clean

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
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
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
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload

dev-frontend:
	cd frontend/apps/web && npm run dev

test-backend:
	cd backend && . .venv/bin/activate && pytest

status:
	docker-compose ps
