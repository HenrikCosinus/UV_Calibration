from Agilent_Controller_RS232 import Agilent33250A
from GPIOController import GPIOController
import logging
import sys
import serial
import RPi.GPIO as GPIO
import time
import numpy as np
import json
import paho.mqtt.client as mqtt
from MQTTHandler import MQTTHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("HighLevelControlLog"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class HighLevelControl():
    def __init__(self):
        self.initialize_hardware()
        logger.info("hardware initialization worked in the _init_")
        self.system_status = "idle"
        topics = {
            'operation_status': f"/status",
            'UI_command': f"/ui_command",
            'control_response': f"/control_response",
        }
        self.mqtt = MQTTHandler(client_id="backend_controller", broker="172.17.0.1", port=1883, topics=topics)
        self.setup_mqtt_handlers()
        self.mqtt.connect()

    def initialize_hardware(self):
        try:
            self.agilent = Agilent33250A(port="/dev/ttyUSB0", baud_rate=57600, timeout=5000)
            self.GPIOController = GPIOController(pins=[17, 18, 22, 27])
            logger.info("Hardware initialized successfully")
        except Exception as e:
            logger.error(f"Hardware initialization failed: {str(e)}")
            raise

    def setup_mqtt_handlers(self):
        self.mqtt.on_ui_command(self.handle_ui_command)
        self.mqtt.on_status_update(self.update_system_status)
        logger.info("MQTT handlers configured")

    def update_system_status(self, msg=None):
        status = {
            "channel": getattr(self, "current_channel", None),
            "status": self.system_status,
            "timestamp": time.time()
        }
        self.mqtt.update_status(status)
        logger.debug(f"Status updated: {status}")

    
    def connect_to_generator(self):
        for port in Agilent33250A.find_usb_serial_ports():
            try:
                self.agilent = Agilent33250A(port=port)
                return
            except Exception as e:
                continue
        raise RuntimeError("No Agilent 33250A device found on available ports")


    def handle_ui_command(self, command):
        try:
            command = json.loads(command) if isinstance(command, str) else command
            logger.info(f"Received command: {command}")

            command_type = command.get("type")

            if command_type == "channel_select":
                self.handle_channel_selection(command["channel"])

            elif command_type == "burst":
                self.handle_burst_command(command["cycles"])

            elif command_type == "signal_config":
                self.handle_signal_config(command)
            
            elif command_type == "connect_generator":
                self.connect_to_generator()
            
            elif command_type == "disconnect_generator":
                self.agilent.disconnect()

            elif command_type == "all_off":
                self.all_off()

            else:
                logger.warning(f"Unknown command type: {command_type}")
                self.mqtt.send_response({
                    "error": f"Unknown command type: {command_type}",
                    "command": command
                })

        except Exception as e:
            logger.error(f"Command handling error: {str(e)}")
            self.mqtt.send_response({
                "error": str(e),
                "command": command
            })


    def handle_signal_config(self, command):
        try:
            frequency = float(command.get("frequency", 1000))                   # Default 1 kHz
            burst_count = int(command.get("bursts", 10))                        # Default 10 bursts
            duty_cycle = float(command.get("duty_cycle", 50.0))                 # Default 50%
            inter_block_delay = float(command.get("inter_burst_wait", 0.5))     # Default 0.5s wait between blocks

            # Call the actual configuration logic that sets the agilent controller.
            logger.info(f"handle_signal_config reaches at least up to the config transmittance to the agilent {self.configure_signal}")
            self.configure_signal(
                frequency=frequency,
                burst_count=burst_count,
                duty_cycle=duty_cycle,
                inter_block_delay=inter_block_delay
            )

            logger.info("Signal configuration handled successfully.")
            self.mqtt.send_response({"status": "Signal configuration applied."})

        except Exception as e:
            logger.error(f"Error in handle_signal_config: {str(e)}")
            self.mqtt.send_response({"error": f"Signal config failed: {str(e)}"})

    def configure_signal(self, frequency, burst_count, duty_cycle, inter_block_delay):
        try:
            self.agilent.set_frequency(frequency)
            self.agilent.set_burst_count(burst_count)
            self.agilent.set_duty_cycle(duty_cycle)
            self.inter_block_delay = inter_block_delay

            logging.info(f"Signal configured: {frequency=}, {burst_count=}, {duty_cycle=}, {inter_block_delay=}")
        except Exception as e:
            logging.error(f"Failed to configure signal: {str(e)}")
            raise

    def handle_channel_selection(self, channel: int):
        try:
            if 1 <= channel <= 8:
                self.activate_channel(channel)
            else:
                raise ValueError("Invalid channel number")
            self.current_channel = channel
            self.update_system_status()
            self.mqtt.send_response({
                "type": "channel_status",
                "channel": channel,
                "success": True
            })
        except Exception as e:
            logger.error(f"Channel selection error: {str(e)}")
            raise

    def activate_channel(self, channel: int):
        channel_methods = {
            1: self.GPIOController.Switch_1,
            2: self.GPIOController.Switch_2,
            3: self.GPIOController.Switch_3,
            4: self.GPIOController.Switch_4,
            5: self.GPIOController.Switch_5,
            6: self.GPIOController.Switch_6,
            7: self.GPIOController.Switch_7,
            8: self.GPIOController.Switch_8
        }
        
        channel_methods[channel]()
        logger.info(f"Activated UV channel {channel}")

    def all_off(self):
        self.GPIOController.set_all_pins(False)

    def cleanup(self):
        logger.info("Starting system cleanup")
        self.all_off()
        self.agilent.close()
        self.mqtt.disconnect()
        logger.info("Cleanup completed")
    
    def handle_burst_command(self, cycles: int):
        try:
            self.n_burst_series(cycles)
            self.mqtt.send_response({
                "type": "burst_status",
                "cycles": cycles,
                "success": True
            })
        except Exception as e:
            logger.error(f"Burst command error: {str(e)}")
            raise

    def n_burst_series(self, n: int):
        try:
            self.agilent.apply_waveform("PULS", 10000, 1.0)
            self.agilent.inst.write("FUNC:PULS:DCYCLE 20")
            for cycle_count in range(n, 0, -1):
                self.agilent.set_burst_mode(cycles=cycle_count, trigger_source="BUS", enable=True)
                self.agilent.send_trigger()
                time.sleep(0.1)
                
            logger.info(f"Completed {n} burst cycles")
            
        except Exception as e:
            logger.error(f"Burst operation failed: {str(e)}")
            raise

    def demo_basic_waveforms(self):
        # Sine wave
        self.agilent.apply_waveform("SIN", 1000, 1.0)
        self.agilent.configure_output(load="INF", state=True)
        logger.info("Generating 1 kHz sine wave")
        time.sleep(3)
        
        # Square wave
        self.agilent.apply_waveform("SQU", 1000, 1.0)
        logger.info("Generating 1 kHz square wave")
        time.sleep(3)
        
        # Ramp wave
        self.agilent.apply_waveform("RAMP", 1000, 1.0)
        logger.info("Generating 1 kHz ramp wave")
        time.sleep(3)
        
        # Pulse wave
        self.agilent.configure_pulse(frequency=1000, width=100e-6, edge_time=1e-6)
        logger.info("Generating 1 kHz pulse wave")
        time.sleep(3)
        
        # Noise
        self.agilent.apply_waveform("NOIS", 1, 1.0)
        logger.info("Generating noise")
        time.sleep(3)

    def demo_am_modulation(self):
        """Demonstrate AM modulation"""
        logger.info("--- AM Modulation Demo ---")
        
        # Setup carrier
        self.agilent.apply_waveform("SIN", 1e6, 1.0)
        self.agilent.configure_output(load="INF", state=True)
        
        # Setup AM modulation
        self.agilent.set_am_modulation(depth=80, mod_frequency=1000, mod_shape="RAMP", enable=True)
        logger.info("AM Modulation enabled")
        time.sleep(5)
        
        # Disable AM
        self.agilent.set_am_modulation(enable=False)
        logger.info("AM Modulation disabled")

    def demo_fm_modulation(self):
        """Demonstrate FM modulation"""
        logger.info("--- FM Modulation Demo ---")
        
        # Setup carrier
        self.agilent.apply_waveform("SIN", 20e3, 1.0)
        self.agilent.configure_output(load="50", state=True)
        
        # Setup FM modulation
        self.agilent.set_fm_modulation(deviation=5e3, mod_frequency=1000, mod_shape="SIN", enable=True)
        logger.info("FM Modulation enabled")
        time.sleep(5)
        
        # Disable FM
        self.agilent.set_fm_modulation(enable=False)
        logger.info("FM Modulation disabled")

    def demo_frequency_sweep(self):
        """Demonstrate frequency sweep"""
        logger.info("--- Frequency Sweep Demo ---")
        
        # Setup waveform
        self.agilent.apply_waveform("SIN", 1000, 1.0)
        
        # Configure sweep
        self.agilent.set_frequency_sweep(start_freq=100, stop_freq=10000, sweep_time=5, enable=True)
        logger.info("Frequency sweep enabled")
        time.sleep(10)
        
        # Disable sweep
        self.agilent.set_frequency_sweep(enable=False)
        logger.info("Frequency sweep disabled")

    def demo_arbitrary_waveform(self):
        logger.info("--- Arbitrary Waveform Demo ---")
        
        # Create a simple arbitrary waveform
        data = [-1.0, -0.5, 0.0, 0.5, 1.0, 0.5, 0.0, -0.5]
        
        # Upload waveform
        self.agilent.upload_arbitrary_waveform(data)
        self.agilent.select_arbitrary_waveform()
        
        # Apply and output
        self.agilent.apply_waveform("USER", 1000, 1.0)
        logger.info("Arbitrary waveform enabled")
        time.sleep(5)
        
        # Create a more complex waveform
        x = np.linspace(0, 2*np.pi, 100)
        data = np.sin(x) * np.sin(5*x)
        
        # Upload and apply
        self.agilent.upload_arbitrary_waveform(data)
        self.agilent.apply_waveform("USER", 500, 1.0)
        logger.info("Complex arbitrary waveform enabled")
        time.sleep(5)


