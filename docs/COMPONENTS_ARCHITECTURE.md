# 🏗️ Components Architecture Diagram - Expense Tracker

**Last Updated:** 2026-01-15

---

## 📊 Overview

This document provides a detailed **components architecture diagram** showing all the modules, services, and their interactions in the Expense Tracker application.

---

## 🎯 Components Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL CLIENTS                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Web Client  │  │ Mobile App   │  │  API Client   │  │  Swagger UI   │   │
│  │  (React)    │  │  (iOS/Android)│  │  (Postman)   │  │  (Docs)      │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
└─────────┼─────────────────┼──────────────────┼─────────────────┼─────────────┘
          │                 │                  │                 │
          └─────────────────┴──────────────────┴─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    APPLICATION LOAD BALANCER (AWS ALB)                       │
│  • SSL/TLS Termination                                                      │
│  • Health Checks                                                             │
│  • Request Routing                                                           │
└──────────────────────────┬──────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FASTAPI APPLICATION (ECS Task)                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    MIDDLEWARE LAYER                                  │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │   │
│  │  │ RequestID      │  │ Timing         │  │ Logging         │    │   │
│  │  │ Middleware     │  │ Middleware     │  │ Middleware      │    │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘    │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │   │
│  │  │ Prometheus     │  │ CORS           │  │ Rate Limiting   │    │   │
│  │  │ Middleware     │  │ Middleware     │  │ Middleware      │    │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                            │                                                  │
│                            ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    ROUTER LAYER (API Endpoints)                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ Auth Router  │  │ Users Router │  │ Categories   │              │   │
│  │  │ /api/v1/auth │  │ /api/v1/users│  │ Router        │              │   │
│  │  │              │  │              │  │ /api/v1/      │              │   │
│  │  │ • register   │  │ • profile    │  │ categories   │              │   │
│  │  │ • login      │  │ • change_pwd  │  │              │              │   │
│  │  │ • refresh    │  │ • delete     │  │ • CRUD       │              │   │
│  │  │ • verify     │  │              │  │ • defaults   │              │   │
│  │  │ • reset_pwd  │  │              │  │              │              │   │
│  │  │ • logout     │  │              │  │              │              │   │
│  │  │ • me         │  │              │  │              │              │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │   │
│  │         │                 │                  │                       │   │
│  │  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐            │   │
│  │  │ Tags Router  │  │ Transactions │  │ Analytics     │            │   │
│  │  │ /api/v1/tags│  │ Router       │  │ Router        │            │   │
│  │  │              │  │ /api/v1/     │  │ /api/v1/      │            │   │
│  │  │ • CRUD       │  │ transactions │  │ analytics    │            │   │
│  │  │              │  │              │  │              │            │   │
│  │  │              │  │ • create     │  │ • dashboard  │            │   │
│  │  │              │  │ • list        │  │ • breakdown  │            │   │
│  │  │              │  │ • get         │  │ • trends     │            │   │
│  │  │              │  │ • update      │  │ • cashflow   │            │   │
│  │  │              │  │ • delete      │  │ • tags       │            │   │
│  │  │              │  │ • stats       │  │              │            │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │   │
│  │         │                 │                  │                       │   │
│  │  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐            │   │
│  │  │ Receipts     │  │ Reports      │  │ Monitoring   │            │   │
│  │  │ Router       │  │ Router       │  │ Router       │            │   │
│  │  │ /api/v1/     │  │ /api/v1/     │  │ /api/v1/     │            │   │
│  │  │ transactions │  │ reports      │  │ monitoring   │            │   │
│  │  │ /{id}/receipt│  │              │  │              │            │   │
│  │  │              │  │ • request    │  │ • health     │            │   │
│  │  │ • upload     │  │ • status     │  │ • detailed   │            │   │
│  │  │ • presigned  │  │ • list       │  │ • metrics    │            │   │
│  │  │ • confirm    │  │ • download   │  │ • system     │            │   │
│  │  │ • get        │  │ • delete     │  │              │            │   │
│  │  │ • delete     │  │              │  │              │            │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │   │
│  └─────────┼─────────────────┼──────────────────┼──────────────────────┘   │
│            │                 │                  │                              │
│            └─────────────────┴──────────────────┘                              │
│                            │                                                    │
│                            ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │                    DEPENDENCIES LAYER                                 │     │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐      │     │
│  │  │ get_current_   │  │ get_db         │  │ get_redis       │      │     │
│  │  │ user           │  │ (DB Session)   │  │ (Redis Client)   │      │     │
│  │  │ (JWT Auth)     │  │                │  │                  │      │     │
│  │  └────────────────┘  └────────────────┘  └────────────────┘      │     │
│  │  ┌────────────────┐  ┌────────────────┐                            │     │
│  │  │ rate_limit_by_ │  │ Exception      │                            │     │
│  │  │ ip             │  │ Handlers       │                            │     │
│  │  └────────────────┘  └────────────────┘                            │     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│                            │                                                    │
│                            ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │                    SERVICE LAYER (Business Logic)                       │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │     │
│  │  │ Auth         │  │ User         │  │ Category     │              │     │
│  │  │ Service      │  │ Service      │  │ Service      │              │     │
│  │  │              │  │              │  │              │              │     │
│  │  │ • register   │  │ • get_profile│  │ • create     │              │     │
│  │  │ • login      │  │ • change_pwd │  │ • list       │              │     │
│  │  │ • refresh    │  │ • delete     │  │ • update     │              │     │
│  │  │ • verify     │  │              │  │ • delete     │              │     │
│  │  │ • reset_pwd  │  │              │  │ • defaults   │              │     │
│  │  │ • logout     │  │              │  │              │              │     │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │     │
│  │         │                 │                  │                       │     │
│  │  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐            │     │
│  │  │ Tag          │  │ Transaction  │  │ Analytics    │            │     │
│  │  │ Service      │  │ Service      │  │ Service      │            │     │
│  │  │              │  │              │  │              │            │     │
│  │  │ • CRUD       │  │ • create     │  │ • dashboard  │            │     │
│  │  │              │  │ • list        │  │ • breakdown  │            │     │
│  │  │              │  │ • get         │  │ • trends     │            │     │
│  │  │              │  │ • update      │  │ • cashflow   │            │     │
│  │  │              │  │ • delete      │  │ • tags       │            │     │
│  │  │              │  │ • stats       │  │              │            │     │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │     │
│  │         │                 │                  │                       │     │
│  │  ┌──────▼───────┐  ┌──────▼───────┐                                │     │
│  │  │ Receipt      │  │ Report       │                                │     │
│  │  │ Service      │  │ Service      │                                │     │
│  │  │              │  │              │                                │     │
│  │  │ • upload     │  │ • request     │                                │     │
│  │  │ • presigned  │  │ • get_status  │                                │     │
│  │  │ • confirm    │  │ • list        │                                │     │
│  │  │ • get        │  │ • download    │                                │     │
│  │  │ • delete     │  │ • delete      │                                │     │
│  │  └──────┬───────┘  └──────┬───────┘                                │     │
│  └─────────┼─────────────────┼──────────────────────────────────────────┘     │
│            │                 │                                                    │
│            └─────────────────┘                                                    │
│                            │                                                      │
│                            ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐       │
│  │                    REPOSITORY LAYER (Data Access)                     │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │       │
│  │  │ Category     │  │ Tag          │  │ Transaction  │              │       │
│  │  │ Repository   │  │ Repository   │  │ Repository   │              │       │
│  │  │              │  │              │  │              │              │       │
│  │  │ • CRUD ops   │  │ • CRUD ops   │  │ • CRUD ops   │              │       │
│  │  │ • queries    │  │ • queries    │  │ • filters    │              │       │
│  │  │ • pagination │  │ • pagination │  │ • pagination │              │       │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │       │
│  │         │                 │                  │                       │       │
│  │  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐            │       │
│  │  │ Analytics    │  │ Receipt      │  │ Report        │            │       │
│  │  │ Repository   │  │ Repository   │  │ Repository    │            │       │
│  │  │              │  │              │  │              │            │       │
│  │  │ • aggregates │  │ • CRUD ops   │  │ • CRUD ops   │            │       │
│  │  │ • group_by   │  │ • queries    │  │ • queries    │            │       │
│  │  │ • time_series│  │              │  │ • status     │            │       │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │       │
│  └─────────┼─────────────────┼──────────────────┼──────────────────────┘       │
│            │                 │                  │                                  │
│            └─────────────────┴──────────────────┘                                  │
│                            │                                                      │
│                            ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐       │
│  │                    INFRASTRUCTURE LAYER                                 │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │       │
│  │  │ Redis Client │  │ S3 Client    │  │ Celery App    │              │       │
│  │  │              │  │              │  │               │              │       │
│  │  │ • caching    │  │ • upload      │  │ • task queue  │              │       │
│  │  │ • rate limit │  │ • download    │  │ • routing     │              │       │
│  │  │ • stampede   │  │ • presigned   │  │ • config      │              │       │
│  │  │   prevention │  │ • delete      │  │               │              │       │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │       │
│  └─────────┼─────────────────┼──────────────────┼──────────────────────┘       │
│            │                 │                  │                                  │
└────────────┼─────────────────┼──────────────────┼────────────────────────────────┘
             │                 │                  │
             ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────────┐
│  PostgreSQL  │  │    Redis     │  │  AWS S3 Bucket                   │
│  Database    │  │  (ElastiCache)│  │  (Receipt Storage)                │
│              │  │              │  │                                    │
│  • Users     │  │  • Cache     │  │  • Receipt files                 │
│  • Categories│  │  • Rate limit│  │  • PDF reports                  │
│  • Tags      │  │  • Celery    │  │  • Presigned URLs                │
│  • Transactions│ │    broker   │  │                                    │
│  • Receipts  │  │  • Results   │  │                                    │
│  • Reports   │  │    backend   │  │                                    │
└──────────────┘  └──────────────┘  └──────────────────────────────────┘
```

---

## 🔄 Background Processing Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CELERY WORKER (ECS Task)                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Celery Application                                 │   │
│  │  • Task Queue: reports                                                │   │
│  │  • Serialization: JSON                                               │   │
│  │  • Time Limits: 5 min hard, 4 min soft                               │   │
│  │  • Retry Policy: 3 max retries, 60s delay                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                            │                                                  │
│                            ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    TASK HANDLERS                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │ Report Generation Task                                        │   │   │
│  │  │ app.modules.reports.tasks.generate_pdf_report                │   │   │
│  │  │                                                               │   │   │
│  │  │ 1. Fetch transaction data                                     │   │   │
│  │  │ 2. Generate charts (Matplotlib)                               │   │   │
│  │  │ 3. Create PDF (ReportLab)                                     │   │   │
│  │  │ 4. Upload to S3                                               │   │   │
│  │  │ 5. Update report status                                       │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                            │                                                  │
│                            ▼                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    INFRASTRUCTURE                                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │   │
│  │  │ PostgreSQL   │  │ Redis        │  │ AWS S3       │            │   │
│  │  │ (Read Data)  │  │ (Task Queue) │  │ (Store PDF)  │            │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    FLOWER (Monitoring Dashboard)                      │   │
│  │  • Task monitoring                                                    │   │
│  │  • Worker status                                                      │   │
│  │  • Queue statistics                                                   │   │
│  │  • Task history                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Component Details

### 1. **Middleware Layer**
- **RequestIDMiddleware**: Generates unique request IDs for tracing
- **TimingMiddleware**: Measures request processing time
- **LoggingMiddleware**: Structured JSON logging
- **PrometheusMiddleware**: Metrics collection
- **CORSMiddleware**: Cross-origin resource sharing
- **Rate Limiting Middleware**: Redis-based rate limiting

### 2. **Router Layer** (9 Modules)
- **Auth Router**: Authentication endpoints
- **Users Router**: User management
- **Categories Router**: Category CRUD
- **Tags Router**: Tag CRUD
- **Transactions Router**: Transaction management
- **Analytics Router**: Analytics and dashboards
- **Receipts Router**: Receipt upload/download
- **Reports Router**: Report generation requests
- **Monitoring Router**: Health checks and metrics

### 3. **Service Layer** (8 Services)
Each service contains business logic:
- **AuthService**: Authentication, JWT tokens, password hashing
- **UserService**: Profile management, password changes
- **CategoryService**: Category operations
- **TagService**: Tag operations
- **TransactionService**: Transaction CRUD, filtering, pagination
- **AnalyticsService**: Dashboard, trends, breakdowns, cash flow
- **ReceiptService**: S3 upload/download, presigned URLs
- **ReportService**: Report job management, status tracking

### 4. **Repository Layer** (6 Repositories)
Data access layer with database queries:
- **CategoryRepository**: Category database operations
- **TagRepository**: Tag database operations
- **TransactionRepository**: Transaction queries with filters
- **AnalyticsRepository**: Aggregations, group by, time series
- **ReceiptRepository**: Receipt database operations
- **ReportRepository**: Report job database operations

### 5. **Infrastructure Layer**
- **RedisClient**: Caching, rate limiting, stampede prevention
- **S3Client**: File upload/download, presigned URLs
- **CeleryApp**: Background task processing
- **Database Session**: SQLAlchemy async session management

### 6. **Models Layer** (6 Models)
SQLAlchemy ORM models:
- **User**: User accounts, authentication
- **Category**: Expense/income categories
- **Tag**: Transaction tags
- **Transaction**: Expenses and income
- **Receipt**: Receipt metadata
- **ReportJob**: Report generation jobs

---

## 🔄 Data Flow Examples

### Example 1: User Registration Flow
```
Client → ALB → FastAPI
  → RequestIDMiddleware (generate ID)
  → CORS Middleware (validate origin)
  → Rate Limiting (check limits)
  → Auth Router (/register)
  → Auth Service (validate, hash password)
  → User Repository (create user)
  → PostgreSQL (insert user)
  → Redis (cache user data)
  → Response (user + tokens)
```

### Example 2: Transaction Creation Flow
```
Client → ALB → FastAPI
  → Middleware (ID, timing, logging)
  → Auth Dependency (validate JWT)
  → Transactions Router (/transactions)
  → Transaction Service (validate, process)
  → Transaction Repository (query category, tags)
  → PostgreSQL (insert transaction)
  → Redis (invalidate cache)
  → Response (transaction data)
```

### Example 3: Dashboard Analytics Flow
```
Client → ALB → FastAPI
  → Middleware
  → Auth Dependency
  → Analytics Router (/dashboard)
  → Analytics Service (check cache)
  → Redis (cache hit?) → Return cached data
  → OR → Analytics Repository (query DB)
  → PostgreSQL (aggregate queries)
  → Redis (store cache, 10min TTL)
  → Response (dashboard data)
```

### Example 4: Report Generation Flow
```
Client → ALB → FastAPI
  → Reports Router (/reports)
  → Report Service (create job)
  → Report Repository (save job)
  → PostgreSQL (insert job)
  → Celery (enqueue task)
  → Redis (task queue)
  → Celery Worker (process task)
  → Report Task (generate PDF)
  → PostgreSQL (read transactions)
  → Matplotlib (generate charts)
  → ReportLab (create PDF)
  → S3 (upload PDF)
  → PostgreSQL (update job status)
  → Response (job ID)
```

### Example 5: Receipt Upload Flow
```
Client → FastAPI
  → Receipts Router (/presigned-upload)
  → Receipt Service (generate URL)
  → S3 Client (create presigned URL)
  → AWS S3 (generate URL)
  → Response (presigned URL)

Client → AWS S3 (direct upload)
  → S3 (store file)

Client → FastAPI
  → Receipts Router (/confirm-upload)
  → Receipt Service (save metadata)
  → Receipt Repository (create record)
  → PostgreSQL (insert receipt)
  → Response (receipt data)
```

---

## 🔗 Component Interactions

### Authentication Flow
```
Router → Service → Security (JWT) → Repository → Database
                ↓
            Redis (token cache)
```

### Caching Strategy
```
Service → Redis (check cache)
    ↓ (miss)
Repository → Database → Service → Redis (store) → Response
```

### Background Jobs
```
Service → Celery → Redis Queue → Worker → Task → S3/Database
```

### File Operations
```
Service → S3 Client → AWS S3 (presigned URL)
Client → AWS S3 (direct upload)
Service → S3 Client → AWS S3 (verify) → Database (metadata)
```

---

## 📊 Component Responsibilities

| Component | Responsibility | Dependencies |
|-----------|---------------|--------------|
| **Router** | HTTP request handling, validation | Service, Dependencies |
| **Service** | Business logic, orchestration | Repository, Infrastructure |
| **Repository** | Data access, queries | Database, Models |
| **Infrastructure** | External services (Redis, S3, Celery) | AWS Services |
| **Models** | Data structure, ORM mapping | Database |
| **Middleware** | Cross-cutting concerns | Core utilities |
| **Dependencies** | Dependency injection | Security, Database |

---

## 🎯 Architecture Principles

1. **Separation of Concerns**: Each layer has a single responsibility
2. **Dependency Injection**: FastAPI dependencies for loose coupling
3. **Async/Await**: Full async support for I/O operations
4. **Caching Strategy**: Redis caching with stampede prevention
5. **Background Processing**: Celery for long-running tasks
6. **Error Handling**: Centralized exception handlers
7. **Logging**: Structured JSON logging with request IDs
8. **Metrics**: Prometheus metrics for observability

---

**Documentation Location**: `docs/COMPONENTS_ARCHITECTURE.md`
