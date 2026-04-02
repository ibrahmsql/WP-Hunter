#!/usr/bin/env python3
"""Temodar Agent web launcher."""

import os
import uvicorn

from server.app import create_app


def main() -> None:
    app = create_app()
    host = os.getenv("TEMODAR_AGENT_HOST", "127.0.0.1")
    port = int(os.getenv("TEMODAR_AGENT_PORT", "8080"))
    uvicorn.run(app, host=host, port=port, log_level="warning", workers=1)


if __name__ == "__main__":
    main()
