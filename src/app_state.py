class AppState:
    def __init__(self, rangos_hsv_default):
        self.estado = "MENU_INICIAL"
        self.color_seleccionado = ""
        self.frame_hsv_global = None
        self.rangos_hsv = rangos_hsv_default
        self.drag_inicio = None
        self.drag_actual = None
        self.disco_cx = 0
        self.disco_cy = 0
        self.disco_radio = 0
        self.disco_listo = False