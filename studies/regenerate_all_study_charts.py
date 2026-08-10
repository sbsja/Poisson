"""Generate the current chart suite from completed study summary manifests."""

from __future__ import annotations

import json

from run_all_studies import STUDIES_DIR, STUDY_FILES
from v6_study_charts import generate_study_charts


def main():
    generated = 0
    for relative in STUDY_FILES:
        results_dir = (STUDIES_DIR / relative).parent / "results"
        summary_path = results_dir / "summary.json"
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        files = generate_study_charts(results_dir, data)
        generated += len(files)
        print(f"{data['study']}: {len(files)} charts", flush=True)
    print(f"Generated {generated} study charts across {len(STUDY_FILES)} studies.")


if __name__ == "__main__":
    main()
