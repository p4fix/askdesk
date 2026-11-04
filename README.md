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
- [ ] **Phase 4: RAG Retrieval Engine & Grounded AI Suggestion Service**
- [ ] **Phase 5: React + TypeScript Frontend Application**
- [ ] **Phase 6: Real-Time Updates (SSE) & Rigorous SDET Testing**
- [ ] **Phase 7: Production Containerization & Deployment**

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

### 4. Run Test Suite
```bash
cd backend
pytest
```

---

## 📡 REST API Reference

### Authentication (`/api/v1/auth/`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register/` | Public | Register initial Organization and Admin account |
| `POST` | `/api/v1/auth/login/` | Public | Authenticate; returns JWT access and refresh tokens |
| `POST` | `/api/v1/auth/refresh/` | Public | Refresh expired access token |
| `GET` | `/api/v1/auth/me/` | Authenticated | Fetch current user profile and tenant metadata |
| `POST` | `/api/v1/auth/users/` | Admin only | Provision/list support agents in organization |

### Ticket Management (`/api/v1/tickets/`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/tickets/` | Agent / Admin | List tickets (filters: `status`, `priority`, `assigned_to`, `search`) |
| `POST` | `/api/v1/tickets/` | Agent / Admin | Submit a new customer support ticket |
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
