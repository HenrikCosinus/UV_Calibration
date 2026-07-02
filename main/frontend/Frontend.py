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
            'hardware_status': f"/hardware_status",
        }
        self.mqtt = MQTTHandler(
            client_id="web_ui",
            broker="localhost",
            port=1883,
            topics=topics
        )
        logger.info("Connecting MQTT client (web_ui) to broker 172.17.0.1:1883")
        self.mqtt.connect()
        logger.info("MQTT connect() called.")

        self.temp_readings = []

        self.mqtt.client.subscribe("/temperature", qos=1)
        self.mqtt.client.message_callback_add("/temperature", self._on_temp_message)
        self.mqtt.client.subscribe("/hardware_status", qos=1)
        self.mqtt.client.message_callback_add("/hardware_status", self._on_hardware_status)
        logger.info("Subscribed to /temperature and /hardware_status")

    def create_ui(self):
        # ── Row 1: three equal columns ────────────────────────────────────────
        with ui.row().classes("w-full gap-4 items-start"):

            # Column 1 — UV LED Channel
            with ui.card().classes("flex-1"):
                ui.label('UV LED Channel').classes('text-h6')
                self.switch_dropdown = ui.select(
                    label='Select Channel',
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
                    placeholder='Add notes for this channel...',
                    value=initial_note
                ).classes('w-full')

                ui.separator()
                ui.label('Potentiometer Level').classes('text-subtitle1 mt-2')
                current_channel = self.switch_dropdown.value
                initial_percent = self.channel_pot_settings.get(current_channel, 50)
                self.pot_percent_input = ui.number(
                    label='Level (%)',
                    value=initial_percent,
                    min=0, max=100, step=1
                ).classes('w-full')

                def save_notes_for_channel():
                    channel = self.switch_dropdown.value
                    self.channel_notes_store[channel] = self.channel_notes.value
                    self.save_notes()
                    ui.notify(f"Notes for {channel} saved.", color='positive')

                def update_notes_field():
                    channel = self.switch_dropdown.value
                    self.channel_notes.value = self.channel_notes_store.get(channel, '')

                def update_pot_input():
                    channel = self.switch_dropdown.value
                    self.pot_percent_input.value = self.channel_pot_settings.get(channel, 50)

                self.switch_dropdown.on('update:model-value', update_pot_input)
                self.switch_dropdown.on('update:model-value', update_notes_field)
                with ui.row().classes('gap-2 mt-2'):
                    ui.button('Save Notes', on_click=save_notes_for_channel).classes('bg-green-600')
                    ui.button('Activate Channel', on_click=self.execute_switch).classes('bg-blue-700')

            # Column 2 — Signal Configuration + Signal Generator stacked
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
                            self.mqtt.publish(topic="/ui_command", payload=json.dumps(settings), qos=1)
                            ui.notify("Signal configuration sent!", color='positive')
                        except Exception as e:
                            logger.error(f"send_signal_settings error: {e}")
                            ui.notify(f"Error: {str(e)}", color='negative')

                    def send_burst_trigger():
                        try:
                            payload = {"type": "trigger_burst"}
                            logger.info(f"→ /ui_command: {payload}")
                            self.mqtt.publish(topic="/ui_command", payload=json.dumps(payload), qos=1)
                            ui.notify("Triggered burst series", color='positive')
                        except Exception as e:
                            logger.error(f"send_burst_trigger error: {e}")
                            ui.notify(f"Burst trigger failed: {str(e)}", color='negative')

                    def send_pulse_train_sweep():
                        try:
                            payload = {"type": "pulse_train_sweep"}
                            logger.info(f"→ /ui_command: {payload}")
                            self.mqtt.publish(topic="/ui_command", payload=json.dumps(payload), qos=1)
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
                            self.mqtt.publish(topic="/ui_command", payload=json.dumps(payload), qos=1)
                            ui.notify('Connect command sent', color='info')
                        except Exception as e:
                            logger.error(f"connect_generator error: {e}")
                            ui.notify(f'Error sending connect command: {str(e)}', color='negative')

                    def disconnect_generator():
                        try:
                            payload = {"type": "disconnect_generator"}
                            logger.info(f"→ /ui_command: {payload}")
                            self.mqtt.publish(topic="/ui_command", payload=json.dumps(payload), qos=1)
                            ui.notify('Disconnect command sent', color='info')
                        except Exception as e:
                            logger.error(f"disconnect_generator error: {e}")
                            ui.notify(f'Error sending disconnect command: {str(e)}', color='negative')

                    with ui.row().classes('gap-2 mt-2'):
                        ui.button('Reset and Reconnect', on_click=connect_generator).classes('bg-green-700')
                        ui.button('Disconnect', on_click=disconnect_generator).classes('bg-red-700')

            # Column 3 — Temperature
            with ui.card().classes("flex-1"):
                ui.label('Live Temperature').classes('text-h6')
                temp_display = ui.column().classes("gap-1")

                def refresh_ui():
                    try:
                        temp_display.clear()
                        with temp_display:
                            if self.temp_readings:
                                temp, ts = self.temp_readings[-1]
                                ui.label(f"{temp:.2f} K").classes('text-h5')
                                if ts is not None:
                                    ui.label(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))).classes("text-caption text-grey")
                            else:
                                ui.label("No reading yet").classes("text-grey")
                        logger.debug(f"refresh_ui: {len(self.temp_readings)} readings displayed")
                    except Exception:
                        timer.cancel()

                timer = ui.timer(interval=5.0, callback=refresh_ui)

        # ── Row 2: Potentiometer Sweep full width ─────────────────────────────
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
                        self.mqtt.publish(topic="/ui_command", payload=json.dumps(settings), qos=1)
                        ui.notify('Voltage sweep command sent', color='positive')
                    except Exception as e:
                        logger.error(f"voltage_sweep error: {e}")
                        ui.notify(f'Error: {str(e)}', color='negative')

                ui.button("Start Sweep", on_click=voltage_sweep).classes('bg-purple-600')
            ui.label('Duration is the wait time per step, not total sweep time.').classes('text-caption text-grey-6 mt-1')

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
                payload = {
                    "type": command_type,
                    "channel": channel_number,
                    "pot_percent": percent
                }
                self.channel_pot_settings[selected_channel] = percent
                self.save_pot_settings()
            elif selected_channel == "All Off":
                payload = {"type": "all_off"}
            else:
                ui.notify("Unknown channel selected.", color='warning')
                return

            logger.info(f"→ /ui_command: {payload}")
            self.mqtt.publish(
                topic="/ui_command",
                payload=json.dumps(payload),
                qos=1
            )
            ui.notify(f'{selected_channel} activated', color='positive')
        except Exception as e:
            logger.error(f"execute_switch error: {e}")
            ui.notify(f'Error: {str(e)}', color='negative')

    def load_notes(self):
        try:
            if self.notes_file.exists():
                with open(self.notes_file) as f:
                    self.channel_notes_store = json.load(f)
        except Exception as e:
            print(f"Failed to load notes: {e}")

    def save_notes(self):
        try:
            with open(self.notes_file, 'w') as f:
                json.dump(self.channel_notes_store, f, indent=2)
        except Exception as e:
            print(f"Failed to save notes: {e}")

    def load_pot_settings(self):
        try:
            if self.pot_settings_file.exists():
                with open(self.pot_settings_file) as f:
                    self.channel_pot_settings = json.load(f)
        except Exception as e:
            print(f"Failed to load potentiometer settings: {e}")

    def save_pot_settings(self):
        try:
            with open(self.pot_settings_file, 'w') as f:
                json.dump(self.channel_pot_settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save potentiometer settings: {e}")

    def _on_temp_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
            logger.debug(f"/temperature raw: {payload}")
            if "temperature_k" in payload:
                self.temp_readings.append((payload["temperature_k"], payload.get("timestamp")))
                if len(self.temp_readings) > 20:
                    self.temp_readings.pop(0)
                logger.info(f"Temperature queued: {payload['temperature_k']:.2f} K")
            else:
                logger.warning(f"/temperature payload missing 'temperature_k': {payload}")
        except Exception as e:
            logger.error(f"Temperature parse error in MQTT callback: {e}")

    def _on_hardware_status(self, client, userdata, message):
        try:
            status = json.loads(message.payload.decode())
            labels = {
                "agilent":  "Agilent signal generator",
                "gpio":     "GPIO multiplexer",
                "ad5260":   "AD5260 potentiometer",
                "max31865": "MAX31865 temperature sensor",
            }
            for key, name in labels.items():
                if not status.get(key, True):
                    ui.notify(f"{name} failed to initialize", type="negative", close_button=True, timeout=0)
        except Exception as e:
            logger.error(f"hardware_status parse error: {e}")
