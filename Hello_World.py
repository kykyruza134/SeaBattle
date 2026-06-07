import sys
import random
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    QRect,
    QTimer,
    Qt,
    QParallelAnimationGroup
)
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox
)
SIZE = 10

# количество кораблей
SHIP_TYPES = {
    4: 1,
    3: 2,
    2: 3,
    1: 4
}


# =========================================================
# КЛЕТКА
# =========================================================

class CellButton(QPushButton):

    def __init__(self, x, y, parent):
        super().__init__()

        self.x = x
        self.y = y
        self.parent_window = parent

        self.setFixedSize(self.parent_window.cell_size, self.parent_window.cell_size)
        self.setSizePolicy(
            self.sizePolicy().Policy.Fixed,
            self.sizePolicy().Policy.Fixed
        )

        self.ships_layout = QVBoxLayout()
        self.ships_opacity_effect = None
        self.ships_anim = None

        self.setStyleSheet("""
            background-color: white;
            border: 1px solid black;
        """)

        self.setMouseTracking(True)

    def enterEvent(self, event):
        self.parent_window.hover_cell(self.x, self.y)

    def leaveEvent(self, event):
        self.parent_window.clear_preview()

    def mousePressEvent(self, event):
        self.parent_window.cell_clicked(
        self.x,
        self.y
)


# =========================================================
# КНОПКА КОРАБЛЯ
# =========================================================

class ShipButton(QPushButton):

    def __init__(self, size_ship, parent):
        super().__init__()

        self.parent_window = parent
        self.size_ship = size_ship

        self.setFixedHeight(60)
        self.cell_size = 40

        self.update_text()

        self.setStyleSheet("""
            QPushButton {
                background-color: #d0d0d0;
                font-size: 16px;
                text-align: left;
                padding-left: 15px;
            }
        """)

    def update_text(self):

        names = {
            1: "Однопалубный",
            2: "Двухпалубный",
            3: "Трёхпалубный",
            4: "Четырёхпалубный"
        }

        left = self.parent_window.remaining_ships[self.size_ship]

        self.setText(
            f"{left} шт. | {names[self.size_ship]}"
        )

    def mousePressEvent(self, event):

        if self.parent_window.remaining_ships[self.size_ship] <= 0:
            return

        self.parent_window.select_ship(self)


# =========================================================
# ИГРА
# =========================================================

class SeaBattle(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Морской бой")

        # --- ВАЖНО: создаём ДО UI ---
        self.p1_buttons = {}
        self.p2_buttons = {}
        self.cell_size = 40

        self.p1_ships = set()
        self.p2_ships = set()

        self.p1_hits = set()
        self.p2_hits = set()

        self.remaining_ships = SHIP_TYPES.copy()


        self.phase = "placement"
        self.current_player = 1
        self.selected_size = None
        self.horizontal = True
        self.preview_buttons = []
        self.turn_time = 60
        self.timer = None

        self.init_ui()
        self.update_cell_size()

    def random_shot(self):

        if self.phase != "battle":
            return

        buttons = (
            self.p2_buttons
            if self.current_player == 1
            else self.p1_buttons
        )

        hits = (
            self.p2_hits
            if self.current_player == 1
            else self.p1_hits
        )

        available = [
            cell
            for cell in buttons.keys()
            if cell not in hits
        ]

        if not available:
            return

        x, y = random.choice(available)

        self.attack(x, y)

    def start_turn_timer(self):

        self.turn_time = 60

        if self.timer:
            self.timer.stop()

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update_timer
        )

        self.timer.start(1000)

        self.update_timer_label()

    def update_timer(self):

        self.turn_time -= 1

        self.update_timer_label()

        if self.turn_time <= 0:

            self.timer.stop()

            self.switch_turn()

            self.start_turn_timer()

    def update_timer_label(self):

        minutes = self.turn_time // 60
        seconds = self.turn_time % 60

        self.timer_label.setText(
            f"{minutes:02}:{seconds:02}"
        )

    def alive_ships_count(self, ships, hits):

        visited = set()
        alive = 0

        for cell in ships:

            if cell in visited:
              continue

            ship = self.get_ship_from_cell(
                cell,
                ships
            )

            visited.update(ship)

            if not ship.issubset(hits):
                alive += 1

        return alive

    def update_fleet_info(self):

        p1_left = len(self.p1_ships - self.p1_hits)
        p2_left = len(self.p2_ships - self.p2_hits)

        self.player_fleet_label.setText(
            "■ " * p1_left
        )

        self.enemy_fleet_label.setText(
            "■ " * p2_left
        )

    # =====================================================
    # ПОИСК УНИЧТОЖЕННОГО КОРАБЛЯ
    # =====================================================

    def get_ship_from_cell(self, cell, ships):

        visited = set()
        stack = [cell]

        while stack:
            c = stack.pop()

            if c in visited:
                continue

            visited.add(c)

            x, y = c

            for nx, ny in [
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1)
            ]:
                if (nx, ny) in ships and (nx, ny) not in visited:
                    stack.append((nx, ny))

        return visited


# =====================================================
# КОРАБЛЬ УНИЧТОЖЕН?
# =====================================================

    def is_ship_destroyed(self, ship_cells, hits):

        return ship_cells.issubset(hits)


# =====================================================
# ОТМЕТИТЬ КЛЕТКИ ВОКРУГ КОРАБЛЯ
# =====================================================

    def mark_around_ship(self, ship_cells, hits):

        for x, y in ship_cells:

            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):

                    nx = x + dx
                    ny = y + dy

                    if 0 <= nx < SIZE and 0 <= ny < SIZE:

                        if (nx, ny) not in ship_cells:
                            hits.add((nx, ny))

    def resizeEvent(self, event):
        self.update_cell_size()
        super().resizeEvent(event)

    def update_cell_size(self):
        if not hasattr(self, "p1_buttons") or not hasattr(self, "p2_buttons"):
            return

        available = min(self.width(), self.height())
        size = int(available / (SIZE * 2.5))
        size = max(20, min(60, size))

        self.cell_size = size

        for btn in list(self.p1_buttons.values()) + list(self.p2_buttons.values()):
            btn.setFixedSize(size, size)

    def animate_fields_to_center(self):

        start_spacing = 40
        end_spacing = 140

        self.spacing_anim = QPropertyAnimation(
            self.fields_layout,
            b"spacing"
        )

        self.spacing_anim.setDuration(900)

        self.spacing_anim.setStartValue(start_spacing)

        self.spacing_anim.setEndValue(end_spacing)

        self.spacing_anim.setEasingCurve(
        QEasingCurve.Type.InOutCubic
        )

        self.spacing_anim.start()
    # =====================================================
    # UI
    # =====================================================

    def init_ui(self):

        main = QVBoxLayout()
        self.setLayout(main)

        # ---------------- информация ----------------

        self.info = QLabel()
        self.info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.info.setStyleSheet("""
            font-size: 24px;
            padding: 15px;
        """)

        main.addWidget(self.info)
        main.addStretch(1)

        # =================================================
        # ОСНОВНОЙ КОНТЕЙНЕР
        # =================================================

        body = QHBoxLayout()
        main.addLayout(body)

        # =================================================
        # ПАНЕЛЬ БОЯ
        # =================================================

        self.battle_panel = QWidget()

        self.battle_panel.setStyleSheet("""
            QWidget {
                border: 1px solid gray;
                background: #1e1e1e;
            }
        """)

        battle_layout = QHBoxLayout(self.battle_panel)

        # =================================================
        # ЛЕВАЯ ЧАСТЬ
        # =================================================

        left_panel = QWidget()
        left_layout = QHBoxLayout(left_panel)

        self.random_shot_btn = QPushButton(
            "Случайный выстрел"
        )

        self.random_shot_btn.setFixedSize(180, 50)

        left_layout.addWidget(self.random_shot_btn)

        timer_text = QLabel("Осталось\nвремени:")

        timer_text.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        left_layout.addWidget(timer_text)

        self.timer_label = QLabel("01:00")

        self.timer_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.timer_label.setFixedSize(120, 60)

        self.timer_label.setStyleSheet("""
            QLabel {
            border: 2px solid black;
            font-size: 28px;
            font-weight: bold;
            background: #1e1e1e;
            }
        """)

        left_layout.addWidget(self.timer_label)

        battle_layout.addWidget(left_panel, 2)

        # =================================================
        # ВАШ ФЛОТ
        # =================================================

        player_group = QWidget()

        player_layout = QVBoxLayout(player_group)

        player_title = QLabel("Ваш флот")
        player_title.setAlignment(
        Qt.AlignmentFlag.AlignCenter
        )

        player_layout.addWidget(player_title)

        self.player_fleet_label = QLabel()

        self.player_fleet_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.player_fleet_label.setStyleSheet("""
            font-size: 18px;
        """)

        player_layout.addWidget(
            self.player_fleet_label
        )

        battle_layout.addWidget(player_group)

        # =================================================
        # ФЛОТ ПРОТИВНИКА
        # =================================================

        enemy_group = QWidget()

        enemy_layout = QVBoxLayout(enemy_group)

        enemy_title = QLabel("Флот противника")

        enemy_title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        enemy_layout.addWidget(enemy_title)

        self.enemy_fleet_label = QLabel()

        self.enemy_fleet_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.enemy_fleet_label.setStyleSheet("""
            font-size: 18px;
        """)

        enemy_layout.addWidget(
            self.enemy_fleet_label
        )

        battle_layout.addWidget(enemy_group)

        self.battle_panel.hide()

        main.addWidget(self.battle_panel)

        # =================================================
        # КОНТЕЙНЕР ДЛЯ ДВУХ ПОЛЕЙ
        # =================================================
        body.addStretch(1)

        self.fields_wrapper = QWidget()

        self.fields_layout = QHBoxLayout(self.fields_wrapper)

        self.fields_layout.setSpacing(40)

        self.fields_layout.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.fields_layout.setContentsMargins(
            0, 0, 0, 0
        )

        body.addWidget(self.fields_wrapper)
        body.addStretch(1)

        # =================================================
        # ПОЛЕ ИГРОКА 1
        # =================================================

        self.p1_container = QWidget()
        p1_layout = QVBoxLayout(self.p1_container)

        p1_title = QLabel("Игрок 1")
        p1_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        p1_title.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            """)

        p1_layout.addWidget(p1_title)

        self.p1_grid = QGridLayout()
        self.p1_grid.setSpacing(2)
        self.p1_grid.setContentsMargins(0, 0, 0, 0)
        p1_layout.addLayout(self.p1_grid)

        self.fields_layout.addWidget(self.p1_container)

        # =================================================
        # ПОЛЕ ИГРОКА 2
        # =================================================

        self.p2_container = QWidget()
        p2_layout = QVBoxLayout(self.p2_container)

        p2_title = QLabel("Игрок 2")
        p2_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        p2_title.setStyleSheet("""
        font-size: 22px;
        font-weight: bold;
        """)

        p2_layout.addWidget(p2_title)

        self.p2_grid = QGridLayout()
        self.p2_grid.setSpacing(2)
        self.p2_grid.setContentsMargins(0, 0, 0, 0)
        p2_layout.addLayout(self.p2_grid)

        self.fields_layout.addWidget(self.p2_container)

        # =================================================
        # ПАНЕЛЬ КОРАБЛЕЙ
        # =================================================

        ships_layout = QVBoxLayout()

        ships_title = QLabel("Корабли")
        ships_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ships_title.setStyleSheet("""
        font-size: 22px;
        font-weight: bold;
        """)

        ships_layout.addWidget(ships_title)

        self.ship_buttons = {}

        for size in [4, 3, 2, 1]:

            btn = ShipButton(size, self)

            ships_layout.addWidget(btn)

            self.ship_buttons[size] = btn

        rotate_info = QLabel("\nR - повернуть корабль")

        rotate_info.setStyleSheet("""
        font-size: 18px;
        """)

        ships_layout.addWidget(rotate_info)

        ships_layout.addStretch()

        self.ships_container = QWidget()
        self.ships_container.setLayout(ships_layout)

        self.ships_container.setFixedWidth(260)

        body.addWidget(self.ships_container)

        # =================================================
        # СОЗДАНИЕ КНОПОК
        # =================================================

        for x in range(SIZE):
            for y in range(SIZE):

                btn1 = CellButton(x, y, self)

                self.p1_grid.addWidget(btn1, x, y)

                self.p1_buttons[(x, y)] = btn1

                btn2 = CellButton(x, y, self)

                self.p2_grid.addWidget(btn2, x, y)

                self.p2_buttons[(x, y)] = btn2

        self.update_info()
        self.update_cell_size()
        self.random_shot_btn.clicked.connect(
            self.random_shot
        )

    # =====================================================
    # ИНФО
    # =====================================================

    def update_info(self):

        if self.phase == "placement":

            direction = "Горизонтально"

            if not self.horizontal:
                direction = "Вертикально"

            self.info.setText(
                f"Игрок {self.current_player} расставляет корабли | "
                f"{direction}"
            )

        else:

            self.info.setText(
                f"Ход игрока {self.current_player}"
            )

    # =====================================================
    # ВЫБОР КОРАБЛЯ
    # =====================================================

    def select_ship(self, button):

        self.selected_size = button.size_ship

        for btn in self.ship_buttons.values():

            btn.setStyleSheet("""
                QPushButton {
                    background-color: #d0d0d0;
                    font-size: 16px;
                    text-align: left;
                    padding-left: 15px;
                }
            """)

        button.setStyleSheet("""
            QPushButton {
                background-color: lightgreen;
                font-size: 16px;
                text-align: left;
                padding-left: 15px;
            }
        """)

    # =====================================================
    # ПОВОРОТ
    # =====================================================

    def keyPressEvent(self, event):

        if event.key() == Qt.Key.Key_R:

            self.horizontal = not self.horizontal

            self.update_info()

    # =====================================================
    # ПОЛУЧИТЬ ТЕКУЩЕЕ ПОЛЕ
    # =====================================================

    def current_field(self):

        if self.current_player == 1:
            return self.p1_ships

        return self.p2_ships

    def current_buttons(self):

        if self.current_player == 1:
            return self.p1_buttons

        return self.p2_buttons

    # =====================================================
    # PREVIEW
    # =====================================================

    def hover_cell(self, x, y):

        if self.phase != "placement":
            return

        if self.selected_size is None:
            return

        self.clear_preview()

        cells = self.get_ship_cells(x, y, self.selected_size)

        valid = self.can_place(cells)

        for cx, cy in cells:

            if 0 <= cx < SIZE and 0 <= cy < SIZE:

                btn = self.current_buttons()[(cx, cy)]

                if valid:

                    btn.setStyleSheet("""
                        background-color: lightgreen;
                        border: 1px solid black;
                    """)

                else:

                    btn.setStyleSheet("""
                        background-color: pink;
                        border: 1px solid black;
                    """)

                self.preview_buttons.append(btn)

    def clear_preview(self):

        for btn in self.preview_buttons:

            btn.setStyleSheet("""
                background-color: white;
                border: 1px solid black;
            """)

        self.preview_buttons.clear()

        self.repaint_ships()

    # =====================================================
    # КООРДИНАТЫ КОРАБЛЯ
    # =====================================================

    def get_ship_cells(self, x, y, size):

        cells = []

        for i in range(size):

            if self.horizontal:
                cells.append((x, y + i))
            else:
                cells.append((x + i, y))

        return cells

    # =====================================================
    # ПРОВЕРКА УСТАНОВКИ
    # =====================================================

    def can_place(self, cells):

        field = self.current_field()

        for x, y in cells:

            # выход за поле
            if x < 0 or y < 0:
                return False

            if x >= SIZE or y >= SIZE:
                return False

            # проверяем саму клетку и все соседние
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):

                    nx = x + dx
                    ny = y + dy

                    if (nx, ny) in field:
                        return False

        return True

    # =====================================================
    # КЛИК
    # =====================================================

    def cell_clicked(self, x, y):

        if self.phase == "placement":
            self.place_ship(x, y)
            self.update_field_access()
            return

        self.attack(x, y)

    # =====================================================
    # УСТАНОВКА КОРАБЛЯ
    # =====================================================

    def place_ship(self, x, y):

        if self.selected_size is None:
            return
        if self.remaining_ships[self.selected_size] <= 0:
            return

        cells = self.get_ship_cells(
            x,
            y,
            self.selected_size
        )

        if not self.can_place(cells):
            return

        field = self.current_field()

        for cell in cells:
            field.add(cell)

        self.remaining_ships[self.selected_size] -= 1

        self.ship_buttons[self.selected_size].update_text()

        if self.remaining_ships[self.selected_size] <= 0:

            self.ship_buttons[self.selected_size].setEnabled(False)

        self.repaint_ships()

        self.clear_preview()

        # все корабли расставлены
        if all(v == 0 for v in self.remaining_ships.values()):

            # игрок 2
            if self.current_player == 1:

                QMessageBox.information(
                    self,
                    "Игрок 2",
                    "Теперь игрок 2 расставляет корабли"
                )

                self.current_player = 2
                self.update_info()

                self.update_field_access()
                self.repaint_ships()

                self.remaining_ships = SHIP_TYPES.copy()

                for size in self.ship_buttons:

                    self.ship_buttons[size].setEnabled(True)
                    self.ship_buttons[size].update_text()

                self.selected_size = None

                self.repaint_ships()

            else:

                self.selected_size = None

                QMessageBox.information(
                    self,
                    "Бой",
                    "Все корабли расставлены!")

                self.hide_ships_panel_and_start_game()

                self.update_info()

    # =====================================================
    # ОЧИСТКА ПОЛЯ
    # =====================================================

    def clear_board_visual(self):

        for btn in self.p1_buttons.values():

            btn.setText("")

            btn.setStyleSheet("""
                background-color: white;
                border: 1px solid black;
            """)

        for btn in self.p2_buttons.values():

            btn.setText("")

            btn.setStyleSheet("""
                background-color: white;
                border: 1px solid black;
            """)

    # =====================================================
    # ПЕРЕРИСОВКА
    # =====================================================

    def repaint_ships(self):

        self.clear_board_visual()

        # ---------------- РАССТАНОВКА ----------------

        if self.phase == "placement":

            # игрок 1 видит свои корабли
            if self.current_player == 1:

                for x, y in self.p1_ships:

                    self.p1_buttons[(x, y)].setStyleSheet("""
                        background-color: gray;
                        border: 1px solid black;
                    """)

            # игрок 2 видит свои корабли
            else:

                for x, y in self.p2_ships:

                    self.p2_buttons[(x, y)].setStyleSheet("""
                        background-color: gray;
                        border: 1px solid black;
                    """)

        # ---------------- БОЙ ----------------

        else:

            for x, y in self.p1_hits:

                btn = self.p1_buttons[(x, y)]

                if (x, y) in self.p1_ships:

                    btn.setText("X")

                    btn.setStyleSheet("""
                        background-color: red;
                        border: 1px solid black;
                    """)

                else:

                    btn.setText("•")

                    btn.setStyleSheet("""
                        background-color: lightblue;
                        border: 1px solid black;
                    """)

            for x, y in self.p2_hits:

                btn = self.p2_buttons[(x, y)]

                if (x, y) in self.p2_ships:

                    btn.setText("X")

                    btn.setStyleSheet("""
                        background-color: red;
                        border: 1px solid black;
                    """)

                else:

                    btn.setText("•")

                    btn.setStyleSheet("""
                        background-color: lightblue;
                        border: 1px solid black;
                    """)

    # =====================================================
    # АТАКА
    # =====================================================

    def attack(self, x, y):

        if self.phase != "battle":
            return

        enemy = 2 if self.current_player == 1 else 1

        # ---------------- атака игрока 1 ----------------

        if enemy == 2:

            if (x, y) in self.p2_hits:
                return

            self.p2_hits.add((x, y))

            btn = self.p2_buttons[(x, y)]

            if (x, y) in self.p2_ships:

                ship = self.get_ship_from_cell(
                    (x, y),
                    self.p2_ships
                )

                if self.is_ship_destroyed(ship, self.p2_hits):
                    self.mark_around_ship(ship, self.p2_hits)

                btn.setText("X")

                btn.setStyleSheet("""
                    background-color: red;
                    border: 1px solid black;
                """)

            else:

                btn.setText("•")

                btn.setStyleSheet("""
                    background-color: lightblue;
                    border: 1px solid black;
                """)

                self.switch_turn()
                self.update_field_access()

        # ---------------- атака игрока 2 ----------------

        else:

            if (x, y) in self.p1_hits:
                return

            self.p1_hits.add((x, y))

            btn = self.p1_buttons[(x, y)]

            if (x, y) in self.p1_ships:

                ship = self.get_ship_from_cell(
                (x, y),
                self.p1_ships
                )

                if self.is_ship_destroyed(ship, self.p1_hits):
                    self.mark_around_ship(ship, self.p1_hits)

                btn.setText("X")

                btn.setStyleSheet("""
                background-color: red;
                border: 1px solid black;
                """)

            else:

                btn.setText("•")

                btn.setStyleSheet("""
                    background-color: lightblue;
                    border: 1px solid black;
                """)

                self.switch_turn()

        if self.check_win():
            return

        self.repaint_ships()

        self.update_info()

    # =====================================================
    # СМЕНА ХОДА
    # =====================================================

    def switch_turn(self):

        self.current_player = 2 if self.current_player == 1 else 1
        self.update_field_access()
        self.start_turn_timer()
        self.update_fleet_info()

    # =====================================================
    # ДОСТУП К ПОЛЯМ
    # =====================================================

    def update_field_access(self):

        if self.phase == "placement":
            return

        # игрок 1 стреляет по полю игрока 2
        if self.current_player == 1:

            for btn in self.p1_buttons.values():
                btn.setEnabled(False)

            for btn in self.p2_buttons.values():
                btn.setEnabled(True)

        # игрок 2 стреляет по полю игрока 1
        else:

            for btn in self.p2_buttons.values():
                btn.setEnabled(False)

            for btn in self.p1_buttons.values():
                btn.setEnabled(True)

    # =====================================================
    # ПОБЕДА
    # =====================================================

    def check_win(self):

        # игрок 1 победил
        if self.p2_ships.issubset(self.p2_hits):

            QMessageBox.information(
                self,
                "Победа",
                "Игрок 1 победил!"
            )

            QApplication.quit()
            return True

        # игрок 2 победил
        if self.p1_ships.issubset(self.p1_hits):

            QMessageBox.information(
                self,
                "Победа",
                "Игрок 2 победил!"
            )

            QApplication.quit()
            return True

        return False

    def hide_ships_panel_and_start_game(self):

        self.ships_opacity_effect = QGraphicsOpacityEffect()
        self.ships_container.setGraphicsEffect(self.ships_opacity_effect)

        self.ships_anim = QPropertyAnimation(self.ships_opacity_effect, b"opacity")
        self.ships_anim.setDuration(700)
        self.ships_anim.setStartValue(1)
        self.ships_anim.setEndValue(0)
        self.ships_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        def finish():

            self.ships_container.hide()
            self.phase = "battle"
            
            self.battle_panel.show()
            self.update_fleet_info()
            self.start_turn_timer()

            self.animate_fields_to_center()

            self.update_info()
            self.update_field_access()
            self.update_field_access()
            self.repaint_ships()

        self.ships_anim.finished.connect(finish)
        self.ships_anim.start()

# =========================================================
# ЗАПУСК
# =========================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = SeaBattle()

    window.show()

    sys.exit(app.exec())