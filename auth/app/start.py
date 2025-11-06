"""Auth service launcher: starts Uvicorn.\n\nMigrations at container startup have been retired in favor of manual,\nversioned SQL under auth/migrations. See auth/alembic/README.md for details.
"""
from __future__ import annotations
import sys

def main() -> None:
    # Start the ASGI server
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
