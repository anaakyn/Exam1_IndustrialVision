from config import PUNTUACIONES

MAX_THROWS = 3


class GameManager:

    def __init__(self, arduino):
        self.puntaje_total = 0
        self.throws        = 0
        self.last_score    = 0
        self.arduino       = arduino

    def reset(self):
        self.puntaje_total = 0
        self.throws        = 0
        self.last_score    = 0
        print("Reset game")

    def registrar_evento(self, sector):
        if self.throws >= MAX_THROWS:
            return

        puntos = PUNTUACIONES.get(sector, 0)

        self.throws        += 1
        self.last_score     = puntos
        self.puntaje_total += puntos

        print(f"Pelota confirmada en {sector} +{puntos}pts | Total: {self.puntaje_total} ({self.throws}/{MAX_THROWS})")

        mensaje = f"{self.throws},{self.last_score},{self.puntaje_total}\n"
        self.arduino.write(mensaje.encode())