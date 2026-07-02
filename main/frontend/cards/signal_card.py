import logging
import json
from nicegui import ui

logger = logging.getLogger(__name__)


def build_signal_card(frontend):
    with ui.column().classes("flex-1 gap-4"):
        with ui.card().classes("w-full"):
            ui.label('Signal Configuration').classes('text-h6')
            frequency_input = ui.input(label='Frequency (Hz)', value='1000').props('type=number step=1 suffix=Hz').classes('w-full')
            burst_count_input = ui.input(label='Bursts per block', value='5').props('type=number step=1 suffix=bursts').classes('w-full')
            duty_cycle_input = ui.input(label='Duty Cycle (%)', value='50').props('type=number step=1 suffix=%').classes('w-full')
            inter_block_delay_input = ui.input(label='Delay between burst blocks (s)', value='2.0').props('type=number step=0.1 suffix=s').classes('w-full')

            def send_signal_settings():
                try:
                    settings = {
                        "type": "signal_config",
                        "frequency": float(frequency_input.value),
                        "bursts": int(burst_count_input.value),
                        "duty_cycle": float(duty_cycle_input.value),
                        "inter_block_delay": float(inter_block_delay_input.value),
                    }
                    logger.info(f"→ /ui_command: {settings}")
                    frontend.mqtt.publish(topic="/ui_command", payload=json.dumps(settings), qos=1)
                    ui.notify("Signal configuration sent!", color='positive')
                except Exception as e:
                    logger.error(f"send_signal_settings error: {e}")
                    ui.notify(f"Error: {str(e)}", color='negative')

            def send_burst_trigger():
                try:
                    payload = {"type": "trigger_burst"}
                    logger.info(f"→ /ui_command: {payload}")
                    frontend.mqtt.publish(topic="/ui_command", payload=json.dumps(payload), qos=1)
                    ui.notify("Triggered burst series", color='positive')
                except Exception as e:
                    logger.error(f"send_burst_trigger error: {e}")
                    ui.notify(f"Burst trigger failed: {str(e)}", color='negative')

            def send_pulse_train_sweep():
                try:
                    payload = {"type": "pulse_train_sweep"}
                    logger.info(f"→ /ui_command: {payload}")
                    frontend.mqtt.publish(topic="/ui_command", payload=json.dumps(payload), qos=1)
                    ui.notify("Sweeping pulse train started", color='positive')
                except Exception as e:
                    logger.error(f"send_pulse_train_sweep error: {e}")
                    ui.notify(f"Pulse train sweep failed: {str(e)}", color='negative')

            ui.button("Send Signal Settings", on_click=send_signal_settings).classes('mt-2 w-full bg-purple-600')
            ui.button("Trigger Burst Series", on_click=send_burst_trigger).classes('mt-2 w-full bg-orange-600')
            ui.separator()
            ui.label('Pulse Train Sweep').classes('text-subtitle1')
            ui.label(
                'Square wave 5 MHz, 50% duty cycle, 100 ns single pulse, '
                'train max 4 µs, pulses 1→20, 100 ms between trains.'
            ).classes('text-caption text-grey-6')
            ui.button("Start Pulse Train Sweep", on_click=send_pulse_train_sweep).classes('mt-2 w-full bg-orange-600')

        with ui.card().classes("w-full"):
            ui.label('Signal Generator').classes('text-h6')

            def connect_generator():
                try:
                    payload = {"type": "connect_generator"}
                    logger.info(f"→ /ui_command: {payload}")
                    frontend.mqtt.publish(topic="/ui_command", payload=json.dumps(payload), qos=1)
                    ui.notify('Connect command sent', color='info')
                except Exception as e:
                    logger.error(f"connect_generator error: {e}")
                    ui.notify(f'Error sending connect command: {str(e)}', color='negative')

            def disconnect_generator():
                try:
                    payload = {"type": "disconnect_generator"}
                    logger.info(f"→ /ui_command: {payload}")
                    frontend.mqtt.publish(topic="/ui_command", payload=json.dumps(payload), qos=1)
                    ui.notify('Disconnect command sent', color='info')
                except Exception as e:
                    logger.error(f"disconnect_generator error: {e}")
                    ui.notify(f'Error sending disconnect command: {str(e)}', color='negative')

            with ui.row().classes('gap-2 mt-2'):
                ui.button('Reset and Reconnect', on_click=connect_generator).classes('bg-green-700')
                ui.button('Disconnect', on_click=disconnect_generator).classes('bg-red-700')
