"""
Simple GPIO Controller for Raspberry Pi
Controls 4 GPIO pins that can be set high or low.
"""
import RPi.GPIO as GPIO
import time
import spidev
import logging
import sys
import json
from dataclasses import dataclass
from dataclasses import asdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("GPIO logging"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GPIOController:    
    def __init__(self, pins=[24, 23, 22, 27]):
        'Pin 24: On/Off, Pins 23, 22, 27 are A2, A1 and A0 respectively. Aka 18 = 0/1, 22 = 2/0, 27 = 4/0 from binary numbering. Also all Pin references are BCM'
        self.pins = pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        
        logging.info(f"GPIO Controller initialized with pins: {self.pins}")
    
    def set_pin(self, pin_index, state):        
        pin = self.pins[pin_index]
        GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
        logging.info(f"Pin {pin} (index {pin_index}) set to {'HIGH' if state else 'LOW'}")
        return True
    
    def set_all_pins(self, state):
        for i in range(len(self.pins)):
            self.set_pin(i, state)
    
    def cleanup(self):
        GPIO.cleanup()
        logging.info("GPIO cleanup complete")

    def Switch_1(self):
        self.set_all_pins(state=False)
        self.set_pin(pin_index=0, state=True) 

    def Switch_2(self):
        self.set_all_pins(state=False)
        self.set_pin(pin_index=0, state=True) 
        self.set_pin(pin_index=1, state=True) 

    def Switch_3(self):
        self.set_all_pins(state=False)
        self.set_pin(pin_index=0, state=True) 
        self.set_pin(pin_index=2, state=True) 

    def Switch_4(self):
        self.set_all_pins(state=False)
        self.set_pin(pin_index=0, state=True)
        self.set_pin(pin_index=1, state=True)
        self.set_pin(pin_index=2, state=True)

    def Switch_5(self):
        self.set_all_pins(state=False)
        self.set_pin(pin_index=0, state=True)
        self.set_pin(pin_index=3, state=True) 

    def Switch_6(self):
        self.set_all_pins(state=False)
        self.set_pin(pin_index=0, state=True)
        self.set_pin(pin_index=3, state=True)
        self.set_pin(pin_index=1, state=True)

    def Switch_7(self):
        self.set_all_pins(state=False)
        self.set_pin(pin_index=0, state=True)
        self.set_pin(pin_index=3, state=True)
        self.set_pin(pin_index=2, state=True)

    def Switch_8(self):
        self.set_all_pins(state=True)

@dataclass
class CalibrationPoint:
    name: str
    code: int
    voltage: float
    notes: str = ""

class AD5260Controller:
    def __init__(self, pins=[14, 9, 10, 25, 8], rab=20000, vdd=5.0, vss=0.0):
        """
        Initialize SPI interface for AD5260 control.
        Parameters:
        - pins: [CLK, SDO, SDI, PR*, CS*] (BCM numbering)
        - rab: Nominal resistance (20kΩ, 50kΩ, or 200kΩ)
        - vdd: Positive supply voltage (default 5.0V)
        - vss: Negative supply voltage (default 0.0V)
        """
        self.CLK = pins[0]  # Clock
        self.SDO = pins[1]  # MISO (not used for AD5260 write)
        self.SDI = pins[2]  # MOSI
        self.PR = pins[3]   # Parallel Reset (active low)
        self.CS = pins[4]   # Chip Select (active low)

        self.rab = rab      # Nominal resistance (ohms)
        self.rw = 60        # Wiper resistance (ohms)
        self.vdd = vdd      # Positive supply
        self.vss = vss      # Negative supply

        self.calibration_points = []

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.PR, GPIO.OUT)
        GPIO.output(self.PR, GPIO.HIGH)  # Deassert reset
        GPIO.setup(self.CS, GPIO.OUT)
        GPIO.output(self.CS, GPIO.HIGH)  # Deselect device
        
        # Setup SPI bus (using hardware SPI)
        self.spi = spidev.SpiDev()
        self.spi.open(0, 1)  # Bus 0, CE1
        self.spi.max_speed_hz = 500000
        self.spi.mode = 0b00  # CPOL=0, CPHA=0
        
        logging.info(f"[AD5260] Initialized | RAB={rab/1000}kΩ | VDD={vdd}V | VSS={vss}V")

    def reset(self):
        GPIO.output(self.PR, GPIO.LOW)
        time.sleep(0.01)  # 10ms pulse width
        GPIO.output(self.PR, GPIO.HIGH)
        logging.info("[AD5260] Reset to midscale (code 128)")

    def set_resistance(self, code):
        """
        Set wiper position (0-255)
        0 = minimum resistance (A terminal)
        255 = maximum resistance (B terminal)
        """
        if not 0 <= code <= 255:
            raise ValueError("Code must be 0-255")
            
        data = [code]
        GPIO.output(self.CS, GPIO.LOW)
        self.spi.xfer2(data)
        GPIO.output(self.CS, GPIO.HIGH)
        
        logging.info(f"[AD5260] Set code: {code} | Expected voltage: {self.calculate_voltage(code):.2f}V")

    def calculate_voltage(self, code):
        """
        Calculate expected wiper voltage based on current code.
        Formula from AD5260 datasheet: V_W = (D/256)*(V_A - V_B) + V_B
        """
        return (code / 256) * (self.vdd - self.vss) + self.vss

    def voltage_sweep(self, start_v, end_v, steps, duration=0.1):
        if not (self.vss <= start_v <= self.vdd) or not (self.vss <= end_v <= self.vdd):
            raise ValueError(f"Voltages must be between {self.vss}V and {self.vdd}V")
        results = []
        step_size = (end_v - start_v) / steps
        logging.info(f"[AD5260] Starting sweep: {start_v}V → {end_v}V ({steps} steps)")
        
        for step in range(steps + 1):
            target_v = start_v + step * step_size
            code = int(255 * (target_v - self.vss) / (self.vdd - self.vss))
            code = max(0, min(255, code))  # Clamp to valid range
            
            self.set_resistance(code)
            time.sleep(duration)
            
            results.append({
                'step': step,
                'code': code,
                'target_v': target_v,
                'actual_v': self.calculate_voltage(code),
                'timestamp': time.time()
            })
        
        return results

    def save_calibration(self, filename="ad5260_calibration.json"):
        #Save calibration data to JSON file
        data = {
            'device': 'AD5260',
            'rab': self.rab,
            'vdd': self.vdd,
            'vss': self.vss,
            'calibration': [asdict(p) for p in self.calibration_points]
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        logging.info(f"[AD5260] Saved calibration to {filename}")

    def load_calibration(self, filename="ad5260_calibration.json"):
        with open(filename) as f:
            data = json.load(f)
        self.calibration_points = [CalibrationPoint(**p) for p in data['calibration']]
        print(f"[AD5260] Loaded {len(self.calibration_points)} calibration points")

    def cleanup(self):
        self.spi.close()
        GPIO.cleanup()
        print("[AD5260] Cleaned up SPI and GPIO")
