import logging
import time
import RPi.GPIO as GPIO
from nicegui import ui
import paho.mqtt.client as mqtt
import json
from MQTTHandler import MQTTHandler

class Frontend():
    def __init__(self):
        topics = {
            'operation_status': f"/status",
            'UI_command': f"/ui_command",
            'control_response': f"/control_response",
        }
        
        self.mqtt = MQTTHandler(
            client_id="web_ui",
            broker="172.17.0.1",
            port=1883,
            topics=topics
        )
        self.mqtt.connect()

    def create_ui(self):
        with ui.row().classes("w-full justify-start"):
            with ui.card().classes("w-1/2"):
                ui.label('Select UV_LED:').classes('mt-4')
                switch_options = [
                    'Switch 1', 'Switch 2', 'Switch 3', 'Switch 4',
                    'Switch 5', 'Switch 6', 'Switch 7', 'Switch 8',
                    'All Off'
                ]
                self.switch_dropdown = ui.select(
                    label='Available UV-LEDs',
                    options=switch_options,
                    value='Switch 1'  # Default to first switch
                ).classes('w-full')

                ui.button('Activate Channel', on_click=self.execute_switch).classes('mt-2 w-full bg-blue-700')
            """ui.separator()
                ui.label('Channel Notes').classes('mt-4')

                self.notes_area = ui.textarea(
                    label='Detector Notes',
                    value=self.channel_notes,
                    readonly=True
                ).classes('w-full')

                def toggle_notes_edit():
                    if self.edit_mode:
                        self.channel_notes = self.notes_area.value
                        self.notes_area.readonly = True
                        ui.notify("Notes saved!", color='positive')
                    else:
                        self.notes_area.readonly = False
                    self.edit_mode = not self.edit_mode

                ui.button(
                    "Edit Notes" if not self.edit_mode else "Save Notes",
                    on_click=toggle_notes_edit
                ).classes('mt-2 bg-yellow-500')
            """

            with ui.card().classes("w-1/2"):
                ui.label('Signal Configuration').classes('text-h6')

                frequency_input = ui.input(label='Frequency (Hz)', value='1000').props('type=number step=1')
                burst_count_input = ui.input(label='Bursts per block', value='5').props('type=number step=1')
                duty_cycle_input = ui.input(label='Duty Cycle (%)', value='50').props('type=number step=1')
                inter_block_delay_input = ui.input(label='Delay between burst blocks (s)', value='2.0').props('type=number step=0.1')

                def send_signal_settings():
                    try:
                        settings = {
                            "type": "signal_config",
                            "frequency": float(frequency_input.value),
                            "bursts": int(burst_count_input.value),
                            "duty_cycle": float(duty_cycle_input.value),
                            "inter_block_delay": float(inter_block_delay_input.value),
                        }

                        self.mqtt.publish(
                            topic="/ui_command",
                            payload=json.dumps(settings),
                            qos=1
                        )
                        ui.notify("Signal configuration sent!", color='positive')
                    except Exception as e:
                        ui.notify(f"Error: {str(e)}", color='negative')

                ui.button("Send Signal Settings", on_click=send_signal_settings).classes('mt-2 w-full bg-purple-600')

                def send_burst_trigger():
                    try:
                        self.mqtt.publish(
                            topic="/ui_command",
                            payload=json.dumps({
                                "type": "trigger_burst"
                            }),
                            qos=1
                        )
                        ui.notify(f"Triggered burst series", color='positive')
                    except Exception as e:
                        ui.notify(f"Burst trigger failed: {str(e)}", color='negative')

                ui.button(
                    "Trigger Burst Series",
                    on_click=send_burst_trigger
                ).classes('mt-2 w-full bg-orange-600')

                ui.separator()
                with ui.card().classes("w-2/2"):
                    ui.label(
                    '⚙️Pulse Train Sweep:\n\n'
                    'This will run a preset sweep: \n'
                    '- Square wave, 5 MHz\n'
                    '- 50% duty cycle, 100 ns single pulse\n'
                    '- Train max length 4 µs\n'
                    '- Number of pulses: 1 → 20\n'
                    '- 100 ms wait between trains\n'
                    '- Runs automatically on backend'
                    ).classes('text-sm')
                    
                    def send_pulse_train_sweep():
                        try:
                            self.mqtt.publish(
                                topic="/ui_command",
                                payload=json.dumps({
                                    "type": "pulse_train_sweep"
                                }),
                                qos=1
                            )
                            ui.notify(f"Sweeping pulse train started", color='positive')
                        except Exception as e:
                            ui.notify(f"Pulse train sweep failed: {str(e)}", color='negative')

                    ui.button(
                        "Start Pulse Train Sweep",
                        on_click=send_pulse_train_sweep
                    ).classes('mt-2 w-full bg-orange-600')

                ui.separator()
                ui.label('Signal Generator').classes('text-h6')
                #status_label = ui.label('Status: Disconnected').classes('mt-2')
                def connect_generator():
                    try:
                        self.mqtt.publish(
                            topic="/ui_command",
                            payload=json.dumps({
                                "type": "connect_generator"
                            }),
                            qos=1
                        )
                        #status_label.text = 'Status: Connecting...'
                        ui.notify('Connect command sent via MQTT', color='info')
                    except Exception as e:
                        #status_label.text = f'Connection command error: {str(e)}'
                        ui.notify(f'Error sending connect command: {str(e)}', color='negative')

                def disconnect_generator():
                    try:
                        self.mqtt.publish(
                            topic="/ui_command",
                            payload=json.dumps({
                                "type": "disconnect_generator"
                            }),
                            qos=1
                        )
                        #status_label.text = 'Status: Disconnecting...'
                        ui.notify('Disconnect command sent via MQTT', color='info')
                    except Exception as e:
                        ui.notify(f'Error sending disconnect command: {str(e)}', color='negative')


                with ui.row():
                    connect_btn = ui.button('Reset and Reconnect', on_click=connect_generator).classes('mt-2 bg-green-700')
                    disconnect_btn = ui.button('Disconnect', on_click=disconnect_generator).classes('mt-2 bg-red-700')

    def execute_switch(self):
        selected_channel = self.switch_dropdown.value
        if selected_channel is None:
            ui.notify("Please select a channel.", color='warning')
            return
        try:
            if "Switch" in selected_channel:
                channel_number = int(selected_channel.split()[1])
                command_type = "channel_select"
            else:
                channel_number = 0
                command_type = "all_off"

            payload = {
                "type": command_type,
                "channel": channel_number
            }

            self.mqtt.publish(
                topic="/ui_command",
                payload=json.dumps(payload),
                qos=1
            )
            ui.notify(f'Channel {selected_channel} selected', color='positive')
        except Exception as e:
            error_msg = f"MQTT error: {str(e)}"
            ui.notify(error_msg, color='negative')