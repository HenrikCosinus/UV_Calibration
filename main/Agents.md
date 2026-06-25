# AGENTS.md

## Projekt
Dieses Repository enthält die Steuer- und Bediensoftware für das optische COSINUS-Kalibrationssystem.
Die Software steuert kurze LED-Lichtpulse über eine Kombination aus Raspberry Pi, GPIO-gesteuertem Multiplexer, AD5260-Digitalpotentiometer, Agilent 33250A Signalgenerator, MAX31865-Temperaturmessung und NiceGUI-Weboberfläche.

Die Anwendung wird über `main.py` gestartet. Das Frontend kommuniziert nicht direkt mit der Hardware, sondern über MQTT mit dem Backend. Wichtige MQTT-Topics sind `/ui_command`, `/control_response`, `/status` und `/temperature`.

Ziel bei Änderungen ist immer: Laborsoftware stabiler, nachvollziehbarer und sicherer machen, ohne unnötige Architekturänderungen oder riskante Hardwareaktionen.

## Struktur
- `main.py`: Einstiegspunkt; startet Backend, Frontend und NiceGUI auf Port 8080.
- `Backend.py`: High-Level-Steuerlogik; verarbeitet MQTT-Kommandos und ruft Hardwarecontroller auf.
- `Frontend.py`: NiceGUI-Bedienoberfläche für Kanalwahl, Notizen, Potentiometer, Signalgenerator, Burst/Sweep und Temperaturanzeige.
- `MQTTHandler.py`: MQTT-Kommunikation zwischen Frontend und Backend.
- `GPIOController.py`: GPIO-Multiplexer, AD5260-SPI-Ansteuerung und MAX31865-Temperaturmessung.
- `Agilent_Controller_RS232.py`: SCPI-Kommunikation mit dem Agilent 33250A über PyVISA/RS232.
- `Tester.py`: Manuelle Tests oder Hilfsskripte.
- `docs/`: Dokumentation zu Hardware, Architektur, Pinbelegung und Laborbetrieb.
- `tests/`: Automatisierte Tests, falls vorhanden.

## Architekturregeln
- Frontend und Hardwarezugriff bleiben getrennt.
- Das Frontend kommuniziert mit dem Backend über MQTT, nicht durch direkte Hardwareaufrufe.
- MQTT-Topics und JSON-Payloads gelten als Schnittstellenvertrag und dürfen nicht ohne Begründung geändert werden.
- Hardware-nahe Logik gehört in `GPIOController.py` oder `Agilent_Controller_RS232.py`.
- High-Level-Abläufe, Validierung und Koordination gehören in `Backend.py`.
- UI-Logik gehört in `Frontend.py`.
- Keine großen Umstrukturierungen ohne vorherige Begründung und Rückfrage.

## Hardware-Sicherheitsregeln
- Keine GPIO-Pinbelegung ändern, ohne die Änderung explizit zu begründen.
- Keine Signalgenerator-Ausgänge, Bursts, Sweeps oder Trigger aktivieren, wenn die Aufgabe nicht ausdrücklich danach fragt.
- Keine `sudo`-Befehle ungefragt ausführen; Raspberry-Pi-spezifische Befehle nur vorschlagen, wenn die Umgebung nicht eindeutig sicher ist.
- Keine realen Hardwarezustände verändern, wenn eine Simulation, ein Dry-Run oder eine reine Codeprüfung ausreicht.
- Hardwarezugriffe müssen robust gegen fehlende Geräte, Permission-Fehler, getrennte Kabel, falsche Ports und temporäre Lesefehler sein.
- Fehlerbehandlung und Logging dürfen nicht entfernt werden.
- Kanalnotizen, Messlogs und bestehende JSON-Daten nicht überschreiben, außer die Aufgabe verlangt es ausdrücklich.

## Befehle
- Syntax aller Python-Dateien prüfen: `python3 -m compileall .`
- Syntax der Hauptdateien prüfen: `python3 -m py_compile Backend.py Agilent_Controller_RS232.py Frontend.py main.py GPIOController.py MQTTHandler.py Tester.py`
- Formatierung prüfen: `black --check .`
- Formatierung anwenden: `black .`
- Lint prüfen, falls Ruff installiert ist: `ruff check .`
- Tests ausführen, falls vorhanden: `pytest`
- Anwendung starten: `python3 main.py`

## Stil und Qualität
- Änderungen sollen minimal-invasiv sein.
- Bestehenden Code-Stil beibehalten.
- Keine neuen externen Python-Abhängigkeiten ohne klare Begründung.
- Keine Secrets, Passwörter, privaten Pfade oder lokalen Zugangsdaten committen.
- Exceptions nicht stumm schlucken; Fehler sollen geloggt oder verständlich zurückgegeben werden.
- Bei Hardwarefehlern soll die UI/Backend-Kommunikation kontrolliert weiterlaufen, soweit möglich.
- Bestehende öffentliche Funktionsnamen, MQTT-Topics und Payload-Formate nicht unnötig brechen.
- Kommentare zu Hardwareannahmen, Pinbelegungen und Geräteverhalten erhalten oder verbessern.

## Umgang mit Tests
- Wenn automatisierte Tests vorhanden sind, relevante Tests ausführen.
- Wenn keine Tests vorhanden sind, mindestens `python3 -m compileall .` ausführen.
- Hardwareabhängige Funktionen nicht blind als getestet ausgeben, wenn keine reale Hardware verfügbar ist.
- Bei Hardwareabhängigkeit klar angeben, was nicht getestet werden konnte und welcher manuelle Test auf dem Raspberry Pi nötig ist.

## Done when
Eine Aufgabe gilt erst als abgeschlossen, wenn:
- der Code syntaktisch geprüft wurde,
- relevante Tests oder Checks ausgeführt wurden,
- der Diff klein und nachvollziehbar ist,
- keine unnötigen Architekturänderungen eingeführt wurden,
- Hardware-Sicherheitsregeln eingehalten wurden,
- geänderte Dateien kurz zusammengefasst wurden,
- ausgeführte Befehle genannt wurden,
- offene Risiken oder nicht getestete Hardwarepfade genannt wurden.