import serial

ser = serial.Serial('/dev/ttyUSB0', baudrate = 9600, timeout = 1)