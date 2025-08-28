import pyvisa
import time
import numpy as np
import argparse
import sys
import logging
from MQTTHandler import MQTTHandler
from backend.Backend import HighLevelControl
from frontend.Frontend import Frontend
import asyncio
from nicegui import ui


def main():
    backend = HighLevelControl()
    frontend = Frontend()
    frontend.create_ui()

    ui.run(
        title="UV_LED Control Interface",
        port=8080,
        host="0.0.0.0",     
        reload=False     
    )

if __name__ == "__main__":
    main()
