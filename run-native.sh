#!/bin/bash

################################################################################
# Self-Hosted AI Lead Generation Platform - Native Startup Script (No Docker)
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "================================================================================"
echo "Self-Hosted AI Lead Generation Platform - Native Startup Script (No Docker)"
echo "================================================================================"
echo ""

# Function to print colored messages
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

################################################################################
# Check System Requirements
################################################################################
print_info "Checking system requirements..."

MISSING_DEPS=()

# Check Python 3.12+
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python 3.10+ required, found $PYTHON_VERSION"
        MISSING_DEPS+=("python3.10+")
    fi
else
    print_error "python3 is not installed"
    MISSING_DEPS+=("python3")
fi

# Check pip
if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
    print_success "pip found"
else
    print_error "pip is not installed"
    MISSING_DEPS+=("python3-pip")
fi

# Check Node.js 18+
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)
    if [ "$NODE_MAJOR" -ge 18 ]; then
        print_success "Node.js $NODE_VERSION found"
    else
        print_error "Node.js 18+ required, found $NODE_VERSION"
        MISSING_DEPS+=("nodejs 18+")
    fi
else
    print_warning "Node.js not found (frontend will not run)"
fi

# Check npm
if command -v npm &> /dev/null; then
    print_success "npm found"
else
    print_warning "npm not found (frontend will not run)"
fi

# Check PostgreSQL
if command -v psql &> /dev/null; then
    print_success "PostgreSQL client found"
else
    print_warning "PostgreSQL not found - you'll need to install it manually"
fi

# Check Redis
if command -v redis-cli &> /dev/null; then
    print_success "Redis client found"
else
    print_warning "Redis not found - you'll need to install it manually"
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    print_error "Missing critical dependencies: ${MISSING_DEPS[*]}"
    print_info "Install Python 3.10+: https://www.python.org/downloads/"
    exit 1
fi

################################################################################
# Create Directory Structure
################################################################################
print_info "Creating directory structure..."

mkdir -p "$SCRIPT_DIR/data/postgres"
mkdir -p "$SCRIPT_DIR/data/redis"
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/uploads"
mkdir -p "$SCRIPT_DIR/exports"

################################################################################
# Setup Environment Variables
################################################################################
print_info "Setting up environment configuration..."

ENV_FILE="$SCRIPT_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    # Generate a random secret key
    SECRET_KEY_VALUE="leadgen-secret-$(date +%s)-$$"
    if command -v openssl &> /dev/null; then
        SECRET_KEY_VALUE="leadgen-$(openssl rand -hex 32 2>/dev/null || echo $SECRET_KEY_VALUE)"
    fi
    
    cat > "$ENV_FILE" << EOF
# =============================================================================
# Self-Hosted AI Lead Generation Platform - Environment Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Application Settings
# -----------------------------------------------------------------------------
APP_NAME="Lead Generation Platform"
APP_ENV=development
DEBUG=True
SECRET_KEY="$SECRET_KEY_VALUE"

# -----------------------------------------------------------------------------
# Database Configuration (PostgreSQL)
# -----------------------------------------------------------------------------
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=leadgen
POSTGRES_USER=leadgen_user
POSTGRES_PASSWORD=LeadGen123!SecurePassword

# Database URL for SQLAlchemy
DATABASE_URL=postgresql://leadgen_user:LeadGen123!SecurePassword@localhost:5432/leadgen

# -----------------------------------------------------------------------------
# Redis Configuration
# -----------------------------------------------------------------------------
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# -----------------------------------------------------------------------------
# API Settings
# -----------------------------------------------------------------------------
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000","http://127.0.0.1:3000","http://127.0.0.1:8000"]

# -----------------------------------------------------------------------------
# Default Admin User
# -----------------------------------------------------------------------------
DEFAULT_ADMIN_EMAIL=admin@leadgen.local
DEFAULT_ADMIN_PASSWORD=Admin123!ChangeMe

# -----------------------------------------------------------------------------
# Processing Settings
# -----------------------------------------------------------------------------
MAX_BATCH_SIZE=10000
WORKER_CONCURRENCY=4
REQUEST_TIMEOUT=30
MAX_RETRIES=3

# -----------------------------------------------------------------------------
# File Storage
# -----------------------------------------------------------------------------
UPLOAD_DIR=$SCRIPT_DIR/uploads
EXPORT_DIR=$SCRIPT_DIR/exports

# -----------------------------------------------------------------------------
# Optional API Keys (Configure as needed)
# -----------------------------------------------------------------------------
# Google Custom Search API
GOOGLE_API_KEY=
GOOGLE_CSE_ID=

# Bing Search API
BING_API_KEY=

# Hunter.io API
HUNTER_API_KEY=

# Clearbit API
CLEARBIT_API_KEY=

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_LEVEL=INFO
LOG_FILE=$SCRIPT_DIR/logs/backend.log
EOF
    
    print_success "Created .env file at $ENV_FILE"
else
    print_info ".env file already exists"
fi

# Load environment variables (handle special characters properly)
print_info "Loading environment variables..."
while IFS='=' read -r line; do
    # Skip comments and empty lines
    [[ -z "$line" || "$line" =~ ^#.* ]] && continue
    # Extract key and value
    key="${line%%=*}"
    value="${line#*=}"
    # Remove surrounding quotes if present
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
    # Export the variable
    export "$key=$value"
done < "$ENV_FILE"

################################################################################
# Setup Python Backend
################################################################################
print_info "Setting up Python backend..."

cd "$SCRIPT_DIR/backend"

# Use system Python packages (already installed globally)
print_success "Using system-wide Python packages"

cd "$SCRIPT_DIR"

################################################################################
# Setup Frontend (Optional)
################################################################################
if command -v node &> /dev/null && command -v npm &> /dev/null; then
    print_info "Setting up frontend..."
    
    cd "$SCRIPT_DIR/frontend"
    
    # Install dependencies if node_modules doesn't exist
    if [ ! -d "node_modules" ]; then
        print_info "Installing frontend dependencies (this may take several minutes)..."
        npm install --legacy-peer-deps 2>/dev/null || npm install
        print_success "Frontend dependencies installed"
    else
        print_info "Frontend dependencies already installed"
    fi
    
    cd "$SCRIPT_DIR"
else
    print_warning "Skipping frontend setup (Node.js/npm not available)"
fi

################################################################################
# Start Services
################################################################################
print_info ""
print_info "================================================================================"
print_info "Starting Services"
print_info "================================================================================"
print_info ""

# Function to start PostgreSQL (if not running)
start_postgres() {
    if command -v pg_ctl &> /dev/null; then
        PG_DATA="$SCRIPT_DIR/data/postgres"
        if [ ! -d "$PG_DATA" ]; then
            print_info "Initializing PostgreSQL database..."
            initdb -D "$PG_DATA" 2>/dev/null || true
        fi
        
        # Check if PostgreSQL is running
        if ! pg_isready -h localhost -p 5432 &> /dev/null; then
            print_info "Starting PostgreSQL..."
            pg_ctl -D "$PG_DATA" -l "$SCRIPT_DIR/logs/postgres.log" start 2>/dev/null || true
            sleep 3
        fi
    else
        print_warning "PostgreSQL server tools not found."
        print_info "Please ensure PostgreSQL is installed and running on localhost:5432"
        print_info "Create database manually:"
        print_info "  createdb leadgen"
        print_info "  psql -c \"CREATE USER leadgen_user WITH PASSWORD 'LeadGen123!SecurePassword';\""
        print_info "  psql -c \"GRANT ALL PRIVILEGES ON DATABASE leadgen TO leadgen_user;\""
    fi
}

# Function to start Redis (if not running)
start_redis() {
    if command -v redis-server &> /dev/null; then
        # Check if Redis is running
        if ! redis-cli ping &> /dev/null; then
            print_info "Starting Redis..."
            redis-server --daemonize yes --dir "$SCRIPT_DIR/data/redis" --logfile "$SCRIPT_DIR/logs/redis.log" 2>/dev/null || true
            sleep 2
        fi
    else
        print_warning "Redis server not found."
        print_info "Please ensure Redis is installed and running on localhost:6379"
    fi
}

# Check/start services
print_info "Checking database and cache services..."

# Try to start PostgreSQL
start_postgres

# Try to start Redis
start_redis

# Wait for services to be ready
print_info "Waiting for services to be ready..."
sleep 3

# Verify PostgreSQL connection
if command -v psql &> /dev/null; then
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" &> /dev/null; then
        print_success "PostgreSQL connection verified"
    else
        print_warning "Could not connect to PostgreSQL. Please ensure it's running and database exists."
        print_info "Database: $POSTGRES_DB"
        print_info "User: $POSTGRES_USER"
        print_info "Host: localhost:$POSTGRES_PORT"
    fi
fi

# Verify Redis connection
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        print_success "Redis connection verified"
    else
        print_warning "Could not connect to Redis. Please ensure it's running."
        print_info "Host: localhost:$REDIS_PORT"
    fi
fi

################################################################################
# Run Database Migrations
################################################################################
print_info ""
print_info "Running database migrations..."

cd "$SCRIPT_DIR/backend"

# Set environment variables for migration
export PYTHONPATH="$SCRIPT_DIR/backend:$PYTHONPATH"

# Run Alembic migrations or create tables
python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR/backend')
from app.core.database import engine, Base
from app.models.schemas import User, Batch, Lead, ProcessingLog
Base.metadata.create_all(bind=engine)
print('Database tables created successfully')
" 2>&1 || print_warning "Could not create database tables automatically"

# Create default admin user
python3 -c "
import sys
import os
sys.path.insert(0, '$SCRIPT_DIR/backend')

from app.core.database import async_session_maker, engine, Base
from app.core.security import get_password_hash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

async def create_admin():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session_maker() as session:
        from app.models.schemas import User
        result = await session.execute(select(User).where(User.email == 'admin@leadgen.local'))
        existing = result.scalar_one_or_none()
        if not existing:
            from datetime import datetime
            admin = User(
                email='admin@leadgen.local',
                hashed_password=get_password_hash('Admin123!ChangeMe'),
                full_name='System Administrator',
                is_active=True,
                is_superuser=True,
                created_at=datetime.utcnow()
            )
            session.add(admin)
            await session.commit()
            print('Default admin user created')
        else:
            print('Admin user already exists')

asyncio.run(create_admin())
" 2>&1 || print_info "Admin user setup will occur on first API start"

cd "$SCRIPT_DIR"

################################################################################
# Start Backend Server
################################################################################
print_info ""
print_info "Starting backend server..."

cd "$SCRIPT_DIR/backend"

export PYTHONPATH="$SCRIPT_DIR/backend:$PYTHONPATH"

# Start backend in background
nohup python3 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    > "$SCRIPT_DIR/logs/backend.log" 2>&1 &

BACKEND_PID=$!
echo $BACKEND_PID > "$SCRIPT_DIR/logs/backend.pid"

print_success "Backend server started (PID: $BACKEND_PID)"

# Wait for backend to be ready
print_info "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/health &> /dev/null; then
        print_success "Backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_warning "Backend is starting but may need more time"
    fi
    sleep 1
done

################################################################################
# Start Celery Worker
################################################################################
print_info "Starting Celery worker..."

cd "$SCRIPT_DIR/backend"

export PYTHONPATH="$SCRIPT_DIR/backend:$PYTHONPATH"

# Start worker in background (with SQLite-compatible settings)
nohup python3 -m celery -A app.workers.celery_app worker \
    --loglevel=info \
    --concurrency=${WORKER_CONCURRENCY:-2} \
    --pool=solo \
    > "$SCRIPT_DIR/logs/worker.log" 2>&1 &

WORKER_PID=$!
echo $WORKER_PID > "$SCRIPT_DIR/logs/worker.pid"

print_success "Celery worker started (PID: $WORKER_PID)"

################################################################################
# Start Frontend (if available)
################################################################################
if [ -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    print_info "Starting frontend development server..."
    
    cd "$SCRIPT_DIR/frontend"
    
    # Start Next.js in background
    nohup npm run dev \
        > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &
    
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$SCRIPT_DIR/logs/frontend.pid"
    
    print_success "Frontend server started (PID: $FRONTEND_PID)"
    
    # Wait for frontend to be ready
    print_info "Waiting for frontend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:3000 &> /dev/null; then
            print_success "Frontend is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "Frontend is starting but may need more time"
        fi
        sleep 1
    done
else
    print_warning "Skipping frontend (not installed)"
fi

cd "$SCRIPT_DIR"

################################################################################
# Display Access Information
################################################################################
print_info ""
echo "================================================================================"
print_success "Platform Started Successfully!"
echo "================================================================================"
print_info ""
print_info "Access the platform at:"
print_info "  Frontend:  http://localhost:3000"
print_info "  API:       http://localhost:8000"
print_info "  API Docs:  http://localhost:8000/docs"
print_info ""
print_info "Default Admin Credentials:"
print_info "  Email:    admin@leadgen.local"
print_info "  Password: Admin123!ChangeMe"
print_info ""
print_info "Service Status:"
print_info "  Backend:   Running (PID: $BACKEND_PID)"
print_info "  Worker:    Running (PID: $WORKER_PID)"
if [ -n "$FRONTEND_PID" ]; then
    print_info "  Frontend:  Running (PID: $FRONTEND_PID)"
fi
print_info ""
print_info "Log Files:"
print_info "  Backend:   $SCRIPT_DIR/logs/backend.log"
print_info "  Worker:    $SCRIPT_DIR/logs/worker.log"
if [ -n "$FRONTEND_PID" ]; then
    print_info "  Frontend:  $SCRIPT_DIR/logs/frontend.log"
fi
print_info ""
print_info "To stop all services, run:"
print_info "  ./stop.sh"
print_info ""
print_info "To view logs in real-time:"
print_info "  tail -f $SCRIPT_DIR/logs/backend.log"
print_info "  tail -f $SCRIPT_DIR/logs/worker.log"
echo "================================================================================"
print_info ""
print_warning "NOTE: If you encounter database/connection errors, please ensure:"
print_warning "  1. PostgreSQL is running on localhost:5432"
print_warning "  2. Redis is running on localhost:6379"
print_warning "  3. Database 'leadgen' exists with proper user permissions"
print_info ""

# Keep script running to show logs option
read -p "Press Ctrl+C to exit (services will continue running in background)..." 
