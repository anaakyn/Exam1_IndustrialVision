class GameState:

    def __init__(self):
        self.running = False
        self.reset()

    def reset(self):
        self.throws = 0
        self.last_score = 0
        self.total_score = 0

    def add_score(self, points):
        self.throws += 1
        self.last_score = points
        self.total_score += points