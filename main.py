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
    Backend = HighLevelControl()
    Front = Frontend()
    Backend.initialize_hardware()
    port ="/dev/ttyUSB0"
    baud_rate = 57600
    logger.info(f"Connecting to Agilent 33250A on {port} at {baud_rate} baud")
    Backend.agilent(port, baud_rate)
    Front.create_ui()
    #ui.run(title="Agilent 33250A Demo Runner", port=8085, reload=True)
    ui.run(title="UI_Test", port=1884, reload = True, host="134.107.69.228")
    Backend.agilent.set_burst_mode()
if __name__ == "__main__":
    main()