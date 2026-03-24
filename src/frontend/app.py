import os

import httpx
import streamlit as st

GENERATION_SERVICE_URL = os.environ.get("GENERATION_SERVICE_URL", "http://localhost:8080")

st.title("RAG Knowledge Assistant")

query = st.text_input("", placeholder="Ask a question about your documents and data...")

if st.button("Ask") and query:
    with st.spinner("Retrieving context and generating answer..."):
        try:
            response = httpx.post(
                f"{GENERATION_SERVICE_URL}/generate",
                json={"query": query},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            st.markdown(data["answer"])

            with st.expander("Sources"):
                for citation in data["citations"]:
                    st.markdown(
                        f"- **{citation['source_key']}** — {citation['section']} "
                        f"(`{citation['type']}`)"
                    )

        except httpx.HTTPStatusError as e:
            st.error(f"The generation service returned an error: {e.response.status_code}")
        except httpx.ConnectError:
            st.error("Could not connect to the generation service. Is it running?")
        except Exception as e:
            st.error(f"Unexpected error: {e}")
