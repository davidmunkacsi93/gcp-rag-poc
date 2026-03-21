# Architecture

## C4 Model

### L1 — System Context

```mermaid
C4Context
  title System Context — GCP RAG Platform

  Person(analyst, "Enterprise Analyst")
  Person(dealteam, "Deal Team / Risk Officer")

  System(rag, "GCP RAG Platform")

  System_Ext(gcs_docs, "GCS (documents)\nBox substitute")
  System_Ext(cloudsql, "Cloud SQL\nSnowflake substitute")
  System_Ext(bigquery_ext, "BigQuery (Global)")

  Rel(analyst, rag, "Asks business questions", "HTTPS / Chat UI")
  Rel(dealteam, rag, "Initiates DD workflows", "HTTPS / Chat UI")
  Rel(rag, gcs_docs, "Ingests documents from", "GCS API")
  Rel(rag, cloudsql, "Queries structured data from", "PostgreSQL")
  Rel(rag, bigquery_ext, "Queries global metrics from", "BigQuery API")
```

#### Components

| Element | Type | Description |
|---|---|---|
| Enterprise Analyst | User | Regional finance analyst querying across business metrics and internal documents |
| Deal Team / Risk Officer | User | Initiates multi-step due diligence workflows requiring cross-source synthesis |
| GCP RAG Platform | System | The platform under design — routes NL queries to the appropriate retrieval paths and returns grounded, cited answers |
| GCS (documents) | External System (POC substitute for Box) | GCS bucket holding internal reports, strategy documents, and guidance in `raw/` |
| Cloud SQL | External System (POC substitute for Snowflake) | PostgreSQL instance holding regional P&L, product-level metrics, and regional KPIs |
| BigQuery (Global) | External System | Global data warehouse owned by HQ — enterprise-wide metrics and reference data |

---

### L2 — Containers

```mermaid
C4Container
  title Container Diagram — GCP RAG Platform

  Person(user, "Analyst / Deal Team")

  System_Boundary(rag, "GCP RAG Platform") {
    Container(ui, "Chat Interface", "Web App / Cloud Run")
    Container(api, "RAG API", "Python / Cloud Run")
    Container(ingestion, "Ingestion Service", "Python / Cloud Run")
    ContainerDb(vectorstore, "Vector Store", "Vertex AI Vector Search")
    ContainerDb(docstore, "Document Store", "GCS")
    ContainerDb(metastore, "Metadata Store", "Firestore")
    Container(llm, "Generation Service", "Vertex AI / Gemini")
  }

  System_Ext(gcs_src, "GCS (documents)\nBox substitute")
  System_Ext(cloudsql, "Cloud SQL\nSnowflake substitute")
  System_Ext(bq, "BigQuery (Global)")

  Rel(user, ui, "Interacts with", "HTTPS")
  Rel(ui, api, "Sends queries to", "REST")
  Rel(api, vectorstore, "Semantic retrieval", "gRPC")
  Rel(api, bq, "Structured query (NL-to-SQL)", "BigQuery API")
  Rel(api, cloudsql, "Structured query (NL-to-SQL)", "PostgreSQL")
  Rel(api, llm, "Sends assembled context", "Vertex AI API")
  Rel(api, metastore, "Reads source lineage", "Firestore API")
  Rel(ingestion, gcs_src, "Pulls documents from", "GCS API")
  Rel(ingestion, docstore, "Stores chunks in", "GCS API")
  Rel(ingestion, vectorstore, "Writes embeddings to", "gRPC")
  Rel(ingestion, metastore, "Writes metadata to", "Firestore API")
```

> **Note:** The direct connections from the RAG API to Snowflake and BigQuery reflect the internal Structured Retriever component's responsibility, not a direct dependency of the API container itself. See L3 for the accurate component-level view.

#### Containers

| Container | Technology | Description |
|---|---|---|
| Chat Interface | Web App / Cloud Run | User-facing interface for natural-language query entry and response display. Stateless; delegates all logic to the RAG API. |
| RAG API | Python / Cloud Run | Central orchestrator. Receives queries, activates the appropriate retrieval paths, assembles context, and drives generation. |
| Ingestion Service | Python / Cloud Run | Offline pipeline that pulls documents from GCS, chunks and preprocesses them, generates embeddings via Vertex AI, and writes to platform storage. Runs on schedule or event trigger. |
| Vector Store | Vertex AI Vector Search | Stores dense vector embeddings of document chunks. Queried by the Semantic Retriever for nearest-neighbour search. |
| Document Store | GCS | Persistent storage for raw and chunked documents post-ingestion. Source of truth for document content. |
| Metadata Store | Firestore | Stores document metadata, ingestion state, and chunk-to-source lineage records used for citation resolution. |
| Generation Service | Vertex AI / Gemini | Receives an assembled prompt with retrieved context and produces the final grounded answer. |

---

### L3 — RAG API (Component)

```mermaid
C4Component
  title Component Diagram — RAG API

  Container_Boundary(api, "RAG API") {
    Component(router, "Query Router")
    Component(retriever_semantic, "Semantic Retriever")
    Component(retriever_structured, "Structured Retriever")
    Component(fusion, "Context Fusion")
    Component(prompt_builder, "Prompt Builder")
    Component(agent_planner, "Agent Planner")
  }

  ContainerDb(vectorstore, "Vector Store", "Vertex AI Vector Search")
  ContainerDb(metastore, "Metadata Store", "Firestore")
  System_Ext(bq, "BigQuery")
  System_Ext(cloudsql, "Cloud SQL\nSnowflake substitute")
  Container(llm, "Generation Service", "Gemini")

  Rel(router, retriever_semantic, "Activates")
  Rel(router, retriever_structured, "Activates")
  Rel(router, agent_planner, "Activates for agentic queries")
  Rel(retriever_semantic, vectorstore, "Queries")
  Rel(retriever_semantic, metastore, "Resolves source lineage")
  Rel(retriever_structured, bq, "Queries")
  Rel(retriever_structured, cloudsql, "Queries")
  Rel(fusion, prompt_builder, "Passes ranked context to")
  Rel(prompt_builder, llm, "Sends prompt to")
  Rel(agent_planner, retriever_semantic, "Calls iteratively")
  Rel(agent_planner, retriever_structured, "Calls iteratively")
  Rel(agent_planner, prompt_builder, "Passes final context to")
```

#### Components

| Component | Description |
|---|---|
| Query Router | Classifies the incoming query and determines which retrieval paths to activate — semantic, structured, or both. For agentic queries (UC-02), hands off to the Agent Planner. |
| Semantic Retriever | Performs nearest-neighbour search against the Vector Store to find relevant document chunks. Resolves chunk-to-source lineage via the Metadata Store for citation. |
| Structured Retriever | Translates the natural-language query into SQL and executes it against BigQuery or Cloud SQL. Owns all connections to structured external sources. |
| Context Fusion | Merges results from all active retrieval paths, de-duplicates, and re-ranks by relevance before passing to the Prompt Builder. |
| Prompt Builder | Assembles the final prompt: system instructions, retrieved context with citations, and the original query. Controls context window budget. |
| Agent Planner | Implements the agentic loop for multi-step workflows (UC-02). Plans a sequence of retrieval and reasoning steps, executes them iteratively, and hands the final assembled context to the Prompt Builder. |

---

## Data Architecture

### Data Sources & Ownership

| Source | Type | Owner | Content | Access Pattern |
|---|---|---|---|---|
| GCS (documents) | Unstructured | RAG Platform (POC substitute for Box) | Internal reports, strategy docs, risk assessments, guidance | Pull via GCS API on schedule or event |
| Cloud SQL (PostgreSQL) | Structured | RAG Platform (POC substitute for Snowflake) | Regional P&L, product-level metrics, regional KPIs | NL-to-SQL query at runtime |
| BigQuery (Global) | Structured | Global HQ / data platform | Enterprise-wide metrics, KPIs, reference data | NL-to-SQL query at runtime |
| GCS (Document Store) | Unstructured | RAG Platform | Chunked and raw documents post-ingestion | Internal — read by retrieval layer |
| Vertex AI Vector Search | Vector | RAG Platform | Embeddings of document chunks | Internal — semantic retrieval |
| Firestore | Semi-structured | RAG Platform | Document metadata, chunk-to-source lineage, ingestion state | Internal — lineage and citation resolution |

---

### Data Flow

```mermaid
flowchart LR
  subgraph Sources["Data Sources (POC)"]
    GCSR[(GCS\nraw/ documents\nBox substitute)]
    CSQL[(Cloud SQL\nPostgreSQL\nSnowflake substitute)]
    BQ[(BigQuery\nGlobal Metrics)]
  end

  subgraph Ingestion["Ingestion Pipeline"]
    PULL[Pull & Parse]
    CHUNK[Chunk & Preprocess]
    EMBED[Embed\nVertex AI]
  end

  subgraph Storage["Platform Storage"]
    GCSP[(GCS\nprocessed/ chunks)]
    VS[(Vector Store\nVertex AI\nVector Search)]
    FS[(Firestore\nMetadata & Lineage)]
  end

  subgraph Query["Query Path"]
    ROUTER[Query Router]
    SEM[Semantic Retriever]
    STR[Structured Retriever]
    FUSION[Context Fusion]
    GEN[Gemini Generation]
  end

  GCSR -->|GCS API| PULL
  PULL -->|doc metadata\ntitle, type, source key| FS
  PULL --> CHUNK
  CHUNK -->|chunk text\n+ section| GCSP
  CHUNK -->|chunk records\nlinked to doc| FS
  GCSP -->|chunks| EMBED
  EMBED -->|embeddings| VS

  ROUTER --> SEM --> VS
  SEM -->|resolve chunk → source| FS
  ROUTER --> STR
  STR -->|NL-to-SQL| BQ
  STR -->|NL-to-SQL| CSQL
  SEM & STR --> FUSION --> GEN
```

---

### Data Governance Principles

- **Lineage** — every answer chunk is traceable to a source document or query via Firestore metadata
- **No data duplication at rest** — structured sources (Cloud SQL, BigQuery) are queried live; only documents are ingested and stored
- **Access control** — service accounts follow least-privilege; Cloud SQL credentials are stored in Secret Manager
- **Data residency** — all GCP-managed storage (GCS, Firestore, Vector Search) is provisioned in a single agreed region
- **Retention** — ingested document chunks inherit the retention policy of the source; metadata is retained for the lifetime of the POC
