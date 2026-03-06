<h1 align="center">
  📱 JobPulse — SMS Job Alerts API
</h1>

<p align="center">
  <strong>A production-ready REST API for distributing job offers via SMS in Burkina Faso 🇧🇫</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/DRF-3.16-ff1709?style=for-the-badge&logo=django&logoColor=white" alt="DRF">
  <img src="https://img.shields.io/badge/Celery-5.6-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery">
  <img src="https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Orange_SMS-API-FF6600?style=for-the-badge" alt="Orange SMS">
</p>

---

## 🎯 Overview

**JobPulse** is a backend API designed to connect job seekers in Burkina Faso with employment opportunities through **SMS alerts**. Users subscribe to job categories via a web interface or USSD, and receive daily SMS notifications with relevant job postings — delivered through the **Orange SMS API**.

### ✨ Key Features

| Feature | Description |
|---|---|
| 📲 **OTP Authentication** | Phone-based signup/login with SMS OTP verification |
| 📨 **Orange SMS Integration** | OAuth2-secured SMS delivery via Orange Burkina Faso API |
| 📋 **Job Subscriptions** | Category-based subscription system (web + USSD) |
| ⏰ **Daily Broadcasts** | Automated daily job alerts via Celery Beat (8:00 AM) |
| 📞 **USSD Webhook** | Interactive USSD menu for feature phone users |
| 📤 **Bulk Upload** | CSV-based bulk import for jobs and subscribers |
| 🛡️ **Blacklist System** | Phone number blacklisting with auto-enforcement |
| 📊 **Admin Dashboard** | Real-time stats: subscribers, jobs, SMS delivered |
| 📖 **API Documentation** | Interactive Swagger UI + ReDoc |

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Nginx      │────▶│  Gunicorn    │────▶│  Django + DRF    │
│  (Reverse    │     │  (WSGI)      │     │  REST API        │
│   Proxy)     │     └──────────────┘     └────────┬─────────┘
└──────────────┘                                   │
                                                   │
                    ┌──────────────┐     ┌─────────▼─────────┐
                    │  PostgreSQL  │◀────│   Django ORM      │
                    │  Database    │     └───────────────────┘
                    └──────────────┘
                                                   │
                    ┌──────────────┐     ┌─────────▼─────────┐
                    │    Redis     │◀────│  Celery Worker     │
                    │  (Broker +   │     │  + Celery Beat     │
                    │   Cache)     │     └─────────┬─────────┘
                    └──────────────┘               │
                                         ┌─────────▼─────────┐
                                         │  Orange SMS API   │
                                         │  (Burkina Faso)   │
                                         └───────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Framework** | Django 6.0 + DRF 3.16 | REST API core |
| **Authentication** | SimpleJWT + OTP | Phone-based auth with SMS verification |
| **SMS Provider** | Orange SMS API | OAuth2-secured SMS delivery |
| **Task Queue** | Celery 5.6 | Async SMS sending + scheduled broadcasts |
| **Database** | PostgreSQL 15 | Primary data store |
| **Cache/Broker** | Redis 7 | Celery broker + OAuth2 token cache |
| **WSGI Server** | Gunicorn | Production-grade application server |
| **Reverse Proxy** | Nginx | SSL termination + static files (manual setup) |
| **Containerization** | Docker Compose | Full-stack deployment |
| **Documentation** | drf-spectacular | Swagger UI + ReDoc auto-generation |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git

### 1. Clone & Setup

```bash
git clone git@github.com:mohammadSelimReza/JobPulse-Web-App.git
cd JobPulse-Web-App
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 3. Development Setup

```bash
# Start infrastructure services
docker compose up -d

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### 4. Start Celery Workers (separate terminal)

```bash
source .venv/bin/activate
celery -A core worker --loglevel=info
```

### 5. Start Celery Beat Scheduler (separate terminal)

```bash
source .venv/bin/activate
celery -A core beat --loglevel=info
```

---

## 🐳 Production Deployment

Deploy the entire stack with a single command:

```bash
# Configure production environment
cp .env.example .env
# Edit .env with production values (SECRET_KEY, ALLOWED_HOSTS, DB creds, Orange API keys)

# Deploy
docker compose -f docker-compose.prod.yml up -d --build
```

This starts:

- **Web** — Django + Gunicorn on port 8000
- **Celery Worker** — Async SMS task processing
- **Celery Beat** — Daily job broadcast scheduler
- **PostgreSQL** — Database with health checks
- **Redis** — Broker + cache with health checks

> **Note:** Nginx reverse proxy should be configured manually on the VPS to proxy to port 8000.

---

## 📡 API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/request-otp/` | — | Request OTP via SMS |
| `POST` | `/api/v1/auth/verify-otp/` | — | Verify OTP → JWT tokens |
| `POST` | `/api/v1/auth/admin-login/` | — | Admin JWT login |
| `POST` | `/api/v1/auth/token/refresh/` | — | Refresh JWT token |
| `GET/POST` | `/api/v1/subscriptions/` | 🔒 JWT | Manage subscriptions |
| `POST` | `/api/v1/ussd/callback/` | — | USSD webhook endpoint |
| `CRUD` | `/api/v1/admin/jobs/` | 🔒 Admin | Manage job offers |
| `POST` | `/api/v1/admin/jobs/bulk-upload/` | 🔒 Admin | CSV bulk upload jobs |
| `CRUD` | `/api/v1/admin/subscribers/` | 🔒 Admin | Manage subscribers |
| `POST` | `/api/v1/admin/subscribers/bulk-upload/` | 🔒 Admin | CSV bulk upload subscribers |
| `CRUD` | `/api/v1/admin/blacklist/` | 🔒 Admin | Manage phone blacklist |
| `GET` | `/api/v1/admin/dashboard-stats/` | 🔒 Admin | Dashboard statistics |

### 📖 Interactive Documentation

| URL | Type |
|---|---|
| `/api/schema/swagger-ui/` | Swagger UI |
| `/api/schema/redoc/` | ReDoc |
| `/api/schema/` | OpenAPI JSON Schema |

---

## 📁 Project Structure

```
JobPulse-Web-App/
├── api/                          # Main application
│   ├── models.py                 # User, OTP, Job, Subscription, Blacklist, SMSLog
│   ├── views.py                  # API views and viewsets
│   ├── serializers.py            # DRF serializers with E.164 validation
│   ├── tasks.py                  # Celery tasks (Orange SMS + daily broadcasts)
│   ├── urls.py                   # API routing
│   ├── admin.py                  # Django admin registration
│   └── tests.py                  # Unit tests
├── core/                         # Django project config
│   ├── settings/
│   │   ├── base.py               # Shared settings
│   │   ├── development.py        # Dev overrides (DEBUG=True)
│   │   └── production.py         # Prod security (HSTS, secure cookies)
│   ├── celery.py                 # Celery app + beat schedule
│   ├── urls.py                   # Root URL routing
│   ├── wsgi.py                   # WSGI entrypoint
│   └── asgi.py                   # ASGI entrypoint
├── Dockerfile                    # Production container image
├── docker-compose.yml            # Dev services (DB + Redis)
├── docker-compose.prod.yml       # Full production stack
├── entrypoint.sh                 # Container startup script
├── gunicorn.conf.py              # Gunicorn configuration
├── requirements.txt              # Python dependencies
├── manage.py                     # Django CLI
├── .env.example                  # Environment variable template
└── .gitignore                    # Git exclusions
```

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Django secret key |
| `DEBUG` | ✅ | Debug mode (False in production) |
| `ALLOWED_HOSTS` | ✅ | Comma-separated allowed hostnames |
| `DATABASE_URL` | ✅ | PostgreSQL connection URL |
| `REDIS_URL` | ✅ | Redis connection URL |
| `ORANGE_CLIENT_ID` | ✅ | Orange API client ID |
| `ORANGE_CLIENT_SECRET` | ✅ | Orange API client secret |
| `ORANGE_AUTH_HEADER` | ✅ | Orange API Basic auth header |
| `ORANGE_SENDER_ADDRESS` | ✅ | SMS sender address (tel:+226...) |
| `CORS_ALLOWED_ORIGINS` | Prod | Allowed CORS origins |
| `SECURE_SSL_REDIRECT` | Prod | Enable HTTPS redirect |

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test api --verbosity=2

# Run specific test class
python manage.py test api.tests.AuthenticationTests
```

---

## 📄 License

This project is proprietary software built for the Sahel Job Offers platform.

---

<p align="center">
  Built with ❤️ for Burkina Faso 🇧🇫
</p>
