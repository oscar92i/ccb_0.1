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

        # Breathing widget
        self.breath_widget = BreathingWidget()

        # Timer label
        self.timer_label = QtWidgets.QLabel("")
        self.timer_label.setAlignment(QtCore.Qt.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 16px; color: red;")
        self.timer_label.hide()

        # Buttons
        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.setFixedHeight(40)
        self.start_button.clicked.connect(self.start_session)

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

        self.settings_button = QtWidgets.QPushButton("Settings")
        self.settings_button.setFixedHeight(40)
        self.settings_button.clicked.connect(self.open_settings)

        # Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.remaining_seconds = 0
        self.use_timer = False
        self.timer_minutes = 5
        self.running = False
        self.paused = False

        # Layout
        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.pause_button)
        self.button_layout.addWidget(self.resume_button)
        self.button_layout.addWidget(self.reset_button)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.settings_button)
        layout.addWidget(self.timer_label)
        layout.addWidget(self.breath_widget)
        layout.addLayout(self.button_layout)

        container = QtWidgets.QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    # ---------------- Start / Pause / Resume / Reset ----------------
    def start_session(self):
        self.breath_widget.anim_group.start()
        self.running = True
        self.paused = False
        self.start_button.hide()
        self.pause_button.show()
        self.resume_button.hide()
        self.reset_button.hide()
        if self.use_timer:
            self.remaining_seconds = self.timer_minutes * 60
            self.update_timer()
            self.timer_label.show()
            self.timer.start(1000)

    def pause_session(self):
        self.breath_widget.anim_group.pause()
        self.timer.stop()
        self.paused = True
        self.start_button.hide()
        self.pause_button.hide()
        self.resume_button.show()
        self.reset_button.show()

    def resume_session(self):
        self.breath_widget.anim_group.resume()
        self.paused = False
        self.resume_button.hide()
        self.reset_button.show()
        self.pause_button.show()
        if self.use_timer:
            self.timer.start(1000)

    def reset_session(self):
        self.breath_widget.anim_group.stop()
        self.breath_widget._radius = self.breath_widget.min_radius
        self.breath_widget.update()
        self.remaining_seconds = self.timer_minutes * 60
        self.running = False
        self.paused = False
        self.start_button.show()
        self.pause_button.hide()
        self.resume_button.hide()
        self.reset_button.hide()
        if self.use_timer:
            self.update_timer()
            self.timer_label.show()
        else:
            self.timer_label.hide()
        self.timer.stop()

    # ---------------- Timer Update ----------------
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
            self.start_button.show()
            self.pause_button.hide()
            self.resume_button.hide()
            self.reset_button.show()

    # ---------------- Open Settings ----------------
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

            # Resume breathing only if running and not paused
            if self.running and not self.paused:
                self.breath_widget.anim_group.start()

            # Update timer settings
            self.use_timer = dialog.timer_enabled
            self.timer_minutes = dialog.timer_spinbox.value()
            self.timer_label.setVisible(self.use_timer)

# -------------------- Run App --------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
