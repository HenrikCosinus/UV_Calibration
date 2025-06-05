import time
import numpy as np
import sys
import json
import logging
from typing import Callable, Dict, Optional
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agilent_33250a.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MQTTHandler:
    def __init__(self, client_id: str, broker: str = "localhost", port: int = 1883, topics: Optional[Dict[str, str]] = None):
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.topics = topics or {}
        # Configure logging
        self.logger = logging.getLogger(f"{__name__}.{client_id}")
        self._setup_client()

    def _setup_client(self):
        """Initialize the MQTT client with callbacks."""
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.connected = False
        
        # Message handler registry
        self._message_handlers = {}
        
    def register_handler(self, topic: str, handler: Callable):
        """Register a callback for a specific topic."""
        self._message_handlers[topic] = handler
        if self.connected:
            self.client.subscribe(topic)
            
    def connect(self):
        """Connect to the MQTT broker."""
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            self.logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Connection failed: {str(e)}")
            return False
            
    def disconnect(self):
        """Disconnect from the MQTT broker."""
        self.client.publish(self.topics.get('status', 'status'), 
                          json.dumps({"status": "offline"}), 
                          qos=1, 
                          retain=True)
        self.client.loop_stop()
        self.client.disconnect()
        self.logger.info("Disconnected from MQTT broker")
        
    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection events."""
        if rc == 0:
            self.connected = True
            self.logger.info("Successfully connected to MQTT broker")
            
            # Subscribe to registered topics
            for topic in self._message_handlers:
                client.subscribe(topic)
                
            # Publish online status
            client.publish(self.topics.get('status', 'status'),
                         json.dumps({"status": "online"}),
                         qos=1,
                         retain=True)
        else:
            self.logger.error(f"Connection failed with code {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection events."""
        self.connected = False
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection (code: {rc})")
            
    def _on_message(self, client, userdata, msg):
        """Route incoming messages to registered handlers."""
        try:
            payload = msg.payload.decode("utf-8")
            self.logger.debug(f"Received message on {msg.topic}: {payload}")
            
            # Try to parse as JSON
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                pass  # Keep as raw string if not JSON
                
            # Call registered handler if exists
            handler = self._message_handlers.get(msg.topic)
            if handler:
                handler(payload)
            else:
                self.logger.warning(f"No handler registered for topic {msg.topic}")
                
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            
    def publish(self, topic: str, payload, qos: int = 1, retain: bool = False):
        """Publish a message to a topic."""
        if not isinstance(payload, str):
            payload = json.dumps(payload)
            
        self.client.publish(topic, payload, qos=qos, retain=retain)
        self.logger.debug(f"Published to {topic}: {payload}")
