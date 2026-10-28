import sys, os, shutil, traceback
from dataclasses import dataclass
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QSoundEffect
from PySide6.QtCore import QUrl, QTimer

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

        # Main circle
        painter.setBrush(QtGui.QColor("#4CAF50"))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(center, self._radius, self._radius)

        # Markers
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
    def __init__(self, settings: SessionSettings, play_sound_callback=None):
        super().__init__()
        self.setWindowTitle("Breathing Settings")
        self.settings = settings
        self.play_sound_callback = play_sound_callback

        # Sliders
        self.inhale_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.inhale_slider.setMinimum(1)
        self.inhale_slider.setMaximum(9)
        self.inhale_slider.setValue(settings.inhale_time)
        self.inhale_slider.valueChanged.connect(self.update_exhale)

        self.inhale_label = QtWidgets.QLabel(f"Inhale: {settings.inhale_time}s")
        self.exhale_label = QtWidgets.QLabel(f"Exhale: {settings.exhale_time}s")

        # Timer
        self.timer_checkbox = QtWidgets.QCheckBox("Use session timer")
        self.timer_checkbox.setChecked(settings.use_timer)

        self.timer_spinbox = QtWidgets.QSpinBox()
        self.timer_spinbox.setRange(1, 120)
        self.timer_spinbox.setValue(settings.timer_minutes)
        self.timer_spinbox.setSuffix(" min")
        self.timer_spinbox.setEnabled(settings.use_timer)
        self.timer_checkbox.toggled.connect(self.timer_spinbox.setEnabled)

        # Markers
        self.fixed_max_checkbox = QtWidgets.QCheckBox("Show max radius marker")
        self.fixed_max_checkbox.setChecked(settings.show_max_marker)
        self.fixed_min_checkbox = QtWidgets.QCheckBox("Show min radius marker")
        self.fixed_min_checkbox.setChecked(settings.show_min_marker)

        # Buttons
        ok_button = QtWidgets.QPushButton("OK")
        cancel_button = QtWidgets.QPushButton("Cancel")
        ok_button.clicked.connect(self.on_ok)
        cancel_button.clicked.connect(self.on_cancel)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.inhale_label)
        layout.addWidget(self.inhale_slider)
        layout.addWidget(self.exhale_label)
        layout.addWidget(self.timer_checkbox)
        layout.addWidget(self.timer_spinbox)
        layout.addWidget(self.fixed_max_checkbox)
        layout.addWidget(self.fixed_min_checkbox)
        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(ok_button)
        btns.addWidget(cancel_button)
        layout.addLayout(btns)
        self.setLayout(layout)

    def update_exhale(self, value):
        self.settings.inhale_time = value
        self.settings.exhale_time = 10 - value
        self.inhale_label.setText(f"Inhale: {value}s")
        self.exhale_label.setText(f"Exhale: {10 - value}s")

    def on_ok(self):
        if self.play_sound_callback:
            self.play_sound_callback("assets/sounds/one_key.wav")
        self.settings.use_timer = self.timer_checkbox.isChecked()
        self.settings.timer_minutes = self.timer_spinbox.value()
        self.settings.show_max_marker = self.fixed_max_checkbox.isChecked()
        self.settings.show_min_marker = self.fixed_min_checkbox.isChecked()
        self.accept()

    def on_cancel(self):
        if self.play_sound_callback:
            self.play_sound_callback("assets/sounds/one_key.wav")
        self.reject()

# -------------------- Main Window --------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cardiac Coherence Breathing")
        self.setMinimumSize(400, 540)
        self.setMaximumSize(1920, 1080)
        self.resize(800, 700)

        self.setWindowIcon(QtGui.QIcon("assets/logo.png"))

        self.session_settings = SessionSettings()
        self.remaining_seconds = 0

        # ---------- Sounds ----------
        self.click_sound = QSoundEffect()
        self.click_sound.setSource(QUrl.fromLocalFile("assets/sounds/one_key.wav"))
        self.click_sound.setVolume(0.5)

        self.startup_sound = QSoundEffect()
        self.startup_sound.setSource(QUrl.fromLocalFile("assets/sounds/short_music.wav"))
        self.startup_sound.setVolume(0.4)
        self.startup_sound.play()

        # ---------- Music ----------
        self.player = QMediaPlayer()
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setMuted(False)

        # ---------- Timer ----------
        self.timer_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 16px; color: red;")
        self.timer_label.hide()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

        # ---------- Breathing Widget ----------
        self.breath_widget = BreathingWidget()

        # ---------- Menu ----------
        logo_label = QtWidgets.QLabel()
        logo_label.setPixmap(QtGui.QPixmap("assets/logo.png").scaledToWidth(200))
        logo_label.setAlignment(QtCore.Qt.AlignCenter)

        self.start_button_menu = QtWidgets.QPushButton("Breathing Exercise")
        self.start_button_menu.clicked.connect(self.open_breathing_page)

        self.param_button_menu = QtWidgets.QPushButton("Parameters")
        self.param_button_menu.clicked.connect(lambda: self.open_settings_with_sound())

        self.add_music_button = QtWidgets.QPushButton("Add Music")
        self.add_music_button.clicked.connect(self.add_music)
        self.add_music_button.setObjectName("addMusicButton")

        self.delete_music_button = QtWidgets.QPushButton("Delete Music")
        self.delete_music_button.clicked.connect(self.delete_music)
        self.delete_music_button.setObjectName("deleteMusicButton")

        self.quit_button_menu = QtWidgets.QPushButton("Quit")
        self.quit_button_menu.clicked.connect(QtWidgets.QApplication.quit)

        # --- Row layout for Add/Delete music ---
        music_buttons_layout = QtWidgets.QHBoxLayout()
        music_buttons_layout.addWidget(self.add_music_button)
        music_buttons_layout.addWidget(self.delete_music_button)

        # --- Main vertical layout ---
        menu_layout = QtWidgets.QVBoxLayout()
        menu_layout.addWidget(logo_label)
        menu_layout.addSpacing(50)
        menu_layout.addWidget(self.start_button_menu)
        menu_layout.addWidget(self.param_button_menu)
        menu_layout.addLayout(music_buttons_layout)
        menu_layout.addStretch(1)
        menu_layout.addWidget(self.quit_button_menu, alignment=QtCore.Qt.AlignCenter)

        menu_page = QtWidgets.QWidget()
        menu_page.setLayout(menu_layout)

        # ---------- Breathing Page ----------
        self.start_session_button = QtWidgets.QPushButton("Start Session")
        self.start_session_button.clicked.connect(self.start_session)

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

        self.mute_button = QtWidgets.QPushButton("Mute")
        self.mute_button.clicked.connect(self.toggle_mute)

        self.music_selector = QtWidgets.QComboBox()
        self.populate_music_list()
        self.music_selector.currentTextChanged.connect(self.change_music)

        # --- Breathing control buttons ---
        for btn in [self.start_session_button, self.pause_button, self.resume_button, self.reset_button]:
            btn.setObjectName("breathControl")

        self.back_button.setObjectName("backButton")

        # --- Music layout (selector + mute) ---
        music_layout = QtWidgets.QHBoxLayout()
        music_layout.addWidget(self.music_selector)
        music_layout.addWidget(self.mute_button)

        # --- Session layout ---
        session_layout = QtWidgets.QVBoxLayout()
        session_layout.addWidget(self.timer_label)
        session_layout.addWidget(self.breath_widget)
        session_layout.addLayout(music_layout)

        # --- Start session row ---
        start_layout = QtWidgets.QHBoxLayout()
        start_layout.addStretch()
        start_layout.addWidget(self.start_session_button)
        start_layout.addStretch()
        session_layout.addLayout(start_layout)

        # --- Controls row (pause/resume + reset) ---
        controls_layout = QtWidgets.QHBoxLayout()
        controls_layout.setSpacing(10)  # small gap
        controls_layout.setAlignment(QtCore.Qt.AlignCenter)

        # Limit button sizes
        for btn in [self.pause_button, self.resume_button, self.reset_button]:
            btn.setMaximumWidth(60)  # keeps them compact

        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.resume_button)
        controls_layout.addWidget(self.reset_button)
        session_layout.addLayout(controls_layout)

        # --- Back to menu alone ---
        back_layout = QtWidgets.QHBoxLayout()
        back_layout.addStretch()
        back_layout.addWidget(self.back_button)
        back_layout.addStretch()
        session_layout.addLayout(back_layout)

        # --- Final page setup ---
        session_page = QtWidgets.QWidget()
        session_page.setLayout(session_layout)

        # ---------- Stacked Widget ----------
        self.stacked_widget = QtWidgets.QStackedWidget()
        self.stacked_widget.addWidget(menu_page)
        self.stacked_widget.addWidget(session_page)
        self.setCentralWidget(self.stacked_widget)

        # --- Load external stylesheets ---
        with open("assets/styles/main_window.qss", "r") as f:
            self.setStyleSheet(f.read())

        with open("assets/styles/breathing_window.qss", "r") as f:
            self.breath_widget.setStyleSheet(f.read())


    # ---------- Music ----------
    def populate_music_list(self):
        folder = "assets/musics"
        os.makedirs(folder, exist_ok=True)
        self.music_selector.clear()
        self.music_selector.addItem("No music")
        for f in os.listdir(folder):
            if f.lower().endswith((".mp3", ".wav")):
                self.music_selector.addItem(f)

    def change_music(self, name):
        folder = "assets/musics"
        if name == "No music":
            self.player.stop()
            return
        path = os.path.join(folder, name)
        if os.path.exists(path):
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()

    def toggle_mute(self):
        muted = not self.audio_output.isMuted()
        self.audio_output.setMuted(muted)
        self.mute_button.setText("Unmute" if muted else "Mute")

    def add_music(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Music", "", "Audio Files (*.mp3 *.wav)"
        )
        if not path:
            return
        folder = "assets/musics"
        os.makedirs(folder, exist_ok=True)
        name = os.path.basename(path)
        dest = os.path.join(folder, name)
        if os.path.exists(dest):
            QtWidgets.QMessageBox.warning(self, "Duplicate", f"{name} already exists.")
            return
        shutil.copy(path, dest)
        self.populate_music_list()
        QtWidgets.QMessageBox.information(self, "Added", f"{name} added successfully.")

    def delete_music(self):
        folder = "assets/musics"
        files = [f for f in os.listdir(folder) if f.lower().endswith((".mp3", ".wav"))]
        if not files:
            QtWidgets.QMessageBox.information(self, "No Music", "No music found.")
            return
        item, ok = QtWidgets.QInputDialog.getItem(self, "Delete Music", "Select:", files, 0, False)
        if ok and item:
            os.remove(os.path.join(folder, item))
            self.populate_music_list()
            QtWidgets.QMessageBox.information(self, "Deleted", f"{item} deleted.")

    # ---------- Navigation ----------
    def open_settings_with_sound(self):
        self.play_sound("assets/sounds/one_key.wav")
        dialog = SettingsDialog(self.session_settings, self.play_sound)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.breath_widget.inhale_time = self.session_settings.inhale_time
            self.breath_widget.exhale_time = self.session_settings.exhale_time
            self.breath_widget.show_min_marker = self.session_settings.show_min_marker
            self.breath_widget.show_max_marker = self.session_settings.show_max_marker
            self.breath_widget.create_animations()

    def open_breathing_page(self):
        self.stacked_widget.setCurrentIndex(1)
        self.player.stop()
        self.music_selector.setCurrentIndex(0)
        self.breath_widget.anim_group.stop()
        self.timer.stop()
        self.timer_label.hide()
        self.start_session_button.show()
        self.pause_button.hide()
        self.resume_button.hide()
        self.reset_button.hide()

    def back_to_menu(self):
        self.player.stop()
        self.timer.stop()
        self.breath_widget.anim_group.stop()
        self.music_selector.setCurrentIndex(0)
        self.mute_button.setText("Mute")
        self.stacked_widget.setCurrentIndex(0)

    # ---------- Sounds ----------
    def play_sound(self, path):
        self.click_sound.setSource(QUrl.fromLocalFile(path))
        self.click_sound.play()

    # ---------- Session ----------
    def start_session(self):
        self.play_sound("assets/sounds/one_key.wav")
        self.start_session_button.hide()
        self.breath_widget.inhale_time = self.session_settings.inhale_time
        self.breath_widget.exhale_time = self.session_settings.exhale_time
        self.breath_widget.show_max_marker = self.session_settings.show_max_marker
        self.breath_widget.show_min_marker = self.session_settings.show_min_marker
        self.breath_widget.create_animations()
        self.breath_widget.anim_group.start()

        self.remaining_seconds = self.session_settings.timer_minutes * 60
        self.timer_label.setVisible(self.session_settings.use_timer)
        if self.session_settings.use_timer:
            self.timer.start(1000)

        self.pause_button.show()
        self.resume_button.hide()
        self.reset_button.show()

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
        self.reset_button.show()

    def reset_session(self):
        """Reset the breathing session — stop animation and show Start button."""
        self.breath_widget.anim_group.stop()
        self.timer.stop()
        self.breath_widget._radius = self.breath_widget.min_radius
        self.breath_widget.update()
        self.breath_widget.create_animations()

        self.remaining_seconds = self.session_settings.timer_minutes * 60
        self.timer_label.setVisible(self.session_settings.use_timer)
        if self.session_settings.use_timer:
            m, s = divmod(self.remaining_seconds, 60)
            self.timer_label.setText(f"Timer: {m:02d}:{s:02d}")

        self.start_session_button.show()
        self.pause_button.hide()
        self.resume_button.hide()
        self.reset_button.hide()

    # ---------- Timer ----------
    def update_timer(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            m, s = divmod(self.remaining_seconds, 60)
            self.timer_label.setText(f"Timer: {m:02d}:{s:02d}")
        else:
            self.timer.stop()
            self.breath_widget.anim_group.pause()

# -------------------- Run App --------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
