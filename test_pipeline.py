from pathlib import Path

from agent.pipeline import build_dpr, from_text, kpis, run

DATA = Path(__file__).resolve().parent.parent / "data"


def test_text_parser_reads_whatsapp_line():
    ups = from_text((DATA / "sample_whatsapp.txt").read_text(), "2026-10-15", "whatsapp")
    assert len(ups) == 1
    assert ups[0].site_id == "SITE-1005" and ups[0].actual_visits == 3


def test_later_sources_override_sheet_and_breaches_flagged(tmp_path):
    res = run(DATA / "sample_sheet.csv", DATA / "sample_email.txt",
              DATA / "sample_whatsapp.txt", tmp_path, "2026-10-15", use_llm=False)
    assert res["sites_reported"] == 7
    assert set(res["breach_sites"]) == {"SITE-1002", "SITE-1005"}
    assert Path(res["xlsx"]).exists() and Path(res["feed"]).exists()


def test_kpis_empty_safe():
    k = kpis(build_dpr([]))
    assert k["sites_reported"] == 0 and k["completion_pct"] == 0.0
