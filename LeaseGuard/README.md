# 🏠 LeaseGuard

**AI-powered lease analyzer.** Upload your rental agreement, ask anything in plain English, and get clause-by-clause risk scores grounded in your state's actual tenant law — not generic templates.

> Built on LangGraph 0.2 · ChromaDB · Tavily · Gemini / Claude / GPT-4o (swappable at runtime)

---

## The Problem

Everyone who has ever rented an apartment has signed a lease they didn't fully read. Hidden auto-renewal clauses, illegal entry provisions, security deposit terms that violate state law, early termination fees buried on page 18. Most people sign anyway because they don't want to seem difficult and they can't afford a lawyer.

LeaseGuard reads it for you.

---

## Architecture

```
User Query (plain English) + Uploaded Lease PDF
        │
        ▼
┌─────────────────┐
│   Router Node   │  Detects task: flag_risks | explain_clause | rights | summary
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Research Node  │  ① Lease chunks from ChromaDB (uploaded PDF)
│                 │  ② State tenant law chunks (pre-ingested per state)
│                 │  ③ Tavily live web search for current rights
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Analysis Node  │  Risk scores 1–5 per clause category
│                 │  Flagged clauses with quotes + negotiation tips
│                 │  Illegal clauses identified against state law
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Writer Node   │  Plain-English summary — no jargon
│                 │  Specific negotiation advice per flagged clause
└─────────────────┘
```

---

## Supported Query Types

| Type | Example | Output |
|------|---------|--------|
| `flag_risks` | *"Flag all risky clauses"* | Risk-scored clause cards, negotiation tips |
| `explain_clause` | *"What does the automatic renewal clause mean?"* | Plain-English explanation |
| `rights` | *"Can my landlord enter without notice in NY?"* | State law answer |
| `summary` | *"Summarize my lease"* | Plain-English full summary |
| `compare` | *"Is this lease fair compared to standard terms?"* | Comparison against typical lease |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | LangGraph 0.2+ |
| LLM (swappable) | Gemini 2.5 Flash · Claude 3.5 Haiku · GPT-4o |
| Vector store | ChromaDB (two collections: lease + state law) |
| PDF extraction | pdfplumber (primary) · pypdf (fallback) |
| Web search | Tavily API |
| State law corpus | Nolo.com state tenant law pages (50 states + DC) |
| Frontend | Streamlit + Plotly |

---

## Quickstart

### 1. Install

```bash
git clone https://github.com/mishitak468/LeaseGuard.git
cd LeaseGuard
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

```env
GOOGLE_API_KEY=...       # Required (Gemini)
ANTHROPIC_API_KEY=...    # Optional (Claude)
OPENAI_API_KEY=...       # Optional (GPT-4o)
TAVILY_API_KEY=...       # Recommended (live tenant rights search)
```

### 3. Ingest state tenant laws (one-time)

```bash
# All 50 states (~10 minutes, ~2,000 chunks)
python src/ingest_state_laws.py

# Single state only
python src/ingest_state_laws.py --state NY
```

### 4. Launch

```bash
streamlit run app.py
```

Upload your lease PDF in the sidebar, select your state, and ask.

---

## Privacy

- Your lease PDF is chunked and stored in a **local** ChromaDB instance — nothing is sent to a remote database
- The LLM API receives text chunks to analyze — same as pasting text into ChatGPT yourself
- Nothing persists after your session if you clear the lease collection
- LeaseGuard is not a law firm and does not provide legal advice

---

## Metrics

```bash
python metrics_report.py          # full report with resume bullets
python metrics_report.py --bullets # bullets only
python metrics_report.py --json    # raw JSON
```

---

## Key Design Decisions

**Why two ChromaDB collections?**
The lease collection is ephemeral — wiped and reloaded on each upload. The state law collection is persistent and pre-ingested. Keeping them separate means the Research node can apply a `state` metadata filter to the law collection without cross-contaminating lease chunks.

**Why pdfplumber over pypdf?**
Real leases have multi-column layouts, tables, and inconsistent spacing. pdfplumber handles these significantly better. pypdf is kept as a fallback.

**Why chunk on section boundaries?**
Lease sections are semantically self-contained. A chunk that starts in the middle of a section loses the context of what clause it belongs to. Section-boundary chunking preserves clause integrity, which directly improves retrieval precision.

**Why is the Writer node only shown retrieved context?**
The Writer system prompt explicitly limits output to the retrieved context. This is the architectural guarantee against hallucination — the Writer cannot invent clauses that aren't in the lease.

---

## License

MIT — not legal advice.