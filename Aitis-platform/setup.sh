#!/bin/bash
set -e

echo "🚀 AITIS Platform - Initial Setup"
echo "=================================="

# Check for required tools
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker and Docker Compose found"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
else
    echo "✅ .env file already exists"
fi

# Create backend .env if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "📝 Creating backend/.env file..."
    cp backend/.env.example backend/.env
    echo "⚠️  Please edit backend/.env with your Jira credentials"
else
    echo "✅ backend/.env file already exists"
fi

# Create frontend .env.local if it doesn't exist
if [ ! -f frontend/apps/web/.env.local ]; then
    echo "📝 Creating frontend/.env.local file..."
    cp frontend/apps/web/.env.local.example frontend/apps/web/.env.local
    echo "✅ frontend/.env.local created"
else
    echo "✅ frontend/.env.local file already exists"
fi

echo ""
echo "📚 Next steps:"
echo "1. Review and update your configuration files:"
echo "   - .env"
echo "   - backend/.env"
echo "   - frontend/apps/web/.env.local"
echo ""
echo "2. Start the services:"
echo "   docker-compose up --build"
echo ""
echo "3. Access the application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "✨ Setup complete!"
