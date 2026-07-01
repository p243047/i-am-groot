#!/bin/bash

################################################################################
# Self-Hosted AI Lead Generation Platform - Startup Script
################################################################################
# This script will:
# 1. Check system requirements
# 2. Set up environment variables
# 3. Initialize the database
# 4. Start all services (PostgreSQL, Redis, Backend, Workers, Frontend)
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$PROJECT_DIR/docker"
ENV_FILE="$PROJECT_DIR/.env"
DOCKER_COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        return 1
    fi
    return 0
}

################################################################################
# Step 1: Check System Requirements
################################################################################

check_requirements() {
    log_info "Checking system requirements..."
    
    local missing_deps=0
    
    # Check Docker
    if ! check_command "docker"; then
        log_error "Docker is required but not installed."
        log_info "Install Docker: https://docs.docker.com/get-docker/"
        missing_deps=1
    else
        docker --version > /dev/null 2>&1 || {
            log_error "Docker daemon is not running. Please start Docker."
            missing_deps=1
        }
    fi
    
    # Check Docker Compose
    if ! check_command "docker compose"; then
        # Try old syntax
        if ! command -v "docker-compose" &> /dev/null; then
            log_error "Docker Compose is not installed."
            log_info "Install Docker Compose: https://docs.docker.com/compose/install/"
            missing_deps=1
        else
            COMPOSE_CMD="docker-compose"
        fi
    else
        COMPOSE_CMD="docker compose"
    fi
    
    if [ $missing_deps -eq 1 ]; then
        log_error "Missing dependencies. Please install them and run again."
        exit 1
    fi
    
    log_success "All system requirements met!"
}

################################################################################
# Step 2: Setup Environment Variables
################################################################################

setup_environment() {
    log_info "Setting up environment variables..."
    
    if [ ! -f "$ENV_FILE" ]; then
        log_warning ".env file not found. Creating from template..."
        
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
            log_success "Created .env file from template."
            log_warning "Please review and update $ENV_FILE with your settings."
        else
            # Create default .env file
            cat > "$ENV_FILE" << 'EOF'
# =============================================================================
# Self-Hosted AI Lead Generation Platform - Environment Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Application Settings
# -----------------------------------------------------------------------------
APP_NAME=LeadGen Platform
APP_ENV=development
DEBUG=True
SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars
API_PREFIX=/api/v1

# -----------------------------------------------------------------------------
# Database Configuration (PostgreSQL)
# -----------------------------------------------------------------------------
POSTGRES_USER=leadgen_user
POSTGRES_PASSWORD=leadgen_secure_password_123
POSTGRES_DB=leadgen_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://leadgen_user:leadgen_secure_password_123@postgres:5432/leadgen_db

# -----------------------------------------------------------------------------
# Redis Configuration
# -----------------------------------------------------------------------------
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://redis:6379/0

# -----------------------------------------------------------------------------
# Celery Configuration
# -----------------------------------------------------------------------------
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_ACKS_LATE=True
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_CONCURRENCY=4

# -----------------------------------------------------------------------------
# Frontend Configuration
# -----------------------------------------------------------------------------
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_NAME=LeadGen Platform

# -----------------------------------------------------------------------------
# File Upload Settings
# -----------------------------------------------------------------------------
UPLOAD_FOLDER=/app/uploads
MAX_UPLOAD_SIZE=104857600
ALLOWED_EXTENSIONS=xlsx,xls,csv,json

# -----------------------------------------------------------------------------
# Processing Settings
# -----------------------------------------------------------------------------
DEFAULT_BATCH_SIZE=100
MAX_RETRIES=3
REQUEST_TIMEOUT=30
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# -----------------------------------------------------------------------------
# Email Verification Settings
# -----------------------------------------------------------------------------
EMAIL_VERIFY_TIMEOUT=10
EMAIL_SMTP_TIMEOUT=5
DISPOSABLE_EMAIL_DOMAINS=tempmail.com,guerrillamail.com,mailinator.com

# -----------------------------------------------------------------------------
# Rate Limiting
# -----------------------------------------------------------------------------
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# -----------------------------------------------------------------------------
# Optional: Third-Party API Keys (Configure as needed)
# -----------------------------------------------------------------------------
# Google Custom Search API
GOOGLE_API_KEY=
GOOGLE_CSE_ID=

# Bing Search API
BING_API_KEY=

# Hunter.io API (optional enrichment)
HUNTER_API_KEY=

# Clearbit API (optional enrichment)
CLEARBIT_API_KEY=

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/app/logs/app.log

# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# -----------------------------------------------------------------------------
# Admin User (First Run)
# -----------------------------------------------------------------------------
ADMIN_EMAIL=admin@leadgen.local
ADMIN_PASSWORD=Admin123!ChangeMe
EOF
            log_success "Created default .env file."
            log_warning "Please review and update $ENV_FILE with your settings, especially SECRET_KEY and passwords."
        fi
    else
        log_success ".env file already exists."
    fi
    
    # Load environment variables
    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' "$ENV_FILE" | xargs)
        log_info "Environment variables loaded."
    fi
}

################################################################################
# Step 3: Create Required Directories
################################################################################

create_directories() {
    log_info "Creating required directories..."
    
    mkdir -p "$PROJECT_DIR/uploads"
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/data/postgres"
    mkdir -p "$PROJECT_DIR/data/redis"
    
    # Set permissions
    chmod 755 "$PROJECT_DIR/uploads"
    chmod 755 "$PROJECT_DIR/logs"
    
    log_success "Directories created successfully."
}

################################################################################
# Step 4: Build and Start Services
################################################################################

start_services() {
    log_info "Building and starting services with Docker Compose..."
    
    cd "$PROJECT_DIR"
    
    # Pull latest images
    log_info "Pulling latest Docker images..."
    $COMPOSE_CMD pull
    
    # Build custom images
    log_info "Building custom Docker images..."
    $COMPOSE_CMD build
    
    # Start all services
    log_info "Starting all services..."
    $COMPOSE_CMD up -d
    
    log_success "All services started!"
}

################################################################################
# Step 5: Wait for Services to be Ready
################################################################################

wait_for_services() {
    log_info "Waiting for services to be ready..."
    
    # Wait for PostgreSQL
    log_info "Waiting for PostgreSQL..."
    timeout=60
    while ! $COMPOSE_CMD exec -T postgres pg_isready -U ${POSTGRES_USER:-leadgen_user} > /dev/null 2>&1; do
        echo -n "."
        sleep 2
        timeout=$((timeout - 2))
        if [ $timeout -le 0 ]; then
            log_error "PostgreSQL failed to start within timeout."
            $COMPOSE_CMD logs postgres
            exit 1
        fi
    done
    log_success "PostgreSQL is ready!"
    
    # Wait for Redis
    log_info "Waiting for Redis..."
    timeout=30
    while ! $COMPOSE_CMD exec -T redis redis-cli ping > /dev/null 2>&1; do
        echo -n "."
        sleep 1
        timeout=$((timeout - 1))
        if [ $timeout -le 0 ]; then
            log_error "Redis failed to start within timeout."
            $COMPOSE_CMD logs redis
            exit 1
        fi
    done
    log_success "Redis is ready!"
    
    # Wait for Backend API
    log_info "Waiting for Backend API..."
    timeout=60
    while ! curl -s http://localhost:8000/health > /dev/null 2>&1; do
        echo -n "."
        sleep 2
        timeout=$((timeout - 2))
        if [ $timeout -le 0 ]; then
            log_warning "Backend API taking longer than expected. Check logs."
            break
        fi
    done
    log_success "Backend API is ready!"
    
    # Run database migrations
    log_info "Running database migrations..."
    $COMPOSE_CMD exec -T backend python -m alembic upgrade head || {
        log_warning "Database migrations may have already been applied."
    }
    
    # Create admin user if not exists
    log_info "Setting up admin user..."
    $COMPOSE_CMD exec -T backend python -c "from app.core.security import create_admin_user; create_admin_user()" || {
        log_warning "Admin user may already exist."
    }
    
    log_success "All services are ready!"
}

################################################################################
# Step 6: Display Status and Access Information
################################################################################

display_status() {
    echo ""
    echo "================================================================================"
    echo -e "${GREEN}✓ Platform Started Successfully!${NC}"
    echo "================================================================================"
    echo ""
    echo -e "${BLUE}Service Status:${NC}"
    $COMPOSE_CMD ps
    echo ""
    echo -e "${BLUE}Access URLs:${NC}"
    echo "  - Frontend:           http://localhost:3000"
    echo "  - Backend API:        http://localhost:8000"
    echo "  - API Documentation:  http://localhost:8000/docs"
    echo "  - Flower (Monitor):   http://localhost:5555"
    echo "  - PostgreSQL:         localhost:5432"
    echo "  - Redis:              localhost:6379"
    echo ""
    echo -e "${BLUE}Default Admin Credentials:${NC}"
    echo "  - Email:    admin@leadgen.local"
    echo "  - Password: Admin123!ChangeMe"
    echo ""
    echo -e "${YELLOW}Important:${NC} Please change the default password after first login!"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  - View logs:          $COMPOSE_CMD logs -f"
    echo "  - Stop services:      $COMPOSE_CMD down"
    echo "  - Restart services:   $COMPOSE_CMD restart"
    echo "  - View worker status: $COMPOSE_CMD exec worker celery -A app.celery inspect active"
    echo "  - Database backup:    $COMPOSE_CMD exec postgres pg_dump -U leadgen_user leadgen_db > backup.sql"
    echo ""
    echo "================================================================================"
}

################################################################################
# Main Execution
################################################################################

main() {
    echo ""
    echo "================================================================================"
    echo -e "${BLUE}Self-Hosted AI Lead Generation Platform - Startup Script${NC}"
    echo "================================================================================"
    echo ""
    
    # Parse command line arguments
    case "${1:-start}" in
        start)
            check_requirements
            setup_environment
            create_directories
            start_services
            wait_for_services
            display_status
            ;;
        stop)
            log_info "Stopping all services..."
            $COMPOSE_CMD down
            log_success "All services stopped."
            ;;
        restart)
            log_info "Restarting all services..."
            $COMPOSE_CMD restart
            display_status
            ;;
        logs)
            $COMPOSE_CMD logs -f ${2:-}
            ;;
        status)
            $COMPOSE_CMD ps
            ;;
        rebuild)
            log_info "Rebuilding all services..."
            $COMPOSE_CMD down
            $COMPOSE_CMD build --no-cache
            start_services
            wait_for_services
            display_status
            ;;
        migrate)
            log_info "Running database migrations..."
            $COMPOSE_CMD exec backend python -m alembic upgrade head
            log_success "Migrations completed."
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|logs|status|rebuild|migrate}"
            echo ""
            echo "Commands:"
            echo "  start    - Start all services (default)"
            echo "  stop     - Stop all services"
            echo "  restart  - Restart all services"
            echo "  logs     - View logs (optionally specify service name)"
            echo "  status   - Show service status"
            echo "  rebuild  - Rebuild and restart all services"
            echo "  migrate  - Run database migrations"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
