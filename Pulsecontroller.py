from gpiozero import LED
from time import sleep
import json

class LEDPulseController:
    def __init__(self, config_file="led_config.json"):
        """
        Initialize with configuration file
        """
        with open(config_file) as f:
            self.config = json.load(f)
        
        self.led = LED(self.config["gpio_pin"])
        
    def pulse(self, duration=0.5, pause=0.5, count=1):
        """
        Simple LED pulse
        """
        for _ in range(count):
            self.led.on()
            sleep(duration)
            self.led.off()
            sleep(pause)
    
    def morse_code(self, message, dot_duration=0.2):
        """
        Morse code blinking
        """
        morse_dict = {
            'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.',
            'F': '..-.', 'G': '--.', 'H': '....', 'I': '..', 'J': '.---',
            'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.', 'O': '---',
            'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-',
            'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--',
            'Z': '--..', ' ': ' '
        }
        
        for char in message.upper():
            if char in morse_dict:
                code = morse_dict[char]
                print(f"{char}: {code}")
                for symbol in code:
                    if symbol == '.':
                        self.led.on()
                        sleep(dot_duration)
                        self.led.off()
                    elif symbol == '-':
                        self.led.on()
                        sleep(dot_duration * 3)
                        self.led.off()
                    sleep(dot_duration)  # Pause between symbols
                sleep(dot_duration * 2)  # Pause between letters
    
    def run_pattern(self, pattern_name):
        """Run a predefined pattern from config"""
        pattern = self.config["patterns"][pattern_name]
        
        if pattern["type"] == "pulse":
            self.pulse(
                duration=pattern["duration"],
                pause=pattern["pause"],
                count=pattern["count"]
            )
        elif pattern["type"] == "morse":
            self.morse_code(
                message=pattern["message"],
                dot_duration=pattern["dot_duration"]
            )
        elif pattern["type"] == "custom":
            for _ in range(pattern.get("repeat", 1)):
                for step in pattern["sequence"]:
                    self.led.on() if step["state"] else self.led.off()
                    sleep(step["duration"])
