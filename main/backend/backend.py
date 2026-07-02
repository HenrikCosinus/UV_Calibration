from agilent_controller_rs232 import Agilent33250A
from gpio_controller import Multiplexer, AD5260Controller, MAX31865Controller
import logging
import sys
import os
import serial
import RPi.GPIO as GPIO
import time
import numpy as np
import json
import paho.mqtt.client as mqtt
from mqtt_handler import MQTTHandler
import threading

# Logging is configured centrally in main.py. basicConfig here is commented out so
# it does not override the root logger that main.py sets up before importing this module.
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("HighLevelControl.log"),
#         logging.StreamHandler(sys.stdout)
#     ]
# )
logger = logging.getLogger(__name__)

class HighLevelControl():
    def __init__(self):
        logger.info("hardware initialization worked in the _init_")
        self.system_status = "idle"
        # BUG FIX (Bug 1): current_channel was never initialized. handle_channel_selection()
        # uses it as a fallback default when no "channel" key is in the command, causing
        # AttributeError on the very first call.
        self.current_channel = None
        logger.info("[Backend] system_status=idle, current_channel=None")
        topics = {
            'temperature': f"/temperature",
            'operation_status': f"/status",
            'UI_command': f"/ui_command",
            'control_response': f"/control_response",
            'hardware_status': f"/hardware_status",
        }
        self.mqtt = MQTTHandler(
            client_id="backend_controller",
            broker="localhost",
            port=1883,
            topics=topics
            )
        self.setup_mqtt_handlers()
        self.mqtt.connect()
        self.initialize_hardware()
        self.start_temp_loop(interval=5)

    def initialize_hardware(self):
        self.agilent = None
        self.GPIOController = None
        self.AD5260Controller = None
        self.MAX31865Controller = None

        try:
            self.agilent = Agilent33250A(port="/dev/ttyUSB0", baud_rate=57600, timeout=5000)
            logger.info("[Hardware] Agilent initialized.")
        except Exception as e:
            logger.warning(f"[Hardware] Agilent init failed — continuing without it: {e}")

        try:
            self.GPIOController = Multiplexer(pins=[17, 18, 22, 27])
            logger.info("[Hardware] GPIO multiplexer initialized.")
        except Exception as e:
            logger.warning(f"[Hardware] GPIO multiplexer init failed — continuing without it: {e}")

        try:
            self.AD5260Controller = AD5260Controller(pins=[14, 9, 10, 25, 8], rab=20000, vdd=10.0, vss=0.0)
            logger.info("[Hardware] AD5260 potentiometer initialized.")
        except Exception as e:
            logger.warning(f"[Hardware] AD5260 init failed — continuing without it: {e}")

        # TODO: CS pin conflict — AD5260 is initialized with CS=BCM8 (physical pin 24, CE0) via GPIO bit-bang,
        # and MAX31865 is also assigned CS=BCM8 via board.D8. When both are connected, move AD5260 CS to
        # BCM7 (physical pin 26, CE1) and update spidev.open(0,1) to match, or move MAX31865 to a free GPIO.
        try:
            self.MAX31865Controller = MAX31865Controller(cs_pin=5, wires=3, rtd_nominal=100.0, ref_resistor=430.0)
            logger.info("[Hardware] MAX31865 temperature sensor initialized.")
        except Exception as e:
            logger.warning(f"[Hardware] MAX31865 init failed — continuing without it: {e}")

        available = [name for name, obj in [
            ("Agilent", self.agilent),
            ("GPIO", self.GPIOController),
            ("AD5260", self.AD5260Controller),
        ] if obj is not None]
        logger.info(f"[Hardware] Initialization complete. Available: {available}")

        # Publish hardware init status so the frontend can show persistent error banners.
        # Each key is False if that device failed to initialize.
        self.mqtt.publish("/hardware_status", json.dumps({
            "agilent":  self.agilent is not None,
            "gpio":     self.GPIOController is not None,
            "ad5260":   self.AD5260Controller is not None,
            "max31865": self.MAX31865Controller is not None,
        }), qos=1, retain=True)

    def setup_mqtt_handlers(self):
        self.mqtt.on_ui_command(self.handle_ui_command)
        logger.info("[Backend] MQTT handler registered: /ui_command → handle_ui_command")

    def start_temp_loop(self, interval):
        temp_thread = threading.Thread(target=self.update_temp_loop, args=(interval,), daemon=True)
        temp_thread.start()
        logger.info("Temperature loop started in background thread")

    def update_temp_loop(self, interval):
        file_path = "Temperature_measurements.json"
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                json.dump([], f)
        while True:
            try:
                if self.MAX31865Controller is None:
                    logger.warning("[update_temp_loop] MAX31865 not available, skipping read.")
                    time.sleep(interval)
                    continue
                temp_k = float(self.MAX31865Controller.read_temperature_k())
                timestamp = time.time()
                measurement = {
                    "timestamp": timestamp,
                    "temperature_k": temp_k
                }
                payload = json.dumps(measurement)
                self.mqtt.publish("/temperature", payload, qos=1)
                with open(file_path, "r+") as f:
                    data = json.load(f)
                    data.append(measurement)
                    if len(data) > 1000:
                        data = data[-1000:]
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, indent=2)

            except Exception as e:
                logging.error(f"[MAX31865] Read error: {e}")
            time.sleep(interval)

    def connect_to_generator(self):
        # BUG FIX (Bug 7): opening a new Agilent33250A without closing the existing one
        # leaked the old pyvisa resource handle. Now explicitly close before reconnecting.
        if self.agilent is not None:
            try:
                logger.info("[connect_to_generator] Closing existing Agilent connection before reconnect.")
                self.agilent.close()
            except Exception as e:
                logger.warning(f"[connect_to_generator] Error closing existing connection: {e}")
            self.agilent = None

        for port in Agilent33250A.find_usb_serial_ports():
            try:
                logger.info(f"[connect_to_generator] Trying port {port}...")
                self.agilent = Agilent33250A(port=port)
                logger.info(f"[connect_to_generator] Connected on {port}")
                return
            except Exception as e:
                logger.warning(f"[connect_to_generator] Failed on {port}: {e}")
                continue
        raise RuntimeError("No Agilent 33250A device found on available ports")


    def handle_ui_command(self, command):
        try:
            command = json.loads(command) if isinstance(command, str) else command
            logger.info(f"[handle_ui_command] ← received: {command}")

            command_type = command.get("type")

            if command_type == "channel_select":
                self.handle_channel_selection(command)

            elif command_type == "burst":
                threading.Thread(target=self.handle_burst_command, args=(command,), daemon=True).start()
                logger.info("[handle_ui_command] burst started in background thread")

            elif command_type == "signal_config":
                self.handle_signal_config(command)
            
            elif command_type == "connect_generator":
                self.connect_to_generator()
            
            elif command_type == "disconnect_generator":
                self.agilent.disconnect()

            elif command_type == "all_off":
                self.all_off()
            
            elif command_type == "trigger_burst":
                # BUG FIX (Bug 5): was passing the entire command dict as `n` to send_trigger().
                # send_trigger(n) uses n only for the log file entry; *TRG still fires either way,
                # but the log file would contain a JSON object string instead of a cycle count.
                # self.agilent.send_trigger(command)
                burst_n = command.get("cycles", 1)
                logger.info(f"[trigger_burst] Triggering burst, cycles={burst_n}")
                self.agilent.send_trigger(burst_n)

            elif command_type == "pulse_train_sweep":
                # Run in a background thread so the paho network loop stays free to
                # send keepalive PINGREQs. Blocking here caused broker disconnect after 60s.
                threading.Thread(target=self.sweeping_pulse_train, daemon=True).start()
                logger.info("[handle_ui_command] pulse_train_sweep started in background thread")

            elif command_type == "potentiometer_voltage_sweep":
                # Same reason — sweep can take minutes (255 steps × duration), must not block paho.
                threading.Thread(target=self.voltage_sweep, args=(command,), daemon=True).start()
                logger.info("[handle_ui_command] voltage_sweep started in background thread")

            elif command_type == "potentiometer_set_percent":
                self.handle_channel_selection(command)

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
        if self.agilent is None:
            logger.error("[handle_signal_config] Agilent not available.")
            self.mqtt.send_response({"error": "Agilent not connected."})
            return
        try:
            frequency = float(command.get("frequency", 1000))                   # Default 1 kHz
            burst_count = int(command.get("bursts", 10))                        # Default 10 bursts
            duty_cycle = float(command.get("duty_cycle", 50.0))                 # Default 50%
            amplitude = float(command.get("amplitude", 3.0))                    # Default 3 V (no UI control yet)
            inter_block_delay = float(command.get("inter_block_delay", 0.5))    # Default 0.5s wait between blocks

            # BUG FIX (Bug 8): was logging `{self.configure_signal}` which prints the function
            # object reference, not useful data. Replaced with actual parameter values.
            # logger.info(f"handle_signal_config reaches at least up to the config transmittance to the agilent {self.configure_signal}")
            logger.info(f"[handle_signal_config] freq={frequency}Hz bursts={burst_count} duty={duty_cycle}% amp={amplitude}V delay={inter_block_delay}s")
            self.configure_signal(frequency=frequency, burst_count=burst_count, duty_cycle=duty_cycle, amplitude=amplitude, inter_block_delay=inter_block_delay)
            logger.info("[handle_signal_config] Signal configuration applied successfully.")
            self.mqtt.send_response({"status": "Signal configuration applied."})

        except Exception as e:
            logger.error(f"Error in handle_signal_config: {str(e)}")
            self.mqtt.send_response({"error": f"Signal config failed: {str(e)}"})

    def configure_signal(self, frequency, burst_count, duty_cycle, amplitude, inter_block_delay):
        try:
            period = 1.0 / frequency
            width = period * (duty_cycle / 100.0)
            edge_time = min(1e-6, 0.1 * width)

            self.agilent.configure_pulse(
                frequency=frequency,
                width=width,
                edge_time=edge_time
            )
            self.agilent.send("OUTPUT ON")
            self.agilent.set_burst_mode(
                cycles=burst_count,
                trigger_source="BUS",
                enable=True
            )

            self.inter_block_delay = inter_block_delay

            logger.info(f"Signal configured: frequency={frequency}, period={period}, width={width}, duty_cycle={duty_cycle}, bursts={burst_count}, inter_block_delay={inter_block_delay}")

        except Exception as e:
            logger.error(f"Failed to configure signal: {str(e)}")
            raise
    
    def voltage_sweep(self, command):
        if self.AD5260Controller is None:
            logger.error("[voltage_sweep] AD5260 not available.")
            self.mqtt.send_response({"error": "Potentiometer not connected."})
            return
        # BUG FIX (Bug 2): Key names mismatched with what the Frontend sends.
        # Frontend publishes: "voltage_start_v", "voltage_end_v", "voltage_sweep_steps", "voltage_sweep_duration"
        # Backend was reading: "start_v", "end_v", "sweep_steps", "sweep_duration"
        # Result: sweep always ran with default values, completely ignoring UI input.
        # voltage_start_v = float(command.get("start_v", 0))
        # voltage_end_v = float(command.get("end_v", 10))
        # voltage_sweep_steps = float(command.get("sweep_steps", 256))
        # voltage_sweep_duration = float(command.get("sweep_duration", 5))
        voltage_start_v = float(command.get("voltage_start_v", 0))
        voltage_end_v = float(command.get("voltage_end_v", 10))
        voltage_sweep_steps = int(command.get("voltage_sweep_steps", 256))
        voltage_sweep_duration = float(command.get("voltage_sweep_duration", 5))
        logger.info(f"[voltage_sweep] start={voltage_start_v}V end={voltage_end_v}V steps={voltage_sweep_steps} duration={voltage_sweep_duration}s")
        self.AD5260Controller.voltage_sweep(start_v=voltage_start_v, end_v=voltage_end_v, steps=voltage_sweep_steps, duration=voltage_sweep_duration)

    def handle_channel_selection(self, command):
        if self.GPIOController is None or self.AD5260Controller is None:
            logger.error("[handle_channel_selection] GPIO or AD5260 not available.")
            self.mqtt.send_response({"error": "GPIO or potentiometer not connected."})
            return
        try:
            channel = command.get("channel", self.current_channel)  # Default to current if not given
            logger.info(f"[handle_channel_selection] requested channel={channel}, current_channel={self.current_channel}")
            if channel is not None and (1 <= channel <= 8) and channel != self.current_channel:
                self.activate_channel(channel)
                self.current_channel = channel
                logger.info(f"[handle_channel_selection] switched to channel {channel}")
            elif channel is None:
                logger.warning("[handle_channel_selection] No channel in command and current_channel is None — skipping activate.")

            percent = command.get("percent", 50)
            if not (0 <= percent <= 100):
                raise ValueError("Percent must be between 0 and 100")
            code = int((percent / 100) * 255)
            self.AD5260Controller.set_resistance(code)
            logger.info(f"[handle_channel_selection] Potentiometer for channel {channel} set to {percent:.1f}% (code {code})")

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
        if self.GPIOController is None:
            logger.warning("[all_off] GPIO not available, skipping.")
            return
        self.GPIOController.set_all_pins(False)

    def cleanup(self):
        logger.info("Starting system cleanup")
        self.all_off()
        self.agilent.close()
        self.mqtt.disconnect()
        logger.info("Cleanup completed")
    
    def handle_burst_command(self, command):
        if self.agilent is None:
            logger.error("[handle_burst_command] Agilent not available.")
            self.mqtt.send_response({"error": "Agilent not connected."})
            return
        try:
            cycles = command.get("cycles")
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
            period = 1.0 / 10000
            width = period * 0.2  # 20% duty cycle
            self.agilent.configure_pulse(frequency=10000, width=width, edge_time=1e-6)

            for cycle_count in range(n, 0, -1):
                self.agilent.set_burst_mode(cycles=cycle_count, trigger_source="BUS", enable=True)
                self.agilent.send_trigger(cycle_count)
                time.sleep(0.1)

            logger.info(f"Completed {n} burst cycles")

        except Exception as e:
            logger.error(f"Burst operation failed: {str(e)}")
            raise
    
    def sweeping_pulse_train(self, max_pulses=20, min_pulses=1, inter_train_wait=0.1):
        if self.agilent is None:
            logger.error("[sweeping_pulse_train] Agilent not available.")
            self.mqtt.send_response({"error": "Agilent not connected."})
            return
        try:
            self.agilent.send("*RST")
            self.agilent.send("*CLS")
            self.agilent.send("FUNCTION SQUARE")
            self.agilent.send("FREQUENCY 5E6")  # 5 MHz
            self.agilent.send("OUTPUT ON")
            self.agilent.send("BURST:MODE TRIG")
            self.agilent.send("BURST:PHASE 0")
            self.agilent.send("TRIGGER:SOURCE BUS")
            self.agilent.send("BURST:STATE ON")

            logger.info("Starting pulse train sweep")

            for n in range(max_pulses, min_pulses - 1, -1):
                self.agilent.send(f"BURST:NCYCLES {n}")
                self.agilent.send_trigger(n)
                time.sleep(inter_train_wait)  # Wait 100 ms or as needed

            logger.info("Pulse train sweep complete.")

        except Exception as e:
            logger.error(f"Pulse train sweep failed: {str(e)}")
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


