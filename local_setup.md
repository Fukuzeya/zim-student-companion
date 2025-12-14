# 🚀 Zim Student Companion - Local Setup Guide

Complete step-by-step guide to run the application on your local machine.

---

## 📋 Prerequisites

Before starting, ensure you have the following installed:

| Software | Version | Download Link |
|----------|---------|---------------|
| Python | 3.11+ | https://python.org |
| Docker & Docker Compose | Latest | https://docker.com |
| Git | Latest | https://git-scm.com |
| Node.js (for Angular) | 18+ | https://nodejs.org |
| ngrok (for WhatsApp testing) | Latest | https://ngrok.com |

### Required API Keys

You'll need to obtain:
1. **Google Gemini API Key** - https://makersuite.google.com/app/apikey (Free tier available)
2. **WhatsApp Business API** - https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
3. **Paynow Zimbabwe** - https://www.paynow.co.zw/developers (for payments)

---

## 📁 Step 1: Clone & Setup Project Structure

```bash
# Create project directory
mkdir zim-student-companion
cd zim-student-companion

# Create the directory structure
mkdir -p backend/app/{api/v1,models,schemas,services/{rag,whatsapp,practice,gamification,payments,notifications,analytics},core,tasks}
mkdir -p backend/{alembic/versions,scripts,tests}
mkdir -p documents/{syllabi,past_papers,marking_schemes,textbooks,teacher_notes}
mkdir -p dashboard
mkdir -p nginx/ssl

# Initialize git
git init
```

---

## 📝 Step 2: Create Environment File

Create `.env` file in the project root:

```bash
# Create .env file
cat > .env << 'EOF'
# ===========================================
# ZIM STUDENT COMPANION - ENVIRONMENT CONFIG
# ===========================================

# Application
APP_NAME="Zim Student Companion"
DEBUG=true
SECRET_KEY=your-super-secret-key-change-this-in-production-use-openssl-rand-hex-32

# Database
DATABASE_URL=postgresql://zsc_user:zsc_password@localhost:5432/zsc_db
REDIS_URL=redis://localhost:6379/0

# Gemini AI (Get from https://makersuite.google.com/app/apikey)
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_EMBEDDING_MODEL=text-embedding-004

# Qdrant Vector Store
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=zimsec_documents

# WhatsApp Business API (Get from Meta Developer Portal)
WHATSAPP_TOKEN=your-whatsapp-access-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_VERIFY_TOKEN=your-custom-verify-token-any-string
WHATSAPP_BUSINESS_ACCOUNT_ID=your-business-account-id

# Paynow Zimbabwe (Get from Paynow Developer Portal)
PAYNOW_INTEGRATION_ID=your-paynow-integration-id
PAYNOW_INTEGRATION_KEY=your-paynow-integration-key
PAYNOW_RESULT_URL=https://your-ngrok-url.ngrok.io/api/v1/payments/webhook/paynow
PAYNOW_RETURN_URL=https://your-domain.com/payment/success

# JWT Settings
JWT_SECRET_KEY=your-jwt-secret-key-also-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate Limits
FREE_DAILY_QUESTIONS=5
BASIC_DAILY_QUESTIONS=50
PREMIUM_DAILY_QUESTIONS=1000
EOF
```

---

## 🐳 Step 3: Start Infrastructure with Docker

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: zsc_postgres
    environment:
      POSTGRES_USER: zsc_user
      POSTGRES_PASSWORD: zsc_password
      POSTGRES_DB: zsc_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U zsc_user -d zsc_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: zsc_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    container_name: zsc_qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      QDRANT__LOG_LEVEL: INFO

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
```

Start the services:

```bash
# Start all infrastructure services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check logs if needed
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f qdrant
```

---

## 🐍 Step 4: Setup Python Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Create requirements.txt
cat > requirements.txt << 'EOF'
# FastAPI & ASGI
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Database
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
alembic==1.13.1

# Redis
redis==5.0.1

# Validation
pydantic==2.5.3
pydantic-settings==2.1.0

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# HTTP Client
httpx==0.26.0

# AI/ML
google-generativeai==0.3.2

# Vector Store
qdrant-client==1.7.0

# Document Processing
pymupdf==1.23.8
python-docx==1.1.0

# Background Tasks
celery==5.3.6

# Payments
paynow==1.0.2

# Utilities
aiofiles==23.2.1
python-dateutil==2.8.2

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
httpx==0.26.0
aiosqlite==0.19.0
EOF

# Install dependencies
pip install -r requirements.txt
```

---

## 📂 Step 5: Create Application Files

Copy all the code files from the artifacts I provided earlier into the appropriate directories:

```bash
# Backend structure should look like:
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # Main FastAPI app
│   ├── config.py            # Settings
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependencies
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py    # Main router
│   │       ├── auth.py
│   │       ├── students.py
│   │       ├── parents.py
│   │       ├── practice.py
│   │       ├── competitions.py
│   │       ├── payments.py
│   │       ├── admin.py
│   │       └── webhooks.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── ... (all model files)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── ... (all schema files)
│   ├── services/
│   │   ├── rag/
│   │   ├── whatsapp/
│   │   ├── practice/
│   │   ├── gamification/
│   │   ├── payments/
│   │   ├── notifications/
│   │   └── analytics/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── redis.py
│   │   ├── security.py
│   │   ├── cache.py
│   │   └── exceptions.py
│   └── tasks/
│       ├── __init__.py
│       ├── celery_app.py
│       └── ... (task files)
├── alembic/
├── scripts/
├── tests/
└── requirements.txt
```

Create `__init__.py` files:

```bash
# Create all __init__.py files
touch app/__init__.py
touch app/api/__init__.py
touch app/api/v1/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/services/__init__.py
touch app/services/rag/__init__.py
touch app/services/whatsapp/__init__.py
touch app/services/practice/__init__.py
touch app/services/gamification/__init__.py
touch app/services/payments/__init__.py
touch app/services/notifications/__init__.py
touch app/services/analytics/__init__.py
touch app/core/__init__.py
touch app/tasks/__init__.py
```

---

## 🗃️ Step 6: Initialize Database

```bash
# Make sure you're in the backend directory with venv activated

# Initialize Alembic
alembic init alembic

# Update alembic/env.py (replace content with the version from artifacts)

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

**Alternative: Create tables directly (for quick testing)**

```bash
# Start Python shell
python

# Run this in Python:
>>> import asyncio
>>> from app.core.database import engine, Base
>>> from app.models import *  # Import all models
>>> 
>>> async def create_tables():
...     async with engine.begin() as conn:
...         await conn.run_sync(Base.metadata.create_all)
...     print("Tables created!")
>>> 
>>> asyncio.run(create_tables())
```

---

## 🌱 Step 7: Seed Initial Data

```bash
# Run the seed script
python scripts/seed_subjects.py

# Create admin user
python scripts/create_admin.py \
  --phone "+263771234567" \
  --email "admin@zimstudent.com" \
  --password "AdminPass123!"
```

---

## ▶️ Step 8: Run the Application

### Terminal 1: Run FastAPI Backend

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run with auto-reload for development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Run Celery Worker (for background tasks)

```bash
cd backend
source venv/bin/activate

# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info
```

### Terminal 3: Run Celery Beat (for scheduled tasks)

```bash
cd backend
source venv/bin/activate

# Start Celery beat scheduler
celery -A app.tasks.celery_app beat --loglevel=info
```

---

## 🌐 Step 9: Setup ngrok for WhatsApp Webhook

WhatsApp requires a public HTTPS URL for webhooks. Use ngrok for local development:

```bash
# Install ngrok (if not installed)
# Download from https://ngrok.com/download

# Start ngrok tunnel
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and:

1. Update your `.env` file:
   ```
   PAYNOW_RESULT_URL=https://abc123.ngrok.io/api/v1/payments/webhook/paynow
   ```

2. Configure in Meta Developer Portal:
   - Go to your WhatsApp App → Configuration
   - Set Webhook URL: `https://abc123.ngrok.io/api/v1/webhooks/whatsapp`
   - Set Verify Token: (same as `WHATSAPP_VERIFY_TOKEN` in .env)
   - Subscribe to messages

---

## ✅ Step 10: Verify Installation

### Check API Health

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","app":"Zim Student Companion"}
```

### Access API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### Check Qdrant Dashboard

Open: http://localhost:6333/dashboard

### Test WhatsApp Webhook

```bash
# Test webhook verification
curl "http://localhost:8000/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=your-custom-verify-token-any-string&hub.challenge=test123"
# Expected: test123
```

---

## 📄 Step 11: Ingest ZIMSEC Documents

```bash
# Place your PDF documents in the documents folder
# Then run the ingestion script

# Ingest syllabi
python scripts/ingest_documents.py \
  --dir ./documents/syllabi \
  --type syllabus

# Ingest past papers
python scripts/ingest_documents.py \
  --dir ./documents/past_papers \
  --type past_paper

# Ingest a single file
python scripts/ingest_documents.py \
  --file ./documents/math_form3.pdf \
  --type textbook \
  --subject Mathematics \
  --grade "Form 3" \
  --level secondary
```

---

## 🧪 Step 12: Run Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_rag.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=app --cov-report=html
```

---

## 📱 Step 13: Test WhatsApp Integration

1. Send a message to your WhatsApp Business number
2. You should receive the onboarding flow
3. Complete registration and test features

### Quick Test Commands (via WhatsApp):
- Send: `Hi` → Start onboarding
- Send: `menu` → Show main menu
- Send: `practice` → Start practice session
- Send: `help` → Show help

---

## 🔧 Troubleshooting

### Common Issues

**1. Database Connection Error**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Restart if needed
docker-compose restart postgres
```

**2. Redis Connection Error**
```bash
# Test Redis connection
redis-cli ping
# Expected: PONG
```

**3. Qdrant Connection Error**
```bash
# Check Qdrant status
curl http://localhost:6333/collections
```

**4. WhatsApp Webhook Not Working**
- Verify ngrok is running and URL is correct
- Check webhook URL in Meta Developer Portal
- Ensure verify token matches

**5. Gemini API Error**
- Verify API key is correct
- Check quota limits at https://makersuite.google.com

---

## 🚀 Quick Start Commands (TL;DR)

```bash
# 1. Start infrastructure
docker-compose up -d

# 2. Setup Python environment
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Initialize database
python -c "
import asyncio
from app.core.database import engine, Base
from app.models import *
asyncio.run(engine.begin().__aenter__().then(lambda c: c.run_sync(Base.metadata.create_all)))
"

# 4. Seed data
python scripts/seed_subjects.py

# 5. Run app
uvicorn app.main:app --reload --port 8000

# 6. (In new terminal) Start ngrok
ngrok http 8000
```

---

## 📞 Support

If you encounter issues:
1. Check the logs: `docker-compose logs -f`
2. Review the API docs: http://localhost:8000/api/docs
3. Test endpoints with curl or Postman

Good luck with your Zim Student Companion! 🎓🇿🇼