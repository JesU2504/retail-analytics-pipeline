import argparse
import json
import os
import subprocess
from pathlib import Path

from retail_pipeline.dashboard import export_dashboard
from retail_pipeline.demo import generate, generate_showcase
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
    parser.add_argument(
        "command", choices=["demo", "showcase", "dashboard", "ingest", "build", "report"]
    )
    parser.add_argument("--database", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("build/report.html"))
    parser.add_argument("--project-dir", type=Path, default=Path("dbt"))
    parser.add_argument("--full-refresh", action="store_true")
    args = parser.parse_args()
    if args.database is None:
        args.database = Path(
            "build/showcase.duckdb" if args.command == "showcase" else "build/retail.duckdb"
        )
    if args.command in {"demo", "showcase"}:
        folder = args.database.parent / (
            "showcase-data" if args.command == "showcase" else "demo-data"
        )
        (generate_showcase if args.command == "showcase" else generate)(folder)
        for batch in ["initial", "updates"]:
            print(json.dumps(ingest(args.database, folder / batch)))
            build(args.database, args.project_dir)
        print(json.dumps(report(args.database, args.output)))
        snapshot = args.database.parent / (
            "showcase.json" if args.command == "showcase" else "validation.json"
        )
        print(
            json.dumps(
                export_dashboard(
                    args.database, snapshot, args.project_dir / "target/run_results.json"
                )
            )
        )
    elif args.command == "dashboard":
        build(args.database, args.project_dir)
        print(
            json.dumps(
                export_dashboard(
                    args.database,
                    args.output.with_suffix(".json"),
                    args.project_dir / "target/run_results.json",
                )
            )
        )
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
