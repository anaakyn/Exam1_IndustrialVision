import serial
import time


class ArduinoNanoController:

    def __init__(self, port="COM9", baud=9600):
        self.port = port
        self.baud = baud
        self.serial = None
        self.connect()

    def connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baud)
            time.sleep(2)  # Esperar reinicio del Nano
            print(f"[Serial] Conectado a {self.port}")
        except Exception as e:
            print(f"[Serial] Error conectando: {e}")

    def send_scores(self, throws, last, total):
        if self.serial and self.serial.is_open:
            msg = f"{throws},{last},{total}\n"
            self.serial.write(msg.encode())

    def send_start(self):
        if self.serial and self.serial.is_open:
            self.serial.write(b"START\n")

    def send_stop(self):
        if self.serial and self.serial.is_open:
            self.serial.write(b"STOP\n")

    def close(self):
        if self.serial and self.serial.is_open:
            self.serial.close()