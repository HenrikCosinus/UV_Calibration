import logging
import time
from nicegui import ui
import paho.mqtt.client as mqtt
import json
from pathlib import Path
from MQTTHandler import MQTTHandler
import threading
from frontend.cards.uv_led_card import build_uv_led_card
from frontend.cards.signal_card import build_signal_card
from frontend.cards.temperature_card import build_temperature_card
from frontend.cards.potentiometer_card import build_potentiometer_card

logger = logging.getLogger(__name__)

class Frontend():
    def __init__(self):
        self.notes_file = Path('channel_notes.json')
        self.channel_notes_store = {}
        self._load_notes()
        self.pot_settings_file = Path('potentiometer_settings.json')
        self.channel_pot_settings = {}
        self._load_pot_settings()
        topics = {
            'temperature': f"/temperature",
            'operation_status': f"/status",
            'UI_command': f"/ui_command",
            'control_response': f"/control_response",
            'hardware_status': f"/hardware_status",
        }
        self.mqtt = MQTTHandler(
            client_id="web_ui",
            broker="localhost",
            port=1883,
            topics=topics
        )
        logger.info("Connecting MQTT client (web_ui) to broker 172.17.0.1:1883")
        self.mqtt.connect()
        logger.info("MQTT connect() called.")

        self.temp_readings = []

        self.mqtt.register_handler("/temperature", self._on_temp_message)
        self.mqtt.register_handler("/hardware_status", self._on_hardware_status)
        logger.info("Subscribed to /temperature and /hardware_status")

    def create_ui(self):
        with ui.row().classes("w-full gap-4 items-start"):
            build_uv_led_card(self)
            build_signal_card(self)
            build_temperature_card(self)
        build_potentiometer_card(self)

    def _load_notes(self):
        try:
            if self.notes_file.exists():
                with open(self.notes_file) as f:
                    self.channel_notes_store = json.load(f)
        except Exception as e:
            print(f"Failed to load notes: {e}")

    def _save_notes(self):
        try:
            with open(self.notes_file, 'w') as f:
                json.dump(self.channel_notes_store, f, indent=2)
        except Exception as e:
            print(f"Failed to save notes: {e}")

    def _load_pot_settings(self):
        try:
            if self.pot_settings_file.exists():
                with open(self.pot_settings_file) as f:
                    self.channel_pot_settings = json.load(f)
        except Exception as e:
            print(f"Failed to load potentiometer settings: {e}")

    def _save_pot_settings(self):
        try:
            with open(self.pot_settings_file, 'w') as f:
                json.dump(self.channel_pot_settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save potentiometer settings: {e}")

    def _on_temp_message(self, payload):
        try:
            logger.debug(f"/temperature raw: {payload}")
            if "temperature_k" in payload:
                self.temp_readings.append((payload["temperature_k"], payload.get("timestamp")))
                if len(self.temp_readings) > 20:
                    self.temp_readings.pop(0)
                logger.info(f"Temperature queued: {payload['temperature_k']:.2f} K")
            else:
                logger.warning(f"/temperature payload missing 'temperature_k': {payload}")
        except Exception as e:
            logger.error(f"Temperature parse error in MQTT callback: {e}")

    def _on_hardware_status(self, payload):
        try:
            labels = {
                "agilent":  "Agilent signal generator",
                "gpio":     "GPIO multiplexer",
                "ad5260":   "AD5260 potentiometer",
                "max31865": "MAX31865 temperature sensor",
            }
            for key, name in labels.items():
                if not payload.get(key, True):
                    ui.notify(f"{name} failed to initialize", type="negative", close_button=True, timeout=0)
        except Exception as e:
            logger.error(f"hardware_status parse error: {e}")
