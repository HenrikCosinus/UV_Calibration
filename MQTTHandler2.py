import time
import numpy as np
import argparse
import sys
import logging
import json
import threading
import paho.mqtt.client as mqtt
import Agilent_Controller_RS232

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

# Global variable for generator
generator = None

class MQTTHandler:
    def __init__(self, broker="localhost", port=1883, client_id="agilent_controller"):
        """Initialize MQTT client handler."""
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.topic_prefix = "agilent/33250a"
        self.command_topic = f"{self.topic_prefix}/command"
        self.response_topic = f"{self.topic_prefix}/response"
        self.status_topic = f"{self.topic_prefix}/status"
        
        # Initialize MQTT client
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Flag to track connection status
        self.connected = False
        
    def connect(self):
        """Connect to MQTT broker."""
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.client.publish(self.status_topic, json.dumps({"status": "offline"}), qos=1, retain=True)
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker")
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self.connected = True
            # Subscribe to command topic
            self.client.subscribe(self.command_topic)
            # Publish online status
            self.client.publish(self.status_topic, json.dumps({"status": "online"}), qos=1, retain=True)
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")
            self.connected = False
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        logger.info("Disconnected from MQTT broker")
        self.connected = False
    
    def on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages."""
        global generator
        
        try:
            payload = msg.payload.decode("utf-8")
            logger.info(f"Received MQTT message: {payload} on topic {msg.topic}")
            
            if msg.topic == self.command_topic and generator:
                command_data = json.loads(payload)
                command = command_data.get("command", "")
                
                # Handle special commands
                if command.lower() == "demo":
                    demo_type = command_data.get("type", "basic")
                    self._handle_demo_command(demo_type)
                    return
                
                # Process normal SCPI command
                response = self._execute_command(command)
                
                # Publish response
                self.publish_response(command, response)
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON in MQTT message")
            self.publish_response("error", "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {str(e)}")
            self.publish_response("error", str(e))
    
    def _execute_command(self, command):
        """Execute SCPI command on the generator."""
        try:
            if '?' in command:
                response = generator.inst.query(command)
                return response.strip()
            else:
                generator.inst.write(command)
                return "Command executed"
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            return f"Error: {str(e)}"
    
    def _handle_demo_command(self, demo_type):
        """Handle demo commands received via MQTT."""
        try:
            if demo_type == "basic":
                threading.Thread(target=Agilent_Controller_RS232.demo_basic_waveforms, args=(generator,)).start()
            elif demo_type == "am":
                threading.Thread(target=Agilent_Controller_RS232.demo_am_modulation, args=(generator,)).start()
            elif demo_type == "fm":
                threading.Thread(target=Agilent_Controller_RS232.demo_fm_modulation, args=(generator,)).start()
            elif demo_type == "sweep":
                threading.Thread(target=Agilent_Controller_RS232.demo_frequency_sweep, args=(generator,)).start()
            elif demo_type == "burst":
                threading.Thread(target=Agilent_Controller_RS232.demo_burst_mode, args=(generator,)).start()
            elif demo_type == "arbitrary":
                threading.Thread(target=Agilent_Controller_RS232.demo_arbitrary_waveform, args=(generator,)).start()
            elif demo_type == "all":
                threading.Thread(target=self._run_all_demos).start()
            else:
                self.publish_response("demo", f"Unknown demo type: {demo_type}")
                return
            
            self.publish_response("demo", f"Started {demo_type} demo")
        except Exception as e:
            logger.error(f"Error running demo: {str(e)}")
            self.publish_response("demo", f"Error: {str(e)}")
    
    def _run_all_demos(self):
        """Run all demo sequences."""
        Agilent_Controller_RS232.demo_basic_waveforms(generator)
        Agilent_Controller_RS232.demo_am_modulation(generator)
        Agilent_Controller_RS232.demo_fm_modulation(generator)
        Agilent_Controller_RS232.demo_frequency_sweep(generator)
        Agilent_Controller_RS232.demo_burst_mode(generator)
        Agilent_Controller_RS232.demo_arbitrary_waveform(generator)
        self.publish_response("demo", "All demos completed")
    
    def publish_response(self, command, response):
        """Publish response to MQTT topic."""
        response_data = {
            "command": command,
            "response": response,
            "timestamp": time.time()
        }
        self.client.publish(self.response_topic, json.dumps(response_data))
        logger.debug(f"Published response: {response_data}")

