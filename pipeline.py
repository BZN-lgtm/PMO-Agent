"""Daily progress pipeline: ingest -> normalise -> flag -> summarise -> publish.

Collects site progress updates from several sources (Google Sheet export,
email bodies, WhatsApp chat export), merges them into a Daily Progress
Report (DPR), flags SLA breaches, and writes an Excel DPR plus a JSON feed
for the management dashboard.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

import pandas as pd

DPR_COLUMNS = [
    "date", "site_id", "region", "scope", "activity", "sla_visits",
    "actual_visits", "status", "team_lead", "source",
]


@dataclass
class SiteUpdate:
    date: str
    site_id: str
    region: str
    scope: str
    activity: str
    sla_visits: int
    actual_visits: int
    status: str
    team_lead: str
    source: str


# ---------------------------------------------------------------- ingest
def from_sheet_export(path: Path) -> list[SiteUpdate]:
    """Rows exported from the implementation-manager Google Sheet (CSV)."""
    df = pd.read_csv(path)
    return [
        SiteUpdate(
            date=str(r["Date"]), site_id=str(r["Site ID"]), region=str(r["Region"]),
            scope=str(r["Scope"]), activity=str(r["Activity"]),
            sla_visits=int(r["SLA Visits"]), actual_visits=int(r["Actual Visits"]),
            status=str(r["Status"]), team_lead=str(r["Team Lead"]), source="sheet",
        )
        for _, r in df.iterrows()
    ]


# "SITE-1042 | Install | Done | visits 2/3 | TL Ahmed | Central | Operator A"
LINE_RE = re.compile(
    r"(?P<site>SITE-\d+)\s*\|\s*(?P<act>[^|]+)\|\s*(?P<status>[^|]+)\|\s*visits\s*"
    r"(?P<actual>\d+)\s*/\s*(?P<sla>\d+)\s*\|\s*TL\s+(?P<tl>[^|]+)\|\s*(?P<region>[^|]+)\|\s*(?P<scope>.+)",
    re.IGNORECASE,
)


def from_text(text: str, day: str, source: str) -> list[SiteUpdate]:
    """Parse free-text updates from email bodies or a WhatsApp export."""
    out = []
    for line in text.splitlines():
        m = LINE_RE.search(line)
        if not m:
            continue
        out.append(SiteUpdate(
            date=day, site_id=m["site"].upper(), region=m["region"].strip(),
            scope=m["scope"].strip(), activity=m["act"].strip(),
            sla_visits=int(m["sla"]), actual_visits=int(m["actual"]),
            status=m["status"].strip().title(), team_lead=m["tl"].strip(), source=source,
        ))
    return out


# ---------------------------------------------------------------- transform
def build_dpr(updates: list[SiteUpdate]) -> pd.DataFrame:
    df = pd.DataFrame([asdict(u) for u in updates], columns=DPR_COLUMNS)
    # latest source wins per site/day: sheet < email < whatsapp
    order = {"sheet": 0, "email": 1, "whatsapp": 2}
    df["_rank"] = df["source"].map(order)
    df = (df.sort_values("_rank")
            .drop_duplicates(["date", "site_id"], keep="last")
            .drop(columns="_rank")
            .sort_values(["region", "site_id"])
            .reset_index(drop=True))
    df["sla_breach"] = df["actual_visits"] > df["sla_visits"]
    return df


def kpis(dpr: pd.DataFrame) -> dict:
    total = len(dpr)
    done = int((dpr["status"].str.lower() == "done").sum())
    return {
        "sites_reported": total,
        "completed": done,
        "completion_pct": round(100 * done / total, 1) if total else 0.0,
        "sla_breaches": int(dpr["sla_breach"].sum()),
        "by_region": dpr.groupby("region")["site_id"].count().to_dict(),
        "breach_sites": dpr.loc[dpr["sla_breach"], "site_id"].tolist(),
    }


# ---------------------------------------------------------------- publish
def publish(dpr: pd.DataFrame, summary: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    xlsx = out_dir / f"DPR_{summary['date']}.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as xw:
        dpr.to_excel(xw, sheet_name="DPR", index=False)
        pd.DataFrame([{k: v for k, v in summary.items() if not isinstance(v, (dict, list))}]) \
            .to_excel(xw, sheet_name="Summary", index=False)
    feed = out_dir / "dashboard_feed.json"
    feed.write_text(json.dumps({"summary": summary, "rows": dpr.to_dict("records")},
                               indent=2, default=str))
    return xlsx, feed


def run(sheet_csv: Path, email_txt: Path | None, whatsapp_txt: Path | None,
        out_dir: Path, day: str | None = None, use_llm: bool = True) -> dict:
    from agent.summarizer import summarize

    day = day or date.today().isoformat()
    updates = from_sheet_export(sheet_csv)
    if email_txt and email_txt.exists():
        updates += from_text(email_txt.read_text(), day, "email")
    if whatsapp_txt and whatsapp_txt.exists():
        updates += from_text(whatsapp_txt.read_text(), day, "whatsapp")
    dpr = build_dpr(updates)
    summary = {"date": day, **kpis(dpr)}
    summary["narrative"] = summarize(summary, use_llm=use_llm)
    xlsx, feed = publish(dpr, summary, out_dir)
    return {"xlsx": str(xlsx), "feed": str(feed), **summary}
