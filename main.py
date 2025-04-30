import pyvisa
import time
import numpy as np
import argparse
import sys
import logging
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

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Control Agilent 33250A Signal Generator")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="USB-to-serial port (default: /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=57600, help="Baud rate (default: 57600)")
    parser.add_argument("--list-ports", action="store_true", help="List available serial ports")
    parser.add_argument("--demo", action="store_true", help="Run demo sequence")
    
    args = parser.parse_args()
    
    if args.list_ports:
        ports = Agilent_Controller_RS232.find_usb_serial_ports()
        print("Available USB-to-Serial ports:")
        for port in ports:
            print(f"  {port}")
        return
    
    try:
        logger.info(f"Connecting to Agilent 33250A on {args.port} at {args.baud} baud")
        generator = Agilent_Controller_RS232.Agilent33250A(port=args.port, baud_rate=args.baud)
        
        if args.demo:
            Agilent_Controller_RS232.demo_basic_waveforms(generator)
            Agilent_Controller_RS232.demo_am_modulation(generator)
            Agilent_Controller_RS232.demo_fm_modulation(generator)
            Agilent_Controller_RS232.demo_frequency_sweep(generator)
            Agilent_Controller_RS232.demo_burst_mode(generator)
            Agilent_Controller_RS232.demo_arbitrary_waveform(generator)
        else:
            print("Connected to Agilent 33250A")
            print("Type 'exit' to quit")
            
            while True:
                cmd = input("Command: ")
                if cmd.lower() in ['exit', 'quit']:
                    break
                elif cmd.strip():
                    try:
                        if '?' in cmd:
                            response = generator.inst.query(cmd)
                            print(f"Response: {response}")
                        else:
                            generator.inst.write(cmd)
                            print("Command sent")
                    except Exception as e:
                        print(f"Error: {str(e)}")
        
        generator.close()
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()