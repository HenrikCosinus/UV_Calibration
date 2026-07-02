import logging
import json
from nicegui import ui

logger = logging.getLogger(__name__)


def build_uv_led_card(frontend):
    with ui.card().classes("flex-1"):
        ui.label('UV LED Channel').classes('text-h6')
        frontend.switch_dropdown = ui.select(
            label='Select Channel',
            options=[
                'Switch 1', 'Switch 2', 'Switch 3', 'Switch 4',
                'Switch 5', 'Switch 6', 'Switch 7', 'Switch 8',
                'All Off'
            ],
            value='Switch 1'
        ).classes('w-full')

        initial_note = frontend.channel_notes_store.get('Switch 1', '')
        frontend.channel_notes = ui.textarea(
            label='Channel Notes',
            placeholder='Add notes for this channel...',
            value=initial_note
        ).classes('w-full')

        ui.separator()
        ui.label('Potentiometer Level').classes('text-subtitle1 mt-2')
        current_channel = frontend.switch_dropdown.value
        initial_percent = frontend.channel_pot_settings.get(current_channel, 50)
        frontend.pot_percent_input = ui.number(
            label='Level (%)',
            value=initial_percent,
            min=0, max=100, step=1
        ).classes('w-full')

        def save_notes_for_channel():
            channel = frontend.switch_dropdown.value
            frontend.channel_notes_store[channel] = frontend.channel_notes.value
            frontend._save_notes()
            ui.notify(f"Notes for {channel} saved.", color='positive')

        def update_notes_field():
            channel = frontend.switch_dropdown.value
            frontend.channel_notes.value = frontend.channel_notes_store.get(channel, '')

        def update_pot_input():
            channel = frontend.switch_dropdown.value
            frontend.pot_percent_input.value = frontend.channel_pot_settings.get(channel, 50)

        def execute_switch():
            selected_channel = frontend.switch_dropdown.value
            if selected_channel is None:
                ui.notify("Please select a channel.", color='warning')
                return
            try:
                if "Switch" in selected_channel:
                    channel_number = int(selected_channel.split()[1])
                    percent = float(frontend.pot_percent_input.value)
                    payload = {
                        "type": "channel_select",
                        "channel": channel_number,
                        "pot_percent": percent
                    }
                    frontend.channel_pot_settings[selected_channel] = percent
                    frontend._save_pot_settings()
                elif selected_channel == "All Off":
                    payload = {"type": "all_off"}
                else:
                    ui.notify("Unknown channel selected.", color='warning')
                    return
                logger.info(f"→ /ui_command: {payload}")
                frontend.mqtt.publish(topic="/ui_command", payload=json.dumps(payload), qos=1)
                ui.notify(f'{selected_channel} activated', color='positive')
            except Exception as e:
                logger.error(f"execute_switch error: {e}")
                ui.notify(f'Error: {str(e)}', color='negative')

        frontend.switch_dropdown.on('update:model-value', update_pot_input)
        frontend.switch_dropdown.on('update:model-value', update_notes_field)
        with ui.row().classes('gap-2 mt-2'):
            ui.button('Save Notes', on_click=save_notes_for_channel).classes('bg-green-600')
            ui.button('Activate Channel', on_click=execute_switch).classes('bg-blue-700')
