import sys
import logging
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Centralized logging — configured here at module level, BEFORE local imports,
# so this basicConfig call wins. Python only applies the first basicConfig call
# that finds the root logger with no handlers; all subsequent calls (in Backend.py,
# GPIOController.py, etc.) are silently ignored. This means all modules log to
# one unified file and stdout with a consistent format.
file_handler = logging.FileHandler(LOG_DIR / "uv_calibration.log")
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[file_handler, console_handler]
)
logging.getLogger('pyvisa').setLevel(logging.WARNING)
# Prevent uvicorn from adding its own handlers to the root logger,
# which caused every log record to appear 3 times.
logging.getLogger('uvicorn').propagate = False
logging.getLogger('uvicorn.access').propagate = False
logging.getLogger('uvicorn.error').propagate = False
logger = logging.getLogger(__name__)

import pyvisa
import time
import numpy as np
import argparse
import asyncio
from nicegui import ui
from mqtt_handler import MQTTHandler
from backend.backend import HighLevelControl
from frontend.frontend import Frontend


def main():
    logger.info("=== UV Calibration System starting ===")
    logger.info("Initializing backend (hardware + MQTT)...")
    backend = HighLevelControl()
    logger.info("Backend initialized successfully.")
    logger.info("Initializing frontend (UI + MQTT)...")
    frontend = Frontend()
    logger.info("Frontend initialized.")

    @ui.page('/')
    def index():
        frontend.create_ui()

    logger.info("Starting NiceGUI web server on 0.0.0.0:8080")
    ui.run(
        title="UV_LED Control Interface",
        port=8080,
        host="0.0.0.0",
        reload=False,
        websocket_max_size=16 * 1024 * 1024,  # 16 MB
    )

if __name__ == "__main__":
    main()
