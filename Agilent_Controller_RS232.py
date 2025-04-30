#!/usr/bin/env python3
"""
Raspberry Pi to Agilent 33250A Signal Generator Communication via RS-232
===============================================================
This script provides a complete implementation for controlling an Agilent 33250A
signal generator from a Raspberry Pi using a USB-to-RS232 adapter.

Requirements:
- Raspberry Pi (any model)
- USB-to-RS232 adapter
- PyVISA and PyVISA-py libraries
- Agilent 33250A signal generator with RS-232 port

Hardware Setup:
- Connect USB-to-RS232 adapter to Raspberry Pi
- Connect RS-232 cable from adapter to Agilent 33250A rear panel RS-232 port
- Configure 33250A for RS-232 operation (see manual for details)

Installation:
    sudo apt-get update
    sudo apt-get install python3-pip
    pip3 install pyvisa pyvisa-py pyserial
"""

import pyvisa
import time
import numpy as np
import argparse
import sys
import logging

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

"""Class to control the Agilent 33250A Function/Arbitrary Waveform Generator"""
class Agilent33250A:
    def __init__(self, port="/dev/ttyUSB0", baud_rate=57600, timeout=5000):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.inst = None
    
        try:
            self.rm = pyvisa.ResourceManager('@py')
            resources = self.rm.list_resources()
            logger.info(f"Available resources: {resources}")
            
            # Connect using ASRL (Serial) resource
            resource_name = f"ASRL{port}::INSTR"
            logger.info(f"Connecting to {resource_name}")
            self.inst = self.rm.open_resource(resource_name)
            
            # Configure serial settings
            self.inst.baud_rate = baud_rate
            self.inst.data_bits = 8
            self.inst.stop_bits = pyvisa.constants.StopBits.one
            self.inst.parity = pyvisa.constants.Parity.none
            self.inst.flow_control = pyvisa.constants.VI_ASRL_FLOW_DTR_DSR
            self.inst.timeout = timeout
            
            # Test connection
            self.inst.write("*IDN?")
            idn = self.inst.read()
            logger.info(f"Connected to: {idn}")
            self.reset()
            
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            raise
    
    def reset(self):
        logger.info("Resetting instrument...")
        self.inst.write("*RST")
        self.inst.write("*CLS")
        
    def check_errors(self):
        while True:
            err = self.inst.query(":SYST:ERR?").strip()
            err_num = int(err.split(',')[0])
            if err_num == 0:
                break
            else:
                logger.warning(f"Instrument error: {err}")
                
    def close(self):
        if self.inst:
            self.inst.close()
            logger.info("Connection closed")
            
    def configure_output(self, load="INF", state=True):
        """        
        Args:
            load (str): Output load in ohms or "INF" for high impedance
            state (bool): Enable/disable output
        """
        self.inst.write(f"OUTPUT:LOAD {load}")
        self.inst.write(f"OUTPUT:STATE {'ON' if state else 'OFF'}")
        
    def configure_sync(self, state=True):
        """
        Args:
            state (bool): Enable/disable sync output
        """
        self.inst.write(f"OUTPUT:SYNC {'ON' if state else 'OFF'}")
        
    def apply_waveform(self, waveform_type, frequency, amplitude, offset=0):
        """
        Apply a standard waveform
        
        Args:
            waveform_type (str): SIN, SQU, RAMP, PULS, NOIS, DC, USER
            frequency (float): Frequency in Hz
            amplitude (float): Peak-to-peak amplitude in volts
            offset (float): DC offset in volts
        """
        cmd = f"APPLY:{waveform_type} {frequency},{amplitude},{offset}"
        logger.info(f"Applying waveform: {cmd}")
        self.inst.write(cmd)
        
    def set_am_modulation(self, depth=80, mod_frequency=1000, mod_shape="SIN", enable=True):
        """
        Configure amplitude modulation
        
        Args:
            depth (int): Modulation depth in percent (0-120)
            mod_frequency (float): Modulation frequency in Hz
            mod_shape (str): SIN, SQU, RAMP, NOIS, or USER
            enable (bool): Enable/disable modulation
        """
        self.inst.write(f"AM:INTERNAL:FUNCTION {mod_shape}")
        self.inst.write(f"AM:INTERNAL:FREQUENCY {mod_frequency}")
        self.inst.write(f"AM:DEPTH {depth}")
        self.inst.write(f"AM:STATE {'ON' if enable else 'OFF'}")
        
    def set_fm_modulation(self, deviation=1000, mod_frequency=1000, mod_shape="SIN", enable=True):
        """
        Configure frequency modulation
        
        Args:
            deviation (float): Frequency deviation in Hz
            mod_frequency (float): Modulation frequency in Hz
            mod_shape (str): SIN, SQU, RAMP, NOIS, or USER
            enable (bool): Enable/disable modulation
        """
        self.inst.write(f"FM:INTERNAL:FUNCTION {mod_shape}")
        self.inst.write(f"FM:INTERNAL:FREQUENCY {mod_frequency}")
        self.inst.write(f"FM:DEVIATION {deviation}")
        self.inst.write(f"FM:STATE {'ON' if enable else 'OFF'}")
        
    def set_frequency_sweep(self, start_freq=100, stop_freq=1000, sweep_time=1, enable=True):
        """
        Configure frequency sweep
        
        Args:
            start_freq (float): Start frequency in Hz
            stop_freq (float): Stop frequency in Hz
            sweep_time (float): Sweep time in seconds
            enable (bool): Enable/disable sweep
        """
        self.inst.write(f"FREQUENCY:START {start_freq}")
        self.inst.write(f"FREQUENCY:STOP {stop_freq}")
        self.inst.write(f"SWEEP:TIME {sweep_time}")
        self.inst.write(f"SWEEP:STATE {'ON' if enable else 'OFF'}")
        
    def configure_pulse(self, frequency=1000, width=100e-6, edge_time=10e-6):
        """
        Configure pulse waveform
        
        Args:
            frequency (float): Pulse frequency in Hz
            width (float): Pulse width in seconds
            edge_time (float): Edge time in seconds
        """
        period = 1.0 / frequency
        self.inst.write(f"FUNCTION PULSE")
        self.inst.write(f"PULSE:PERIOD {period}")
        self.inst.write(f"PULSE:WIDTH {width}")
        self.inst.write(f"PULSE:TRANSITION {edge_time}")
        
    def set_burst_mode(self, cycles=3, phase=0, trigger_source="BUS", enable=True):
        """
        Configure burst mode
        
        Args:
            cycles (int): Number of cycles per burst
            phase (float): Starting phase in degrees
            trigger_source (str): IMM, EXT, or BUS
            enable (bool): Enable/disable burst mode
        """
        self.inst.write(f"BURST:MODE TRIG")
        self.inst.write(f"BURST:NCYCLES {cycles}")
        self.inst.write(f"BURST:PHASE {phase}")
        self.inst.write(f"TRIGGER:SOURCE {trigger_source}")
        self.inst.write(f"BURST:STATE {'ON' if enable else 'OFF'}")
        
    def send_trigger(self):
        """Send software trigger"""
        self.inst.write("*TRG")
        
    def upload_arbitrary_waveform(self, data, name="VOLATILE"):
        """
        Upload arbitrary waveform data
        
        Args:
            data (list/array): Waveform data points (-1.0 to 1.0)
            name (str): Waveform name (default: VOLATILE)
        """
        if isinstance(data, np.ndarray):
            data_list = data.tolist()
        else:
            data_list = list(data)
            
        # Format as comma-separated list
        data_str = ",".join(str(x) for x in data_list)
        cmd = f"DATA:{name} "
        logger.info(f"Uploading arbitrary waveform ({len(data_list)} points)")
        self.inst.write(cmd + data_str)
        
    def upload_arbitrary_waveform_binary(self, data, name="VOLATILE"):
        """
        Upload arbitrary waveform data in binary format
        
        Args:
            data (numpy.ndarray): Waveform data points (-2047 to 2047)
            name (str): Waveform name (default: VOLATILE)
        """
        # Convert to int16 array (from -2047 to 2047)
        if not isinstance(data, np.ndarray):
            data = np.array(data, dtype=np.int16)
        else:
            data = data.astype(np.int16)
            
        cmd = f"DATA:DAC:{name} "
        logger.info(f"Uploading binary arbitrary waveform ({len(data)} points)")
        self.inst.write_binary_values(cmd, data, datatype='h', is_big_endian=True)
        
    def select_arbitrary_waveform(self, name="VOLATILE"):
        """
        Select an arbitrary waveform
        
        Args:
            name (str): Waveform name (default: VOLATILE)
        """
        self.inst.write(f"FUNCTION:USER {name}")
        
    def get_status_byte(self):
        """Get and return the status byte"""
        return int(self.inst.query("*STB?").strip())
    
    def wait_for_completion(self, timeout=10):
        """
        Wait for operation to complete
        
        Args:
            timeout (int): Timeout in seconds
            
        Returns:
            bool: True if successful, False if timed out
        """
        self.inst.write("*OPC")
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            stb = self.get_status_byte()
            if stb & 0x10:  # Check if operation complete bit is set
                return True
            time.sleep(0.1)
        return False


def demo_basic_waveforms(gen):
    """Demonstrate basic waveform generation capabilities"""
    logger.info("--- Basic Waveform Demo ---")
    
    # Sine wave
    gen.apply_waveform("SIN", 1000, 1.0)
    gen.configure_output(load="INF", state=True)
    logger.info("Generating 1 kHz sine wave")
    time.sleep(3)
    
    # Square wave
    gen.apply_waveform("SQU", 1000, 1.0)
    logger.info("Generating 1 kHz square wave")
    time.sleep(3)
    
    # Ramp wave
    gen.apply_waveform("RAMP", 1000, 1.0)
    logger.info("Generating 1 kHz ramp wave")
    time.sleep(3)
    
    # Pulse wave
    gen.configure_pulse(frequency=1000, width=100e-6, edge_time=1e-6)
    logger.info("Generating 1 kHz pulse wave")
    time.sleep(3)
    
    # Noise
    gen.apply_waveform("NOIS", 1, 1.0)
    logger.info("Generating noise")
    time.sleep(3)


def demo_am_modulation(gen):
    """Demonstrate AM modulation"""
    logger.info("--- AM Modulation Demo ---")
    
    # Setup carrier
    gen.apply_waveform("SIN", 1e6, 1.0)
    gen.configure_output(load="INF", state=True)
    
    # Setup AM modulation
    gen.set_am_modulation(depth=80, mod_frequency=1000, mod_shape="RAMP", enable=True)
    logger.info("AM Modulation enabled")
    time.sleep(5)
    
    # Disable AM
    gen.set_am_modulation(enable=False)
    logger.info("AM Modulation disabled")


def demo_fm_modulation(gen):
    """Demonstrate FM modulation"""
    logger.info("--- FM Modulation Demo ---")
    
    # Setup carrier
    gen.apply_waveform("SIN", 20e3, 1.0)
    gen.configure_output(load="50", state=True)
    
    # Setup FM modulation
    gen.set_fm_modulation(deviation=5e3, mod_frequency=1000, mod_shape="SIN", enable=True)
    logger.info("FM Modulation enabled")
    time.sleep(5)
    
    # Disable FM
    gen.set_fm_modulation(enable=False)
    logger.info("FM Modulation disabled")


def demo_frequency_sweep(gen):
    """Demonstrate frequency sweep"""
    logger.info("--- Frequency Sweep Demo ---")
    
    # Setup waveform
    gen.apply_waveform("SIN", 1000, 1.0)
    
    # Configure sweep
    gen.set_frequency_sweep(start_freq=100, stop_freq=10000, sweep_time=5, enable=True)
    logger.info("Frequency sweep enabled")
    time.sleep(10)
    
    # Disable sweep
    gen.set_frequency_sweep(enable=False)
    logger.info("Frequency sweep disabled")


def demo_burst_mode(gen):
    """Demonstrate burst mode"""
    logger.info("--- Burst Mode Demo ---")
    
    # Setup waveform
    gen.apply_waveform("SQU", 1000, 1.0)
    gen.inst.write("FUNC:SQU:DCYCLE 20")  # 20% duty cycle
    
    # Configure burst mode
    gen.set_burst_mode(cycles=5, trigger_source="BUS", enable=True)
    gen.configure_sync(state=True)
    
    # Send triggers
    logger.info("Sending burst triggers")
    for _ in range(10):
        gen.send_trigger()
        time.sleep(0.5)
    
    # Disable burst mode
    gen.set_burst_mode(enable=False)
    logger.info("Burst mode disabled")


def demo_arbitrary_waveform(gen):
    """Demonstrate arbitrary waveform generation"""
    logger.info("--- Arbitrary Waveform Demo ---")
    
    # Create a simple arbitrary waveform
    data = [-1.0, -0.5, 0.0, 0.5, 1.0, 0.5, 0.0, -0.5]
    
    # Upload waveform
    gen.upload_arbitrary_waveform(data)
    gen.select_arbitrary_waveform()
    
    # Apply and output
    gen.apply_waveform("USER", 1000, 1.0)
    logger.info("Arbitrary waveform enabled")
    time.sleep(5)
    
    # Create a more complex waveform
    x = np.linspace(0, 2*np.pi, 100)
    data = np.sin(x) * np.sin(5*x)
    
    # Upload and apply
    gen.upload_arbitrary_waveform(data)
    gen.apply_waveform("USER", 500, 1.0)
    logger.info("Complex arbitrary waveform enabled")
    time.sleep(5)


def find_usb_serial_ports():
    import glob
    return glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
