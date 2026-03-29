import os
import uuid

import httpx
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2 import id_token

GENERATION_SERVICE_URL = os.environ.get("GENERATION_SERVICE_URL", "http://localhost:8080")


def _auth_headers(audience: str) -> dict:
    """Return an Authorization header when calling a private Cloud Run service.
    Falls back to no auth for local development (localhost audiences)."""
    if "localhost" in audience or "127.0.0.1" in audience:
        return {}
    try:
        token = id_token.fetch_id_token(Request(), audience)
        return {"Authorization": f"Bearer {token}"}
    except Exception:
        return {}

st.set_page_config(page_title="RAG Knowledge Assistant", layout="centered")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; max-width: 760px; }
    .meta { color: #888; font-size: 0.78rem; margin-top: 0.4rem; }
</style>
""", unsafe_allow_html=True)

st.title("RAG Knowledge Assistant")
st.caption("Ask questions grounded in your documents and structured data.")

query = st.text_input(
    "Question",
    placeholder="What were the top 3 underperforming product lines in EMEA last quarter?",
    label_visibility="collapsed",
)

if st.button("Ask", type="primary", disabled=not bool(query)):
    correlation_id = str(uuid.uuid4())[:8]
    with st.spinner("Retrieving context and generating answer…"):
        try:
            headers = _auth_headers(GENERATION_SERVICE_URL)
            headers["X-Correlation-ID"] = correlation_id
            response = httpx.post(
                f"{GENERATION_SERVICE_URL}/generate",
                json={"query": query},
                headers=headers,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            with st.container(border=True):
                st.markdown(data["answer"])
                st.markdown(
                    f'<p class="meta">Model: {data["model"]} &nbsp;·&nbsp; '
                    f'Prompt tokens: {data["prompt_tokens"]} &nbsp;·&nbsp; '
                    f'Request: <code>{correlation_id}</code></p>',
                    unsafe_allow_html=True,
                )

            if data["citations"]:
                with st.expander(f"Sources ({len(data['citations'])})"):
                    for citation in data["citations"]:
                        st.markdown(
                            f"- **{citation['source_key']}** — {citation['section']} "
                            f"`{citation['type']}`"
                        )

        except httpx.HTTPStatusError as e:
            st.error(f"Generation service error: {e.response.status_code}")
        except httpx.ConnectError:
            st.error("Could not connect to the generation service.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")
