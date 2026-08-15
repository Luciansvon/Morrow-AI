"""Root-level runtime entrypoint used by PM2."""

import asyncio

from src.main import main


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
