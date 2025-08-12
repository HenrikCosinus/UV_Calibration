import logging
import time
import RPi.GPIO as GPIO
from nicegui import ui
import paho.mqtt.client as mqtt
import json
from pathlib import Path
from MQTTHandler import MQTTHandler

class Frontend():
    def __init__(self):
        self.notes_file = Path('channel_notes.json')
        self.channel_notes_store = {} 
        self.load_notes()
        topics = {
            'temperature': f"/temperature",
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

                with ui.row().classes('items-start gap-4'):
                    self.switch_dropdown = ui.select(
                        label='Available UV-LEDs',
                        options=[
                            'Switch 1', 'Switch 2', 'Switch 3', 'Switch 4',
                            'Switch 5', 'Switch 6', 'Switch 7', 'Switch 8',
                            'All Off'
                        ],
                        value='Switch 1'
                    ).classes('w-full')

                    initial_note = self.channel_notes_store.get('Switch 1', '')
                    self.channel_notes = ui.textarea(
                        label='Channel Notes',
                        placeholder='Add notes for the channels...',
                        value=initial_note  # <<< load on startup
                    ).classes('w-full')
                
                def save_notes_for_channel():
                    channel = self.switch_dropdown.value
                    self.channel_notes_store[channel] = self.channel_notes.value
                    self.save_notes()
                    ui.notify(f"Notes for {channel} saved.", color='positive')

                def update_notes_field(e):
                    channel = self.switch_dropdown.value
                    note = self.channel_notes_store.get(channel, '')
                    self.channel_notes.value = note

                ui.button('Save Notes', on_click=save_notes_for_channel).classes('mt-2 bg-green-600')
                ui.button('Activate Channel', on_click=self.execute_switch).classes('mt-2 w-full bg-blue-700')

                self.switch_dropdown.on('update:model-value', update_notes_field)
                #self.switch_dropdown.on('change', update_notes_field)


            with ui.card().classes("w-1/3"):
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
                with ui.card().classes("w-1/3"):
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
                
            ui.separator()
            ui.label('Potentiometer control').classes('text-h6')
            with ui.card().classes("w-1/3"):
                ui.label('Sweep Configuration').classes('text-h6')
                start_v = ui.input(label='start_v', value='0').props('type=number step=1')
                end_v = ui.input(label='end_v', value='10').props('type=number step=1')
                steps = ui.input(label='steps (max 256)', value='256').props('type=number step=1')
                sweep_duration = ui.input(label='Sweep duration', value='1').props('type=number step=0.1')

                def voltage_sweep():
                    try:
                        settings = {
                            "type": "potentiometer_voltage_sweep",
                            "voltage_start_v" : float(start_v.value),
                            "voltage_end_v" : float(end_v.value),
                            "voltage_sweep_steps" : float(steps.value),
                            "voltage_sweep_duration" : float(sweep_duration.value)
                        }

                        self.mqtt.publish(
                            topic="/ui_command",
                            payload=json.dumps(settings),
                            qos=1
                        )
                        ui.notify('Voltage sweep command sent', color='positive')
                    except Exception as e:
                        #status_label.text = f'Connection command error: {str(e)}'
                        ui.notify(f'Error sending connect command: {str(e)}', color='negative')

                ui.button("Do voltage sweep", on_click=voltage_sweep).classes('mt-2 w-full bg-purple-600')


            ui.separator()
            with ui.card().classes("w-1/3"):
                ui.label('Live Temperature Readout').classes('text-h6')

                temp_display = ui.column().classes("gap-1")
                self.temp_readings = []

                def add_temperature_reading(temp_value):
                    # Keep only the last 20 readings
                    self.temp_readings.append(temp_value)
                    if len(self.temp_readings) > 20:
                        self.temp_readings.pop(0)
                    temp_display.clear()

                def on_temp_message(client, userdata, message):
                    try:
                        payload = json.loads(message.payload.decode())
                        if "temperature_c" in payload:
                            add_temperature_reading(payload["temperature_c"])
                    except Exception as e:
                        ui.notify(f"Temperature parse error: {e}", color="negative")


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

    def load_notes(self):
        if self.notes_file.exists():
            try:
                with open(self.notes_file, 'r') as f:
                    self.channel_notes_store = json.load(f)
            except Exception as e:
                print(f"Failed to load notes: {e}")
        else:
            self.channel_notes_store = {}

    def save_notes(self):
        try:
            with open(self.notes_file, 'w') as f:
                json.dump(self.channel_notes_store, f, indent=2)
        except Exception as e:
            print(f"Failed to save notes: {e}")
