"""Initialize LangChain model clients from independent provider settings."""

import os
from dotenv import load

load()

llm_provider = os.getenv("LLM_PROVIDER", "docker").lower()
embedding_provider = os.getenv("EMBEDDING_PROVIDER", "docker").lower()

# Chat and embedding providers are selected independently so deployments can,
# for example, keep embeddings local while using a hosted chat model.
# --- LLM Initialization ---
if llm_provider == "docker":
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        base_url=os.getenv("LOCAL_AI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("LOCAL_AI_API_KEY", "not-needed"),
        model=os.getenv(
            "LOCAL_LLM_MODEL", "hf.co/bartowski/llama-3.2-1b-instruct-gguf"
        ),
    )
else:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini"),
    )

# --- Embedding Initialization ---
if embedding_provider == "docker":
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        base_url=os.getenv("LOCAL_AI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("LOCAL_AI_API_KEY", "not-needed"),
        model=os.getenv("LOCAL_EMBEDDING_MODEL", "ai/embeddinggemma:latest"),
        # Some local OpenAI-compatible endpoints omit token-count metadata, so
        # disable LangChain's context-length preflight for this provider.
        check_embedding_ctx_length=False,
    )
else:
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )

# Export initialized clients for callers that need consistent model selection
# without rebuilding provider configuration in each module.