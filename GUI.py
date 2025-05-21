import logging
from nicegui import ui, app
import glob
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agilent_demo.log"),
    ]
)
logger = logging.getLogger(__name__)

try:
    from Agilent_Controller_RS232 import (
        Agilent33250A, 
        find_usb_serial_ports,
        demo_basic_waveforms,
        demo_am_modulation,
        demo_fm_modulation,
        demo_frequency_sweep,
        demo_burst_mode,
        demo_arbitrary_waveform
    )
    logger.info("Successfully imported Agilent controller modules")
    CONTROLLER_AVAILABLE = True
except ImportError:
    logger.warning("Agilent controller modules not found. UI will be displayed in demo mode only.")
    CONTROLLER_AVAILABLE = False

def create_ui():
    # Dark theme
    ui.dark_mode().enable()
    with ui.header().classes('bg-blue-900'):
        ui.label('Agilent 33250A Demo Runner').classes('text-h4 text-white')
    with ui.row().classes('w-full justify-center items-start'):
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
                ui.notify('Ports refreshed', color='info')
                
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
                        demo_warning.visible = False
                        ui.notify('Connected to generator!', color='positive')
                        logger.info(f"Connected to generator at {port}")
                    else:
                        status_label.text = 'Status: Already connected'
                except Exception as e:
                    status_label.text = f'Status: Connection error - {str(e)}'
                    ui.notify(f'Connection error: {str(e)}', color='negative')
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
                        demo_warning.visible = True
                        ui.notify('Disconnected from generator', color='info')
                        logger.info("Disconnected from generator")
                    else:
                        status_label.text = 'Status: Already disconnected'
                except Exception as e:
                    status_label.text = f'Status: Disconnection error - {str(e)}'
                    ui.notify(f'Disconnection error: {str(e)}', color='negative')
                    logger.error(f"Disconnection error: {str(e)}")
            
            with ui.row():
                connect_btn = ui.button('Connect', on_click=connect_generator).classes('mt-2 bg-green-700')
                disconnect_btn = ui.button('Disconnect', on_click=disconnect_generator).classes('mt-2 bg-red-700')
                disconnect_btn.visible = False
        
        # Demo functions panel
        demo_card = ui.card().classes('m-4')
        with demo_card:
            ui.label('Demo Functions').classes('text-h6')
            
            # Demo functions 
            with ui.column().classes('w-full gap-2'):
                ui.button('Basic Waveforms Demo', on_click=lambda: run_demo(demo_basic_waveforms), icon='waves').classes('w-full bg-blue-700')
                ui.button('AM Modulation Demo', on_click=lambda: run_demo(demo_am_modulation), icon='signal_cellular_alt').classes('w-full bg-indigo-700')
                ui.button('FM Modulation Demo', on_click=lambda: run_demo(demo_fm_modulation), icon='tune').classes('w-full bg-purple-700')
                ui.button('Frequency Sweep Demo', on_click=lambda: run_demo(demo_frequency_sweep), icon='low_priority').classes('w-full bg-teal-700')
                ui.button('Burst Mode Demo', on_click=lambda: run_demo(demo_burst_mode), icon='repeat').classes('w-full bg-green-700')
                ui.button('Arbitrary Waveform Demo', on_click=lambda: run_demo(demo_arbitrary_waveform), icon='show_chart').classes('w-full bg-amber-700')
                
            # Status indicator
            demo_status = ui.label('Ready to run demos').classes('mt-4 text-center')
            
            def run_demo(demo_function):
                if generator is None:
                    ui.notify('Please connect to a generator first', color='negative')
                    return
                
                try:
                    demo_status.text = f'Running: {demo_function.__name__}'
                    ui.notify(f'Running {demo_function.__name__}', color='info')
                    logger.info(f"Starting {demo_function.__name__}")
                    
                    # Run the demo in a separate thread to avoid blocking UI
                    def run_async():
                        try:
                            result = demo_function(generator)
                            ui.notify(f'Completed {demo_function.__name__}', color='positive')
                            demo_status.text = f'Completed: {demo_function.__name__}'
                        except Exception as e:
                            error_msg = f"Error in {demo_function.__name__}: {str(e)}"
                            ui.notify(error_msg, color='negative')
                            demo_status.text = error_msg
                            logger.error(error_msg)
                    
                    # Schedule the demo to run asynchronously
                    app.schedule(run_async)
                    
                except Exception as e:
                    error_msg = f"Failed to start {demo_function.__name__}: {str(e)}"
                    ui.notify(error_msg, color='negative')
                    demo_status.text = error_msg
                    logger.error(error_msg)
            
            def stop_output():
                if generator is None:
                    ui.notify('No active connection', color='warning')
                    return
                
                try:
                    # Reset and disable output
                    generator.configure_output(state=False)
                    generator.reset()
                    ui.notify('Output stopped', color='positive')
                    demo_status.text = 'Output stopped'
                    logger.info("Output stopped")
                except Exception as e:
                    ui.notify(f'Error stopping output: {str(e)}', color='negative')
                    logger.error(f"Error stopping output: {str(e)}")
        
        # Always show the demo card, but add a warning when not connected
        demo_warning = ui.label('⚠️ NOT CONNECTED - Connect to a device before running demos').classes('text-red-500 font-bold w-full text-center mt-1 mb-3')
        
        def update_warning_visibility():
            demo_warning.visible = generator is None
            
        # Update warning visibility when connection status changes
        app.on_connect(lambda: update_warning_visibility())

    # Display a footer with additional information
    with ui.footer().classes('bg-blue-900 text-white'):
        ui.label('Note: Demo functions will run through a sequence of preset waveforms to demonstrate the generator\'s capabilities')


create_ui()
ui.run(title="Agilent 33250A Demo Runner", port=8084, reload=False)