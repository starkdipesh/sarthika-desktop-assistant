"""ChatGPT-style animated wavy loader widget for Sarthika Code.

Provides a smooth, hardware-accelerated 3-dot sinusoidal wave animation
displayed while the LLM is prefilling context and preparing tokens.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget


class WavyLoaderWidget(QWidget):
    """ChatGPT-style 3-dot sinusoidal bouncing loader."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setMinimumWidth(80)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background: transparent;")

        self._dot_radius = 4.0
        self._dot_spacing = 8.0
        self._phase = 0.0
        self._dot_color = QColor("#38bdf8")  # Brand cyan / sky-blue

        self._timer = QTimer(self)
        self._timer.setInterval(33)  # ~30 FPS smooth animation
        self._timer.timeout.connect(self._on_tick)

    def start_animation(self) -> None:
        """Start the wave animation and show widget."""
        self._phase = 0.0
        self.setVisible(True)
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def stop_animation(self) -> None:
        """Stop the wave animation and hide widget."""
        if self._timer.isActive():
            self._timer.stop()
        self.setVisible(False)

    def is_animating(self) -> bool:
        """Return True if timer is active."""
        return self._timer.isActive()

    def _on_tick(self) -> None:
        """Advance wave phase on each timer tick."""
        self._phase += 0.16
        if self._phase > 2.0 * math.pi:
            self._phase -= 2.0 * math.pi
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint 3 sinusoidal bouncing dots with dynamic alpha."""
        if not self.isVisible():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_y = self.height() / 2.0
        start_x = 10.0
        num_dots = 3

        for i in range(num_dots):
            # Phase offset for each successive dot creates the traveling wave
            dot_phase = self._phase - (i * 0.85)
            # Vertical sine oscillation: amplitude = 4.5px
            offset_y = math.sin(dot_phase) * 4.5
            x = start_x + i * (self._dot_radius * 2.0 + self._dot_spacing)
            y = center_y + offset_y

            # Dynamic opacity (dimmer at bottom, bright at wave crest)
            normalized = (math.sin(dot_phase) + 1.0) / 2.0  # 0.0 to 1.0
            alpha = int(100 + 155 * normalized)

            dot_color = QColor(self._dot_color)
            dot_color.setAlpha(max(60, min(255, alpha)))

            painter.setBrush(dot_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                int(x - self._dot_radius),
                int(y - self._dot_radius),
                int(self._dot_radius * 2.0),
                int(self._dot_radius * 2.0),
            )

        painter.end()
