"""CLI entry point.

    python main.py --sheet data/sample_sheet.csv --email data/sample_email.txt \
                   --whatsapp data/sample_whatsapp.txt --out output
"""
import argparse
import json
from pathlib import Path

from agent.pipeline import run


def main() -> None:
    p = argparse.ArgumentParser(description="Daily mobile-network progress agent")
    p.add_argument("--sheet", type=Path, required=True)
    p.add_argument("--email", type=Path)
    p.add_argument("--whatsapp", type=Path)
    p.add_argument("--out", type=Path, default=Path("output"))
    p.add_argument("--date")
    p.add_argument("--no-llm", action="store_true", help="use template summary only")
    a = p.parse_args()
    result = run(a.sheet, a.email, a.whatsapp, a.out, a.date, use_llm=not a.no_llm)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
