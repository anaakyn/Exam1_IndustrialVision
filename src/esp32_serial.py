import serial
import time

class ESP32Controller:
    def __init__(self, port="COM10", baudrate=115200):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)

    def send_scores(self, throws, last_score, total):
        message = f"{throws},{last_score},{total}\n"
        self.ser.write(message.encode())

    def send_start(self):
        self.ser.write(b"START\n")

    def send_stop(self):
        self.ser.write(b"STOP\n")
