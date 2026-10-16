# 📡 Mobile Network Progress Agent

An AI agent that replaces a manual daily reporting loop in telecom rollout projects.
It collects site progress from **Google Sheets, email and WhatsApp**, merges it into a
**Daily Progress Report (DPR)**, flags **SLA breaches**, writes an **AI-generated
management brief** with Claude, and feeds a **leadership dashboard**.

> Built for a real mobile-network deployment program. All data in this repo is synthetic.

## The problem
Field team leads report progress through three different channels. A PMO analyst then
re-types it into Excel, checks SLA visits by hand, formats it and screenshots it for
management every evening — slow, error-prone and easy to fudge.

## How it works
```
 Google Sheet ─┐
 Email bodies ─┼─► ingest ─► normalise & de-duplicate ─► SLA flagging ─► KPIs
 WhatsApp     ─┘                (latest source wins)     (actual > SLA)    │
                                                                            ▼
                              Excel DPR  ◄── publish ◄── Claude summary (with template fallback)
                              dashboard_feed.json ──► HTML dashboard
```

| Layer | What it does |
|---|---|
| `agent/pipeline.py` | Parsers for each source, DPR builder, KPI + SLA-breach logic, Excel/JSON publishing |
| `agent/summarizer.py` | Claude API brief for management; deterministic fallback if no key / API error |
| `dashboard/index.html` | KPI cards, AI brief, region & status charts, breach-highlighted DPR table |
| `tests/` | pytest suite covering parsing, source precedence and breach detection |

## Quick start
```bash
pip install -r requirements.txt
python main.py --sheet data/sample_sheet.csv --email data/sample_email.txt \
               --whatsapp data/sample_whatsapp.txt --out output --date 2026-10-15
python -m http.server 8000   # open http://localhost:8000/dashboard/
```
Set `ANTHROPIC_API_KEY` to get Claude-written briefs; add `--no-llm` to skip the API.

## Design decisions
- **Source precedence** — sheet < email < WhatsApp, so the most recent field message wins.
- **SLA rule** — a site is breached when actual visits exceed the SLA visit count.
- **LLM never blocks the report** — any API failure falls back to a template brief.
- Runs daily on a scheduler (cron / Task Scheduler) at end of the working day.

## Tech
Python · pandas · openpyxl · Anthropic Claude API · Chart.js · pytest

## Author
**Bilal Zubair Nizam** — MS Artificial Intelligence Engineering
