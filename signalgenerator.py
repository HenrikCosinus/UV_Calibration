import time
import sys
import pyvisa
from typing import List

"This is 1:1 copy of the example code given in the manual of the Agilent signalgenerator changed from original c++ to python...hope this works"

def check_errors(io_obj: pyvisa.resources.MessageBasedResource):
    """Check for and display any errors in the instrument's error queue."""
    while True:
        error_response = io_obj.query(":SYST:ERR?")
        error_num, error_msg = error_response.strip().split(',', 1)
        error_num = int(error_num)
        
        if error_num == 0:
            break
        else:
            print(f"\nERROR {error_num}: {error_msg}")

def pause():
    input("Press Enter to continue...")
    print()

def fill_array() -> List[float]:
    return [
        -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0, -1.0, 1.0,
        1.0, 1.0, -1.0, -1.0, -1.0, -1.0, 1.0, 1.0, 1.0, 1.0
    ]

def main():
    rm = pyvisa.ResourceManager()
    
    try:
        # RS-232 Configuration (uncomment and modify as needed)
        # io_obj = rm.open_resource("ASRL1::INSTR", baud_rate=57600, data_bits=8)
        # io_obj.write_termination = '\n'
        # io_obj.read_termination = '\n'
        
        # GPIB Configuration (example)
        io_obj = rm.open_resource("GPIB0::10::INSTR")
        
        # Reset instrument to default state
        io_obj.write("*RST")
        io_obj.write("*CLS")
        
        # AM Modulation
        print("AM Modulation")
        io_obj.write("OUTPut:LOAD INFinity")
        io_obj.write("APPLy:SINusoid 1e6,1,0")
        io_obj.write("AM:INTernal:FUNCtion RAMP")
        io_obj.write("AM:INTernal:FREQuency 10e3")
        io_obj.write("AM:DEPTh 80")
        io_obj.write("AM:STATe ON")
        check_errors(io_obj)
        pause()
        io_obj.write("AM:STATe OFF")
        
        # FM Modulation
        print("FM Modulation")
        io_obj.write("OUTP:LOAD 50")
        io_obj.write("APPL:SIN 20e3,1,0")
        io_obj.write("FM:DEV 20e3")
        io_obj.write("FM:INT:FREQ 1000")
        io_obj.write("FM:STAT ON")
        check_errors(io_obj)
        pause()
        io_obj.write("FM:STAT OFF")
        
        # Linear Sweep
        print("Linear Sweep")
        io_obj.write("SWEEP:TIME 1")
        io_obj.write("FREQ:START 100")
        io_obj.write("FREQ:STOP 20000")
        io_obj.write("SWEEP:STAT ON")
        check_errors(io_obj)
        pause()
        io_obj.write("SWEEP:STAT OFF")
        
        # Pulse with variable Edge Times
        print("Pulse Waveform with variable Edge Times")
        io_obj.write("OUTPUT:STATE OFF")
        io_obj.write("VOLT:LOW 0;:VOLT:HIGH 0.75")
        io_obj.write("PULSE:PERIOD 1e-3")
        io_obj.write("PULSE:WIDTH 100e-6")
        io_obj.write("PULSE:TRAN 10e-6")
        io_obj.write("FUNC PULSE")
        io_obj.write("OUTPUT:STATE ON")
        
        for i in range(10):
            edge_time = 10e-6 + 1e-6 * i
            io_obj.write(f"PULS:TRAN {edge_time}")
            time.sleep(0.3)
        
        check_errors(io_obj)
        pause()
        
        # Triggered Burst
        print("Triggered Burst")
        io_obj.write("OUTPUT:STATE OFF")
        io_obj.write("OUTPUT:SYNC OFF")
        io_obj.write("FUNC SQUARE")
        io_obj.write("FREQUENCY 20e3")
        io_obj.write("VOLT 1;:VOLT:OFFSET 0")
        io_obj.write("FUNC:SQUARE:DCYCLE 20")
        io_obj.write("TRIG:SOUR BUS")
        io_obj.write("BURST:NCYCLES 3")
        io_obj.write("BURST:STAT ON")
        io_obj.write("OUTPUT:STATE ON")
        io_obj.write("OUTPUT:SYNC ON")
        check_errors(io_obj)
        
        for _ in range(20):
            io_obj.write("*TRG")
            time.sleep(0.1)
        
        pause()
        
        # Download 20-point Arbitrary waveform (ASCII)
        print("Download a 20 point Arbitrary waveform using ASCII")
        real_array = fill_array()
        array_str = "DATA VOLATILE, " + ",".join(map(str, real_array))
        io_obj.write(array_str)
        io_obj.write("FUNC:USER VOLATILE")
        io_obj.write("APPLY:USER 10e3,1,0")
        check_errors(io_obj)
        pause()
        
        # Download 6-point Arbitrary waveform (Binary)
        print("Download a 6 point Arbitrary waveform using Binary")
        binary_data = [2047, -2047, 2047, 2047, -2047, -2047]
        binary_header = "DATA:DAC VOLATILE, #26"  # Header for binary transfer
        io_obj.write_binary_values(binary_header, binary_data, datatype='h')
        time.sleep(0.1)
        io_obj.write("APPLY:USER 5000,1,0")
        check_errors(io_obj)
        pause()
        
        # Using Status Registers
        print("Using the Status Registers")
        io_obj.write("APPLY:SIN 10e3,1,0")
        io_obj.write("TRIG:SOUR BUS")
        io_obj.write("BURST:NCYCLES 50000")
        io_obj.write("BURST:STAT ON")
        io_obj.write("*ESE 1")
        io_obj.write("*SRE 32")
        check_errors(io_obj)
        io_obj.write("*TRG;*OPC")
        
        while True:
            stb = int(io_obj.query("*STB?"))
            if stb & 0x40:  # Test for Master Summary Bit
                break
        
        print("End of Program")
        
    except Exception as e:
        print(f"Exception occurred during processing!\nDescription: {str(e)}", file=sys.stderr)
    finally:
        if 'io_obj' in locals():
            io_obj.close()
        rm.close()

if __name__ == "__main__":
    main()