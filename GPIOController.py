"""
Simple GPIO Controller for Raspberry Pi
Controls 4 GPIO pins that can be set high or low.
"""
import RPi.GPIO as GPIO
import time
import spidev

class GPIOController:    
    def __init__(self, pins=[24, 23, 22, 27]):
        'Pin 24: On/Off, Pins 23, 22, 27 are A2, A1 and A0 respectively. Aka 18 = 0/1, 22 = 2/0, 27 = 4/0 from binary numbering. Also all Pin references are BCM'
        self.pins = pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        
        print(f"GPIO Controller initialized with pins: {self.pins}")
    
    def set_pin(self, pin_index, state):        
        pin = self.pins[pin_index]
        GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
        print(f"Pin {pin} (index {pin_index}) set to {'HIGH' if state else 'LOW'}")
        return True
    
    def set_all_pins(self, state):
        for i in range(len(self.pins)):
            self.set_pin(i, state)
    
    def cleanup(self):
        GPIO.cleanup()
        print("GPIO cleanup complete")

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

class SPIController:
    """
    SPI controller for two devices:
    - Digital Potentiometer: uses hardware SPI plus GPIO PR* control.
    - PT100 sensor board.
    """
    def __init__(self, pinsPoti=[14, 9, 10, 25, 8], pinsPT=[18, 10, 14, 11, 9]):
        """
        pinsPoti: [CLK, SDO, SDI, PR*, CS*]
        pinsPT:   [DRDY, SDI, SCLK, CS*, SDO]
        """
        # Store pin mappings
        self.Poti_CLK = pinsPoti[0]
        self.Poti_SDO = pinsPoti[1]  # MISO
        self.Poti_SDI = pinsPoti[2]  # MOSI
        self.Poti_PR = pinsPoti[3]   # Parallel Reset
        self.Poti_CS = pinsPoti[4]

        self.PT_DRDY = pinsPT[0]
        self.PT_SDI = pinsPT[1]
        self.PT_SCLK = pinsPT[2]
        self.PT_CS = pinsPT[3]
        self.PT_SDO = pinsPT[4]

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(self.Poti_PR, GPIO.OUT)
        GPIO.output(self.Poti_PR, GPIO.HIGH) 

        GPIO.setup(self.PT_DRDY, GPIO.IN)

        GPIO.setup(self.PT_CS, GPIO.OUT)
        GPIO.output(self.PT_CS, GPIO.HIGH)

        # Setup SPI bus
        bus = 0
        device = 1  # Using CE1 for Poti
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = 500_000
        self.spi.mode = 0

        print("[SPI] Initialized on bus 0 device 1")

    def reset_poti(self):
        """Toggle PR* to reset the potentiometer."""
        print("[Poti] Resetting digipot via PR*")
        GPIO.output(self.Poti_PR, GPIO.LOW)
        time.sleep(0.01)
        GPIO.output(self.Poti_PR, GPIO.HIGH)
        time.sleep(0.01)

    def write_poti(self, data):
        """Send bytes to the digital potentiometer."""
        print(f"[Poti] Writing: {data}")
        self.spi.xfer2(data)

    def write_pt(self, data):
        """Write bytes to the PT device using software CS."""
        print(f"[PT] Writing: {data}")
        GPIO.output(self.PT_CS, GPIO.LOW)
        time.sleep(0.001)

        self.spi.xfer2(data)

        GPIO.output(self.PT_CS, GPIO.HIGH)

    def read_pt(self, length=1):
        """Read bytes from the PT device (software CS)."""
        GPIO.output(self.PT_CS, GPIO.LOW)
        time.sleep(0.001)

        result = self.spi.readbytes(length)

        GPIO.output(self.PT_CS, GPIO.HIGH)
        print(f"[PT] Read: {result}")
        return result

    def wait_for_drdy(self, timeout=1.0):
        """Block until DRDY goes low, or timeout (in seconds)."""
        print("[PT] Waiting for DRDY...")
        start = time.time()
        while GPIO.input(self.PT_DRDY) == GPIO.HIGH:
            if time.time() - start > timeout:
                print("[PT] DRDY timeout!")
                return False
            time.sleep(0.001)
        print("[PT] DRDY is LOW, ready.")
        return True

    def cleanup(self):
        """Clean up SPI and GPIO."""
        print("[SPI] Cleaning up...")
        self.spi.close()
        GPIO.cleanup()