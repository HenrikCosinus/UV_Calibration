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
        with ui.card().classes("w-96"):
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
        
        with ui.card().classes('m-4'):
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

            ui.separator()
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


        with ui.card().classes('m-4'):
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