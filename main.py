import pyvisa
import time
import numpy as np
import argparse
import sys
import logging
import Agilent_Controller_RS232 
import MQTTHandler

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
    global generator
    
    parser = argparse.ArgumentParser(description="Control Agilent 33250A Signal Generator with RS232 and MQTT")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="USB-to-serial port (default: /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=57600, help="Baud rate (default: 57600)")
    parser.add_argument("--list-ports", action="store_true", help="List available serial ports")
    parser.add_argument("--demo", action="store_true", help="Run demo sequence")
    parser.add_argument("--mqtt", action="store_true", help="Enable MQTT communication")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker address (default: localhost)")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port (default: 1883)")
    parser.add_argument("--mqtt-client-id", default="agilent_controller", help="MQTT client ID")
    
    args = parser.parse_args()
    
    if args.list_ports:
        ports = Agilent_Controller_RS232.find_usb_serial_ports()
        print("Available USB-to-Serial ports:")
        for port in ports:
            print(f"  {port}")
        return
    
    mqtt_handler = None
    
    try:
        logger.info(f"Connecting to Agilent 33250A on {args.port} at {args.baud} baud")
        generator = Agilent_Controller_RS232.Agilent33250A(port=args.port, baud_rate=args.baud)
        
        # Initialize and connect MQTT if enabled
        if args.mqtt:
            mqtt_handler = MQTTHandler(
                broker=args.mqtt_broker,
                port=args.mqtt_port,
                client_id=args.mqtt_client_id
            )
            if not mqtt_handler.connect():
                logger.warning("MQTT connection failed, continuing with RS232 only")
        
        if args.demo:
            # Run demo sequence
            logger.info("Running demo sequence")
            Agilent_Controller_RS232.demo_basic_waveforms(generator)
            Agilent_Controller_RS232.demo_am_modulation(generator)
            Agilent_Controller_RS232.demo_fm_modulation(generator)
            Agilent_Controller_RS232.demo_frequency_sweep(generator)
            Agilent_Controller_RS232.demo_burst_mode(generator)
            Agilent_Controller_RS232.demo_arbitrary_waveform(generator)
        else:
            # Interactive mode
            print("Connected to Agilent 33250A")
            if mqtt_handler and mqtt_handler.connected:
                print(f"MQTT enabled - listening on topic {mqtt_handler.command_topic}")
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
                            # Also publish to MQTT if enabled
                            if mqtt_handler and mqtt_handler.connected:
                                mqtt_handler.publish_response(cmd, response.strip())
                        else:
                            generator.inst.write(cmd)
                            print("Command sent")
                            # Also publish to MQTT if enabled
                            if mqtt_handler and mqtt_handler.connected:
                                mqtt_handler.publish_response(cmd, "Command executed")
                    except Exception as e:
                        print(f"Error: {str(e)}")
        
        # Clean up
        if mqtt_handler and mqtt_handler.connected:
            mqtt_handler.disconnect()
        
        # Close connection to generator
        generator.close()
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        
        # Attempt to clean up
        try:
            if mqtt_handler and mqtt_handler.connected:
                mqtt_handler.disconnect()
        except:
            pass
            
        try:
            if generator:
                generator.close()
        except:
            pass
            
        sys.exit(1)


if __name__ == "__main__":
    main()