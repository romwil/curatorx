"""Uvicorn entry point."""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    from curatorx.config_store import load_dotenv_file

    if os.environ.get("CURATORX_SKIP_DOTENV") != "1":
        load_dotenv_file()

    port = int(os.environ.get("PORT", "8788"))
    uvicorn.run("curatorx.web.app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
