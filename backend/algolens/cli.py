import argparse
import logging


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="algolens")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="apply database migrations")
    serve = sub.add_parser("serve", help="apply migrations, then run the API")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    sub.add_parser("worker", help="run the job worker")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.command == "migrate":
        from algolens.db.migrate import upgrade

        upgrade()
    elif args.command == "serve":
        import uvicorn

        from algolens.db.migrate import upgrade

        upgrade()
        uvicorn.run("algolens.api.app:app", host=args.host, port=args.port)
    elif args.command == "worker":
        from algolens.worker import run_forever

        run_forever()


if __name__ == "__main__":
    main()
