import sys
from PySide6 import QtCore, QtWidgets, QtGui

# -------------------- Breathing Widget --------------------
class BreathingWidget(QtWidgets.QWidget):
    def __init__(self, inhale_time=5, exhale_time=5, parent=None):
        super().__init__(parent)
        self._radius = 50
        self.min_radius = 50
        self.max_radius = 150
        self.setMinimumSize(400, 400)
        self.setMaximumSize(400, 400)

        # Timing
        self.inhale_time = inhale_time
        self.exhale_time = exhale_time

        # Animations
        self.create_animations()

    def create_animations(self):
        self.expand_anim = QtCore.QPropertyAnimation(self, b"radius")
        self.expand_anim.setStartValue(self.min_radius)
        self.expand_anim.setEndValue(self.max_radius)
        self.expand_anim.setDuration(self.inhale_time * 1000)
        self.expand_anim.setEasingCurve(QtCore.QEasingCurve.InOutSine)

        self.contract_anim = QtCore.QPropertyAnimation(self, b"radius")
        self.contract_anim.setStartValue(self.max_radius)
        self.contract_anim.setEndValue(self.min_radius)
        self.contract_anim.setDuration(self.exhale_time * 1000)
        self.contract_anim.setEasingCurve(QtCore.QEasingCurve.InOutSine)

        self.anim_group = QtCore.QSequentialAnimationGroup()
        self.anim_group.addAnimation(self.expand_anim)
        self.anim_group.addAnimation(self.contract_anim)
        self.anim_group.setLoopCount(-1)

    @QtCore.Property(int)
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, r):
        self._radius = r
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor("#121212"))
        center = self.rect().center()
        painter.setBrush(QtGui.QColor("#4CAF50"))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(center, self._radius, self._radius)

# -------------------- Settings Dialog --------------------
class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, inhale_time, exhale_time, use_timer=False, timer_minutes=5):
        super().__init__()
        self.setWindowTitle("Breathing Settings")

        self.inhale_time = inhale_time
        self.exhale_time = exhale_time
        self.use_timer = use_timer
        self.timer_minutes = timer_minutes

        # Inhale slider
        self.inhale_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.inhale_slider.setMinimum(1)
        self.inhale_slider.setMaximum(9)
        self.inhale_slider.setValue(self.inhale_time)
        self.inhale_slider.valueChanged.connect(self.update_exhale)
        self.inhale_label = QtWidgets.QLabel(f"Inhale: {self.inhale_time}s")

        # Exhale label
        self.exhale_label = QtWidgets.QLabel(f"Exhale: {self.exhale_time}s")

        # Timer checkbox
        self.timer_checkbox = QtWidgets.QCheckBox("Use global session timer")
        self.timer_checkbox.setChecked(self.use_timer)
        self.timer_checkbox.stateChanged.connect(self.toggle_timer_input)

        # Timer spinbox
        self.timer_spinbox = QtWidgets.QSpinBox()
        self.timer_spinbox.setMinimum(1)
        self.timer_spinbox.setMaximum(120)
        self.timer_spinbox.setValue(self.timer_minutes)
        self.timer_spinbox.setSuffix(" min")
        self.timer_spinbox.setEnabled(self.use_timer)

        # OK button
        ok_button = QtWidgets.QPushButton("OK")
        ok_button.clicked.connect(self.accept)

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.inhale_label)
        layout.addWidget(self.inhale_slider)
        layout.addWidget(self.exhale_label)
        layout.addWidget(self.timer_checkbox)
        layout.addWidget(self.timer_spinbox)
        layout.addWidget(ok_button)
        self.setLayout(layout)

    def update_exhale(self, value):
        self.inhale_time = value
        self.exhale_time = 10 - value
        self.inhale_label.setText(f"Inhale: {self.inhale_time}s")
        self.exhale_label.setText(f"Exhale: {self.exhale_time}s")

    def toggle_timer_input(self, state):
        self.timer_spinbox.setEnabled(state == QtCore.Qt.Checked)

    @property
    def timer_enabled(self):
        return self.timer_checkbox.isChecked()

# -------------------- Main Window --------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cardiac Coherence Breathing")
        self.setFixedSize(400, 520)

        # ----------------- Session state -----------------
        self.use_timer = False
        self.timer_minutes = 5
        self.running = False
        self.paused = False
        self.remaining_seconds = 0

        # ----------------- Timer -----------------
        self.timer_label = QtWidgets.QLabel("")
        self.timer_label.setAlignment(QtCore.Qt.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 16px; color: red;")
        self.timer_label.hide()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_timer)

        # ----------------- Breathing widget -----------------
        self.breath_widget = BreathingWidget()

        # ----------------- Buttons -----------------
        # Menu page buttons
        self.start_button_menu = QtWidgets.QPushButton("Start")
        self.start_button_menu.setFixedHeight(40)
        self.start_button_menu.clicked.connect(self.start_session_from_menu)

        self.param_button_menu = QtWidgets.QPushButton("Parameters")
        self.param_button_menu.setFixedHeight(40)
        self.param_button_menu.clicked.connect(self.open_settings)

        self.quit_button_menu = QtWidgets.QPushButton("Quit")
        self.quit_button_menu.setFixedHeight(40)
        self.quit_button_menu.clicked.connect(QtWidgets.QApplication.quit)

        # Session page buttons
        self.pause_button = QtWidgets.QPushButton("Pause")
        self.pause_button.setFixedHeight(40)
        self.pause_button.clicked.connect(self.pause_session)
        self.pause_button.hide()

        self.resume_button = QtWidgets.QPushButton("Resume")
        self.resume_button.setFixedHeight(40)
        self.resume_button.clicked.connect(self.resume_session)
        self.resume_button.hide()

        self.reset_button = QtWidgets.QPushButton("Reset")
        self.reset_button.setFixedHeight(40)
        self.reset_button.clicked.connect(self.reset_session)
        self.reset_button.hide()

        self.back_button = QtWidgets.QPushButton("Back to Menu")
        self.back_button.setFixedHeight(40)
        self.back_button.clicked.connect(self.back_to_menu)
        self.back_button.hide()

        # ----------------- Stacked layout -----------------
        self.stacked_widget = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Menu page
        menu_page = QtWidgets.QWidget()
        menu_layout = QtWidgets.QVBoxLayout()
        menu_layout.addWidget(self.start_button_menu)
        menu_layout.addWidget(self.param_button_menu)
        menu_layout.addWidget(self.quit_button_menu)
        menu_page.setLayout(menu_layout)

        # Session page
        session_page = QtWidgets.QWidget()
        session_layout = QtWidgets.QVBoxLayout()
        session_layout.addWidget(self.timer_label)
        session_layout.addWidget(self.breath_widget)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.resume_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.back_button)
        session_layout.addLayout(button_layout)
        session_page.setLayout(session_layout)

        self.stacked_widget.addWidget(menu_page)      # index 0
        self.stacked_widget.addWidget(session_page)   # index 1

    # ----------------- Menu → Session -----------------
    def start_session_from_menu(self):
        # Apply current settings to breathing widget
        self.breath_widget.anim_group.stop()
        self.breath_widget.create_animations()
        # Reset timer
        self.remaining_seconds = self.timer_minutes * 60
        self.update_timer()
        self.timer_label.setVisible(self.use_timer)
        self.running = True
        self.paused = False

        # Switch to session page
        self.stacked_widget.setCurrentIndex(1)
        self.breath_widget.anim_group.start()
        self.pause_button.show()
        self.resume_button.hide()
        self.reset_button.hide()
        self.back_button.show()
        if self.use_timer:
            self.timer.start(1000)

    # ----------------- Pause / Resume / Reset -----------------
    def pause_session(self):
        self.breath_widget.anim_group.pause()
        self.timer.stop()
        self.paused = True
        self.pause_button.hide()
        self.resume_button.show()
        self.reset_button.show()

    def resume_session(self):
        self.breath_widget.anim_group.resume()
        self.paused = False
        self.pause_button.show()
        self.resume_button.hide()
        self.reset_button.show()
        if self.use_timer:
            self.timer.start(1000)

    def reset_session(self):
        self.breath_widget.anim_group.stop()
        self.breath_widget._radius = self.breath_widget.min_radius
        self.breath_widget.update()
        self.remaining_seconds = self.timer_minutes * 60
        self.paused = False
        self.running = True
        self.pause_button.show()
        self.resume_button.hide()
        self.reset_button.hide()
        if self.use_timer:
            self.update_timer()
            self.timer_label.show()
            self.timer.start(1000)  # restart timer
        else:
            self.timer_label.hide()
        self.breath_widget.anim_group.start()

    # ----------------- Back to Menu -----------------
    def back_to_menu(self):
        self.breath_widget.anim_group.stop()
        self.timer.stop()
        self.running = False
        self.paused = False
        self.stacked_widget.setCurrentIndex(0)
        self.timer_label.hide()
        self.pause_button.hide()
        self.resume_button.hide()
        self.reset_button.hide()
        self.back_button.hide()

    # ----------------- Timer -----------------
    def update_timer(self):
        if self.remaining_seconds > 0:
            minutes = self.remaining_seconds // 60
            seconds = self.remaining_seconds % 60
            self.timer_label.setText(f"Timer: {minutes:02d}:{seconds:02d}")
            self.remaining_seconds -= 1
        else:
            self.timer.stop()
            self.breath_widget.anim_group.pause()
            self.running = False
            self.paused = True
            self.pause_button.hide()
            self.resume_button.hide()
            self.reset_button.show()

    # ----------------- Settings -----------------
    def open_settings(self):
        dialog = SettingsDialog(
            inhale_time=self.breath_widget.inhale_time,
            exhale_time=self.breath_widget.exhale_time,
            use_timer=self.use_timer,
            timer_minutes=self.timer_minutes
        )
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            # Update breathing times
            self.breath_widget.inhale_time = dialog.inhale_time
            self.breath_widget.exhale_time = dialog.exhale_time
            self.breath_widget.anim_group.stop()
            self.breath_widget.create_animations()

            # Update timer settings
            self.use_timer = dialog.timer_enabled
            self.timer_minutes = dialog.timer_spinbox.value()
            # Timer label will be shown only when session starts

# -------------------- Run App --------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
