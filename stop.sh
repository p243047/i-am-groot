#!/bin/bash

################################################################################
# Self-Hosted AI Lead Generation Platform - Stop Script
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
echo "Self-Hosted AI Lead Generation Platform - Stop Script"
echo "================================================================================"
echo ""

# Function to print colored messages
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Stop services by PID
stop_service() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if kill -0 "$PID" 2>/dev/null; then
            print_info "Stopping $service_name (PID: $PID)..."
            kill "$PID" 2>/dev/null || true
            sleep 2
            # Force kill if still running
            if kill -0 "$PID" 2>/dev/null; then
                kill -9 "$PID" 2>/dev/null || true
            fi
            rm -f "$pid_file"
            print_success "$service_name stopped"
        else
            print_warning "$service_name not running (stale PID file removed)"
            rm -f "$pid_file"
        fi
    else
        print_warning "$service_name PID file not found"
    fi
}

# Stop frontend
stop_service "Frontend" "$SCRIPT_DIR/logs/frontend.pid"

# Stop Celery worker
stop_service "Celery Worker" "$SCRIPT_DIR/logs/worker.pid"

# Stop Backend
stop_service "Backend" "$SCRIPT_DIR/logs/backend.pid"

# Try to stop Redis if we started it
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        # Check if Redis was started by us (in our data directory)
        if [ -f "$SCRIPT_DIR/logs/redis.pid" ]; then
            REDIS_PID=$(cat "$SCRIPT_DIR/logs/redis.pid")
            if kill -0 "$REDIS_PID" 2>/dev/null; then
                print_info "Stopping Redis..."
                redis-cli shutdown 2>/dev/null || true
                sleep 2
                rm -f "$SCRIPT_DIR/logs/redis.pid"
                print_success "Redis stopped"
            fi
        else
            print_warning "Redis may have been started manually (not stopping)"
        fi
    fi
fi

# Try to stop PostgreSQL if we started it
if command -v pg_ctl &> /dev/null; then
    PG_DATA="$SCRIPT_DIR/data/postgres"
    if [ -d "$PG_DATA" ]; then
        if pg_isready -h localhost -p 5432 &> /dev/null; then
            # Check if PostgreSQL was started by us
            if [ -f "$SCRIPT_DIR/logs/postgres.pid" ]; then
                print_info "Stopping PostgreSQL..."
                pg_ctl -D "$PG_DATA" stop 2>/dev/null || true
                sleep 2
                rm -f "$SCRIPT_DIR/logs/postgres.pid"
                print_success "PostgreSQL stopped"
            else
                print_warning "PostgreSQL may have been started manually (not stopping)"
            fi
        fi
    fi
fi

# Kill any remaining processes on our ports
print_info "Checking for processes on ports 8000, 3000, and 5555..."

for port in 8000 3000 5555; do
    PID=$(lsof -t -i:$port 2>/dev/null || true)
    if [ -n "$PID" ]; then
        print_warning "Found process $PID on port $port, terminating..."
        kill $PID 2>/dev/null || true
    fi
done

sleep 1

print_info ""
echo "================================================================================"
print_success "All services stopped!"
echo "================================================================================"
print_info ""
print_info "To start the platform again, run:"
print_info "  ./run-native.sh"
print_info ""
