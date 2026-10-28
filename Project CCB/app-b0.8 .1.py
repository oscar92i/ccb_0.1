import sys, os, shutil, traceback
from dataclasses import dataclass
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QSoundEffect
from PySide6.QtCore import QUrl, QTimer
from assets.theme_manager import ThemeManager

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

        # runtime state
        self._radius = 50
        self.inhale_time = inhale_time
        self.exhale_time = exhale_time
        self.show_max_marker = False
        self.show_min_marker = False

        # scaling factors (fractions of the smallest widget dimension)
        # tweak these to change how large the circle becomes
        self.min_scale = 0.15
        self.max_scale = 0.38

        # allow the widget to expand/contract with the window
        self.setMinimumSize(240, 240)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # initial radii (will be recomputed on first resize)
        self.min_radius = 50
        self.max_radius = 150

        # create animations based on current radii
        self.create_animations()

    def resizeEvent(self, event):
        """Recalculate radii based on available space, keep animations consistent."""
        side = min(self.width(), self.height())
        new_min = max(8, int(side * self.min_scale))
        new_max = max(new_min + 4, int(side * self.max_scale))

        # If radii changed, update and recreate animations.
        if new_min != self.min_radius or new_max != self.max_radius:
            was_running = False
            was_paused = False
            if hasattr(self, "anim_group"):
                state = self.anim_group.state()
                was_running = (state == QtCore.QAbstractAnimation.Running)
                was_paused = (state == QtCore.QAbstractAnimation.Paused)
                # stop prior animation before recreating
                try:
                    self.anim_group.stop()
                except Exception:
                    pass

            self.min_radius = new_min
            self.max_radius = new_max

            # ensure current radius is within new bounds
            self._radius = max(self.min_radius, min(self._radius, self.max_radius))

            # recreate animations and restore state
            self.create_animations()
            if was_running:
                try:
                    self.anim_group.start()
                except Exception:
                    pass
            elif was_paused:
                # don't start, keep paused state (leave stopped until resumed)
                pass

        super().resizeEvent(event)

    def create_animations(self):
        """(Re)create the expand/contract animations using current radii/times."""
        # defensive: stop old group
        if hasattr(self, "anim_group") and isinstance(self.anim_group, QtCore.QSequentialAnimationGroup):
            try:
                self.anim_group.stop()
            except Exception:
                pass

        # make integer property animations (Qt prefers numeric types)
        self.expand_anim = QtCore.QPropertyAnimation(self, b"radius")
        self.expand_anim.setStartValue(int(self.min_radius))
        self.expand_anim.setEndValue(int(self.max_radius))
        self.expand_anim.setDuration(max(20, int(self.inhale_time * 1000)))
        self.expand_anim.setEasingCurve(QtCore.QEasingCurve.InOutSine)

        self.contract_anim = QtCore.QPropertyAnimation(self, b"radius")
        self.contract_anim.setStartValue(int(self.max_radius))
        self.contract_anim.setEndValue(int(self.min_radius))
        self.contract_anim.setDuration(max(20, int(self.exhale_time * 1000)))
        self.contract_anim.setEasingCurve(QtCore.QEasingCurve.InOutSine)

        self.anim_group = QtCore.QSequentialAnimationGroup()
        self.anim_group.addAnimation(self.expand_anim)
        self.anim_group.addAnimation(self.contract_anim)
        self.anim_group.setLoopCount(-1)

    @QtCore.Property(int)
    def radius(self):
        return int(self._radius)

    @radius.setter
    def radius(self, r):
        self._radius = int(r)
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

        # Thin outline markers
        pen = QtGui.QPen(QtGui.QColor("#FF5722"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        if self.show_max_marker:
            painter.drawEllipse(center, self.max_radius, self.max_radius)
        if self.show_min_marker:
            painter.drawEllipse(center, self.min_radius, self.min_radius)

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings, play_sound_callback=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Breathing Settings")
        self.settings = settings
        self.play_sound_callback = play_sound_callback
        self.parent_window = parent  # Reference to MainWindow (theme_manager lives there)

        layout = QtWidgets.QVBoxLayout()

        # ---------------- Theme Section ----------------
        self.theme_label = QtWidgets.QLabel("Theme:")
        self.auto_theme_radio = QtWidgets.QRadioButton("Auto")
        self.light_theme_radio = QtWidgets.QRadioButton("Light")
        self.dark_theme_radio = QtWidgets.QRadioButton("Dark")

        self.theme_group = QtWidgets.QButtonGroup()
        self.theme_group.addButton(self.auto_theme_radio)
        self.theme_group.addButton(self.light_theme_radio)
        self.theme_group.addButton(self.dark_theme_radio)

        self.load_current_theme()

        theme_layout = QtWidgets.QHBoxLayout()
        theme_layout.addWidget(self.theme_label)
        theme_layout.addStretch()
        theme_layout.addWidget(self.auto_theme_radio)
        theme_layout.addWidget(self.light_theme_radio)
        theme_layout.addWidget(self.dark_theme_radio)
        layout.addLayout(theme_layout)

        # ---------------- Breathing Settings ----------------
        # Inhale / Exhale slider (10s total)
        self.breath_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.breath_slider.setRange(1, 9)
        self.breath_slider.setValue(self.settings.inhale_time)
        self.breath_slider.valueChanged.connect(self.update_exhale)

        self.inhale_label = QtWidgets.QLabel(f"Inhale: {self.settings.inhale_time}s")
        self.exhale_label = QtWidgets.QLabel(f"Exhale: {self.settings.exhale_time}s")

        layout.addWidget(self.inhale_label)
        layout.addWidget(self.exhale_label)
        layout.addWidget(self.breath_slider)

        # Timer
        self.timer_checkbox = QtWidgets.QCheckBox("Use timer")
        self.timer_checkbox.setChecked(settings.use_timer)

        self.timer_label = QtWidgets.QLabel("Session duration (minutes):")
        self.timer_spinbox = QtWidgets.QSpinBox()
        self.timer_spinbox.setRange(1, 60)
        self.timer_spinbox.setValue(settings.timer_minutes)

        timer_layout = QtWidgets.QHBoxLayout()
        timer_layout.addWidget(self.timer_label)
        timer_layout.addWidget(self.timer_spinbox)
        layout.addWidget(self.timer_checkbox)
        layout.addLayout(timer_layout)

        # Show min/max markers
        self.fixed_min_checkbox = QtWidgets.QCheckBox("Show minimum marker")
        self.fixed_min_checkbox.setChecked(settings.show_min_marker)

        self.fixed_max_checkbox = QtWidgets.QCheckBox("Show maximum marker")
        self.fixed_max_checkbox.setChecked(settings.show_max_marker)

        layout.addWidget(self.fixed_min_checkbox)
        layout.addWidget(self.fixed_max_checkbox)

        # ---------------- Buttons ----------------
        ok_button = QtWidgets.QPushButton("OK")
        cancel_button = QtWidgets.QPushButton("Cancel")
        ok_button.clicked.connect(self.on_ok)
        cancel_button.clicked.connect(self.on_cancel)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch()
        btns.addWidget(ok_button)
        btns.addWidget(cancel_button)
        layout.addLayout(btns)

        self.setLayout(layout)
        self.setMinimumWidth(350)

    def update_exhale(self, value):
        """Keep total inhale+exhale = 10s"""
        self.settings.inhale_time = value
        self.settings.exhale_time = 10 - value
        self.inhale_label.setText(f"Inhale: {value}s")
        self.exhale_label.setText(f"Exhale: {10 - value}s")

    def load_current_theme(self):
        """Preselect current theme from ThemeManager."""
        if not hasattr(self.parent_window, "theme_manager"):
            # default to auto if theme manager isn't available
            self.auto_theme_radio.setChecked(True)
            return
        mode = self.parent_window.theme_manager.mode  # "auto", "light", or "dark"

        if mode == "auto":
            self.auto_theme_radio.setChecked(True)
        elif mode == "light":
            self.light_theme_radio.setChecked(True)
        elif mode == "dark":
            self.dark_theme_radio.setChecked(True)

    def on_ok(self):
        """Apply all settings (breathing + theme) and close."""
        if self.play_sound_callback:
            self.play_sound_callback("assets/sounds/one_key.wav")

        # Save breathing settings
        self.settings.use_timer = self.timer_checkbox.isChecked()
        self.settings.timer_minutes = self.timer_spinbox.value()
        self.settings.show_max_marker = self.fixed_max_checkbox.isChecked()
        self.settings.show_min_marker = self.fixed_max_checkbox.isChecked()

        # Apply selected theme
        if self.auto_theme_radio.isChecked():
            selected_theme = "auto"
        elif self.light_theme_radio.isChecked():
            selected_theme = "light"
        else:
            selected_theme = "dark"

        if hasattr(self.parent_window, "theme_manager"):
            self.parent_window.theme_manager.set_mode(selected_theme)
        else:
            print("Warning: parent has no theme_manager")

        self.accept()

    def on_cancel(self):
        """Cancel and play sound."""
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

        # <<< CHANGED: track mute state in a single place
        self.is_muted = False
        # <<< /CHANGED

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

        # --- About / Info Button ---
        self.about_button = QtWidgets.QPushButton("About Cardiac Coherence")
        self.about_button.clicked.connect(self.show_about_window)
        
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
        menu_layout.addWidget(self.about_button)
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

        # --- Mute button: SVG-based, animated fade transition ---
        self.mute_button = QtWidgets.QPushButton()
        self.mute_button.setObjectName("muteButton")
        self.mute_button.setAccessibleName("muteButton")
        self.mute_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.mute_button.setIcon(QtGui.QIcon("assets/icons/volume_on.svg"))
        self.mute_button.setIconSize(QtCore.QSize(28, 28))
        self.mute_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.mute_button.setFixedSize(38, 38)
        self.mute_button.clicked.connect(self.toggle_mute)

        # opacity animation effect
        self.mute_opacity_effect = QtWidgets.QGraphicsOpacityEffect(self.mute_button)
        self.mute_button.setGraphicsEffect(self.mute_opacity_effect)
        self.mute_anim = QtCore.QPropertyAnimation(self.mute_opacity_effect, b"opacity", self)
        self.mute_anim.setDuration(250)

        # --- Music selector: takes remaining horizontal space ---
        self.music_selector = QtWidgets.QComboBox()
        self.populate_music_list()
        self.music_selector.currentTextChanged.connect(self.change_music)
        self.music_selector.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.music_selector.setMinimumWidth(80)
        self.music_selector.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContentsOnFirstShow)

        # --- Style object names (for your QSS) ---
        for btn in [self.start_session_button, self.pause_button, self.resume_button, self.reset_button]:
            btn.setObjectName("breathControl")
        self.back_button.setObjectName("backButton")

        # --- Music layout: selector EXPANDS, mute stays small ---
        music_layout = QtWidgets.QHBoxLayout()
        music_layout.setContentsMargins(6, 6, 6, 6)
        music_layout.setSpacing(8)
        music_layout.addWidget(self.music_selector)   # no explicit stretch
        music_layout.addWidget(self.mute_button)      # fixed

        # --- Session layout ---
        session_layout = QtWidgets.QVBoxLayout()
        session_layout.setContentsMargins(8, 8, 8, 8)
        session_layout.setSpacing(10)
        session_layout.addWidget(self.timer_label)
        session_layout.addWidget(self.breath_widget, stretch=1)
        session_layout.addLayout(music_layout)

        # --- Start session row (centered but can shrink) ---
        start_layout = QtWidgets.QHBoxLayout()
        start_layout.setContentsMargins(4, 0, 4, 0)
        start_layout.addStretch()
        self.start_session_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.start_session_button.setMinimumWidth(120)
        start_layout.addWidget(self.start_session_button)
        start_layout.addStretch()
        session_layout.addLayout(start_layout)

        # --- Controls row (pause/resume + reset) : shrink-friendly ---
        controls_layout = QtWidgets.QHBoxLayout()
        controls_layout.setSpacing(8)
        controls_layout.setAlignment(QtCore.Qt.AlignCenter)
        controls_layout.setContentsMargins(4, 0, 4, 0)

        for btn in [self.pause_button, self.resume_button, self.reset_button]:
            # Preferred allows shrink; min/max keep them usable and prevent overflow.
            btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            # btn.setMinimumWidth(60)
            # btn.setMaximumWidth(160)
            btn.setFixedHeight(32)
            controls_layout.addWidget(btn)

        session_layout.addLayout(controls_layout)

        # --- Back button row (alone) ---
        back_layout = QtWidgets.QHBoxLayout()
        back_layout.addStretch()
        self.back_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        # self.back_button.setMinimumWidth(100)
        self.back_button.setFixedHeight(32)
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
            session_page.setStyleSheet(f.read())

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
            # <<< CHANGED: ensure mute state propagates to new playback
            self.audio_output.setMuted(self.is_muted)
            # <<< /CHANGED
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()

    def toggle_mute(self):
        """Toggle mute/unmute with smooth icon fade animation."""
        self.is_muted = not self.is_muted
        self.audio_output.setMuted(self.is_muted)

        new_icon = QtGui.QIcon("assets/icons/volume_off.svg") if self.is_muted else QtGui.QIcon("assets/icons/volume_on.svg")

        # Animate fade-out → icon switch → fade-in
        self.mute_anim.stop()
        self.mute_anim.setStartValue(1.0)
        self.mute_anim.setEndValue(0.0)

        def switch_icon():
            self.mute_button.setIcon(new_icon)
            self.mute_anim.finished.disconnect(switch_icon)
            self.mute_anim.setStartValue(0.0)
            self.mute_anim.setEndValue(1.0)
            self.mute_anim.start()

        self.mute_anim.finished.connect(switch_icon)
        self.mute_anim.start()

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

    def show_about_window(self):
        about_window = QtWidgets.QDialog(self)
        about_window.setWindowTitle("About Cardiac Coherence")
        about_window.setMinimumSize(500, 400)

        layout = QtWidgets.QVBoxLayout(about_window)

        text = QtWidgets.QLabel("""
            <h2>What is Cardiac Coherence?</h2>
            <p>
            Cardiac coherence is a simple breathing technique that helps balance your
            nervous system by synchronizing your breathing with your heart rate. 
            Practicing it regularly can reduce stress, improve focus, and promote a
            sense of calm and well-being.
            </p>
            <p>
            The principle is to breathe at a slow, regular rhythm — usually <b>six breaths per minute</b>:
            5 seconds inhaling and 5 seconds exhaling. This stimulates the vagus nerve,
            helping to regulate your emotions and physiological state.
            </p>
            <p>
            This app guides you through a breathing cycle with a smooth animation and
            optional background music, helping you achieve this ideal rhythm effortlessly.
            </p>
        """)
        text.setWordWrap(True)
        layout.addWidget(text)

        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(about_window.close)
        layout.addWidget(close_button, alignment=QtCore.Qt.AlignCenter)

        about_window.exec()

    # ---------- Navigation ----------
    def open_settings_with_sound(self):
        self.play_sound("assets/sounds/one_key.wav")
        dialog = SettingsDialog(self.session_settings, self.play_sound, parent=self)  # ✅ add parent=self
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

        self.audio_output.setMuted(self.is_muted)

    def back_to_menu(self):
        self.player.stop()
        self.timer.stop()
        self.breath_widget.anim_group.stop()
        self.music_selector.setCurrentIndex(0)

        self.stacked_widget.setCurrentIndex(0)

        self.audio_output.setMuted(self.is_muted)
        self.mute_button.setIcon(QtGui.QIcon(
            "assets/icons/volume_off.svg" if self.is_muted else "assets/icons/volume_on.svg"
        ))

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
        self.stacked_widget.setCurrentIndex(1)

        self.audio_output.setMuted(self.is_muted)
        self.mute_button.setIcon(QtGui.QIcon(
            "assets/icons/volume_off.svg" if self.is_muted else "assets/icons/volume_on.svg"
        ))

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
    theme_manager = ThemeManager(app, initial_mode="auto")  # "dark", "light", or "auto"

    window = MainWindow()
    window.theme_manager = theme_manager
    window.show()
    sys.exit(app.exec())
