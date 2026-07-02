import time
import numpy as np
import sys
import json
import logging
import uuid
from typing import Callable, Dict, Optional
import paho.mqtt.client as mqtt

# Logging is configured centrally in main.py. basicConfig here is commented out so
# it does not override the root logger that main.py sets up before importing this module.
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("agilent_33250a.log"),
#         logging.StreamHandler(sys.stdout)
#     ]
# )
logger = logging.getLogger(__name__)

#I dont want a localhost, however at run time this should be replaced with the correct IP from the call coming from the HighlevelControll intialization
class MQTTHandler:
    def __init__(self, client_id: str, broker: str = "localhost", port: int = 1883, topics: Optional[Dict[str, str]] = None):
        self.broker = broker
        self.port = port
        # Append a short unique suffix so multiple processes or restarts never share
        # the same client_id. If two clients with the same id connect, the broker kicks
        # the older one, which triggers its reconnect, which kicks the new one — infinite loop.
        self.client_id = f"{client_id}_{uuid.uuid4().hex[:6]}"
        self.topics = topics or {}
        self.logger = logging.getLogger(f"{__name__}.{client_id}")
        self.logger.info(f"[MQTTHandler] client_id assigned: {self.client_id}")
        self._setup_client()

    def _setup_client(self):
        self.client = mqtt.Client(client_id=self.client_id)
        self.client._reconnect_on_failure = False
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.connected = False
        self._message_handlers = {}
        
    def register_handler(self, topic: str, handler: Callable):
        self._message_handlers[topic] = handler
        if self.connected:
            self.client.subscribe(topic)
            self.logger.info(f"Subscribing the client to topic: {topic}")
            
    
    def send_response(self, data):
        topic = self.topics.get('control_response', 'control_response')
        self.publish(topic, data)

    def update_status(self, status_data):
        topic = self.topics.get('operation_status', 'status')
        self.publish(topic, status_data)

    def on_ui_command(self, handler: Callable):
        self.logger.info(f"on_ui_command is reached")
        self.register_handler(self.topics.get("UI_command", "/ui_command"), handler)

    def on_status_update(self, handler: Callable):
        self.register_handler(self.topics.get("operation_status", "/status"), handler)

    def on_response(self, handler: Callable):
        self.register_handler(self.topics.get("control_response", "/control_response"), handler)

    def connect(self):
        try:
            # BUG FIX (Bug 4): keepalive=True evaluates to int 1 in Python, so the
            # broker disconnects the client after ~1 second of inactivity. Should be
            # an integer in seconds; 60 is the standard default.
            # self.client.connect(self.broker, self.port, keepalive=True)
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            self.logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Connection failed in the connect function of the MQTTHandler: {str(e)}")
            return False        
            
    def disconnect(self):
        self.client.publish(self.topics.get('status', 'status'), 
                          json.dumps({"status": "offline"}), 
                          qos=1, 
                          retain=True)
        self.client.loop_stop()
        self.client.disconnect()
        self.logger.info("Disconnected from MQTT broker")
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.logger.info("Successfully connected to MQTT broker")
            for topic in list(self._message_handlers):
                client.subscribe(topic)
                self.logger.info(f"[MQTT] Subscribed to topic: {topic}")

            client.publish(self.topics.get('status', 'status'),
                         json.dumps({"status": "online"}),
                         qos=1,
                         retain=True)
        else:
            self.logger.error(f"Connection failed with code {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection (code: {rc})")
            
    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            self.logger.debug(f"[MQTT] Raw message on {msg.topic}: {payload}")
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                pass  # Keep as raw string if not JSON

            handler = self._message_handlers.get(msg.topic)
            if handler:
                self.logger.debug(f"[MQTT] Dispatching {msg.topic} → {handler.__name__}")
                handler(payload)
                self.logger.debug(f"[MQTT] Handler {handler.__name__} completed for {msg.topic}")
            else:
                self.logger.warning(f"[MQTT] No handler registered for topic {msg.topic}")
                
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            
    def publish(self, topic: str, payload, qos: int = 1, retain: bool = False):
        """Publish a message to a topic."""
        if not isinstance(payload, str):
            payload = json.dumps(payload)
        result = self.client.publish(topic, payload, qos=qos, retain=retain)
        self.logger.info(f"Published to {topic}: {payload} (result: {result.rc})")

