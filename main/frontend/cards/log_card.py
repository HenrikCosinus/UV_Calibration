import logging
from nicegui import ui

logger = logging.getLogger(__name__)

MAX_LOG_ENTRIES = 200

LEVEL_COLORS = {
    "DEBUG":    "text-grey",
    "INFO":     "text-blue-800",
    "WARNING":  "text-orange",
    "ERROR":    "text-red",
    "CRITICAL": "text-red-900",
}


class UILogHandler(logging.Handler):
    """Logging handler that stores records for the UI to display."""

    def __init__(self):
        super().__init__()
        self.records: list[dict] = []

    def emit(self, record: logging.LogRecord):
        self.records.append({
            "time":    logging.Formatter().formatTime(record, "%H:%M:%S"),
            "name":    record.name,
            "level":   record.levelname,
            "message": record.getMessage(),
        })
        if len(self.records) > MAX_LOG_ENTRIES:
            self.records.pop(0)


# Single handler instance shared across all page connections
_ui_log_handler = UILogHandler()
_ui_log_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(_ui_log_handler)


def build_log_card():
    with ui.card().classes("flex-1"):
        ui.label("System Log").classes("text-h6")

        with ui.row().classes("gap-2 items-center w-full mb-2"):
            name_filter = ui.input(label="Filter by logger").classes("flex-1")
            level_filter = ui.select(
                label="Min level",
                options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                value="INFO"
            ).classes("w-32")

            def export_logs():
                min_level = logging.getLevelName(level_filter.value)
                name_substr = name_filter.value.strip().lower()
                filtered = [
                    r for r in _ui_log_handler.records
                    if logging.getLevelName(r["level"]) >= min_level
                    and (not name_substr or name_substr in r["name"].lower())
                ]
                lines = [
                    f"[{r['time']}] {r['level']:<8} {r['name']} — {r['message']}"
                    for r in filtered
                ]
                ui.download(content="\n".join(lines).encode(), filename="system.log", media_type="text/plain")

            ui.button("Export .log", icon="download", on_click=export_logs).classes("ml-auto")

        log_display = ui.column().classes("gap-0 w-full font-mono text-xs overflow-auto").style("max-height: 300px")

        def refresh_logs():
            try:
                min_level = logging.getLevelName(level_filter.value)
                name_substr = name_filter.value.strip().lower()

                filtered = [
                    r for r in _ui_log_handler.records
                    if logging.getLevelName(r["level"]) >= min_level
                    and (not name_substr or name_substr in r["name"].lower())
                ]

                log_display.clear()
                with log_display:
                    for r in reversed(filtered[-100:]):
                        color = LEVEL_COLORS.get(r["level"], "text-grey")
                        ui.label(
                            f"[{r['time']}] {r['level']:<8} {r['name']} — {r['message']}"
                        ).classes(f"{color} w-full")
            except Exception:
                pass

        ui.timer(interval=2.0, callback=refresh_logs)
