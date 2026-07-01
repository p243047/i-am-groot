# LeadGen AI Platform

A production-ready self-hosted AI Lead Generation Platform that enriches business data from uploaded Excel files. Works like Hunter.io, Apollo.io, Snov.io, and Clearbit, but operates primarily by searching publicly available business information.

## Features

- **Excel/CSV Upload**: Upload business lists for enrichment
- **Multi-source Enrichment**: Searches official websites, Google, LinkedIn, Facebook, and more
- **Email Discovery**: Finds and verifies business emails using multiple strategies
- **Lead Scoring**: AI-powered lead quality scoring (Hot/Warm/Cold)
- **Service Recommendations**: Generates actionable recommendations for each lead
- **Batch Processing**: Async processing with pause/resume/cancel support
- **Export Options**: Export to Excel, CSV, or JSON
- **Real-time Progress**: Live progress tracking and ETA calculation
- **Comprehensive Logging**: Full audit trail of all processing actions

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Next.js   │────▶│   FastAPI   │────▶│  PostgreSQL │
│  Frontend   │     │   Backend   │     │  Database   │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │    Redis    │
                    │   Broker    │
                    └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   Celery    │
                    │   Workers   │
                    └─────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local development)

### Using Docker Compose (Recommended)

```bash
cd docker

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Access the application
# API: http://localhost:8000
# Flower (Celery monitoring): http://localhost:5555
```

### Local Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Set up environment variables
cp .env.example .env
# Edit .env with your settings

# Run database migrations
# (Alembic setup required)

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker in another terminal
celery -A app.workers.celery_app worker --loglevel=info
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login (returns JWT tokens)
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user profile

### Files
- `POST /api/v1/files/upload` - Upload Excel/CSV file
- `POST /api/v1/files/export/{batch_id}` - Export batch results

### Batches
- `GET /api/v1/batches/` - List all batches
- `GET /api/v1/batches/{id}` - Get batch details
- `GET /api/v1/batches/{id}/progress` - Get processing progress
- `POST /api/v1/batches/{id}/start` - Start processing
- `POST /api/v1/batches/{id}/pause` - Pause processing
- `POST /api/v1/batches/{id}/cancel` - Cancel processing
- `DELETE /api/v1/batches/{id}` - Delete batch

### Leads
- `GET /api/v1/leads/batch/{batch_id}` - List leads with filters
- `GET /api/v1/leads/{id}` - Get lead details
- `POST /api/v1/leads/{id}/retry` - Retry failed lead

### Health
- `GET /api/v1/health/` - System health check
- `GET /api/v1/health/queue` - Celery queue status

## Configuration

Key environment variables in `.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/leadgen_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=jwt-secret-key

# External APIs (optional)
GOOGLE_API_KEY=
GOOGLE_CSE_ID=
BING_API_KEY=
```

## Data Collection Sources

The platform searches these sources for business information:

1. **Official Website** (highest confidence)
   - Homepage, Contact, About pages
   - Team/Staff pages
   - Footer/Header sections

2. **Search Engines**
   - Google Search
   - Bing Search
   - DuckDuckGo

3. **Business Directories**
   - Google Maps / Google Business Profile
   - LinkedIn Company Pages
   - Facebook Pages
   - Yellow Pages
   - Yelp
   - BBB

4. **Social Media**
   - LinkedIn
   - Facebook
   - Instagram
   - Twitter/X
   - YouTube
   - TikTok

## Email Discovery Strategy

### Stage 1: Website Scraping
- Scrape all pages for email addresses
- Check contact, about, team pages
- Extract from mailto links

### Stage 2: Public Sources
- Search Google/Bing for emails
- Check business directories
- Social media profiles

### Stage 3: Pattern Generation
Only if domain is known:
- info@domain.com
- contact@domain.com
- sales@domain.com
- firstname.lastname@domain.com

All emails are verified before inclusion.

## Email Verification

- Syntax validation
- MX record check
- Disposable domain detection
- Role account detection
- SMTP verification (basic)

## Lead Scoring

Scores leads 0-100 based on:
- Website existence (+10)
- Email found (+20)
- Social media presence (+10-20)
- Phone number (+10)
- Complete address (+5)
- Industry/category (+5)
- Employee/revenue data (+10)

Quality levels:
- **Hot**: Score >= 70
- **Warm**: Score 40-69
- **Cold**: Score < 40

## Service Recommendations

Automatically generates recommendations:
- Website Development
- SSL Installation
- SEO Improvement
- Social Media Setup
- Google Analytics
- Professional Email
- Local SEO

## Project Structure

```
backend/
├── app/
│   ├── api/           # REST API endpoints
│   ├── core/          # Config, DB, security
│   ├── models/        # SQLAlchemy models
│   ├── services/      # Business logic
│   ├── utils/         # Helper functions
│   ├── workers/       # Celery tasks
│   └── main.py        # FastAPI app
├── tests/             # Test files
├── requirements.txt   # Dependencies
└── .env.example       # Environment template

docker/
├── Dockerfile.backend
└── docker-compose.yml

frontend/              # Next.js frontend (TODO)
docs/                  # Documentation
```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_api.py
```

## Security Considerations

- JWT-based authentication
- Password hashing with bcrypt
- Rate limiting on API endpoints
- Secure file upload validation
- CORS configuration
- Environment variable protection

## Legal Compliance

This platform only collects:
- Publicly available business information
- Data from APIs configured by the user
- Information respecting terms of service

Users are responsible for:
- Complying with data protection laws (GDPR, CCPA)
- Respecting source website terms of service
- Proper use of collected data

## License

MIT License - See LICENSE file for details.

## Support

For issues and feature requests, please open a GitHub issue.
