"""Regenerate the self-contained static demo data file from Python fixtures."""

import json
from pathlib import Path

from .catalog import build_catalog
from .feeds import build_live_feed_files
from .projection import project_game, view_patch, event_second
import shutil


def main() -> None:
    output = Path(__file__).resolve().parent.parent / "static" / "data" / "games.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog()
    output.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n")
    feed_paths = []
    for filename, feed in build_live_feed_files(catalog).items():
        feed_path = output.parent / filename
        feed_path.write_text(json.dumps(feed, ensure_ascii=False, separators=(",", ":")) + "\n")
        feed_paths.append(feed_path)
    # Event/snapshot boundaries are sufficient: facts do not change between them.
    # Individual files keep the initial visitor download small.
    states_dir = output.parent / "analysis"
    if states_dir.exists():
        shutil.rmtree(states_dir)
    states_dir.mkdir()
    index = {"schema_version":"1.1", "games":{}}
    for game in catalog["games"]:
        gid, latest = game["match"]["game_id"], game["available_through_seconds"]
        boundaries = sorted({0,latest} | {event_second(row) for key in ("events","attacks","tracking_snapshots") for row in game[key]})
        index["games"][gid] = boundaries
        for second in boundaries:
            patch = view_patch(project_game(game,second))
            patch.pop("tracking_snapshots",None)
            (states_dir / f"{gid}-{second}.json").write_text(json.dumps(patch,ensure_ascii=False,separators=(",",":"))+"\n")
    (output.parent / "analysis-index.json").write_text(json.dumps(index,separators=(",",":"))+"\n")
    from .acceptance import run_checks
    report = run_checks()
    (output.parent / "verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if report["passed"] != report["total"]:
        raise RuntimeError("Synthetic acceptance checks failed")
    print("Wrote " + ", ".join(str(path) for path in [output, *feed_paths]))


if __name__ == "__main__":
    main()
