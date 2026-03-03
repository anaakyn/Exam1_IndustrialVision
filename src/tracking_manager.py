import numpy as np

from config import DISTANCIA_MISMA_PELOTA, TIEMPO_OLVIDO, MAX_PELOTAS, TIEMPO_CONFIRMACION
from tracker import TrackerPelota


class TrackingManager:

    def __init__(self):
        self.trackers = []

    def reset(self):
        self.trackers = []
        TrackerPelota._id_counter = 0
        print("Reset tracking")

    def actualizar(self, detecciones):
        """
        Devuelve una lista de eventos confirmados:
        [
            {"sector": "Azul", "tracker_id": 3},
            ...
        ]
        """
        eventos_confirmados = []

        trackers_actualizados = set()
        detecciones_asignadas = set()

        if self.trackers and detecciones:
            matriz = []
            for det in detecciones:
                fila = []
                for t in self.trackers:
                    d = np.sqrt((det["cx"] - t.cx) ** 2 + (det["cy"] - t.cy) ** 2)
                    fila.append(d)
                matriz.append(fila)

            while True:
                min_dist = float('inf')
                best_i = best_j = -1

                for i, fila in enumerate(matriz):
                    if i in detecciones_asignadas:
                        continue
                    for j, d in enumerate(fila):
                        t = self.trackers[j]
                        if t.id in trackers_actualizados:
                            continue
                        if d < min_dist:
                            min_dist = d
                            best_i, best_j = i, j

                if best_i == -1 or min_dist > DISTANCIA_MISMA_PELOTA:
                    break

                det = detecciones[best_i]
                t   = self.trackers[best_j]

                t.actualizar(det["cx"], det["cy"], det["color_sector"], None)

                trackers_actualizados.add(t.id)
                detecciones_asignadas.add(best_i)

                # Confirmación temporal
                if not t.confirmada and t.tiempo_visible() >= TIEMPO_CONFIRMACION:
                    t.confirmada = True

                    eventos_confirmados.append({
                        "tracker_id": t.id,
                        "sector": det["color_sector"]
                    })

        # Crear nuevos trackers
        for i, det in enumerate(detecciones):
            if i not in detecciones_asignadas and len(self.trackers) < MAX_PELOTAS:
                nuevo = TrackerPelota(det["cx"], det["cy"], det["color_sector"], None)
                self.trackers.append(nuevo)
                print(f"Nueva pelota en {det['color_sector']}")

        # Eliminar trackers viejos
        self.trackers = [
            t for t in self.trackers
            if t.ausencia() < TIEMPO_OLVIDO
        ]

        return eventos_confirmados