"""Render-safe backend entrypoint.

Behavior:
- BACKEND_MODE=full: try to load full app from main.py
- Otherwise (default): load minimal app from main_minimal.py
- If full load fails, automatically fall back to minimal app
"""

import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mode = os.getenv("BACKEND_MODE", "minimal").strip().lower()

if mode == "full":
    try:
        from main import app as full_app

        app = full_app
        logger.info("Loaded FULL backend app (BACKEND_MODE=full)")
    except Exception as exc:
        from main_minimal import app as minimal_app

        app = minimal_app
        logger.exception("Full app failed to load. Falling back to minimal app. Error: %s", exc)
else:
    from main_minimal import app as minimal_app

    app = minimal_app
    logger.info("Loaded MINIMAL backend app (BACKEND_MODE=%s)", mode)
