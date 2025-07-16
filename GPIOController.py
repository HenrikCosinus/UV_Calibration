"""
Simple GPIO Controller for Raspberry Pi
Controls 4 GPIO pins that can be set high or low.
"""
import RPi.GPIO as GPIO
import time

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

class Potentiometer_controller:
    def __init__(self, pins=[]):
        self.pins = pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        
        print(f"GPIO Controller initialized with pins: {self.pins}")