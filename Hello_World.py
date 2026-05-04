import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton,
    QGridLayout, QLabel, QHBoxLayout,
    QVBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt


SIZE = 10
SHIP_COUNT = 10


class SeaBattle(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Морской бой (2 поля)")
        self.setFixedSize(900, 600)

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.info = QLabel()
        self.info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.info)

        self.fields_layout = QHBoxLayout()
        self.main_layout.addLayout(self.fields_layout)

        # --- поля ---
        self.p1_grid = QGridLayout()
        self.p2_grid = QGridLayout()

        self.fields_layout.addLayout(self.p1_grid)
        self.fields_layout.addLayout(self.p2_grid)

        # кнопки
        self.p1_buttons = {}
        self.p2_buttons = {}

        # корабли
        self.p1_ships = set()
        self.p2_ships = set()

        # попадания
        self.p1_hits = set()
        self.p2_hits = set()

        self.current_player = 1

        self.init_ships()
        self.init_boards()
        self.update_info()

    # ---------------- INIT ----------------
    def init_ships(self):
        while len(self.p1_ships) < SHIP_COUNT:
            self.p1_ships.add((self.rand(), self.rand()))

        while len(self.p2_ships) < SHIP_COUNT:
            self.p2_ships.add((self.rand(), self.rand()))

    def rand(self):
        import random
        return random.randint(0, SIZE - 1)

    def init_boards(self):
        # поле игрока 1 (стреляет игрок 2)
        for x in range(SIZE):
            for y in range(SIZE):
                btn = QPushButton("")
                btn.setFixedSize(35, 35)
                btn.clicked.connect(lambda _, a=x, b=y: self.attack(1, a, b))
                self.p1_grid.addWidget(btn, x, y)
                self.p1_buttons[(x, y)] = btn

        # поле игрока 2 (стреляет игрок 1)
        for x in range(SIZE):
            for y in range(SIZE):
                btn = QPushButton("")
                btn.setFixedSize(35, 35)
                btn.clicked.connect(lambda _, a=x, b=y: self.attack(2, a, b))
                self.p2_grid.addWidget(btn, x, y)
                self.p2_buttons[(x, y)] = btn

    # ---------------- UI ----------------
    def update_info(self):
        self.info.setText(f"Ход игрока {self.current_player}")

    # ---------------- БОЙ ----------------
    def attack(self, target_player, x, y):
        if self.current_player != (1 if target_player == 2 else 2):
            return

        if target_player == 1:
            if (x, y) in self.p1_hits:
                return

            self.p1_hits.add((x, y))
            btn = self.p1_buttons[(x, y)]

            if (x, y) in self.p1_ships:
                btn.setText("X")
                btn.setStyleSheet("background-color: red")
            else:
                btn.setText("•")
                btn.setStyleSheet("background-color: lightblue")
                self.switch_turn()

        else:
            if (x, y) in self.p2_hits:
                return

            self.p2_hits.add((x, y))
            btn = self.p2_buttons[(x, y)]

            if (x, y) in self.p2_ships:
                btn.setText("X")
                btn.setStyleSheet("background-color: red")
            else:
                btn.setText("•")
                btn.setStyleSheet("background-color: lightblue")
                self.switch_turn()

        self.check_win()
        self.update_info()

    # ---------------- ХОД ----------------
    def switch_turn(self):
        self.current_player = 2 if self.current_player == 1 else 1

    # ---------------- ПОБЕДА ----------------
    def check_win(self):
        if self.p1_ships <= self.p2_hits:
            QMessageBox.information(self, "Победа", "Игрок 2 победил!")
            self.reset()

        if self.p2_ships <= self.p1_hits:
            QMessageBox.information(self, "Победа", "Игрок 1 победил!")
            self.reset()

    # ---------------- RESET ----------------
    def reset(self):
        self.p1_ships.clear()
        self.p2_ships.clear()
        self.p1_hits.clear()
        self.p2_hits.clear()
        self.current_player = 1

        for btn in self.p1_buttons.values():
            btn.setText("")
            btn.setStyleSheet("")

        for btn in self.p2_buttons.values():
            btn.setText("")
            btn.setStyleSheet("")

        self.init_ships()
        self.update_info()


# ---------------- RUN ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SeaBattle()
    window.show()
    sys.exit(app.exec())