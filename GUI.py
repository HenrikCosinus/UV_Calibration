import sys
import logging
from nicegui import ui, app
import glob
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pulse_generator.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

try:
    from Agilent_Controller_RS232 import Agilent33250A, find_usb_serial_ports
    logger.info("Successfully imported Agilent controller modules")
except ImportError:
    logger.error("Failed to import Agilent controller modules.")

# Global variable for generator
generator = None

# Define load options
LOAD_OPTIONS = ["50", "INF", "HIGHZ"]

class PulseSequence:
    def __init__(self):
        self.pulses: List[Dict] = []
        self.current_id = 0
        
    def add_pulse(self, width: float, delay: float, amplitude: float = 1.0):
        """Add a pulse to the sequence"""
        self.pulses.append({
            'id': self.current_id,
            'width': width,  # in µs
            'delay': delay,  # in µs
            'amplitude': amplitude  # in volts
        })
        self.current_id += 1
        
    def remove_pulse(self, pulse_id: int):
        """Remove a pulse from the sequence"""
        self.pulses = [p for p in self.pulses if p['id'] != pulse_id]
        
    def clear(self):
        """Clear all pulses"""
        self.pulses = []
        self.current_id = 0
        
    def get_total_duration(self) -> float:
        """Get total sequence duration in µs"""
        return sum(p['width'] + p['delay'] for p in self.pulses)
        
    def generate_waveform(self, sample_rate: int = 100) -> np.ndarray:
        """
        Generate a waveform array for visualization
        sample_rate: samples per µs
        """
        if not self.pulses:
            return np.array([])
            
        total_samples = int(self.get_total_duration() * sample_rate)
        waveform = np.zeros(total_samples)
        
        current_time = 0
        for pulse in self.pulses:
            start_sample = int(current_time * sample_rate)
            width_samples = int(pulse['width'] * sample_rate)
            end_sample = start_sample + width_samples
            
            if end_sample > len(waveform):
                waveform = np.pad(waveform, (0, end_sample - len(waveform)), 'constant')
                
            waveform[start_sample:end_sample] = pulse['amplitude']
            current_time += pulse['width'] + pulse['delay']
            
        return waveform

def create_ui():
    # Initialize pulse sequence
    sequence = PulseSequence()
    
    # Dark theme
    ui.dark_mode().enable()
    
    with ui.header().classes('bg-blue-900'):
        ui.label('Agilent 33250A Pulse Generator').classes('text-h4 text-white')
        
    with ui.row().classes('w-full justify-center items-start'):
        # Connection panel
        with ui.card().classes('m-4'):
            ui.label('Connection').classes('text-h6')
            
            # Available ports
            ports = find_usb_serial_ports()
            port_dropdown = ui.select(
                label='Serial Port',
                options=ports if ports else ['No ports found'],
                value=ports[0] if ports else None
            ).classes('w-full')
            
            def refresh_ports():
                new_ports = find_usb_serial_ports()
                port_dropdown.options = new_ports if new_ports else ['No ports found']
                port_dropdown.value = new_ports[0] if new_ports else None
                
            ui.button('Refresh Ports', on_click=refresh_ports).classes('mt-2')
            
            # Connection status and buttons
            status_label = ui.label('Status: Disconnected').classes('mt-2')
            
            def connect_generator():
                global generator
                try:
                    if generator is None:
                        port = port_dropdown.value
                        generator = Agilent33250A(port=port)
                        generator.reset()
                        status_label.text = f'Status: Connected to {port}'
                        connect_btn.visible = False
                        disconnect_btn.visible = True
                        pulse_card.visible = True
                        logger.info(f"Connected to generator at {port}")
                    else:
                        status_label.text = 'Status: Already connected'
                except Exception as e:
                    status_label.text = f'Status: Connection error - {str(e)}'
                    logger.error(f"Connection error: {str(e)}")
            
            def disconnect_generator():
                global generator
                try:
                    if generator is not None:
                        generator.close()
                        generator = None
                        status_label.text = 'Status: Disconnected'
                        connect_btn.visible = True
                        disconnect_btn.visible = False
                        pulse_card.visible = False
                        logger.info("Disconnected from generator")
                    else:
                        status_label.text = 'Status: Already disconnected'
                except Exception as e:
                    status_label.text = f'Status: Disconnection error - {str(e)}'
                    logger.error(f"Disconnection error: {str(e)}")
            
            with ui.row():
                connect_btn = ui.button('Connect', on_click=connect_generator).classes('mt-2 bg-green-700')
                disconnect_btn = ui.button('Disconnect', on_click=disconnect_generator).classes('mt-2 bg-red-700')
                disconnect_btn.visible = False
        
        # Pulse generator panel
        pulse_card = ui.card().classes('m-4')
        with pulse_card:
            ui.label('Pulse Sequence Configuration').classes('text-h6')
            
            # Output configuration
            with ui.row().classes('w-full items-center'):
                load_select = ui.select(label='Load', options=LOAD_OPTIONS, value='INF').classes('w-32')
                output_toggle = ui.switch('Output Enabled').classes('ml-4')
                ui.button('Apply Output', on_click=lambda: apply_output_settings()).classes('ml-4 bg-blue-700')
            
            # Pulse sequence editor
            with ui.card().classes('w-full mt-4'):
                ui.label('Pulse Sequence').classes('text-h6')
                
                # Pulse parameters
                with ui.row().classes('w-full items-end'):
                    pulse_width = ui.number(label='Width (µs)', value=100, min=0.1, max=1000, step=1).classes('w-32')
                    pulse_delay = ui.number(label='Delay (µs)', value=200, min=0, max=5000, step=1).classes('w-32 ml-2')
                    pulse_amplitude = ui.number(label='Amplitude (V)', value=1.0, min=0.1, max=10.0, step=0.1).classes('w-32 ml-2')
                    ui.button('Add Pulse', on_click=lambda: add_pulse_to_sequence(), icon='add').classes('ml-2 bg-green-700')
                
                # Sequence table - using a grid instead of table for better control
                sequence_grid = ui.grid(columns=5).classes('w-full mt-2')
                sequence_grid.add_header_cell('ID')
                sequence_grid.add_header_cell('Width (µs)')
                sequence_grid.add_header_cell('Delay (µs)')
                sequence_grid.add_header_cell('Amplitude (V)')
                sequence_grid.add_header_cell('Actions')
                
                def update_sequence_grid():
                    sequence_grid.clear()
                    sequence_grid.add_header_cell('ID')
                    sequence_grid.add_header_cell('Width (µs)')
                    sequence_grid.add_header_cell('Delay (µs)')
                    sequence_grid.add_header_cell('Amplitude (V)')
                    sequence_grid.add_header_cell('Actions')
                    
                    for pulse in sequence.pulses:
                        sequence_grid.add_cell(str(pulse['id']))
                        sequence_grid.add_cell(str(pulse['width']))
                        sequence_grid.add_cell(str(pulse['delay']))
                        sequence_grid.add_cell(str(pulse['amplitude']))
                        with sequence_grid.add_cell():
                            ui.button(icon='delete', on_click=lambda p=pulse['id']: remove_pulse_from_sequence(p)).props('flat dense')
                    
                    update_waveform_plot()
                
                def add_pulse_to_sequence():
                    sequence.add_pulse(
                        width=pulse_width.value,
                        delay=pulse_delay.value,
                        amplitude=pulse_amplitude.value
                    )
                    update_sequence_grid()
                
                def remove_pulse_from_sequence(pulse_id: int):
                    sequence.remove_pulse(pulse_id)
                    update_sequence_grid()
                
                # Clear sequence button
                ui.button('Clear Sequence', on_click=lambda: [sequence.clear(), update_sequence_grid()], icon='clear').classes('mt-2 bg-red-700')
            
            # Waveform preview
            with ui.card().classes('w-full mt-4'):
                ui.label('Waveform Preview').classes('text-h6')
                plot = ui.plot().classes('w-full h-64')
                
                def update_waveform_plot():
                    if not sequence.pulses:
                        plot.content = ''
                        return
                    
                    waveform = sequence.generate_waveform()
                    x = np.linspace(0, sequence.get_total_duration(), len(waveform))
                    
                    plot.content = f"""
                    {{
                        const data = {{
                            x: {x.tolist()},
                            y: {waveform.tolist()},
                            type: 'scatter',
                            mode: 'lines',
                            line: {{color: 'blue', width: 2}},
                            name: 'Pulse Sequence'
                        }};
                        
                        const layout = {{
                            title: 'Pulse Sequence (Total: {sequence.get_total_duration():.1f}µs)',
                            xaxis: {{title: 'Time (µs)'}},
                            yaxis: {{title: 'Amplitude (V)', range: [0, {max(1.0, max(p['amplitude'] for p in sequence.pulses) + 0.5)}]}},
                            margin: {{l: 50, r: 20, t: 40, b: 50}},
                            showlegend: false
                        }};
                        
                        Plotly.newPlot('{plot.id}', [data], layout);
                    }}
                    """
            
            # Trigger controls
            with ui.row().classes('w-full justify-center mt-4'):
                ui.button('Send Single Trigger', on_click=lambda: send_trigger(), icon='play_arrow').classes('bg-green-700')
                ui.button('Send Burst (5x)', on_click=lambda: send_burst(5), icon='repeat').classes('ml-4 bg-blue-700')
            
            # Apply settings function
            def apply_output_settings():
                if generator is None:
                    ui.notify('Please connect to a generator first', color='negative')
                    return
                
                try:
                    generator.configure_output(load=load_select.value, state=output_toggle.value)
                    ui.notify('Output settings applied', color='positive')
                    logger.info(f"Applied output settings: Load={load_select.value}, Enabled={output_toggle.value}")
                except Exception as e:
                    ui.notify(f'Error: {str(e)}', color='negative')
                    logger.error(f"Error applying output settings: {str(e)}")
            
            # Send trigger function
            def send_trigger():
                if generator is None:
                    ui.notify('Please connect to a generator first', color='negative')
                    return
                
                try:
                    generator.send_trigger()
                    ui.notify('Trigger sent', color='positive')
                    logger.info("Sent single trigger")
                except Exception as e:
                    ui.notify(f'Error: {str(e)}', color='negative')
                    logger.error(f"Error sending trigger: {str(e)}")
            
            # Send burst function
            def send_burst(count: int):
                if generator is None:
                    ui.notify('Please connect to a generator first', color='negative')
                    return
                
                try:
                    for i in range(count):
                        generator.send_trigger()
                        time.sleep(0.1)  # Small delay between triggers
                    ui.notify(f'Sent {count} triggers', color='positive')
                    logger.info(f"Sent burst of {count} triggers")
                except Exception as e:
                    ui.notify(f'Error: {str(e)}', color='negative')
                    logger.error(f"Error sending burst: {str(e)}")
        
        # Initially hide the pulse card until connected
        pulse_card.visible = False

create_ui()
ui.run(title="Agilent 33250A Pulse Generator", port=8082, reload=False)