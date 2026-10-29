"""Package the browser assets with freshly exported synthetic warehouse snapshots."""

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "build/dashboard")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name in ["showcase", "validation"]:
        source = ROOT / f"build/{name}.json"
        data = json.loads(source.read_text())
        if not data.get("synthetic") or any(t["status"] != "pass" for t in data["quality"]):
            raise ValueError("Only validated synthetic snapshots may be packaged")
        shutil.copyfile(source, args.output / source.name)
    for name in ["index.html", "styles.css", "app.js", "model.mjs"]:
        shutil.copyfile(ROOT / "dashboard" / name, args.output / name)
    print(f"Dashboard prepared in {args.output}")


if __name__ == "__main__":
    main()
