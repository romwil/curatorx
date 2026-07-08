"""Uvicorn entry point."""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8788"))
    uvicorn.run("mediacurator.web.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
