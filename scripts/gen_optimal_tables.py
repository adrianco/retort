#!/usr/bin/env python3
"""Deprecated shim — use `retort report optimal` instead.

The optimal-stack selection logic now lives in `retort.reporting.optimal` and is
exposed as the `retort report optimal` subcommand. This wrapper is kept so old
muscle memory / scripts keep working; it just forwards to the subcommand.

    retort report optimal                       # print tables + health
    retort report optimal --health              # data-health report only
    retort report optimal --write optimal-blog.md   # splice into GEN markers
"""
import sys

from retort.reporting import optimal as opt


def main() -> None:
    args = sys.argv[1:]
    db_path = opt.DB
    if "--db" in args:
        db_path = args[args.index("--db") + 1]
    conn = opt.open_db(db_path)
    try:
        if "--health" in args:
            print(opt.health_report(conn, opt.REPO))
        elif "--write" in args:
            from pathlib import Path

            path = Path(args[args.index("--write") + 1])
            changed, skipped = opt.splice(path, conn)
            for key in skipped:
                print(f"  (no GEN markers for '{key}', skipped)", file=sys.stderr)
            print(f"Spliced {changed} table(s) into {path}")
        else:
            print(opt.render_all(conn, opt.REPO))
    finally:
        conn.close()


if __name__ == "__main__":
    print(
        "note: scripts/gen_optimal_tables.py is deprecated — use "
        "`retort report optimal`.",
        file=sys.stderr,
    )
    main()
