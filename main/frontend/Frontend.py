import logging
import time
# RPi.GPIO was imported but never used directly in Frontend — commented out to avoid
# ImportError on non-Raspberry Pi dev machines.
# import RPi.GPIO as GPIO
from nicegui import ui
import paho.mqtt.client as mqtt
import json
from pathlib import Path
from MQTTHandler import MQTTHandler
import threading

logger = logging.getLogger(__name__)

class Frontend():
    def __init__(self):
        self.notes_file = Path('channel_notes.json')
        self.channel_notes_store = {} 
        self.load_notes()
        self.pot_settings_file = Path('potentiometer_settings.json')
        self.channel_pot_settings = {}
        self.load_pot_settings()
        topics = {
            'temperature': f"/temperature",
            'operation_status': f"/status",
            'UI_command': f"/ui_command",
            'control_response': f"/control_response",
        }
        self.mqtt = MQTTHandler(
            client_id="web_ui",
            broker="localhost",
            port=1883,
            topics=topics
        )
        logger.info("[Frontend] Connecting MQTT client (web_ui) to broker 172.17.0.1:1883")
        self.mqtt.connect()
        logger.info("[Frontend] MQTT connect() called.")

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

                ui.separator()
                ui.label('Set Potentiometer Level').classes('text-h6')
                current_channel = self.switch_dropdown.value
                initial_percent = self.channel_pot_settings.get(current_channel, 50)

                self.pot_percent_input = ui.number(
                    label='Potentiometer level (%)',
                    value=initial_percent,
                    min=0,
                    max=100,
                    step=1
                ).classes('w-full')
                
                def save_notes_for_channel():
                    channel = self.switch_dropdown.value
                    self.channel_notes_store[channel] = self.channel_notes.value
                    self.save_notes()
                    ui.notify(f"Notes for {channel} saved.", color='positive')

                def update_notes_field():
                    channel = self.switch_dropdown.value
                    note = self.channel_notes_store.get(channel, '')
                    self.channel_notes.value = note

                def update_pot_input():
                    channel = self.switch_dropdown.value
                    self.pot_percent_input.value = self.channel_pot_settings.get(channel, 50)


                self.switch_dropdown.on('update:model-value', update_pot_input)
                self.switch_dropdown.on('update:model-value', update_notes_field)
                ui.button('Save Notes', on_click=save_notes_for_channel).classes('mt-2 bg-green-600')
                ui.button('Activate Channel', on_click=self.execute_switch).classes('mt-2 w-full bg-blue-700')

            with ui.card().classes("w-1/3"):
                ui.label('Signal Configuration').classes('text-h6')

                frequency_input = ui.input(label='Frequency (Hz)', value='1000').props('type=number step=1 suffix=Hz')
                burst_count_input = ui.input(label='Bursts per block', value='5').props('type=number step=1 suffix=bursts')
                duty_cycle_input = ui.input(label='Duty Cycle (%)', value='50').props('type=number step=1 suffix=%')
                inter_block_delay_input = ui.input(label='Delay between burst blocks (s)', value='2.0').props('type=number step=0.1 suffix=s')

                def send_signal_settings():
                    try:
                        settings = {
                            "type": "signal_config",
                            "frequency": float(frequency_input.value),
                            "bursts": int(burst_count_input.value),
                            "duty_cycle": float(duty_cycle_input.value),
                            "inter_block_delay": float(inter_block_delay_input.value),
                        }
                        logger.info(f"[Frontend] → /ui_command: {settings}")
                        self.mqtt.publish(
                            topic="/ui_command",
                            payload=json.dumps(settings),
                            qos=1
                        )
                        ui.notify("Signal configuration sent!", color='positive')
                    except Exception as e:
                        logger.error(f"[Frontend] send_signal_settings error: {e}")
                        ui.notify(f"Error: {str(e)}", color='negative')

                ui.button("Send Signal Settings", on_click=send_signal_settings).classes('mt-2 w-full bg-purple-600')

                def send_burst_trigger():
                    try:
                        payload = {"type": "trigger_burst"}
                        logger.info(f"[Frontend] → /ui_command: {payload}")
                        self.mqtt.publish(
                            topic="/ui_command",
                            payload=json.dumps(payload),
                            qos=1
                        )
                        ui.notify(f"Triggered burst series", color='positive')
                    except Exception as e:
                        logger.error(f"[Frontend] send_burst_trigger error: {e}")
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
                            payload = {"type": "pulse_train_sweep"}
                            logger.info(f"[Frontend] → /ui_command: {payload}")
                            self.mqtt.publish(
                                topic="/ui_command",
                                payload=json.dumps(payload),
                                qos=1
                            )
                            ui.notify(f"Sweeping pulse train started", color='positive')
                        except Exception as e:
                            logger.error(f"[Frontend] send_pulse_train_sweep error: {e}")
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
                        payload = {"type": "connect_generator"}
                        logger.info(f"[Frontend] → /ui_command: {payload}")
                        self.mqtt.publish(
                            topic="/ui_command",
                            payload=json.dumps(payload),
                            qos=1
                        )
                        #status_label.text = 'Status: Connecting...'
                        ui.notify('Connect command sent via MQTT', color='info')
                    except Exception as e:
                        #status_label.text = f'Connection command error: {str(e)}'
                        logger.error(f"[Frontend] connect_generator error: {e}")
                        ui.notify(f'Error sending connect command: {str(e)}', color='negative')

                def disconnect_generator():
                    try:
                        payload = {"type": "disconnect_generator"}
                        logger.info(f"[Frontend] → /ui_command: {payload}")
                        self.mqtt.publish(
                            topic="/ui_command",
                            payload=json.dumps(payload),
                            qos=1
                        )
                        #status_label.text = 'Status: Disconnecting...'
                        ui.notify('Disconnect command sent via MQTT', color='info')
                    except Exception as e:
                        logger.error(f"[Frontend] disconnect_generator error: {e}")
                        ui.notify(f'Error sending disconnect command: {str(e)}', color='negative')
                        
                with ui.row():
                    connect_btn = ui.button('Reset and Reconnect', on_click=connect_generator).classes('mt-2 bg-green-700')
                    disconnect_btn = ui.button('Disconnect', on_click=disconnect_generator).classes('mt-2 bg-red-700')
                
            ui.separator()
            ui.label('Potentiometer control').classes('text-h6')
            with ui.card().classes("w-1/3"):
                ui.label('Sweep Configuration').classes('text-h6')
                start_v = ui.input(label='Start voltage (V)', value='0').props('type=number step=0.1 suffix=V')
                end_v = ui.input(label='End voltage (V)', value='10').props('type=number step=0.1 suffix=V')
                steps = ui.input(label='Steps (max 255)', value='255').props('type=number step=1 suffix=steps')
                sweep_duration = ui.input(label='Duration per step (s)', value='1').props('type=number step=0.1 suffix=s')
                ui.label('Duration is the wait time between each individual step, not the total sweep time.').classes('text-caption text-grey-6 text-xs')

                def voltage_sweep():
                    try:
                        settings = {
                            "type": "potentiometer_voltage_sweep",
                            "voltage_start_v": float(start_v.value),
                            "voltage_end_v": float(end_v.value),
                            "voltage_sweep_steps": float(steps.value),
                            "voltage_sweep_duration": float(sweep_duration.value)
                        }
                        logger.info(f"[Frontend] → /ui_command: {settings}")
                        self.mqtt.publish(
                            topic="/ui_command",
                            payload=json.dumps(settings),
                            qos=1
                        )
                        ui.notify('Voltage sweep command sent', color='positive')
                    except Exception as e:
                        #status_label.text = f'Connection command error: {str(e)}'
                        logger.error(f"[Frontend] voltage_sweep error: {e}")
                        ui.notify(f'Error sending connect command: {str(e)}', color='negative')

                ui.button("Do voltage sweep", on_click=voltage_sweep).classes('mt-2 w-full bg-purple-600')


            Temperature readout card commented out — re-enable once core functionality is verified.
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
            
                def on_temp_message(client, userdata, message):
                    # BUG FIX (Bug 6): This callback runs in the paho MQTT background thread.
                    # Calling ui.notify() from a background thread is not thread-safe in NiceGUI
                    # and causes intermittent crashes/silent failures. Removed ui.notify() here;
                    # the timer-driven refresh_ui() picks up new readings on its next tick.
                    # List.append() is safe in CPython (GIL protects single operations).
                    try:
                        payload = json.loads(message.payload.decode())
                        logger.debug(f"[Frontend] /temperature raw: {payload}")
                        if "temperature_k" in payload:
                            add_temperature_reading(payload["temperature_k"])
                            logger.info(f"[Frontend] Temperature queued: {payload['temperature_k']:.2f} K")
                        else:
                            logger.warning(f"[Frontend] /temperature payload missing 'temperature_k': {payload}")
                    except Exception as e:
                        # ui.notify(f"Temperature parse error: {e}", color="negative")  # NOT thread-safe
                        logger.error(f"[Frontend] Temperature parse error in MQTT callback: {e}")
            
                # Subscribe to /temperature directly on the paho client.
                # message_callback_add registers a per-topic callback that takes priority over
                # MQTTHandler._on_message for this topic, so there is no double-dispatch.
                logger.info("[Frontend] Subscribing to /temperature for live readout")
                self.mqtt.client.subscribe("/temperature", qos=1)
                self.mqtt.client.message_callback_add("/temperature", on_temp_message)
            
                def refresh_ui():
                    # BUG FIX (Bug 3): ui.label() calls must be inside a `with temp_display:`
                    # context to attach as children of temp_display. Without it, labels were
                    # created at the page root and never appeared inside the temperature card.
                    temp_display.clear()
                    with temp_display:
                        for temp in self.temp_readings:
                            ui.label(f"{temp:.2f} K")
                    logger.debug(f"[Frontend] refresh_ui: {len(self.temp_readings)} readings displayed")
            
                ui.timer(interval=5.0, callback=refresh_ui)

        
    def execute_switch(self):
        selected_channel = self.switch_dropdown.value
        if selected_channel is None:
            ui.notify("Please select a channel.", color='warning')
            return
        try:
            if "Switch" in selected_channel:
                channel_number = int(selected_channel.split()[1])
                command_type = "channel_select"
                percent = float(self.pot_percent_input.value)
            else:
                channel_number = 0
                command_type = "all_off"
                percent = None

            payload = {
                "type": command_type,
                "channel": channel_number,
                "percent": percent
            }
            logger.info(f"[Frontend] → /ui_command: {payload}")
            self.mqtt.publish(
                topic="/ui_command",
                payload=json.dumps(payload),
                qos=1
            )
            ui.notify(f'Channel {selected_channel} selected with voltage percentage: {percent}', color='positive')

        except Exception as e:
            error_msg = f"MQTT error: {str(e)}"
            logger.error(f"[Frontend] execute_switch error: {e}")
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

    def load_pot_settings(self):
        if self.pot_settings_file.exists():
            try:
                with open(self.pot_settings_file, 'r') as f:
                    self.channel_pot_settings = json.load(f)
            except Exception as e:
                print(f"Failed to load potentiometer settings: {e}")
        else:
            self.channel_pot_settings = {}

    def save_pot_settings(self):
        try:
            with open(self.pot_settings_file, 'w') as f:
                json.dump(self.channel_pot_settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save potentiometer settings: {e}")
