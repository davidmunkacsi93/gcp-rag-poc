# Phase 04 — Generation

Goal: given a query and a `FusedContext` from the retrieval phase, assemble a grounded prompt, call Gemini, and return a structured `GenerationResult` with the answer text and source citations.

> Prerequisites: Phase 03 complete. `retrieve(query)` returns a valid `FusedContext` for semantic, structured, and federated query types.

---

### Stream A — Infrastructure

**A1 — IAM for generation service account**
Create a dedicated `rag-poc-generation` service account in Terraform with the minimum permissions needed to run generation:

- `aiplatform.user` — call Gemini via Vertex AI
- `datastore.viewer` — read from Firestore for citation resolution (chunk and document metadata)

Add the service account resource and IAM bindings alongside the existing `rag-poc-retrieval` service account in `terraform/main.tf`. Do not duplicate any shared Terraform resources — reuse the existing project data source and locals.

---

### Stream B — Local Testing Environment

**B1 — Stub LLM for local testing**
Provide a `StubGenerationClient` that returns a deterministic templated answer without calling Gemini. The stub must:
- Accept the same prompt string as the real client
- Return a fixed answer that includes inline citation markers referencing the first context item (so downstream citation extraction can be tested)
- Report `prompt_tokens` as the character count of the prompt divided by 4 (rough approximation, sufficient for testing)

Wire the stub through the `GENERATION_STUB=true` environment variable, following the same pattern as `get_embedder()` in `src/ingestion/embedder.py` and `get_vector_search_client()` in `src/retrieval/vector_store.py`.

**B2 — Verify generation config loads correctly**
Confirm that `GenerationConfig.from_env()` loads all fields from environment variables with sensible defaults in both local and GCP modes. Add a manual verification step: run `python -c "from src.generation.config import GenerationConfig; print(GenerationConfig.from_env())"` in the local Docker environment and confirm all fields are populated.

---

### Stream C — Core Generation Components

> All generation modules live under `src/generation/`.

**C1 — Generation Config**
Write `src/generation/config.py` with a `GenerationConfig` dataclass following the same `from_env()` class method pattern as `src/ingestion/config.py`.

```python
@dataclass
class GenerationConfig:
    model_name: str = "gemini-2.0-flash-001"
    max_context_tokens: int = 8000
    max_output_tokens: int = 1024
    temperature: float = 0.2
    citation_style: str = "inline"  # e.g., [Source: doc_id, section]

    @classmethod
    def from_env(cls) -> "GenerationConfig":
        ...
```

Environment variable mapping:
- `GENERATION_MODEL` → `model_name`
- `GENERATION_MAX_CONTEXT_TOKENS` → `max_context_tokens`
- `GENERATION_MAX_OUTPUT_TOKENS` → `max_output_tokens`
- `GENERATION_TEMPERATURE` → `temperature`
- `GENERATION_CITATION_STYLE` → `citation_style`

**C2 — Prompt Builder**
Write `src/generation/prompt.py` with the following function:

```python
def build_prompt(query: str, context: FusedContext, config: GenerationConfig | None = None) -> str:
```

Responsibilities:
1. Construct a system instruction that tells Gemini to:
   - Answer using ONLY the provided context
   - Cite sources inline using the format `[Source: <source_ref>, <section>]` for semantic results and `[Source: SQL, <source>]` for structured results
   - Say "I don't have enough information to answer this question." if the context is insufficient
   - Never fabricate information beyond what is in the context
2. Format each `ContextItem` from the `FusedContext` as a numbered reference block:
   - Semantic items: include `source_ref` (the `source_key`), `content` (the chunk text), and `score`
   - Structured items: include `source_ref` (the `generated_sql`), `content` (the formatted table rows), and label as "Structured Data"
3. Respect the `max_context_tokens` budget from `GenerationConfig` — estimate token count as `len(text) // 4` and truncate context items from the bottom of the ranked list if the budget is exceeded
4. Append the user query at the end of the prompt
5. Return the full prompt as a single string

**C3 — Generation Client**
Write `src/generation/client.py` with the following structure:

```python
from abc import ABC, abstractmethod

class BaseGenerationClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, config: GenerationConfig) -> RawGenerationResponse:
        pass

@dataclass
class RawGenerationResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
```

Implementations:

- `VertexGenerationClient` — wraps `vertexai.generative_models.GenerativeModel`. Initialises `vertexai` with the project and location from environment variables. Calls `model.generate_content()` with `generation_config` set from the `GenerationConfig` fields (`max_output_tokens`, `temperature`). Extracts token counts from the response `usage_metadata`.
- `StubGenerationClient` — returns a deterministic response. The answer text is: `"Based on the provided context, {first 80 chars of prompt}... [Source: stub_source, stub_section]"`. Token counts are estimated from string lengths.

Factory function:

```python
def get_generation_client() -> BaseGenerationClient:
```

Returns `StubGenerationClient()` if `os.environ.get("GENERATION_STUB", "").lower() == "true"`, otherwise returns `VertexGenerationClient()`.

**C4 — Citation Assembler**
Write `src/generation/citations.py` with the following:

```python
@dataclass
class Citation:
    source_key: str      # e.g., "gs://bucket/doc.pdf" or "SQL"
    doc_id: str          # Firestore document ID (empty for structured)
    section: str         # section name or "N/A"
    type: str            # "semantic" or "structured"
    generated_sql: str   # empty for semantic results; the SQL query for structured

def extract_citations(answer: str, context: FusedContext) -> list[Citation]:
```

Extraction logic:
1. Use a regex to find all inline citations matching the pattern `[Source: <ref>, <detail>]` in the answer text
2. For each match, look up the corresponding `ContextItem` in the `FusedContext` by matching the `source_ref` field against the extracted `<ref>`
3. For semantic matches: populate `source_key` from the `ContextItem.source_ref`, `section` from the citation detail, `type = "semantic"`, and `generated_sql = ""`
4. For structured matches (where `<ref>` is `"SQL"`): populate `source_key = "SQL"`, `section = "N/A"`, `type = "structured"`, and `generated_sql` from the matching `ContextItem.source_ref`
5. De-duplicate citations by `(source_key, section)` — keep the first occurrence
6. Return the ordered list of unique `Citation` objects

**C5 — Generation Pipeline**
Write `src/generation/pipeline.py` as the callable interface that the deployment layer (Phase 05) and tests will use.

```python
@dataclass
class GenerationResult:
    answer: str
    citations: list[Citation]
    model: str
    prompt_tokens: int

def generate(query: str, context: FusedContext) -> GenerationResult:
```

Steps:
1. Load `GenerationConfig.from_env()`
2. Build the prompt via `build_prompt(query, context, config)`
3. Call `get_generation_client().generate(prompt, config)` to get the `RawGenerationResponse`
4. Extract citations via `extract_citations(response.text, context)`
5. Return `GenerationResult(answer=response.text, citations=citations, model=config.model_name, prompt_tokens=response.prompt_tokens)`

Expose `generate` as the single public API of the generation package. Wire the `__init__.py` accordingly:

```python
# src/generation/__init__.py
from src.generation.pipeline import generate, GenerationResult
from src.generation.citations import Citation
```

No caller should need to import individual components.

---

### Stream D — Tests

**D1 — Unit tests: prompt builder**
Write `tests/generation/test_prompt.py` against synthetic `FusedContext` fixtures. Cover:
- Context items are formatted as numbered reference blocks in the prompt
- System instruction contains the "answer using ONLY the provided context" directive
- System instruction contains the "I don't have enough information" fallback directive
- Structured results are labelled differently from semantic chunks (include "Structured Data" label)
- Context truncation: build a `FusedContext` with items exceeding `max_context_tokens` and verify the prompt respects the budget (items are dropped from the tail)
- The user query appears at the end of the prompt

**D2 — Unit tests: citation assembler**
Write `tests/generation/test_citations.py` with synthetic answer strings containing inline citations. Cover:
- Single semantic citation `[Source: gs://bucket/doc.pdf, Section 3]` is correctly extracted
- Single structured citation `[Source: SQL, bigquery]` is correctly extracted with `generated_sql` populated
- Multiple citations in one answer — all are extracted in order
- Duplicate citations (same source_key and section) are de-duplicated
- Answer with no citations returns an empty list
- Malformed citation markers (missing bracket, no comma) are ignored

**D3 — Local integration test**
Write `tests/generation/test_e2e_local_generation.py` to run the full retrieve-then-generate pipeline against the local Docker environment. Mark with `@pytest.mark.integration`.

Setup: set `GENERATION_STUB=true` so no Gemini API call is made. Use the stub embedder and stub vector store from the retrieval phase.

Assertions:
- Call `retrieve(query)` then `generate(query, context)` for a document-focused query
- The returned `GenerationResult.answer` is non-empty
- The returned `GenerationResult.citations` list has at least one entry
- The `GenerationResult.model` matches the configured model name
- The `GenerationResult.prompt_tokens` is a positive integer

**D4 — GCP end-to-end test**
Write `tests/generation/test_e2e_gcp_generation.py` to run the full pipeline against real GCP services. Mark with `@pytest.mark.gcp`.

Assertions for UC-01 ("What were the top 3 underperforming product lines in EMEA last quarter, and is there any internal remediation guidance applicable to this region?"):
- Answer is non-empty and contains at least 50 characters
- At least one citation references a real `source_key` (not empty, not "stub_source")
- At least one structured citation is present (the query triggers the structured path)

Assertions for UC-02 ("Run a preliminary due diligence summary for Project Apollo — include financial exposure, open risk items, and any regulatory considerations flagged in recent reports."):
- Answer is non-empty and contains at least 50 characters
- At least one semantic citation is present (the query triggers the semantic path for documents)
- Citations reference `source_key` values that exist in Firestore

---

### Completion Criteria

- [ ] Generation service account provisioned via Terraform with `aiplatform.user` and `datastore.viewer` roles
- [ ] `GenerationConfig.from_env()` loads all fields with correct defaults in both local and GCP modes
- [ ] `build_prompt()` respects the `max_context_tokens` budget and includes citation instructions
- [ ] `StubGenerationClient` returns deterministic answers with parseable inline citations
- [ ] `VertexGenerationClient` calls Gemini and returns a valid `RawGenerationResponse` with token counts
- [ ] `extract_citations()` correctly parses inline citations from both semantic and structured sources
- [ ] `generate(query, context)` returns a `GenerationResult` with answer, citations, model name, and token count
- [ ] Unit tests for prompt builder and citation assembler pass locally (`pytest tests/generation/test_prompt.py tests/generation/test_citations.py`)
- [ ] Local integration test passes with all stubs (`pytest -m integration tests/generation/`)
- [ ] GCP E2E test passes against real services (`pytest -m gcp tests/generation/`)
- [ ] All generation results carry citations sufficient for the frontend to render a "Sources" panel
