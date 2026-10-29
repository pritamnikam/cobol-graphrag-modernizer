import os
from dotenv import load

load()

llm_provider = os.getenv("LLM_PROVIDER", "docker").lower()
embedding_provider = os.getenv("EMBEDDING_PROVIDER", "docker").lower()

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
        # Note: Some local embedding endpoints require disabling check for dimensions
        check_embedding_ctx_length=False,
    )
else:
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )