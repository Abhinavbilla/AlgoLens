import argparse
import json
import logging
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="algolens")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="apply database migrations")
    serve = sub.add_parser("serve", help="apply migrations, seed the library, then run the API")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    sub.add_parser("worker", help="run the job worker")
    lib = sub.add_parser("library", help="manage the algorithm library")
    lib_sub = lib.add_subparsers(dest="library_command", required=True)
    lib_sub.add_parser("seed", help="load library/ into the database")
    verify = lib_sub.add_parser("verify", help="verify entries in the sandbox and record results")
    verify.add_argument("slugs", nargs="*", help="entries to verify (default: all)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.command == "migrate":
        from algolens.db.migrate import upgrade

        upgrade()
    elif args.command == "serve":
        import uvicorn

        from algolens.db.migrate import upgrade

        upgrade()
        _seed_library()
        uvicorn.run("algolens.api.app:app", host=args.host, port=args.port)
    elif args.command == "worker":
        from algolens.worker import run_forever

        run_forever()
    elif args.command == "library":
        _seed_library()
        if args.library_command == "verify":
            sys.exit(_verify_library(args.slugs))


def _seed_library() -> None:
    from algolens.config import get_settings
    from algolens.db.session import session_factory
    from algolens.library.loader import load_all, seed

    entries = load_all(get_settings().library_dir)
    with session_factory()() as session:
        seed(session, entries)


def _verify_library(slugs: list[str]) -> int:
    """Exit code 0 if every selected entry verified, 1 if any failed, 2 if any couldn't be
    checked (sandbox unavailable). An entry that couldn't be checked keeps no new verdict."""
    from sqlalchemy import select

    from algolens.db.models import LibraryEntry
    from algolens.db.session import session_factory
    from algolens.library.loader import from_row
    from algolens.library.verify import verify_entry
    from algolens.sandbox.client import SandboxClient, SandboxUnavailable

    client = SandboxClient()
    failed = unchecked = False
    with session_factory()() as session:
        rows = session.scalars(select(LibraryEntry)).all()
        unknown = set(slugs) - {r.slug for r in rows}
        if unknown:
            print(f"unknown entries: {sorted(unknown)}", file=sys.stderr)
            return 2
        for row in rows:
            if slugs and row.slug not in slugs:
                continue
            try:
                result = verify_entry(from_row(row), client)
            except SandboxUnavailable as exc:
                unchecked = True
                print(f"{row.slug}: couldn't verify, no verdict recorded ({exc})", file=sys.stderr)
                continue
            row.verification = result
            session.commit()
            failed |= result["status"] != "verified"
            print(json.dumps({"slug": row.slug, **result}, indent=2))
    client.close()
    return 2 if unchecked else (1 if failed else 0)


if __name__ == "__main__":
    main()
