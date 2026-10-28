import platform
import darkdetect  # pip install darkdetect
from PySide6 import QtCore, QtWidgets

class ThemeManager(QtCore.QObject):
    themeChanged = QtCore.Signal(str)  # emits "dark" or "light"

    def __init__(self, app: QtWidgets.QApplication, initial_mode="auto"):
        super().__init__()
        self.app = app
        self.mode = initial_mode  # "light", "dark", or "auto"
        self.current_theme = None
        self.apply_theme()

    def get_system_theme(self) -> str:
        """Detect the system theme (requires darkdetect)."""
        try:
            return "dark" if darkdetect.isDark() else "light"
        except Exception:
            return "light"

    def get_active_theme(self) -> str:
        """Return actual theme currently used."""
        if self.mode == "auto":
            return self.get_system_theme()
        return self.mode

    def apply_theme(self):
        """Apply the QSS based on current theme."""
        theme = self.get_active_theme()
        if theme == self.current_theme:
            return  # nothing to do
        self.current_theme = theme

        # Load matching stylesheet
        qss_path = f"assets/styles/{theme}_theme.qss"
        try:
            with open(qss_path, "r") as f:
                self.app.setStyleSheet(f.read())
        except FileNotFoundError:
            print(f"⚠️ Missing stylesheet: {qss_path}")

        self.themeChanged.emit(theme)

    def set_mode(self, mode: str):
        """Change between light/dark/auto and apply immediately."""
        if mode not in ("light", "dark", "auto"):
            raise ValueError("Mode must be 'light', 'dark', or 'auto'")
        self.mode = mode
        self.apply_theme()
