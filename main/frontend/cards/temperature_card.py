import logging
import time
from nicegui import ui

logger = logging.getLogger(__name__)


def build_temperature_card(frontend):
    with ui.card().classes("flex-1"):
        ui.label('Live Temperature').classes('text-h6')
        temp_display = ui.column().classes("gap-1")

        def refresh_ui():
            try:
                temp_display.clear()
                with temp_display:
                    if frontend.temp_readings:
                        temp, ts = frontend.temp_readings[-1]
                        ui.label(f"{temp:.2f} C").classes('text-h5')
                        if ts is not None:
                            ui.label(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))).classes("text-caption text-grey")
                    else:
                        ui.label("No reading yet").classes("text-grey")
                logger.debug(f"refresh_ui: {len(frontend.temp_readings)} readings displayed")
            except Exception:
                timer.cancel()

        timer = ui.timer(interval=5.0, callback=refresh_ui)
