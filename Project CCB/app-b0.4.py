import sys
from dataclasses import dataclass
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtCore import QUrl

# -------------------- Session Settings --------------------
@dataclass
class SessionSettings:
    inhale_time: int = 5
    exhale_time: int = 5
    use_timer: bool = False
    timer_minutes: int = 5
    show_min_marker: bool = False
    show_max_marker: bool = False

# -------------------- Breathing Widget --------------------
class BreathingWidget(QtWidgets.QWidget):
    def __init__(self, inhale_time=5, exhale_time=5, parent=None):
        super().__init__(parent)
        self._radius = 50
        self.min_radius = 50
        self.max_radius = 150
        self.setFixedSize(400, 400)

        self.inhale_time = inhale_time
        self.exhale_time = exhale_time
        self.show_max_marker = False
        self.show_min_marker = False

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

        if hasattr(self, "anim_group"):
            self.anim_group.stop()

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

        pen = QtGui.QPen(QtGui.QColor("#FF5722"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        if self.show_max_marker:
            painter.drawEllipse(center, self.max_radius, self.max_radius)
        if self.show_min_marker:
            painter.drawEllipse(center, self.min_radius, self.min_radius)

# -------------------- Settings Dialog --------------------
class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings: SessionSettings, play_sound_callback):
        super().__init__()
        self.setWindowTitle("Breathing Settings")
        self.settings = settings
        self.play_sound = play_sound_callback

        # Inhale/Exhale sliders
        self.inhale_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.inhale_slider.setRange(1, 9)
        self.inhale_slider.setValue(settings.inhale_time)
        self.inhale_slider.valueChanged.connect(self.update_exhale)

        self.inhale_label = QtWidgets.QLabel(f"Inhale: {settings.inhale_time}s")
        self.exhale_label = QtWidgets.QLabel(f"Exhale: {settings.exhale_time}s")

        # Timer controls
        self.timer_checkbox = QtWidgets.QCheckBox("Use global session timer")
        self.timer_checkbox.setChecked(settings.use_timer)
        self.timer_spinbox = QtWidgets.QSpinBox()
        self.timer_spinbox.setRange(1, 120)
        self.timer_spinbox.setSuffix(" min")
        self.timer_spinbox.setValue(settings.timer_minutes)
        self.timer_spinbox.setEnabled(self.timer_checkbox.isChecked())
        self.timer_checkbox.toggled.connect(self.timer_spinbox.setEnabled)

        # Marker checkboxes
        self.fixed_max_checkbox = QtWidgets.QCheckBox("Show max radius marker")
        self.fixed_max_checkbox.setChecked(settings.show_max_marker)
        self.fixed_min_checkbox = QtWidgets.QCheckBox("Show min radius marker")
        self.fixed_min_checkbox.setChecked(settings.show_min_marker)

        # Buttons
        ok_button = QtWidgets.QPushButton("OK")
        cancel_button = QtWidgets.QPushButton("Cancel")
        ok_button.clicked.connect(self.on_ok)
        cancel_button.clicked.connect(self.on_cancel)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(ok_button)
        btn_layout.addWidget(cancel_button)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.inhale_label)
        layout.addWidget(self.inhale_slider)
        layout.addWidget(self.exhale_label)
        layout.addWidget(self.timer_checkbox)
        layout.addWidget(self.timer_spinbox)
        layout.addWidget(self.fixed_max_checkbox)
        layout.addWidget(self.fixed_min_checkbox)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def update_exhale(self, value):
        self.settings.inhale_time = value
        self.settings.exhale_time = 10 - value
        self.inhale_label.setText(f"Inhale: {value}s")
        self.exhale_label.setText(f"Exhale: {10 - value}s")

    def on_ok(self):
        self.play_sound("assets/sounds/one_key.wav")
        self.accept()

    def on_cancel(self):
        self.play_sound("assets/sounds/one_key.wav")
        self.reject()

    def accept(self):
        self.settings.inhale_time = self.inhale_slider.value()
        self.settings.exhale_time = 10 - self.settings.inhale_time
        self.settings.use_timer = self.timer_checkbox.isChecked()
        self.settings.timer_minutes = self.timer_spinbox.value()
        self.settings.show_max_marker = self.fixed_max_checkbox.isChecked()
        self.settings.show_min_marker = self.fixed_min_checkbox.isChecked()
        super().accept()

# -------------------- Main Window --------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cardiac Coherence Breathing")
        self.setFixedSize(400, 520)
        self.setWindowIcon(QtGui.QIcon("assets/logo.png"))

        # Sounds
        self.sounds = {}
        self.preload_sounds()

        # Play startup music
        self.play_sound("assets/sounds/short_music.wav")

        self.session_settings = SessionSettings()
        self.timer_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 16px; color: red;")
        self.timer_label.hide()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.remaining_seconds = 0

        self.breath_widget = BreathingWidget()

        # Buttons
        logo_label = QtWidgets.QLabel()
        logo_label.setPixmap(QtGui.QPixmap("assets/logo.png").scaledToWidth(200))
        logo_label.setAlignment(QtCore.Qt.AlignCenter)

        self.start_button_menu = QtWidgets.QPushButton("Start")
        self.start_button_menu.clicked.connect(self.start_session_from_menu)

        self.param_button_menu = QtWidgets.QPushButton("Parameters")
        self.param_button_menu.clicked.connect(lambda: (
            self.play_sound("assets/sounds/one_key.wav"),
            self.open_settings()
        ))

        self.quit_button_menu = QtWidgets.QPushButton("Quit")
        self.quit_button_menu.clicked.connect(QtWidgets.QApplication.quit)

        self.pause_button = QtWidgets.QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_session)
        self.pause_button.hide()

        self.resume_button = QtWidgets.QPushButton("Resume")
        self.resume_button.clicked.connect(self.resume_session)
        self.resume_button.hide()

        self.reset_button = QtWidgets.QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_session)
        self.reset_button.hide()

        self.back_button = QtWidgets.QPushButton("Back to Menu")
        self.back_button.clicked.connect(self.back_to_menu)
        self.back_button.hide()

        # Pages
        self.stacked_widget = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        menu_page = QtWidgets.QWidget()
        menu_layout = QtWidgets.QVBoxLayout()
        menu_layout.addWidget(logo_label)
        menu_layout.addWidget(self.start_button_menu)
        menu_layout.addWidget(self.param_button_menu)
        menu_layout.addWidget(self.quit_button_menu)
        menu_layout.addStretch()
        menu_page.setLayout(menu_layout)

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

        self.stacked_widget.addWidget(menu_page)
        self.stacked_widget.addWidget(session_page)

    def preload_sounds(self):
        """Preload .wav sounds using QSoundEffect."""
        for name in ["one_key", "short_music"]:
            path = f"assets/sounds/{name}.wav"
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(path))
            effect.setVolume(0.7)
            self.sounds[name] = effect

    def play_sound(self, filepath):
        name = filepath.split("/")[-1].replace(".wav", "")
        if name in self.sounds:
            self.sounds[name].play()

    # --- Session control ---
    def start_session_from_menu(self):
        self.breath_widget.show_max_marker = self.session_settings.show_max_marker
        self.breath_widget.show_min_marker = self.session_settings.show_min_marker
        self.remaining_seconds = self.session_settings.timer_minutes * 60
        self.timer_label.setVisible(self.session_settings.use_timer)
        self.update_timer()

        self.breath_widget.inhale_time = self.session_settings.inhale_time
        self.breath_widget.exhale_time = self.session_settings.exhale_time
        self.breath_widget.create_animations()
        self.breath_widget.anim_group.start()

        self.stacked_widget.setCurrentIndex(1)
        self.pause_button.show()
        self.resume_button.hide()
        self.reset_button.hide()
        self.back_button.show()
        if self.session_settings.use_timer:
            self.timer.start(1000)

    def pause_session(self):
        self.breath_widget.anim_group.pause()
        self.timer.stop()
        self.pause_button.hide()
        self.resume_button.show()
        self.reset_button.show()

    def resume_session(self):
        self.breath_widget.anim_group.resume()
        if self.session_settings.use_timer:
            self.timer.start(1000)
        self.pause_button.show()
        self.resume_button.hide()

    def reset_session(self):
        self.breath_widget.anim_group.stop()
        self.breath_widget._radius = self.breath_widget.min_radius
        self.breath_widget.update()
        self.remaining_seconds = self.session_settings.timer_minutes * 60
        self.update_timer()
        self.breath_widget.create_animations()
        self.breath_widget.anim_group.start()
        if self.session_settings.use_timer:
            self.timer.start(1000)
        self.pause_button.show()
        self.resume_button.hide()
        self.reset_button.hide()

    def back_to_menu(self):
        self.breath_widget.anim_group.stop()
        self.timer.stop()
        self.stacked_widget.setCurrentIndex(0)
        self.timer_label.hide()
        self.pause_button.hide()
        self.resume_button.hide()
        self.reset_button.hide()
        self.back_button.hide()

    def update_timer(self):
        if self.remaining_seconds > 0:
            m, s = divmod(self.remaining_seconds, 60)
            self.timer_label.setText(f"Timer: {m:02d}:{s:02d}")
            self.remaining_seconds -= 1
        else:
            self.timer.stop()
            self.breath_widget.anim_group.pause()
            self.pause_button.hide()
            self.resume_button.hide()
            self.reset_button.show()

    def open_settings(self):
        dialog = SettingsDialog(self.session_settings, self.play_sound)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.breath_widget.inhale_time = self.session_settings.inhale_time
            self.breath_widget.exhale_time = self.session_settings.exhale_time
            self.breath_widget.show_min_marker = self.session_settings.show_min_marker
            self.breath_widget.show_max_marker = self.session_settings.show_max_marker
            self.timer_label.setVisible(self.session_settings.use_timer)
            self.breath_widget.create_animations()

# -------------------- Run --------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
