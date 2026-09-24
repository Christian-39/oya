# Okpo Youths Association Management System (OYA)

## PEACE & PROGRESS

A complete production-ready Django 5.2+ backend for managing the Okpo Youths Association.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Management Commands](#management-commands)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Roles & Permissions](#roles--permissions)
- [Modules](#modules)
- [Development](#development)
- [Production Deployment](#production-deployment)

---

## Overview

OYA is a comprehensive association management system built with Django 5.2+. It provides complete CRUD operations, role-based access control, audit logging, financial management, election management, project tracking, and operational tools for the Okpo Youths Association.

---

## Features

- **Custom Authentication**: Serial number-based login with 6-digit PIN
- **Role-Based Access Control**: Admin, Executive, and Floor Member roles
- **Member Management**: Clan-based membership with age-based status automation
- **Executive Management**: Full executive roster with tenure tracking
- **Election Engine**: 4-year election cycle with candidate management
- **Finance Engine**: Income/expense tracking with receipt upload
- **Project Management**: Multi-status project tracking with progress
- **Operations**: Task force, motorcycle assets, and case files
- **Audit Logging**: Comprehensive action logging for accountability
- **Dashboard**: KPI aggregation with caching
- **System Settings**: Configurable association parameters
- **Notifications**: In-app notification system
- **Global Search**: Q()-based search across all modules
- **Optimized ORM**: select_related, prefetch_related, pagination

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Framework | Django 5.2+ |
| Database | MySQL 8.0 |
| Cache | Redis (optional) |
| Task Queue | Celery (optional) |
| Auth | Custom User Model |
| Currency | Naira (NGN) |

---

## Project Structure

```
oya/
|-- accounts/          # Custom User model, authentication, permissions
|-- auditlogs/         # Audit logging system
|-- core/              # Base models, utilities, middleware, exceptions
|-- dashboard/         # KPI aggregation and dashboard views
|-- elections/         # Election management, candidates, handover ledgers
|-- executives/        # Executive roster and tenure management
|-- finance/           # Income/expense tracking
|-- members/           # Member and Clan management
|-- notifications/     # In-app notification system
|-- operations/        # Task force, motorcycles, case files
|-- oya/               # Project settings and configuration
|-- projects/          # Project tracking and management
|-- settingsapp/       # System-wide configuration
|-- manage.py          # Django management script
|-- requirements.txt   # Python dependencies
|-- .env.example       # Environment configuration template
```

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd oya
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Setup MySQL Database

```sql
CREATE DATABASE oya_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'oya_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON oya_db.* TO 'oya_user'@'localhost';
FLUSH PRIVILEGES;
```

### 6. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create Superuser

```bash
python manage.py createsuperuser
# Enter serial number (e.g., OYA-2026-0001)
# Enter full name
# Enter 6-digit PIN
```

### 8. Seed Data (Optional)

```bash
python manage.py seed_data
```

### 9. Run Development Server

```bash
python manage.py runserver
```

---

## Configuration

All configuration is done via environment variables or the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | (generated) |
| `DJANGO_DEBUG` | Debug mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |
| `DB_NAME` | Database name | `oya_db` |
| `DB_USER` | Database user | `oya_user` |
| `DB_PASSWORD` | Database password | `oya_password` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `3306` |
| `CELERY_BROKER_URL` | Celery broker | `redis://localhost:6379/0` |

---

## Database Setup

### MySQL Configuration

The project uses MySQL 8.0 with the following optimizations:

- **Charset**: `utf8mb4` for full Unicode support
- **SQL Mode**: `STRICT_TRANS_TABLES` for data integrity
- **InnoDB**: Strict mode enabled

### Database Indexes

All models include optimized indexes for common query patterns:

- Status fields
- Foreign key relationships
- Search fields (serial_number, full_name)
- Date fields (created_at)

---

## Running the Application

### Development

```bash
python manage.py runserver
```

### Production

```bash
# Collect static files
python manage.py collectstatic

# Run with Gunicorn
gunicorn oya.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Celery Worker (Optional)

```bash
celery -A oya worker --loglevel=info
celery -A oya beat --loglevel=info
```

---

## Management Commands

### Update Member Statuses

Automatically moves members aged 56+ from ACTIVE to PAST_MEMBER:

```bash
python manage.py update_member_status
```

Options:
- `--dry-run`: Preview changes without applying

### Seed Data

Populates the database with sample data:

```bash
python manage.py seed_data
```

Options:
- `--flush`: Clear existing data before seeding

---

## API Endpoints

### Accounts

| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/accounts/login/` | Login |
| GET | `/accounts/logout/` | Logout |
| GET | `/accounts/profile/` | View profile |
| GET | `/accounts/users/` | List users |
| GET/POST | `/accounts/users/create/` | Create user |
| GET | `/accounts/users/<pk>/` | User detail |
| GET/POST | `/accounts/users/<pk>/update/` | Update user |
| GET/POST | `/accounts/users/<pk>/delete/` | Delete user |
| GET/POST | `/accounts/pin-reset/` | Reset PIN |

### Members

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/members/` | List members |
| GET/POST | `/members/create/` | Create member |
| GET | `/members/<pk>/` | Member detail |
| GET/POST | `/members/<pk>/update/` | Update member |
| GET/POST | `/members/<pk>/remove/` | Remove member |
| GET/POST | `/members/<pk>/delete/` | Delete member |
| GET | `/members/clans/` | List clans |
| GET/POST | `/members/clans/create/` | Create clan |

### Executives

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/executives/` | List executives |
| GET/POST | `/executives/create/` | Create executive |
| GET | `/executives/<pk>/` | Executive detail |
| GET/POST | `/executives/<pk>/update/` | Update executive |
| GET/POST | `/executives/<pk>/end-tenure/` | End tenure |

### Elections

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/elections/` | List elections |
| GET/POST | `/elections/create/` | Create election |
| GET | `/elections/<pk>/` | Election detail |
| GET/POST | `/elections/<pk>/update/` | Update election |
| GET/POST | `/elections/candidates/create/` | Add candidate |
| GET | `/elections/handovers/` | List handovers |
| GET/POST | `/elections/handovers/create/` | Create handover |

### Finance

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/finance/income/` | List income |
| GET/POST | `/finance/income/create/` | Record income |
| GET | `/finance/income/<pk>/` | Income detail |
| GET/POST | `/finance/income/<pk>/delete/` | Delete income |
| GET | `/finance/expenses/` | List expenses |
| GET/POST | `/finance/expenses/create/` | Record expense |
| GET | `/finance/expenses/<pk>/` | Expense detail |
| GET/POST | `/finance/expenses/<pk>/delete/` | Delete expense |
| GET | `/finance/summary/` | Financial summary |

### Projects

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/projects/` | List projects |
| GET/POST | `/projects/create/` | Create project |
| GET | `/projects/<pk>/` | Project detail |
| GET/POST | `/projects/<pk>/update/` | Update project |
| GET/POST | `/projects/<pk>/delete/` | Delete project |

### Operations

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/operations/taskforce/` | List task force |
| GET/POST | `/operations/taskforce/create/` | Assign member |
| GET/POST | `/operations/taskforce/<pk>/remove/` | Remove member |
| GET | `/operations/motorcycles/` | List motorcycles |
| GET/POST | `/operations/motorcycles/create/` | Register motorcycle |
| GET/POST | `/operations/motorcycles/<pk>/update/` | Update motorcycle |
| GET | `/operations/cases/` | List cases |
| GET/POST | `/operations/cases/create/` | Create case |
| GET | `/operations/cases/<pk>/` | Case detail |
| GET/POST | `/operations/cases/<pk>/resolve/` | Resolve case |

### Notifications

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/notifications/` | List notifications |
| GET/POST | `/notifications/create/` | Create notification |
| GET | `/notifications/<pk>/` | Notification detail |
| GET/POST | `/notifications/<pk>/delete/` | Delete notification |
| GET | `/notifications/mark-all-read/` | Mark all read |

### Audit Logs

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/auditlogs/` | List audit logs |

### Dashboard

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/dashboard/` | Main dashboard |
| GET | `/dashboard/admin/` | Admin dashboard |

### Settings

| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/settings/` | System settings |

---

## Authentication

### Serial Number Format

Format: `OYA-YYYY-XXXX`

Example: `OYA-2026-0001`

### PIN

- 6-digit numeric PIN only
- Hashed using Django's password hashing
- Admin can reset PINs for other users

### Login Process

1. User enters serial number and PIN
2. System authenticates via `SerialNumberAuthBackend`
3. Session is created with 24-hour expiry
4. Audit log entry is created

---

## Roles & Permissions

### Admin

- Full CRUD access to all modules
- Can access system settings
- Can manage user permissions
- Can reset PINs
- Can assign task force members
- Can access admin dashboard

### Executive

- CRUD access to most modules
- Cannot access system settings
- Cannot manage permissions
- Can view audit logs

### Floor Member

- View-only access
- Can edit own phone and state
- Cannot access admin URLs
- Can view own profile

---

## Modules

### Module A: Member Engine

- Clan management (Umu Nna groups)
- Member registration with age validation
- Automatic status updates (active -> past member at age 56)
- Male-only membership (18-55 active age)
- Photo upload support

### Module B: Executives

- 16 executive posts
- Tenure tracking with start/end dates
- Current vs past executive distinction
- Handover ledger support

### Module C: Election Engine

- 4-year election cycle
- Election scheduling
- Candidate registration with manifesto
- Vote counting
- Handover ledger for asset transfer

### Module D: Finance Engine

- Income tracking with source
- Expense tracking with categories
- Mandatory receipt upload for expenses
- Treasury balance calculation
- Financial summaries

### Module E: Projects Engine

- Three status levels: Future, At Hand, Finished
- Budget tracking
- Progress percentage
- Project lifecycle management

### Module F: Operations Engine

- Task force member assignment
- Motorcycle asset tracking (Excellent/Needs Service/Grounded)
- Case file management (Open/In Progress/Resolved)
- Fine tracking

### Module G: Notifications

- Multi-type notifications (Info, Success, Warning, etc.)
- Global and user-specific notifications
- Read/unread tracking
- Bulk mark-as-read

### Module H: Audit Logs

- Automatic logging of all CRUD operations
- Login/logout tracking
- PIN reset logging
- Election, finance, project, case action logging
- IP address tracking

---

## Development

### Running Tests

```bash
python manage.py test
```

### Code Style

```bash
# Format with black
black .

# Lint with flake8
flake8 .
```

### Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Production Deployment

### Security Checklist

- [ ] Change `DJANGO_SECRET_KEY` to a secure value
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Configure `DJANGO_ALLOWED_HOSTS`
- [ ] Enable SSL/TLS
- [ ] Set `SESSION_COOKIE_SECURE=True`
- [ ] Set `CSRF_COOKIE_SECURE=True`
- [ ] Configure proper logging
- [ ] Use environment variables for sensitive data

### Docker Deployment (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "oya.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

## License

Proprietary - Okpo Youths Association

---

## Support

For support, contact the system administrator or the OYA technical team.