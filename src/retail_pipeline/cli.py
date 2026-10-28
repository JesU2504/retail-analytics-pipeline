import argparse
import json
import os
import subprocess
from pathlib import Path

from retail_pipeline.demo import generate
from retail_pipeline.ingest import ingest
from retail_pipeline.report import report


def build(database: Path, project: Path, full_refresh=False):
    env = {
        **os.environ,
        "RETAIL_DB_PATH": str(database.resolve()),
        "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
    }
    command = ["dbt", "build", "--project-dir", str(project), "--profiles-dir", str(project)]
    if full_refresh:
        command.append("--full-refresh")
    subprocess.run(command, env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description="Reproducible retail ELT pipeline")
    parser.add_argument("command", choices=["demo", "ingest", "build", "report"])
    parser.add_argument("--database", type=Path, default=Path("build/retail.duckdb"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("build/report.html"))
    parser.add_argument("--project-dir", type=Path, default=Path("dbt"))
    parser.add_argument("--full-refresh", action="store_true")
    args = parser.parse_args()
    if args.command == "demo":
        folder = args.database.parent / "demo-data"
        generate(folder)
        for batch in ["initial", "updates"]:
            print(json.dumps(ingest(args.database, folder / batch)))
            build(args.database, args.project_dir)
        print(json.dumps(report(args.database, args.output)))
    elif args.command == "ingest":
        if args.input is None:
            parser.error("ingest requires --input")
        print(json.dumps(ingest(args.database, args.input)))
    elif args.command == "build":
        build(args.database, args.project_dir, args.full_refresh)
    else:
        print(json.dumps(report(args.database, args.output)))


if __name__ == "__main__":
    main()
