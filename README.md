# AskDesk — AI-Powered Helpdesk with RAG

AskDesk is a production-style, multi-tenant customer support helpdesk platform with Retrieval-Augmented Generation (RAG). It enables support agents to view, triage, and reply to customer tickets with AI-drafted responses grounded strictly in company documentation with precise citations.

---

## 🛠️ Architecture & Tech Stack

- **Backend**: Python 3.14+, Django 6.1+, Django REST Framework (DRF), JWT Authentication (`djangorestframework-simplejwt`).
- **Database & Vectors**: PostgreSQL 16 with `pgvector` for vector similarity search (cosine distance via HNSW indexing).
- **Multi-Tenancy**: Organization-based row-level data isolation.
- **Frontend**: React 18+, TypeScript, Vite, Tailwind CSS (Coming in Phase 5).
- **Testing**: `pytest`, `pytest-django`, REST API automated suites.
- **DevOps**: Docker, Docker Compose.

---

## 📁 Milestone Progress

- [x] **Phase 1: Project Foundation, Docker Environment & Multi-Tenant Auth**
  - Organization and custom User models with UUID primary keys.
  - JWT authentication with tenant claims in payloads.
  - Role-based permissions (`ADMIN`, `SUPPORT_AGENT`).
- [x] **Phase 2: Helpdesk Ticketing System & Conversation History**
  - Ticket lifecycle state machine (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`) and priority tiers (`LOW`, `MEDIUM`, `HIGH`, `URGENT`).
  - Strict tenant boundary on tickets, assignees, and threaded comments.
  - Advanced filtering (`status`, `priority`, `assigned_to`, search) and comment threading (`is_internal_note`).
- [x] **Phase 3: Document Ingestion, Chunking & pgvector Embeddings**
  - PDF & TXT text extraction pipelines (`pypdf` page parser + multi-encoding decoder).
  - Semantic recursive character splitter with sliding token overlap.
  - Pluggable embedding service (`MockEmbeddingService` for deterministic SDET tests, `OpenAIEmbeddingService` for production 1536-dim vectors).
  - Dual-database HNSW indexing (`SafeHnswIndex` for PostgreSQL pgvector + SQLite compatibility).
  - Document upload, chunk statistics, and atomic cascade deletion.
- [x] **Phase 4: RAG Retrieval Engine & Grounded AI Suggestion Service**
  - Multi-tenant cosine vector search with dual-database compatibility (Postgres `CosineDistance` + SQLite vectorized fallback).
  - Pluggable LLM generation service (`MockLLMService` for deterministic SDET suites, `OpenAILLMService` targeting `gpt-4o-mini`).
  - Strict bounded-context anti-hallucination guardrail with standardized fallback string.
  - Full structured citation traceability (`AIDraftCitation` with document title, page number, relevance score, and verbatim excerpt).
  - Human-in-the-loop review workflow (`ACCEPT` / `REJECT`) with auto-dispatching of ticket comments and ticket status progression.
- [x] **Phase 5: React + TypeScript Frontend Application**
  - Modern React 18+ Single Page Application with TypeScript, Vite, and Tailwind CSS.
  - Multi-tenant authentication context with JWT local storage and automatic 401 silent token refresh interceptor.
  - Helpdesk ticket management: list with status/priority filtering, search, and creation modal.
  - Side-by-side ticket detail workspace: threaded customer comments and internal staff notes.
  - Human-in-the-Loop RAG suggestion panel (`AIDraftPanel`) with real-time confidence scoring, expandable citation sources, live text editing, and Accept/Reject review actions.
  - Knowledge base document management: drag-and-drop PDF/TXT uploader and interactive vector similarity search inspector.
- [x] **Phase 6: Real-Time Updates (SSE) & Rigorous SDET Testing**
  - High-performance Server-Sent Events (SSE) streaming endpoint (`GET /api/v1/tickets/stream/`).
  - Thread-safe in-memory pub/sub `TenantEventBroadcaster` guaranteeing strict tenant isolation.
  - Live client synchronization for `ticket.created`, `ticket.updated`, `comment.added`, and `rag.draft_reviewed`.
  - Frontend `useRealtimeStream` hook with browser `EventSource` auto-reconnection and query parameter JWT authorization.
  - Comprehensive 15-test automated SDET suite covering multi-tenant eavesdropping prevention, cross-tenant mutation defense, and high-concurrency event broadcasting.
- [x] **Phase 7: Production Containerization & Deployment**
  - Multi-stage, security-hardened `Dockerfile` for Django backend with non-root user `askdesk` and Gunicorn WSGI runtime.
  - Automated database readiness probe and migration lifecycle hook (`entrypoint.sh`).
  - Multi-stage `Dockerfile` for React SPA with Node 20 build and Nginx 1.27 Alpine production runtime.
  - Nginx reverse proxy configuration with SSE real-time streaming optimization (`proxy_buffering off;`, extended timeout).
  - Production `docker-compose.yml` and `docker-compose.prod.yml` orchestrating PostgreSQL with `pgvector`, Django, and Nginx.
  - Automated container healthcheck endpoints (`GET /api/v1/health/` and `GET /health/`).

---

## 🚀 Quickstart

### 1. Prerequisites
- Python 3.11+
- Git
- Docker and Docker Compose (optional for local SQLite test mode, required for PostgreSQL + pgvector)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/p4fix/AskDesk.git
cd askdesk

# Create virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
cp backend/.env.example backend/.env
```

### 3. Run Migrations & Start Server
```bash
cd backend
python manage.py migrate
python manage.py runserver
```

### 4. Start Frontend Client (React + Vite)
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 5. Run Test Suites
```bash
# Backend pytest suite (76 unit, integration, and SDET tests)
cd backend
pytest

# Frontend unit tests
cd frontend
npm test
```

### 6. Production Deployment with Docker Compose
To deploy the entire production stack (PostgreSQL 16 + pgvector, Django + Gunicorn, and Nginx + React SPA) with a single command:
```bash
# Copy and customize production environment configuration
cp .env.production.example .env

# Build and start all multi-container services in detached mode
docker compose up -d --build

# Verify healthy status across all containers
docker compose ps
```
The application will be accessible at `http://localhost/` (or port 80/443 in production).

---

## 📡 REST API Reference

### System Health & Observability (`/api/v1/health/`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health/` | Public | Root container healthcheck probe |
| `GET` | `/api/v1/health/` | Public | Production healthcheck verifying database and pgvector status |

### Authentication (`/api/v1/auth/`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register/` | Public | Register initial Organization and Admin account |
| `POST` | `/api/v1/auth/login/` | Public | Authenticate; returns JWT access and refresh tokens |
| `POST` | `/api/v1/auth/refresh/` | Public | Refresh expired access token |
| `GET` | `/api/v1/auth/me/` | Authenticated | Fetch current user profile and tenant metadata |
| `POST` | `/api/v1/auth/users/` | Admin only | Provision/list support agents in organization |

### Ticket Management & Real-Time Streams (`/api/v1/tickets/`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/tickets/` | Agent / Admin | List tickets (filters: `status`, `priority`, `assigned_to`, `search`) |
| `POST` | `/api/v1/tickets/` | Agent / Admin | Submit a new customer support ticket |
| `GET` | `/api/v1/tickets/stream/` | Agent / Admin | Real-Time Server-Sent Events (SSE) stream for live queue updates |
| `GET` | `/api/v1/tickets/{id}/` | Agent / Admin | Retrieve full ticket detail with conversation history |
| `PATCH` | `/api/v1/tickets/{id}/` | Agent / Admin | Update status, priority, or assignee |
| `POST` | `/api/v1/tickets/{id}/comments/` | Agent / Admin | Add public customer reply or internal staff note |

### Knowledge Base & Documentation (`/api/v1/documents/`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/documents/` | Agent / Admin | List uploaded documentation and chunk statistics |
| `POST` | `/api/v1/documents/upload/` | Admin only | Upload `.pdf` or `.txt` file; triggers chunking & embedding |
| `GET` | `/api/v1/documents/{id}/` | Agent / Admin | Retrieve document details with extracted snippet previews |
| `DELETE` | `/api/v1/documents/{id}/` | Admin only | Delete document; atomically cascades all vector chunks |

### RAG Retrieval & AI Suggestions (`/api/v1/tickets/` & `/api/v1/rag/`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/tickets/{id}/ai-draft/` | Agent / Admin | Triggers RAG pipeline; returns grounded draft reply with structured citations |
| `GET` | `/api/v1/tickets/{id}/ai-draft/` | Agent / Admin | Retrieves the latest AI suggestion draft for a ticket |
| `POST` | `/api/v1/tickets/{id}/ai-draft/review/` | Agent / Admin | Review draft (`ACCEPT`/`REJECT`); automatically dispatches formal comment on accept |
| `GET` | `/api/v1/rag/search/?query={q}` | Agent / Admin | Direct vector similarity semantic search over tenant knowledge base chunks |

