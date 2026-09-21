# Sovereign Industrial AI Workbench

An on-premise, confidential AI workbench utilizing local open-weight models (Qwen 2.5, Qwen 2.5-VL) powered by LangGraph, LangChain, FAISS RAG, and FastAPI, paired with a modern **Google Gemini-inspired chat interface**.

---

## Features

- **Google Gemini-Inspired Frontend**:
  - Iridescent Google Gemini sparkle theme, branding, and styling.
  - Dark mode (default) and Light mode with persistent state.
  - Collapsible sidebar with conversation history (`localStorage` + backend session `thread_id`).
  - Welcome hero with quick-action suggestion prompt cards.
  - Rich Markdown rendering with headings, tables, quotes, and syntax-highlighted code blocks with 1-click copy.
  - **Interactive Document Generation Cards**: Automatic download badges for generated Word (`.docx`), Excel (`.xlsx`), PowerPoint (`.pptx`), and PDF (`.pdf`) files.
  - **Agent State Inspector**: Collapsible verification badge (`PASS` / `FAIL`), model router decision, and tools executed.
  - Voice dictation (Speech-to-Text) and audio read aloud (Text-to-Speech).
  - Attached document / image upload preview chip.
- **Backend & Local AI Core**:
  - Query analysis and automatic model routing (`qwen2.5:3b`, `qwen2.5vl:3b`).
  - Tool execution: document generation (`docx`, `xlsx`, `pptx`, `pdf`), dataset analysis, calculators.
  - RAG with local FAISS vector store and document indexing.
  - Output verification and automatic correction loop.
  - SQLite checkpointer for session state persistence.

---

## Getting Started

### 1. Prerequisites
- **Python 3.10+** (Virtual environment configured in `venv/`)
- **Ollama** running locally:
  ```bash
  ollama serve
  ollama pull qwen2.5:3b
  ollama pull qwen2.5vl:3b
  ollama pull nomic-embed-text
  ```

### 2. Launch the Application

Double-click `run_workbench.bat` or run:

```bash
# Using the project virtual environment:
.\myenv\Scripts\python.exe run_workbench.py
```

This will start the FastAPI backend on `http://127.0.0.1:8000` and automatically open the Gemini UI in your default browser.

---

## API Endpoints

- `GET /` — Serves the Google Gemini chat interface
- `POST /api/chat` — LangGraph agent turn execution with tool calling, memory, and verification
- `POST /api/upload` — Upload files (.pdf, .docx, .xlsx, .pptx, .png, .jpg)
- `POST /api/upload-and-index` — Upload and index documents into FAISS vector database
- `POST /api/input-directory` — Index entire folders into FAISS vector store
- `GET /api/files` — List all generated and uploaded files
- `GET /api/download/{filename}` — Download generated or uploaded files
- `GET /api/health` — Check server and sovereign mode health

