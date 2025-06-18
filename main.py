import pyvisa
import time
import numpy as np
import argparse
import sys
import logging
from MQTTHandler import MQTTHandler
from Backend import HighLevelControl
from Frontend import Frontend
import asyncio
from nicegui import ui

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("main.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    backend = HighLevelControl()
    frontend = Frontend()
    backend.initialize_hardware()
    frontend.create_ui()

    ui.run(
        title="UV_LED Control Interface",
        port=1884,
        host="0.0.0.0",     
        reload=False     
    )

if __name__ == "__main__":
    main()
