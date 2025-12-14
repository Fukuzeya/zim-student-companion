# 🚀 Zim Student Companion - Setup & Deployment Guide

## Prerequisites

Before starting, ensure you have:

- [ ] Linux server (Ubuntu 22.04 recommended) with 4GB+ RAM
- [ ] Domain name (e.g., api.zimstudent.co.zw)
- [ ] Meta Business Account (for WhatsApp)
- [ ] Google Cloud Account (for Gemini API)
- [ ] Paynow Zimbabwe Merchant Account
- [ ] Basic knowledge of Docker, Linux, and Python

---

## 📋 Step-by-Step Deployment

### Step 1: Server Setup

#### 1.1 Provision a VPS
Recommended providers for Zimbabwe:
- **Hetzner** (€8-15/month) - Best value
- **Contabo** ($5-10/month) - Budget option
- **DigitalOcean** ($12-24/month) - Reliable

Minimum specs:
- 4GB RAM
- 2 vCPU
- 80GB SSD
- Ubuntu 22.04 LTS

#### 1.2 Initial Server Setup
```bash
# SSH into your server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install essentials
apt install -y curl git wget nano ufw

# Setup firewall
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable

# Create non-root user
adduser zscadmin
usermod -aG sudo zscadmin

# Switch to new user
su - zscadmin
```

#### 1.3 Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Logout and login for group changes
exit
ssh zscadmin@your-server-ip
```

---

### Step 2: Get API Keys

#### 2.1 Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Click "Get API Key"
3. Create a new key or use existing
4. Copy the API key (starts with `AIza...`)

**Cost:** Free tier includes 60 requests/minute - sufficient for 1000+ users

#### 2.2 WhatsApp Business API

##### Option A: Meta Cloud API (Recommended)
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app → Select "Business"
3. Add "WhatsApp" product
4. Set up WhatsApp Business Account
5. Get your:
   - **Phone Number ID**
   - **WhatsApp Business Account ID**
   - **Permanent Access Token**

##### Setup Webhook:
1. In Meta Developer Dashboard → WhatsApp → Configuration
2. Webhook URL: `https://api.yourdomain.com/api/v1/webhooks/whatsapp`
3. Verify Token: Create a random string (you'll use this in .env)
4. Subscribe to: `messages`, `message_status`

**Cost:** 
- First 1,000 conversations/month: FREE
- Additional: $0.02-0.06 per conversation

#### 2.3 Paynow Zimbabwe
1. Register at [Paynow.co.zw](https://www.paynow.co.zw/)
2. Complete merchant verification
3. Get your:
   - **Integration ID**
   - **Integration Key**
4. Set Result URL: `https://api.yourdomain.com/api/v1/payments/webhook/paynow`

---

### Step 3: Clone & Configure

#### 3.1 Clone Repository
```bash
cd ~
git clone https://github.com/yourusername/zim-student-companion.git
cd zim-student-companion
```

#### 3.2 Create Environment File
```bash
cp .env.example .env
nano .env
```

Fill in your values:
```env
# Application
APP_NAME="Zim Student Companion"
DEBUG=false
SECRET_KEY=your-super-secret-key-generate-random-64-chars

# Database
DATABASE_URL=postgresql://zsc_user:your_strong_password@postgres:5432/zsc_db
REDIS_URL=redis://redis:6379/0

# Gemini AI
GEMINI_API_KEY=AIza_your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_EMBEDDING_MODEL=text-embedding-004

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# WhatsApp
WHATSAPP_TOKEN=your_whatsapp_permanent_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_random_verify_token
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id

# Paynow
PAYNOW_INTEGRATION_ID=your_integration_id
PAYNOW_INTEGRATION_KEY=your_integration_key
PAYNOW_RESULT_URL=https://api.yourdomain.com/api/v1/payments/webhook/paynow
PAYNOW_RETURN_URL=https://yourdomain.com/payment/success

# JWT
JWT_SECRET_KEY=another-random-secret-key-64-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Rate Limits
FREE_DAILY_QUESTIONS=5
BASIC_DAILY_QUESTIONS=50
PREMIUM_DAILY_QUESTIONS=1000
```

Generate secure keys:
```bash
# Generate random keys
openssl rand -hex 32  # For SECRET_KEY
openssl rand -hex 32  # For JWT_SECRET_KEY
```

---

### Step 4: SSL Certificate

#### Using Certbot (Let's Encrypt)
```bash
# Install certbot
sudo apt install certbot -y

# Get certificate (standalone mode)
sudo certbot certonly --standalone -d api.yourdomain.com

# Certificates will be at:
# /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/api.yourdomain.com/privkey.pem

# Copy to project
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem ./nginx/ssl/
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem ./nginx/ssl/
sudo chown -R $USER:$USER ./nginx/ssl/
```

---

### Step 5: Deploy with Docker

#### 5.1 Build and Start
```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f api
```

#### 5.2 Initialize Database
```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Seed curriculum data
docker-compose -f docker-compose.prod.yml exec api python scripts/seed_subjects.py

# Create admin user
docker-compose -f docker-compose.prod.yml exec api python scripts/create_admin.py \
  --phone "+263771234567" \
  --email "admin@zimstudent.co.zw" \
  --password "YourSecurePassword123"
```

#### 5.3 Verify Deployment
```bash
# Test API health
curl https://api.yourdomain.com/health

# Expected response:
# {"status": "healthy", "app": "Zim Student Companion"}
```

---

### Step 6: Ingest ZIMSEC Content

#### 6.1 Prepare Documents
Organize your documents:
```
documents/
├── syllabi/
│   ├── mathematics_secondary.pdf
│   ├── physics_secondary.pdf
│   └── ...
├── past_papers/
│   ├── mathematics_secondary_form4_2023_paper1.pdf
│   ├── mathematics_secondary_form4_2023_paper2.pdf
│   └── ...
├── marking_schemes/
│   ├── mathematics_secondary_form4_2023_ms.pdf
│   └── ...
└── textbooks/
    └── ...
```

#### 6.2 Run Ingestion
```bash
# Ingest syllabi
docker-compose -f docker-compose.prod.yml exec api \
  python scripts/ingest_documents.py \
  --dir /app/documents/syllabi \
  --type syllabus

# Ingest past papers
docker-compose -f docker-compose.prod.yml exec api \
  python scripts/ingest_documents.py \
  --dir /app/documents/past_papers \
  --type past_paper

# Ingest marking schemes
docker-compose -f docker-compose.prod.yml exec api \
  python scripts/ingest_documents.py \
  --dir /app/documents/marking_schemes \
  --type marking_scheme
```

---

### Step 7: Verify WhatsApp Webhook

1. In Meta Developer Dashboard, click "Verify" on your webhook
2. It should succeed if your server is running
3. Send a test message to your WhatsApp number
4. Check logs:
```bash
docker-compose -f docker-compose.prod.yml logs -f api | grep webhook
```

---

## 🔧 Maintenance Commands

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f celery_worker
```

### Restart Services
```bash
# Restart all
docker-compose -f docker-compose.prod.yml restart

# Restart specific service
docker-compose -f docker-compose.prod.yml restart api
```

### Database Backup
```bash
# Create backup
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U zsc_user zsc_db > backup_$(date +%Y%m%d).sql

# Restore backup
cat backup_20241210.sql | docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U zsc_user zsc_db
```

### Update Application
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Run any new migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

---

## 📊 Monitoring

### Setup Basic Monitoring
```bash
# Install monitoring stack (optional)
docker-compose -f docker-compose.monitoring.yml up -d

# Access:
# - Grafana: http://your-server:3000
# - Prometheus: http://your-server:9090
```

### Key Metrics to Watch
- API response times
- Database connections
- Redis memory usage
- Celery queue length
- WhatsApp message delivery rate

---

## 🔒 Security Checklist

- [ ] Strong passwords for all services
- [ ] Firewall configured (only 80, 443 open)
- [ ] SSL certificate installed
- [ ] Regular backups scheduled
- [ ] Monitoring alerts configured
- [ ] Rate limiting enabled
- [ ] Environment variables secured
- [ ] Regular security updates

---

## 💰 Cost Summary

| Service | Monthly Cost (USD) |
|---------|-------------------|
| VPS Server (4GB) | $8-15 |
| Domain | $1 |
| Gemini API | $0 (free tier) |
| WhatsApp API | $0-50 (usage based) |
| SSL Certificate | $0 (Let's Encrypt) |
| **Total** | **$9-66/month** |

*Costs scale with users. At 1,000 users, expect ~$50-100/month total.*

---

## 🆘 Troubleshooting

### WhatsApp not responding
1. Check webhook logs
2. Verify token is correct
3. Ensure SSL is valid
4. Check Meta dashboard for errors

### Database connection failed
```bash
# Check PostgreSQL status
docker-compose -f docker-compose.prod.yml logs postgres

# Restart PostgreSQL
docker-compose -f docker-compose.prod.yml restart postgres
```

### High memory usage
```bash
# Check memory
docker stats

# Restart heavy services
docker-compose -f docker-compose.prod.yml restart celery_worker
```

### Payment not processing
1. Verify Paynow credentials
2. Check webhook URL is accessible
3. Review Paynow dashboard for errors

---

## 📞 Support

For deployment support:
- Email: support@zimstudent.co.zw
- Documentation: docs.zimstudent.co.zw

---

*Congratulations! Your Zim Student Companion is now live! 🎉*