import flet as ft
from system_state import GameState  

def main(page: ft.Page):

    page.title = "Spinning Disk"
    page.window_width = 900
    page.window_height = 600
    page.theme_mode = ft.ThemeMode.DARK

    game = GameState()

    throws_text = ft.Text(size=22)
    last_score_text = ft.Text(size=22)
    total_score_text = ft.Text(size=24, weight=ft.FontWeight.BOLD)

    def update_ui():
        throws_text.value = f"Lanzamientos válidos: {game.throws}"
        last_score_text.value = f"Puntaje obtenido en el último lanzamiento: {game.last_score}"
        total_score_text.value = f"Puntaje total acumulado: {game.total_score}"
        page.update()

    def start_clicked(e):
        game.reset()
        game.running = True
        print("START presionado")
        update_ui()

    def stop_clicked(e):
        game.running = False
        print("STOP presionado")

    # SOLO PARA PRUEBA (simular lanzamiento)
    def simulate_throw(e):
        if game.running and game.throws < 3:
            import random
            score = random.randint(10, 100)
            game.add_score(score)
            update_ui()

    start_button = ft.Button(
        "START",
        width=150,
        height=50,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.GREEN,
            color=ft.Colors.WHITE
        ),
        on_click=start_clicked
    )

    stop_button = ft.Button(
        "STOP",
        width=150,
        height=50,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE
        ),
        on_click=stop_clicked
    )

    test_button = ft.Button(
        "Simular Lanzamiento",
        on_click=simulate_throw
    )

    page.add(
        ft.Column(
            [
                ft.Text("Spinning Disk", size=30, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                throws_text,
                last_score_text,
                total_score_text,
                ft.Divider(),
                ft.Row([start_button, stop_button], alignment=ft.MainAxisAlignment.CENTER),
                test_button
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20
        )
    )

    update_ui()

ft.run(main)
