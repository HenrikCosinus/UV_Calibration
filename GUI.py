import logging
from nicegui import ui, app
import glob
import time
import RPi.GPIO as GPIO
from GPIOController import GPIOController

gpio_controller = None

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

    with ui.card().classes('m-4'):
        ui.label('GPIO Switch Control').classes('text-h6')
        
        # GPIO Status and buttons
        gpio_status_label = ui.label('Status: Not Initialized').classes('mt-2')
        
        def initialize_gpio():
            global gpio_controller
            try:
                if gpio_controller is None:
                    gpio_controller = GPIOController()
                    gpio_status_label.text = 'Status: Initialized'
                    gpio_init_btn.visible = False
                    gpio_cleanup_btn.visible = True
                    ui.notify('GPIO Controller initialized!', color='positive')
                    logger.info("GPIO Controller initialized")
                else:
                    gpio_status_label.text = 'Status: Already initialized'
            except Exception as e:
                gpio_status_label.text = f'Status: Initialization error - {str(e)}'
                ui.notify(f'Initialization error: {str(e)}', color='negative')
                logger.error(f"GPIO initialization error: {str(e)}")
        
        def cleanup_gpio():
            global gpio_controller
            try:
                if gpio_controller is not None:
                    gpio_controller.cleanup()
                    gpio_controller = None
                    gpio_status_label.text = 'Status: Cleaned up'
                    gpio_init_btn.visible = True
                    gpio_cleanup_btn.visible = False
                    ui.notify('GPIO Controller cleaned up', color='info')
                    logger.info("GPIO Controller cleaned up")
                else:
                    gpio_status_label.text = 'Status: Already cleaned up'
            except Exception as e:
                gpio_status_label.text = f'Status: Cleanup error - {str(e)}'
                ui.notify(f'Cleanup error: {str(e)}', color='negative')
                logger.error(f"GPIO cleanup error: {str(e)}")
        
        with ui.row():
            gpio_init_btn = ui.button('Initialize', on_click=initialize_gpio).classes('mt-2 bg-green-700')
            gpio_cleanup_btn = ui.button('Cleanup', on_click=cleanup_gpio).classes('mt-2 bg-red-700')
            gpio_cleanup_btn.visible = False
        
        # Switch selection dropdown
        ui.label('Select Switch:').classes('mt-4')
        switch_options = [
            'Switch 1', 'Switch 2', 'Switch 3', 'Switch 4',
            'Switch 5', 'Switch 6', 'Switch 7', 'Switch 8',
            'All Off'
        ]
        switch_dropdown = ui.select(
            label='Available Switches',
            options=switch_options,
            value=switch_options[-1]  # Default to "All Off"
        ).classes('w-full')
        
        def execute_switch():
            if gpio_controller is None:
                ui.notify('Please initialize GPIO controller first', color='negative')
                return
            
            selected_switch = switch_dropdown.value
            try:
                # Call the appropriate method on the controller
                if selected_switch == 'Switch 1':
                    gpio_controller.Switch_1()
                elif selected_switch == 'Switch 2':
                    gpio_controller.Switch_2()
                elif selected_switch == 'Switch 3':
                    gpio_controller.Switch_3()
                elif selected_switch == 'Switch 4':
                    gpio_controller.Switch_4()
                elif selected_switch == 'Switch 5':
                    gpio_controller.Switch_5()
                elif selected_switch == 'Switch 6':
                    gpio_controller.Switch_6()
                elif selected_switch == 'Switch 7':
                    gpio_controller.Switch_7()
                elif selected_switch == 'Switch 8':
                    gpio_controller.Switch_8()
                elif selected_switch == 'All Off':
                    gpio_controller.set_all_pins(False)
                
                ui.notify(f'Executed {selected_switch}', color='positive')
                logger.info(f"Executed GPIO {selected_switch}")
            except Exception as e:
                error_msg = f"Error executing {selected_switch}: {str(e)}"
                ui.notify(error_msg, color='negative')
                logger.error(error_msg)
        
        # Execute Switch button
        ui.button('Execute Switch', on_click=execute_switch).classes('mt-2 w-full bg-blue-700')
        
        # Quick access buttons
        ui.label('Quick Access:').classes('mt-4')
        with ui.grid(columns=3).classes('gap-1 mt-2'):
            for i in range(1, 9):
                ui.button(f'S{i}', on_click=lambda i=i: (
                    switch_dropdown.set_value(f'Switch {i}'),
                    execute_switch()
                )).classes('bg-indigo-700')
            ui.button('OFF', on_click=lambda: (
                switch_dropdown.set_value('All Off'),
                execute_switch()
            )).classes('bg-red-700')

    # Display a footer with additional information
    with ui.footer().classes('bg-blue-900 text-white'):
        ui.label('Note: Demo functions will run through a sequence of preset waveforms to demonstrate the generator\'s capabilities')


create_ui()
#ui.run(title="Agilent 33250A Demo Runner", port=8085, reload=True)
ui.run(title="UI_Test", port=1884, reload = True, host="134.107.69.228")