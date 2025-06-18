"""
Raspberry Pi to Agilent 33250A Signal Generator Communication via RS-232
===============================================================
This script provides a complete implementation for controlling an Agilent 33250A
signal generator from a Raspberry Pi using a USB-to-RS232 adapter.

More or less ripped straight from the Agilent manual where it is given in C, and hopefully this works in Pyhton
"""
import pyvisa
from pyvisa import constants
from pyvisa.resources import SerialInstrument
from pyvisa.resources.messagebased import MessageBasedResource
import time
import numpy as np
import argparse
import sys
import logging
from typing import cast


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


class Agilent33250A:
    def __init__(self, port="/dev/ttyUSB0", baud_rate=57600, timeout=50000):
        self.port = port
        self.data_bits = 8
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.rm = pyvisa.ResourceManager('@py')
        resource_list = self.rm.list_resources()
        logger.info(f"Available resources: {resource_list}")

        resource = self.rm.open_resource(
            resource_name='ASRL/dev/ttyUSB0::INSTR',
            baud_rate=57600,
            data_bits=8,
            parity=constants.Parity.none,
            stop_bits=constants.StopBits.one,
            flow_control=constants.VI_ASRL_FLOW_NONE,
            write_termination='\n',
            read_termination='\n',
            timeout=50000
        )
        #self.inst = cast(SerialInstrument, resource)
        self.inst = cast(MessageBasedResource, resource)

        #print(dir(self.inst))
        #and it also shows up here! There is the inst.query! So why the fu* does this not work...
        try:
            idn = self.inst.query("*IDN?")
            logger.info(f"Connecting to: {idn}")
            #self.reset()
        
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            raise

    def connect(self):
        try:
            resource = self.rm.open_resource(
                resource_name=f"ASRL{self.port}::INSTR",
                baud_rate=self.baud_rate,
                data_bits=8,
                parity=constants.Parity.none,
                stop_bits=constants.StopBits.one,
                flow_control=constants.VI_ASRL_FLOW_NONE,
                write_termination='\n',
                read_termination='\n',
                timeout=self.timeout
            )
            self.inst = cast(MessageBasedResource, resource)
            idn = self.inst.query("*IDN?")
            logger.info(f"Connected to: {idn}")
            self.reset()
        except Exception as e:
            logger.error(f"Failed to connect to Agilent33250A: {str(e)}")
            raise

    def is_connected(self):
        return self.inst is not None

    def disconnect(self):
        if self.inst:
            self.inst.close()
            self.inst = None
            logger.info("Agilent33250A disconnected")
    
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

    def set_frequency(self, frequency: float):
        """
        Set the output frequency
        Args:
            frequency (float): Frequency in Hz
        """
        self.inst.write(f"FREQUENCY {frequency}")
        logger.info(f"Frequency set to {frequency} Hz")

    def set_burst_count(self, burst_count: int):
        """
        Set number of cycles per burst
        Args:
            burst_count (int): Number of cycles in a burst
        """
        self.inst.write(f"BURST:NCYCLES {burst_count}")
        logger.info(f"Burst count set to {burst_count} cycles")

    def set_duty_cycle(self, duty_cycle: float):
        """
        Set duty cycle (as % of period)
        Args:
            duty_cycle (float): Duty cycle in percent (0–100)
        """
        self.inst.write("FUNCTION PULSE")

        self.inst.write(f"PULSE:DUTY {duty_cycle}")
        logger.info(f"Duty cycle set to {duty_cycle}%")

    
    @staticmethod
    def find_usb_serial_ports():
        import glob
        return glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
