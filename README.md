# AgroChat MVP

**Intelligent agricultural chat-assistant powered by RAG (Retrieval-Augmented Generation)**

An AI assistant that provides reliable agronomic recommendations for coffee and cocoa farmers in Colombia, backed by official AGROSAVIA documents. Every answer includes source citations for full traceability.

## Architecture

- **Offline pipeline**: PDFs → chunking + metadata → embeddings → FAISS index → disk
- **Online pipeline**: query → embedding → FAISS top-k → prompt builder → LLM (Groq) → answer + sources
- **Embedding model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dims)
- **LLM provider**: Groq API (Llama 3.1 8B / 70B)
- **Vector store**: FAISS (CPU)

## Quick Start

```powershell
# 1. Clone and setup
cd agrochat-mvp
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configure
Copy-Item .env.example .env
# Edit .env → add your GROQ_API_KEY

# 3. Add your PDFs
# Place AGROSAVIA PDFs in:
#   data/docs/coffee/*.pdf
#   data/docs/cocoa/*.pdf

# 4. Build the index
python -m src.build_index

# 5. Run the assistant
python -m src.rag_cli
python -m src.rag_cli --lang ru      # multilingual demo
python -m src.rag_cli --top-k 3      # fewer chunks
```

## Project Structure

```
agrochat-mvp/
├── src/
│   ├── config.py          # Central configuration
│   ├── loader.py          # PDF loading + metadata
│   ├── indexer.py         # Chunking + FAISS index
│   ├── retriever.py       # Similarity search
│   ├── prompt_builder.py  # System/user prompt construction
│   ├── llm_client.py      # Groq API client
│   ├── response_builder.py# Answer + sources formatting
│   ├── build_index.py     # Offline indexing entry point
│   └── rag_cli.py         # Interactive CLI
├── data/
│   ├── docs/
│   │   ├── coffee/        # Coffee PDFs (AGROSAVIA)
│   │   └── cocoa/         # Cocoa PDFs (AGROSAVIA)
│   └── index/             # Persisted FAISS index (generated)
├── tests/
│   └── test_rag.py        # Evaluation suite
├── logs/                  # Runtime logs (generated)
├── docs/                  # Thesis deliverables
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Thesis Context

- **University**: KFU / ITIS
- **Focus**: Colombia / Latin America agricultural sector
- **Approach**: RAG with official sources, transparent citations
- **Scalability**: Architecture ready for more crops, languages, and interfaces (REST API, WhatsApp/Telegram bot)
