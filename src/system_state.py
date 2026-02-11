class GameState:
    def __init__(self):
        self.throws = 0
        self.last_score = 0
        self.total_score = 0
        self.running = False

    def reset(self):
        self.throws = 0
        self.last_score = 0
        self.total_score = 0
        self.running = False

    def add_score(self, score):
        self.last_score = score
        self.total_score += score
        self.throws += 1
