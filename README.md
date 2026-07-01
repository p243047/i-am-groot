# Self-Hosted AI Lead Generation Platform

A production-ready, self-hosted lead generation platform that enriches business data from uploaded Excel files. Works like Hunter.io, Apollo.io, and Snov.io but runs on your own infrastructure.

## Quick Start

### Prerequisites

- **Docker** (v20.10+)
- **Docker Compose** (v2.0+)
- At least 4GB RAM recommended
- 10GB free disk space

### Running the Platform

#### Option 1: Using the run.sh script (Recommended)

```bash
# Make the script executable (already done)
chmod +x run.sh

# Start all services
./run.sh start

# Or simply run (start is default)
./run.sh
```

#### Option 2: Manual Docker Compose

```bash
cd docker

# Create .env file if not exists
cp ../.env.example ../.env  # Edit with your settings

# Start all services
docker compose up -d

# View logs
docker compose logs -f
```

### Access URLs

Once started, access the platform at:

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Web UI |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger/OpenAPI docs |
| Flower | http://localhost:5555 | Celery task monitoring |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache/Broker |

### Default Admin Credentials

```
Email: admin@leadgen.local
Password: Admin123!ChangeMe
```

⚠️ **Important:** Change the default password after first login!

## run.sh Commands

The `run.sh` script provides convenient commands:

```bash
./run.sh start      # Start all services (default)
./run.sh stop       # Stop all services
./run.sh restart    # Restart all services
./run.sh status     # Show service status
./run.sh logs       # View all logs
./run.sh logs backend   # View specific service logs
./run.sh rebuild    # Rebuild and restart (use after code changes)
./run.sh migrate    # Run database migrations
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key variables to configure:

```env
# Security (CHANGE THESE IN PRODUCTION!)
SECRET_KEY=your-super-secret-key-min-32-characters
JWT_SECRET_KEY=your-jwt-secret-key-min-32-characters

# Database
POSTGRES_USER=leadgen_user
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=leadgen_db

# Admin User
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=YourSecurePassword123!

# Optional: Third-party APIs
GOOGLE_API_KEY=your-google-api-key
GOOGLE_CSE_ID=your-custom-search-engine-id
BING_API_KEY=your-bing-api-key
HUNTER_API_KEY=your-hunter-api-key
```

## Project Structure

```
.
├── run.sh                 # Main startup script
├── .env                   # Environment configuration
├── .env.example           # Environment template
├── docker/
│   ├── docker-compose.yml # Service orchestration
│   ├── Dockerfile.backend # Backend container
│   └── Dockerfile.frontend# Frontend container
├── backend/
│   ├── app/               # FastAPI application
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Core utilities
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   ├── workers/       # Celery tasks
│   │   └── main.py        # Application entry
│   ├── tests/             # Test suite
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/               # Next.js application
│   │   ├── app/           # App router pages
│   │   ├── components/    # React components
│   │   ├── lib/           # Utilities
│   │   └── stores/        # State management
│   └── package.json       # Node dependencies
├── uploads/               # Uploaded files
├── logs/                  # Application logs
└── data/
    ├── postgres/          # Database volume
    └── redis/             # Redis volume
```

## Features

### Core Capabilities

- ✅ **Excel/CSV Upload** - Process business lists in bulk
- ✅ **Multi-Source Search** - 20+ public data sources
- ✅ **Email Discovery** - 3-stage email finding engine
- ✅ **Email Verification** - Syntax, MX, SMTP validation
- ✅ **Lead Scoring** - AI-powered hot/warm/cold scoring
- ✅ **Service Recommendations** - Automated suggestions
- ✅ **Batch Processing** - Async processing with Celery
- ✅ **Export Options** - Excel, CSV, JSON formats

### Search Sources

Official Website, Google, Bing, Google Maps, LinkedIn, Facebook, Instagram, X/Twitter, Yellow Pages, Yelp, BBB, Chamber of Commerce, Government Registries, Industry Directories, OpenStreetMap, DuckDuckGo, and more.

### Data Enrichment

Collects: Company info, contacts, social media, website tech stack, emails (verified), phone numbers, addresses, lead scores, confidence scores, and AI recommendations.

## API Usage

### Authentication

```bash
# Get access token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@leadgen.local&password=Admin123!ChangeMe"
```

### Upload and Process File

```bash
# Upload Excel file
curl -X POST http://localhost:8000/api/v1/batches/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@businesses.xlsx" \
  -F "name=My Lead List"

# Start processing
curl -X POST http://localhost:8000/api/v1/batches/{batch_id}/process \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Check Progress

```bash
curl http://localhost:8000/api/v1/batches/{batch_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Export Results

```bash
curl http://localhost:8000/api/v1/batches/{batch_id}/export?format=xlsx \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output results.xlsx
```

Full API documentation available at: http://localhost:8000/docs

## Monitoring

### View Logs

```bash
# All services
./run.sh logs

# Specific service
./run.sh logs backend
./run.sh logs worker
./run.sh logs frontend
```

### Celery Task Monitoring

Access Flower dashboard at http://localhost:5555 to monitor:
- Active tasks
- Task history
- Worker status
- Task statistics

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it leadgen-postgres psql -U leadgen_user -d leadgen_db

# Backup database
docker exec leadgen-postgres pg_dump -U leadgen_user leadgen_db > backup.sql

# Restore database
docker exec -i leadgen-postgres psql -U leadgen_user -d leadgen_db < backup.sql
```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker ps

# View service logs
./run.sh logs

# Rebuild containers
./run.sh rebuild
```

### Port Conflicts

If ports 3000, 5432, 6379, or 8000 are in use, edit `docker/docker-compose.yml` and change the port mappings:

```yaml
ports:
  - "3001:3000"  # Change host port
```

### Database Issues

```bash
# Reset database (WARNING: Deletes all data!)
docker compose down -v
./run.sh start
```

### Memory Issues

Reduce worker concurrency in `.env`:

```env
CELERY_CONCURRENCY=2
```

## Development

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

## Testing

```bash
# Run backend tests
cd backend
pytest

# Run frontend tests
cd frontend
npm test
```

## Security Considerations

1. **Change default credentials** immediately
2. **Use strong SECRET_KEY** values (min 32 characters)
3. **Enable HTTPS** in production (use Traefik or NGINX)
4. **Restrict CORS origins** in production
5. **Regular backups** of database and uploads
6. **Keep Docker images updated**
7. **Use firewall rules** to restrict database access

## Production Deployment

For production deployment:

1. Use strong, unique passwords and secret keys
2. Enable HTTPS with SSL certificates
3. Configure proper backup strategy
4. Set up monitoring and alerting
5. Use environment-specific configurations
6. Consider using Kubernetes for scaling
7. Implement proper logging aggregation

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please open an issue on GitHub.

---

Built with ❤️ using FastAPI, Next.js, PostgreSQL, Redis, and Celery
