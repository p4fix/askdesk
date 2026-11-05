# Technical Decisions & Architectural Log (DECISIONS.md)

This document tracks foundational design choices, tradeoffs, alternatives considered, and edge-case bug fixes encountered during the development of AskDesk.

---

## Decision 001: Vector Store Choice — pgvector vs. Standalone Vector Databases
* **Date**: Phase 1
* **Context**: Need a scalable vector storage and search engine for storing company documentation chunks and executing similarity queries for RAG.
* **Options Considered**:
  1. *Pinecone / Qdrant (Standalone Vector DB)*
  2. *pgvector in PostgreSQL*
* **Decision**: Adopted `pgvector` inside PostgreSQL.
* **Rationale**:
  - **ACID Transactions**: Relational metadata (Organization, Document, Upload Status) and vector embeddings reside in the same database. Document deletion cascades atomically to chunk vectors without sync delay.
  - **Multi-Tenant Security**: Vector retrieval queries can apply an SQL `WHERE organization_id = :org_id` filter in the exact same execution plan, eliminating cross-tenant vector leakage.
  - **Operational Simplicity**: One less external database to manage, backup, and monitor.
* **Tradeoffs**: Extremely large scale (100M+ vectors) requires sharding or memory tuning; acceptable since helpdesk documentation footprints per tenant typically number in thousands or tens of thousands of chunks.

---

## Decision 002: Multi-Tenancy Architecture — Row-Level Scoping vs. Schema-per-Tenant
* **Date**: Phase 1
* **Context**: Support agents and tickets belong to distinct organizations and must never leak across tenants.
* **Options Considered**:
  1. *Database-per-tenant*: Maximum isolation, but prohibitive infrastructure overhead.
  2. *Schema-per-tenant (`django-tenants`)*: Complex migrations and connection pooling issues.
  3. *Row-level isolation (`organization_id` foreign keys)*: Simple migrations, unified pooling, strict queryset filtering.
* **Decision**: Implemented Row-Level isolation with `Organization` foreign keys.
* **Rationale**:
  - Enforced via base model abstract classes and DRF querysets overriding `get_queryset()` to filter by `request.user.organization`.
  - Simplifies testing and automated CI pipelines.

---

## Decision 003: Vector Indexing Algorithm — HNSW vs. IVFFlat
* **Date**: Phase 1
* **Context**: High-speed nearest-neighbor search for document chunks.
* **Decision**: Standardized on **HNSW** (`vector_cosine_ops`).
* **Rationale**:
  - `IVFFlat` requires an upfront training step over existing data; accuracy and recall degrade if data is added incrementally.
  - `HNSW` maintains high recall ($>95\%$) immediately upon chunk ingestion without retraining steps.


---

## Decision 004: Ticket State Machine and Cross-Tenant Assignee Security
* **Date**: Phase 2
* **Context**: Tickets transition across status lifecycle states (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`) with priority tiers (`LOW`, `MEDIUM`, `HIGH`, `URGENT`) and support agent assignment.
* **Security Risk**: If an assignee UUID is accepted without organization validation, an attacker could assign a ticket to an agent in a foreign tenant, leaking issue visibility across tenant boundaries.
* **Decision**: Defense-in-depth enforcement:
  1. **Serializer Level**: `TicketCreateSerializer` and `TicketUpdateSerializer` dynamically scope `assigned_to` queryset to the requesting user's organization in `__init__`, and explicit `validate_assigned_to()` ensures matching `organization_id`.
  2. **Model Level**: `Ticket.clean()` asserts `assigned_to.organization_id == self.organization_id` on save.
* **Rationale**: Multi-layered defense ensures data invariants hold whether tickets are modified via REST API, Django Admin, shell scripts, or Celery asynchronous tasks.

---

## Decision 005: Ticket Comment Threading and Internal Staff Notes
* **Date**: Phase 2
* **Context**: Helpdesk workflows require threaded customer replies alongside private internal notes for tier-1/tier-2 agent collaboration.
* **Options Considered**:
  1. *Separate tables for CustomerReplies and InternalNotes*: Increased schema complexity, duplicated pagination and ordering logic.
  2. *Single unified `TicketComment` with `is_internal_note` flag*: Single chronological timeline, straightforward queryset filtering based on audience.
* **Decision**: Adopted unified `TicketComment` table with `is_internal_note` boolean field.
* **Rationale**: Enables unified chronological conversation threads in the UI while allowing clean filtering (`is_internal_note=False`) when rendering customer-facing views.

---

## Decision 006: Dual-Database Compatibility for pgvector HNSW Indexing (`SafeHnswIndex`)
* **Date**: Phase 3
* **Context**: Production vector retrieval utilizes PostgreSQL with `pgvector` and an HNSW cosine distance index (`vector_cosine_ops`).
* **Problem**: When running automated CI/CD test suites or lightweight local development using SQLite (`USE_SQLITE=True`), SQLite's DDL parser throws `OperationalError: near "WITH": syntax error` when encountering PostgreSQL-specific HNSW index parameters (`m=16, ef_construction=64`).
* **Decision**: Implemented `SafeHnswIndex` subclassing `pgvector.django.HnswIndex`.
  - On PostgreSQL (`schema_editor.connection.vendor == 'postgresql'`), emits full HNSW index DDL.
  - On non-PostgreSQL engines (e.g. SQLite), emits a safe DDL comment `Statement('-- noop non-postgres hnsw index')`.
* **Rationale**: Decouples fast unit/API test suites from external database infrastructure while guaranteeing production PostgreSQL maintains high-speed HNSW indexing.

---

## Decision 007: Pluggable Embedding Architecture with Deterministic Mock Provider
* **Date**: Phase 3
* **Context**: Document chunks must be converted into 1536-dimensional vector embeddings for semantic retrieval.
* **Problem**: Relying solely on live external LLM API endpoints during automated test suites causes flaky tests, rate limiting, network latency, and CI credential dependency.
* **Decision**: Designed an interchangeable provider pattern with `BaseEmbeddingService`:
  - `MockEmbeddingService`: Generates deterministic, L2-normalized 1536-dimensional unit vectors derived from cryptographic SHA-256 digests and vocabulary token hashes.
  - `OpenAIEmbeddingService`: Production client targeting `text-embedding-3-small` using standard library `urllib` (zero third-party SDK overhead).
* **Rationale**: Enables reliable, isolated SDET testing where identical inputs yield identical vectors and overlapping text tokens produce positive cosine similarity, without requiring API keys.

---

## Decision 008: Human-in-the-Loop RAG Architecture vs. Autonomous Direct Auto-Replies
* **Date**: Phase 4
* **Context**: Customer support platforms powered by Large Language Models can generate answers instantly, but autonomous dispatch poses high business and compliance risks (hallucinations, erroneous refund promises, brand liability).
* **Options Considered**:
  1. *Fully Autonomous Auto-Reply Bot*: Instantly sends AI-generated responses to tickets. High risk of incorrect customer promises.
  2. *Human-in-the-Loop (HITL) Draft Lifecycle*: AI synthesizes an `AIDraftResponse` with confidence scoring and structured citations; a human support agent reviews, optionally edits, and accepts/rejects before dispatching to the ticket.
* **Decision**: Adopted Human-in-the-Loop Draft Architecture with explicit review state transitions (`DRAFT_GENERATED` -> `ACCEPTED` / `REJECTED`).
* **Rationale**:
  - Provides a critical safety barrier against hallucinations while drastically accelerating agent productivity (from minutes drafting to seconds reviewing).
  - Maintains full auditability: records `suggested_reply`, `final_edited_reply`, `reviewed_by`, and `reviewed_at`.
  - When accepted, atomically creates a `TicketComment` on the ticket and updates ticket status from `OPEN` to `IN_PROGRESS`.

---

## Decision 009: Multi-Tenant Vector Similarity Retrieval with Dual-Database Fallback
* **Date**: Phase 4
* **Context**: Vector search queries must retrieve semantic chunks strictly within the authenticated user's organization tenant boundary.
* **Problem**: In PostgreSQL with `pgvector`, vector distance queries use the `<=>` cosine distance operator (`CosineDistance`). In local SQLite test environments (`USE_SQLITE=True`), native vector distance SQL operators do not exist.
* **Decision**: Built `VectorSearchService` with dual execution paths:
  1. **PostgreSQL Path**: Applies an indexed HNSW cosine distance query (`CosineDistance('embedding', query_vector)`) strictly pre-filtered by `organization_id` and `document__status='PROCESSED'`.
  2. **SQLite / SDET Fallback Path**: Pulls candidate chunks for the tenant and executes vectorized in-memory cosine similarity calculation in Python ($\frac{u \cdot v}{\|u\| \|v\|}$).
* **Rationale**: Guarantees zero cross-tenant vector leakage at the database layer in production while allowing automated CI/CD test suites to execute instantaneously without requiring a live Postgres/pgvector instance.

---

## Decision 010: Bounded-Context Anti-Hallucination Prompting & Explicit Citation Traceability
* **Date**: Phase 4
* **Context**: Enterprise support agents require factual grounding they can verify before approving customer messages.
* **Decision**: Implemented two synchronized mechanisms:
  1. **Prompt Guardrail**: System prompt strictly restricts the LLM to provide answers *only* from the supplied context chunks. When context is missing or irrelevant, LLM emits a standardized fallback message: `"I do not have enough documentation to answer this question. Please reach out to our human support team for further assistance."`
  2. **Structured Traceability (`AIDraftCitation`)**: Each draft response records foreign-key links to cited `DocumentChunk` records, along with `relevance_score`, `source_title`, `page_number`, and `cited_excerpt`.
* **Rationale**: Eliminates guesswork for support agents by surfacing exact documentation sources and page numbers directly alongside AI draft replies.
