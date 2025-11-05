"""Auth service launcher that optionally runs DB migrations, then starts Uvicorn."""
from __future__ import annotations
import sys

from . import migrate  # noqa: F401


def main() -> None:
    # Run migrations if enabled
    migrate.migrate_if_enabled()

    # Start the ASGI server
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
