import sys
import random

from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
    QStackedWidget,
    QGraphicsOpacityEffect
)

SIZE = 10
TURN_TIME = 60
PLAYERS = (1, 2)

SHIP_TYPES = {4: 1, 3: 2, 2: 3, 1: 4}

SHIP_NAMES = {
    1: "Однопалубный",
    2: "Двухпалубный",
    3: "Трёхпалубный",
    4: "Четырёхпалубный"
}

DARK_STYLE = "QWidget { background-color: #1e1e1e; color: #e0e0e0; }"
TITLE_STYLE = "font-size: 22px; font-weight: bold;"

CELL_EMPTY = "background-color: white; border: 1px solid black;"
CELL_SHIP = "background-color: gray; border: 1px solid black;"
CELL_VALID = "background-color: lightgreen; border: 1px solid black;"
CELL_INVALID = "background-color: pink; border: 1px solid black;"
CELL_HIT = "background-color: red; border: 1px solid black;"
CELL_MISS = "background-color: #1B56FD; color: #FFFCFB; border: 1px solid black;"

SHIP_BUTTON_STYLE = """
    QPushButton {{
        background-color: {};
        color: #062743;
        font-size: 16px;
        text-align: left;
        padding-left: 15px;
    }}
"""

BATTLE_PANEL_STYLE = """
    QWidget {
        border: 1px solid gray;
        background: #1e1e1e;
    }
"""

TIMER_STYLE = """
    QLabel {
        border: 2px solid black;
        font-size: 28px;
        font-weight: bold;
        background: #1e1e1e;
    }
"""

WIN_BUTTON_STYLE = """
    QPushButton {
        background-color: #d0d0d0;
        color: #062743;
        font-size: 20px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #1DCD9F;
    }
"""


def make_label(text, style="", center=True):

    label = QLabel(text)
    label.setStyleSheet(style)

    if center:
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    return label


def neighbours(x, y):
    """Клетка и все соседние с ней клетки в пределах поля."""

    return [
        (x + dx, y + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if 0 <= x + dx < SIZE and 0 <= y + dy < SIZE
    ]


class CellButton(QPushButton):

    def __init__(self, x, y, game):
        super().__init__()

        self.cell = (x, y)
        self.game = game

        self.setFixedSize(game.cell_size, game.cell_size)
        self.setStyleSheet(CELL_EMPTY)

    def enterEvent(self, event):
        self.game.hover_cell(*self.cell)

    def leaveEvent(self, event):
        self.game.clear_preview()

    def mousePressEvent(self, event):
        self.game.cell_clicked(*self.cell)


class ShipButton(QPushButton):

    def __init__(self, size_ship, game):
        super().__init__()

        self.size_ship = size_ship

        self.setFixedHeight(60)
        self.set_selected(False)

        self.clicked.connect(lambda: game.select_ship(self))

    def update_text(self, left):
        self.setText(f"{left} шт. | {SHIP_NAMES[self.size_ship]}")

    def set_selected(self, selected):
        self.setStyleSheet(
            SHIP_BUTTON_STYLE.format("#1DCD9F" if selected else "#d0d0d0")
        )


class SeaBattle(QWidget):

    game_over = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.cell_size = 40

        # всё состояние хранится по номеру игрока 1 или 2
        self.buttons = {p: {} for p in PLAYERS}
        self.ships = {p: set() for p in PLAYERS}
        self.ship_list = {p: [] for p in PLAYERS}
        self.hits = {p: set() for p in PLAYERS}

        self.phase = "placement"
        self.current_player = 1
        self.selected_size = None
        self.horizontal = True
        self.preview_buttons = []

        self.turn_time = TURN_TIME
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

        self.init_ui()

    @property
    def enemy(self):
        return 2 if self.current_player == 1 else 1

    def init_ui(self):

        main = QVBoxLayout(self)

        self.info = make_label("", "font-size: 24px; padding: 15px;")
        main.addWidget(self.info)
        main.addStretch(1)

        # 3 колонки пустая поля панель кораблей
        body = QGridLayout()
        body.setColumnStretch(0, 1)
        body.setColumnStretch(2, 1)
        main.addLayout(body)
        main.addStretch(1)

        self.bottom_spacer = QWidget()
        self.bottom_spacer.setFixedHeight(self.info.sizeHint().height())
        main.addWidget(self.bottom_spacer)

        self.battle_panel = self.create_battle_panel()
        self.battle_panel.hide()
        main.addWidget(self.battle_panel)

        self.fields_wrapper = QWidget()

        self.fields_layout = QHBoxLayout(self.fields_wrapper)
        self.fields_layout.setSpacing(40)
        self.fields_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fields_layout.setContentsMargins(0, 0, 0, 0)

        for player in PLAYERS:
            self.fields_layout.addWidget(self.create_field(player))

        self.ships_container = self.create_ships_panel()

        body.addWidget(self.fields_wrapper, 0, 1)

        body.addWidget(self.ships_container, 0, 2, Qt.AlignmentFlag.AlignRight)

        self.update_info()
        self.update_cell_size()

    def create_field(self, player):

        container = QWidget()
        layout = QVBoxLayout(container)

        layout.addWidget(make_label(f"Игрок {player}", TITLE_STYLE))

        grid = QGridLayout()
        grid.setSpacing(2)
        grid.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(grid)

        for x in range(SIZE):
            for y in range(SIZE):

                btn = CellButton(x, y, self)
                grid.addWidget(btn, x, y)
                self.buttons[player][(x, y)] = btn

        return container

    def create_ships_panel(self):

        panel = QWidget()
        panel.setFixedWidth(260)

        layout = QVBoxLayout(panel)
        layout.addWidget(make_label("Корабли", TITLE_STYLE))

        self.ship_buttons = {}

        for size in sorted(SHIP_TYPES, reverse=True):

            self.ship_buttons[size] = ShipButton(size, self)
            layout.addWidget(self.ship_buttons[size])

        layout.addWidget(
            make_label("\nR - повернуть корабль", "font-size: 18px;", center=False)
        )
        layout.addStretch()

        self.reset_ship_panel()

        return panel

    def create_battle_panel(self):

        panel = QWidget()
        panel.setStyleSheet(BATTLE_PANEL_STYLE)

        layout = QHBoxLayout(panel)

        left_panel = QWidget()
        left_layout = QHBoxLayout(left_panel)

        random_shot_btn = QPushButton("Случайный выстрел")
        random_shot_btn.setFixedSize(180, 50)
        random_shot_btn.clicked.connect(self.random_shot)
        left_layout.addWidget(random_shot_btn)

        left_layout.addWidget(make_label("Осталось\nвремени:"))

        self.timer_label = make_label("01:00", TIMER_STYLE)
        self.timer_label.setFixedSize(120, 60)
        left_layout.addWidget(self.timer_label)

        layout.addWidget(left_panel, 2)

        self.fleet_labels = {}

        for player in PLAYERS:

            group = QWidget()
            group_layout = QVBoxLayout(group)

            group_layout.addWidget(make_label(f"Флот {player} игрока"))

            self.fleet_labels[player] = make_label("", "font-size: 18px;")
            group_layout.addWidget(self.fleet_labels[player])

            layout.addWidget(group)

        return panel

    def animate(self, target, prop, start, end, duration, curve):

        anim = QPropertyAnimation(target, prop, self)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(curve)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        return anim

    def resizeEvent(self, event):
        self.update_cell_size()
        super().resizeEvent(event)

    def update_cell_size(self):

        size = int(min(self.width(), self.height()) / (SIZE * 2.5))
        self.cell_size = max(20, min(60, size))

        for buttons in self.buttons.values():
            for btn in buttons.values():
                btn.setFixedSize(self.cell_size, self.cell_size)

    def update_info(self):

        if self.phase == "placement":

            direction = "Горизонтально" if self.horizontal else "Вертикально"

            self.info.setText(
                f"Игрок {self.current_player} расставляет корабли | {direction}"
            )

        else:
            self.info.setText(f"Ход игрока {self.current_player}")

    def keyPressEvent(self, event):

        if event.key() == Qt.Key.Key_R:

            self.horizontal = not self.horizontal
            self.update_info()

    def repaint_ships(self):

        for player, buttons in self.buttons.items():
            for cell, btn in buttons.items():

                text, style = self.cell_look(player, cell)

                btn.setText(text)
                btn.setStyleSheet(style)

    def cell_look(self, player, cell):

        if self.phase == "placement":

            if player == self.current_player and cell in self.ships[player]:
                return "", CELL_SHIP

            return "", CELL_EMPTY

        if cell not in self.hits[player]:
            return "", CELL_EMPTY

        if cell in self.ships[player]:
            return "X", CELL_HIT

        return "•", CELL_MISS

    def cell_clicked(self, x, y):

        if self.phase == "placement":
            self.place_ship(x, y)
        else:
            self.attack(x, y)

    def reset_ship_panel(self):

        self.remaining_ships = SHIP_TYPES.copy()

        for size, btn in self.ship_buttons.items():

            btn.setEnabled(True)
            btn.set_selected(False)
            btn.update_text(self.remaining_ships[size])

    def select_ship(self, button):

        self.selected_size = button.size_ship

        for btn in self.ship_buttons.values():
            btn.set_selected(btn is button)

    def get_ship_cells(self, x, y, size):

        if self.horizontal:
            return [(x, y + i) for i in range(size)]

        return [(x + i, y) for i in range(size)]

    def can_place(self, cells):

        field = self.ships[self.current_player]

        for x, y in cells:

            if not (0 <= x < SIZE and 0 <= y < SIZE):
                return False

            if any(cell in field for cell in neighbours(x, y)):
                return False

        return True

    def hover_cell(self, x, y):

        if self.phase != "placement" or self.selected_size is None:
            return

        self.clear_preview()

        cells = self.get_ship_cells(x, y, self.selected_size)
        style = CELL_VALID if self.can_place(cells) else CELL_INVALID
        buttons = self.buttons[self.current_player]

        for cell in cells:

            if cell in buttons:

                buttons[cell].setStyleSheet(style)
                self.preview_buttons.append(buttons[cell])

    def clear_preview(self):

        self.preview_buttons.clear()
        self.repaint_ships()

    def place_ship(self, x, y):

        size = self.selected_size

        if size is None or self.remaining_ships[size] <= 0:
            return

        cells = self.get_ship_cells(x, y, size)

        if not self.can_place(cells):
            return

        self.ships[self.current_player].update(cells)
        self.ship_list[self.current_player].append(set(cells))

        self.remaining_ships[size] -= 1
        self.ship_buttons[size].update_text(self.remaining_ships[size])
        self.ship_buttons[size].setEnabled(self.remaining_ships[size] > 0)

        self.clear_preview()

        if any(self.remaining_ships.values()):
            return

        self.selected_size = None

        if self.current_player == 1:

            QMessageBox.information(
                self,
                "Игрок 2",
                "Теперь игрок 2 расставляет корабли"
            )

            self.current_player = 2
            self.reset_ship_panel()
            self.update_info()
            self.repaint_ships()

        else:

            QMessageBox.information(self, "Бой", "Все корабли расставлены!")

            self.start_battle()

    def start_battle(self):

        effect = QGraphicsOpacityEffect(self.ships_container)
        self.ships_container.setGraphicsEffect(effect)

        anim = self.animate(
            effect, b"opacity", 1.0, 0.0, 700, QEasingCurve.Type.InOutQuad
        )
        anim.finished.connect(self.on_ships_panel_hidden)

    def on_ships_panel_hidden(self):

        self.ships_container.hide()
        self.bottom_spacer.hide()
        self.phase = "battle"

        self.current_player = random.choice(PLAYERS)

        self.battle_panel.show()

        self.animate(
            self.fields_layout, b"spacing", 40, 140, 900,
            QEasingCurve.Type.InOutCubic
        )

        self.start_turn_timer()
        self.update_fleet_info()
        self.update_info()
        self.update_field_access()
        self.repaint_ships()

    def start_turn_timer(self):

        self.turn_time = TURN_TIME
        self.update_timer_label()
        self.timer.start(1000)

    def update_timer(self):

        self.turn_time -= 1
        self.update_timer_label()

        if self.turn_time <= 0:
            self.switch_turn()

    def update_timer_label(self):

        minutes, seconds = divmod(self.turn_time, 60)
        self.timer_label.setText(f"{minutes:02}:{seconds:02}")

    def update_fleet_info(self):

        for player, label in self.fleet_labels.items():

            ships = sorted(self.ship_list[player], key=len, reverse=True)

            label.setText(" ".join(
                ("⊠" if ship <= self.hits[player] else "■") * len(ship)
                for ship in ships
            ))

    def update_field_access(self):

        if self.phase == "placement":
            return

        for player, buttons in self.buttons.items():
            for btn in buttons.values():
                btn.setEnabled(player != self.current_player)

    def switch_turn(self):

        self.current_player = self.enemy

        self.update_field_access()
        self.start_turn_timer()
        self.update_fleet_info()
        self.update_info()

    def random_shot(self):

        if self.phase != "battle":
            return

        hits = self.hits[self.enemy]
        available = [cell for cell in self.buttons[self.enemy] if cell not in hits]

        if available:
            self.attack(*random.choice(available))

    def attack(self, x, y):

        if self.phase != "battle":
            return

        shooter = self.current_player
        enemy = self.enemy
        cell = (x, y)
        hits = self.hits[enemy]

        if cell in hits:
            return

        hits.add(cell)

        if cell in self.ships[enemy]:

            ship = next(s for s in self.ship_list[enemy] if cell in s)

            if ship <= hits:
                for sx, sy in ship:
                    hits.update(c for c in neighbours(sx, sy) if c not in ship)

        else:
            self.switch_turn()

        if self.ships[enemy] <= hits:
            self.finish_game(shooter)
            return

        self.update_fleet_info()
        self.repaint_ships()
        self.update_info()

    def finish_game(self, winner):

        self.phase = "finished"
        self.timer.stop()
        self.game_over.emit(winner)


class WinScreen(QWidget):

    restart_clicked = pyqtSignal()
    exit_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()

        main = QVBoxLayout(self)
        main.addStretch(1)

        self.winner_label = make_label(
            "", "font-size: 48px; font-weight: bold; color: #1DCD9F;"
        )
        main.addWidget(self.winner_label)
        main.addSpacing(40)

        buttons = QHBoxLayout()
        buttons.setSpacing(30)
        buttons.addStretch(1)

        for text, signal in (
            ("Начать заново", self.restart_clicked),
            ("Выход", self.exit_clicked)
        ):

            btn = QPushButton(text)
            btn.setFixedSize(220, 60)
            btn.setStyleSheet(WIN_BUTTON_STYLE)
            btn.clicked.connect(signal)

            buttons.addWidget(btn)

        buttons.addStretch(1)

        main.addLayout(buttons)
        main.addStretch(1)

    def set_winner(self, player):
        self.winner_label.setText(f"Победил игрок {player}!")


class MainWindow(QStackedWidget):

    def __init__(self):
        super().__init__()

        self.setStyleSheet(DARK_STYLE)
        self.setWindowTitle("Морской бой")

        self.game = None

        self.win_screen = WinScreen()
        self.win_screen.restart_clicked.connect(self.start_new_game)
        self.win_screen.exit_clicked.connect(QApplication.quit)
        self.addWidget(self.win_screen)

        self.start_new_game()

    def start_new_game(self):

        if self.game is not None:
            self.removeWidget(self.game)
            self.game.deleteLater()

        self.game = SeaBattle()
        self.game.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.game.game_over.connect(self.show_winner)

        self.addWidget(self.game)
        self.setCurrentWidget(self.game)
        self.game.setFocus()

    def show_winner(self, player):

        self.win_screen.set_winner(player)
        self.setCurrentWidget(self.win_screen)


if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())