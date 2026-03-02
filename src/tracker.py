import time
from config import TIEMPO_CONFIRMACION


class TrackerPelota:

    _id_counter = 0

    def __init__(self, cx, cy, sector, puntos):
        TrackerPelota._id_counter += 1
        self.id               = TrackerPelota._id_counter
        self.cx               = cx
        self.cy               = cy
        self.sector           = sector
        self.puntos           = puntos
        self.tiempo_inicio    = time.time()
        self.ultima_vez_vista = time.time()
        self.confirmada       = False
        self.puntos_sumados   = 0

    def actualizar(self, cx, cy, sector, puntos):
        self.cx               = cx
        self.cy               = cy
        self.sector           = sector
        self.puntos           = puntos
        self.ultima_vez_vista = time.time()

    def tiempo_visible(self):
        return time.time() - self.tiempo_inicio

    def ausencia(self):
        return time.time() - self.ultima_vez_vista

    def progreso(self):
        return min(self.tiempo_visible() / TIEMPO_CONFIRMACION, 1.0)