import logging
import json
from nicegui import ui

logger = logging.getLogger(__name__)


def build_potentiometer_card(frontend):
    with ui.card().classes("w-full mt-4"):
        ui.label('Potentiometer Sweep').classes('text-h6')
        with ui.row().classes('gap-4 items-end'):
            start_v = ui.input(label='Start voltage (V)', value='0').props('type=number step=0.1 suffix=V')
            end_v = ui.input(label='End voltage (V)', value='10').props('type=number step=0.1 suffix=V')
            steps = ui.input(label='Steps (max 255)', value='255').props('type=number step=1 suffix=steps')
            sweep_duration = ui.input(label='Duration per step (s)', value='1').props('type=number step=0.1 suffix=s')

            def voltage_sweep():
                try:
                    settings = {
                        "type": "potentiometer_voltage_sweep",
                        "voltage_start_v": float(start_v.value),
                        "voltage_end_v": float(end_v.value),
                        "voltage_sweep_steps": float(steps.value),
                        "voltage_sweep_duration": float(sweep_duration.value)
                    }
                    logger.info(f"→ /ui_command: {settings}")
                    frontend.mqtt.publish(topic="/ui_command", payload=json.dumps(settings), qos=1)
                    ui.notify('Voltage sweep command sent', color='positive')
                except Exception as e:
                    logger.error(f"voltage_sweep error: {e}")
                    ui.notify(f'Error: {str(e)}', color='negative')

            ui.button("Start Sweep", on_click=voltage_sweep).classes('bg-purple-600')
        ui.label('Duration is the wait time per step, not total sweep time.').classes('text-caption text-grey-6 mt-1')
