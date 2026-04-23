# ⚖️ LegislAI

**Agentic legislative intelligence powered by LangGraph.** LegislAI autonomously routes natural-language queries through a 4-node RAG pipeline — retrieving bill text from a ChromaDB vector store, searching the web for live context, scoring sector-level risk, and producing executive summaries or formal policy memos.

> Built on LangGraph 0.2 · ChromaDB · Tavily · Gemini / Claude / GPT-4o (swappable at runtime)

---

## Demo

```
Query: "Compare bills 42 and 108 on healthcare and energy sectors"

→ Router    extracts task=compare, bill_ids=[42, 108]
→ Research  retrieves 12 chunks from ChromaDB + 8 Tavily web snippets
→ Analysis  scores 6 sectors, identifies 14 impacted states, builds head-to-head table
→ Writer    produces executive summary + comparative risk breakdown
```

---
<img width="1341" height="890" alt="Screenshot 2026-04-23 at 12 45 58 AM" src="https://github.com/user-attachments/assets/270b7773-f36c-4ed0-9229-a64ddd0189d1" />


## Architecture

```
User Query (plain English)
        │
        ▼
┌─────────────────┐
│   Router Node   │  Extracts: task type + bill IDs
│                 │  Tasks: "single" | "compare" | "memo"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Research Node  │  ChromaDB vector retrieval (top-k=6 per bill)
│                 │  + Tavily web search (live news & context)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Analysis Node  │  Sector risk scoring (1–5 scale)
│                 │  State impact mapping + bill comparison
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Writer Node   │  Executive summary OR formal policy memo
│                 │  Downloadable as .txt or .json
└─────────────────┘
```

All 4 nodes share a typed `AgentState` (LangGraph `TypedDict`) and stream updates to the UI in real time.

---

## Supported Query Types

| Type | Example Query | Output |
|------|--------------|--------|
| `single` | *"Analyze the impact of bill 1234"* | Risk scores, state map, executive summary |
| `compare` | *"Compare bills 42 and 108 on energy"* | Head-to-head sector table, winner by risk |
| `memo` | *"Draft a policy memo on bill 77"* | Full formal memo, downloadable as .txt |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | LangGraph 0.2+ |
| LLM (swappable) | Gemini 2.5 Flash · Claude 3.5 Haiku · GPT-4o |
| Vector store | ChromaDB |
| Web search | Tavily API |
| Embeddings | Google Generative AI Embeddings |
| Data source | Congress.gov API (118th Congress) |
| Frontend | Streamlit + Plotly |
| Ingestion | aiohttp async pipeline |

---

## Project Structure

```
LegislAI/
├── app.py                      # Streamlit frontend — live agent trace UI
├── requirements.txt
├── .env.example
│
├── src/
│   ├── agent.py                # LangGraph StateGraph — all 4 nodes + graph compile
│   ├── llm_provider.py         # Model-agnostic LLM factory (swap at runtime)
│   ├── tools.py                # ChromaDB retrieval · Tavily search · comparison util
│   ├── vector_db.py            # ChromaDB client + collection setup
│   ├── process_text.py         # Bill chunking logic
│   ├── load_to_db.py           # Embedding + ChromaDB ingestion
│   ├── ingest_bills_async.py   # Async Congress.gov ingestion pipeline
│   └── ingest_bills.py         # Sync fallback ingestion
│
└── data/
    ├── chroma_db/              # Persisted vector store
    ├── enriched_bills.json     # Fetched bill metadata + full text
    └── raw_bills.json          # Raw Congress.gov API response
```

---

## Quickstart

### 1. Clone & install

```bash
git clone https://github.com/mishitak468/LegislAI.git
cd LegislAI
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required — pick at least one LLM
GOOGLE_API_KEY=...          # Gemini (default, recommended)
ANTHROPIC_API_KEY=...       # Claude 3.5 Haiku
OPENAI_API_KEY=...          # GPT-4o

# Required — free at api.congress.gov
CONGRESS_API_KEY=...

# Recommended — enables live web search in Research node
# Free tier at tavily.com (1,000 searches/month)
TAVILY_API_KEY=...
```

### 3. Ingest bills into ChromaDB

```bash
# Step 1: Fetch bill text from Congress.gov API
python src/ingest_bills_async.py

# Step 2: Chunk, embed, and load into ChromaDB
python src/load_to_db.py
```

This populates `data/enriched_bills.json` and `data/chroma_db/`.

### 4. Launch

```bash
streamlit run app.py
```

Navigate to `http://localhost:8501`.

---

## Key Design Decisions

**Why LangGraph over a single LLM call?**
Each node has a focused responsibility. The Router prevents the LLM from hallucinating bill numbers. The Research node grounds the analysis in real document chunks before any generation happens. Separating Analysis from Writing means risk scores are structured JSON before the Writer ever sees them — producing more consistent, parseable outputs.

**Why model-agnostic?**
`llm_provider.py` injects the LLM via LangGraph's `RunnableConfig`. You switch models in the Streamlit sidebar — no code changes needed. This also means you can run Gemini for routing (cheap, fast) and Claude for writing (higher quality) if you extend the config.

**Why ChromaDB + Tavily together?**
ChromaDB provides grounded retrieval from the actual bill text. Tavily fills the temporal gap — bills are static, but their real-world effects (amendments, court challenges, agency rulemaking) evolve. Combining both produces more contextually complete analysis.

**Idempotent ingestion**
`load_to_db.py` generates deterministic chunk IDs (`{bill_number}_{chunk_index}`). Re-running it never duplicates data in ChromaDB.
