"""
Manual hardware test runner for GPIOController.py.

Run this file on the Raspberry Pi, not on a Windows/Linux development PC without
the Raspberry Pi GPIO/SPI libraries installed.

Examples:
    python tests/Tester.py mux
    python tests/Tester.py mux --mux-pins 17 18 22 27
    python tests/Tester.py ad5260
    python tests/Tester.py max31865
    python tests/Tester.py all
"""

import argparse
import sys
import time  # used by ad5260_voltage_sweep and max31865
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_DIR = PROJECT_ROOT / "main"
if str(MAIN_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_DIR))


def import_gpio_controller():
    try:
        from GPIOController import AD5260Controller, MAX31865Controller, Multiplexer
    except Exception as exc:
        print("Could not import GPIOController.py.")
        print("This test runner must be executed on the Raspberry Pi with all hardware libraries installed.")
        raise exc
    return Multiplexer, AD5260Controller, MAX31865Controller


PIN_LABELS = {
    7:  "SPI0 CE1  (physical pin 26)",
    8:  "SPI0 CE0  (physical pin 24)",
    9:  "SPI0 MISO (physical pin 21)",
    10: "SPI0 MOSI (physical pin 19)",
    11: "SPI0 SCLK (physical pin 23)",
    12: "GPIO12    (physical pin 32)",
    13: "GPIO13    (physical pin 33)",
    17: "GPIO17    (physical pin 11)",
    18: "GPIO18    (physical pin 12)",
    22: "GPIO22    (physical pin 15)",
    27: "GPIO27    (physical pin 13)",
}


def test_pins(pins, label):
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        print("RPi.GPIO not available. Run this on the Raspberry Pi.")
        return

    print(f"\n=== {label} pin GPIO-level test ===")
    print(f"BCM pins under test: {pins}")
    print("NOTE: if SPI pins are included, spidev must NOT be open during this test.")
    print("Expected oscilloscope level: LOW ≈ 0 V, HIGH ≈ 3.3 V.")
    print("Press Enter to advance to the next pin.\n")

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

    try:
        print("All pins set LOW. Check baseline.")
        input("Press Enter to start stepping through pins...")

        for pin in pins:
            for p in pins:
                GPIO.output(p, GPIO.LOW)
            GPIO.output(pin, GPIO.HIGH)
            description = PIN_LABELS.get(pin, f"GPIO{pin}")
            print(f"\nBCM {pin} ({description}) → HIGH. All others LOW.")
            input("Press Enter for next pin...")

        for pin in pins:
            GPIO.output(pin, GPIO.LOW)
        print(f"\nAll pins set LOW. {label} pin test complete.")
    finally:
        GPIO.cleanup()


def test_multiplexer_switches(pins):
    Multiplexer, _, _ = import_gpio_controller()
    mux = Multiplexer(pins=pins)

    switch_methods = [
        mux.Switch_1,
        mux.Switch_2,
        mux.Switch_3,
        mux.Switch_4,
        mux.Switch_5,
        mux.Switch_6,
        mux.Switch_7,
        mux.Switch_8,
    ]

    expected_states = [
        [1, 0, 0, 0],
        [1, 1, 0, 0],
        [1, 0, 1, 0],
        [1, 1, 1, 0],
        [1, 0, 0, 1],
        [1, 1, 0, 1],
        [1, 0, 1, 1],
        [1, 1, 1, 1],
    ]

    print("\n=== Multiplexer channel-switch test ===")
    print(f"BCM pins under test: {pins}")
    print("Expected states are listed in pin order [pin0, pin1, pin2, pin3].")
    print("Press Enter to advance to the next channel.\n")

    try:
        for channel, method in enumerate(switch_methods, start=1):
            method()
            states = expected_states[channel - 1]
            print(f"Switch_{channel}: pins {pins} → expected {states}")
            input("Press Enter for next channel...")

        mux.set_all_pins(False)
        print("\nAll pins set LOW. Multiplexer switch test complete.")
    finally:
        mux.cleanup()


def test_ad5260_reset(pins, hold_time, no_prompt):
    _, AD5260Controller, _ = import_gpio_controller()
    pot = AD5260Controller(pins=pins)

    print("\n=== AD5260 reset test ===")
    print(f"Pins [CLK, SDO, SDI, PR*, CS*]: {pins}")
    print(f"Watch PR* / reset pin GPIO{pins[3]}. It should pulse LOW briefly.")

    try:
        wait_for_scope("Prepare oscilloscope trigger on PR* falling edge.", hold_time, no_prompt)
        pot.reset()
        wait_for_scope("Reset pulse was sent. Check PR* low pulse on the oscilloscope.", hold_time, no_prompt)
    finally:
        pot.cleanup()


def test_ad5260_spi_codes(pins, codes):
    _, AD5260Controller, _ = import_gpio_controller()
    pot = AD5260Controller(pins=pins)

    print("\n=== AD5260 SPI code test ===")
    print(f"Pins [CLK, SDO, SDI, PR*, CS*]: {pins}")
    print("Recommended oscilloscope probes: SCLK, MOSI/SDI, CS*, and optionally wiper voltage.")
    print("Expected SPI sequence: CS* LOW, 8 clock pulses/data bits, CS* HIGH.")
    print("Press Enter to send each code.\n")

    try:
        for code in codes:
            expected_voltage = pot.calculate_voltage(code)
            print(f"Sending code {code}. Expected ideal wiper voltage: {expected_voltage:.3f} V")
            pot.set_resistance(code)
            input("Check SPI frame and wiper voltage. Press Enter for next code...")
    finally:
        pot.cleanup()


def test_ad5260_voltage_sweep(pins, start_v, end_v, steps, duration):
    _, AD5260Controller, _ = import_gpio_controller()
    pot = AD5260Controller(pins=pins)

    print("\n=== AD5260 voltage sweep test ===")
    print(f"Sweeping from {start_v} V to {end_v} V in {steps} steps.")
    print("Measure the AD5260 wiper output. It should move stepwise through the requested voltage range.")

    try:
        results = pot.voltage_sweep(start_v=start_v, end_v=end_v, steps=steps, duration=duration)
        print("\nSweep results:")
        for result in results:
            print(
                f"step={result['step']:03d} "
                f"code={result['code']:03d} "
                f"target={result['target_v']:.3f} V "
                f"calculated={result['actual_v']:.3f} V"
            )
    finally:
        pot.cleanup()


def test_max31865(cs_pin, wires, rtd_nominal, ref_resistor, samples, interval):
    _, _, MAX31865Controller = import_gpio_controller()
    sensor = MAX31865Controller(
        cs_pin=cs_pin,
        wires=wires,
        rtd_nominal=rtd_nominal,
        ref_resistor=ref_resistor,
    )

    print("\n=== MAX31865 readout test ===")
    print(f"CS pin: GPIO{cs_pin}, wires={wires}, RTD nominal={rtd_nominal}, reference resistor={ref_resistor}")
    print("Readings should be stable. If faults are printed, check wiring and sensor configuration.")

    for sample in range(1, samples + 1):
        temperature_c = sensor.read_temperature_c()
        temperature_k = temperature_c + 273.15
        resistance = sensor.read_resistance()
        print(
            f"sample={sample:03d} "
            f"temperature={temperature_c:.3f} C / {temperature_k:.3f} K "
            f"resistance={resistance:.3f} ohm"
        )
        time.sleep(interval)


def parse_args():
    parser = argparse.ArgumentParser(description="Manual hardware tests for GPIOController.py")
    parser.add_argument(
        "test",
        choices=["mux", "mux-pins", "mux-switches", "spi-pins", "ad5260", "ad5260-reset", "ad5260-spi", "ad5260-sweep", "max31865", "all"],
        help="Test case to run.",
    )
    parser.add_argument("--mux-pins", type=int, nargs=4, default=[17, 18, 22, 27], help="Multiplexer BCM pins.")
    parser.add_argument("--spi-pins", type=int, nargs="+", default=[10, 9, 11, 8, 7], help="SPI BCM pins to test as plain GPIO outputs.")

    parser.add_argument("--ad-pins", type=int, nargs=5, default=[14, 9, 10, 25, 8], help="AD5260 pins: CLK SDO SDI PR CS.")
    parser.add_argument("--codes", type=int, nargs="+", default=[0, 64, 128, 192, 255], help="AD5260 codes to send.")
    parser.add_argument("--start-v", type=float, default=0.0, help="AD5260 sweep start voltage.")
    parser.add_argument("--end-v", type=float, default=10.0, help="AD5260 sweep end voltage.")
    parser.add_argument("--steps", type=int, default=5, help="AD5260 sweep steps.")
    parser.add_argument("--duration", type=float, default=1.0, help="AD5260 sweep duration per step.")

    parser.add_argument("--max-cs-pin", type=int, default=5, help="MAX31865 chip-select BCM pin.")
    parser.add_argument("--max-wires", type=int, default=3, choices=[2, 3, 4], help="MAX31865 RTD wire count.")
    parser.add_argument("--rtd-nominal", type=float, default=1000.0, help="RTD nominal resistance.")
    parser.add_argument("--ref-resistor", type=float, default=4300.0, help="MAX31865 reference resistor.")
    parser.add_argument("--samples", type=int, default=10, help="MAX31865 samples to read.")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between MAX31865 samples.")

    return parser.parse_args()


def main():
    args = parse_args()

    if args.test in ("mux", "mux-pins", "all"):
        test_pins(args.mux_pins, label="Multiplexer")

    if args.test in ("mux", "mux-switches", "all"):
        test_multiplexer_switches(args.mux_pins)

    if args.test in ("spi-pins",):
        test_pins(args.spi_pins, label="SPI")

    if args.test in ("ad5260", "ad5260-reset", "all"):
        test_ad5260_reset(args.ad_pins, args.hold_time, args.no_prompt)

    if args.test in ("ad5260", "ad5260-spi", "all"):
        test_ad5260_spi_codes(args.ad_pins, args.codes)

    if args.test in ("ad5260", "ad5260-sweep", "all"):
        test_ad5260_voltage_sweep(args.ad_pins, args.start_v, args.end_v, args.steps, args.duration)

    if args.test in ("max31865", "all"):
        test_max31865(
            cs_pin=args.max_cs_pin,
            wires=args.max_wires,
            rtd_nominal=args.rtd_nominal,
            ref_resistor=args.ref_resistor,
            samples=args.samples,
            interval=args.interval,
        )


if __name__ == "__main__":
    main()
