"""Reproduce the acceptance report shown in the app; no network or model mocks."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playerlens.acceptance import run_checks

if __name__ == "__main__":
    report=run_checks()
    output=Path(__file__).resolve().parents[1]/"static/data/verification.json"
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="checks"},ensure_ascii=False))
    raise SystemExit(0 if report["passed"]==report["total"] else 1)
