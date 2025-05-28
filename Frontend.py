import logging
from nicegui import ui, app
import glob
import time
import RPi.GPIO as GPIO
from Backend import HighLevelControl
from nicegui import ui
import paho.mqtt.client as mqtt
import json

class Frontend:
    def __init__(self):
        self.mqtt_client = self.setup_mqtt()
        self.create_ui()

    def setup_mqtt(self):
        client = mqtt.Client()
        client.on_connect = self.on_mqtt_connect
        client.connect("raspberrypi.local", "172.17.0.1")
        client.loop_start()
        return client

    def on_mqtt_connect(self, client, userdata, flags, rc):
        ui.notify(f"MQTT Connected (Code: {rc})")

    def create_ui(self):
        with ui.card().classes("w-96"):
            ui.label('Select UV_LED:').classes('mt-4')
            switch_options = [
                'Switch 1', 'Switch 2', 'Switch 3', 'Switch 4',
                'Switch 5', 'Switch 6', 'Switch 7', 'Switch 8',
                'All Off'
            ]
            switch_dropdown = ui.select(
                label='Available UV-LEDs',
                options=switch_options,
                value=switch_options[-1]
            ).classes('w-full')
            
            # Activation button
            ui.button("Activate", on_click=lambda: (
                execute_switch(switch_dropdown.value),
                ui.notify(f"Channel {switch_dropdown.value} requested")
            )).classes("w-full")

            def execute_switch(self):
                selected_channel = switch_dropdown.value 
                try:
                    self.mqtt_client.publish(
                        topic="uv_calibration/channel_select",
                        payload=str(selected_channel),  # Convert to string for MQTT
                        qos=1  # At least once delivery
                    )
                    ui.notify(f'Channel {selected_channel} selected', color='positive')
                except Exception as e:
                    error_msg = f"MQTT error: {str(e)}"
                    ui.notify(error_msg, color='negative')

            ui.button('Activate Channel', on_click=execute_switch).classes('mt-2 w-full bg-blue-700')

        with ui.card().classes('m-4'):
            ui.label('Connection').classes('text-h6')
            # Available ports
            ports = HighLevelControl.agilent.find_usb_serial_ports()
            port_dropdown = ui.select(
                label='Serial Port',
                options=ports if ports else ['No ports found'],
                value=ports[0] if ports else None
            ).classes('w-full')
            
            def refresh_ports():
                new_ports = HighLevelControl.agilent.find_usb_serial_ports()
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
                        generator = HighLevelControl.agilent(port=port)
                        generator.reset()
                        status_label.text = f'Status: Connected to {port}'
                        connect_btn.visible = False
                        disconnect_btn.visible = True
                        ui.notify('Connected to generator!', color='positive')
                    else:
                        status_label.text = 'Status: Already connected'
                except Exception as e:
                    status_label.text = f'Status: Connection error - {str(e)}'
                    ui.notify(f'Connection error: {str(e)}', color='negative')
            
            def disconnect_generator():
                global generator
                try:
                    if generator is not None:
                        generator.close()
                        generator = None
                        status_label.text = 'Status: Disconnected'
                        connect_btn.visible = True
                        disconnect_btn.visible = False
                        ui.notify('Disconnected from generator', color='info')

                    else:
                        status_label.text = 'Status: Already disconnected'
                except Exception as e:
                    status_label.text = f'Status: Disconnection error - {str(e)}'
                    ui.notify(f'Disconnection error: {str(e)}', color='negative')
            
            with ui.row():
                connect_btn = ui.button('Connect', on_click=connect_generator).classes('mt-2 bg-green-700')
                disconnect_btn = ui.button('Disconnect', on_click=disconnect_generator).classes('mt-2 bg-red-700')
                disconnect_btn.visible = False


            

    create_ui()
    #ui.run(title="Agilent 33250A Demo Runner", port=8085, reload=True)
    ui.run(title="UI_Test", port=1884, reload = True, host="134.107.69.228")