"""Uvicorn entry point."""

from __future__ import annotations

import logging
import os


def main() -> None:
    import uvicorn

    from curatorx.config_store import load_dotenv_file
    from curatorx.logging_config import configure_logging, resolve_log_level

    if os.environ.get("CURATORX_SKIP_DOTENV") != "1":
        load_dotenv_file()

    level = configure_logging()
    port = int(os.environ.get("PORT", "8788"))
    uvicorn.run(
        "curatorx.web.app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level=logging.getLevelName(level).lower(),
    )


if __name__ == "__main__":
    main()
