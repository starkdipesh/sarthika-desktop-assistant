"""Visual lock overlay shielding conversations and context when vault is locked.

Ensures zero unauthorized visual access to conversations, files, or sensitive code
when the user steps away from their computer.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.services.auth_service import LocalAuthService


class VaultLockOverlay(QFrame):
    """Full-coverage overlay presenting a lock screen when private vault is locked."""

    unlocked = Signal()

    def __init__(self, auth_service: LocalAuthService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.auth_service = auth_service
        self.setObjectName("VaultLockOverlay")
        self.setStyleSheet("""
            QFrame#VaultLockOverlay {
                background-color: #080b13;
                border: none;
            }
        """)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        card = QFrame()
        card.setMaximumWidth(460)
        card.setStyleSheet("""
            QFrame {
                background-color: #0c121e;
                border: 1px solid #182236;
                border-radius: 16px;
                padding: 24px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(14)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        lbl_icon = QLabel("🔒")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 38px; margin-bottom: 4px;")
        card_layout.addWidget(lbl_icon)

        # Title
        lbl_title = QLabel("Private Vault Locked")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font_title = QFont()
        font_title.setPointSize(16)
        font_title.setBold(True)
        lbl_title.setFont(font_title)
        lbl_title.setStyleSheet("color: #38bdf8; letter-spacing: 0.3px;")
        card_layout.addWidget(lbl_title)

        # Subtitle
        lbl_sub = QLabel(
            "Your conversations, code snippets, and context files are encrypted "
            "and locked on this local device."
        )
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        card_layout.addWidget(lbl_sub)

        # PIN input
        self.txt_pin = QLineEdit()
        self.txt_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pin.setPlaceholderText("Enter Security PIN")
        self.txt_pin.setStyleSheet("""
            QLineEdit {
                background-color: #060911;
                color: #f8fafc;
                border: 1px solid #1e2e4a;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                letter-spacing: 4px;
                text-align: center;
            }
            QLineEdit:focus {
                border-color: #0284c7;
                background-color: #080b13;
            }
        """)
        self.txt_pin.returnPressed.connect(self._on_unlock_clicked)
        card_layout.addWidget(self.txt_pin)

        # Error label
        self.lbl_error = QLabel("")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 500;")
        card_layout.addWidget(self.lbl_error)

        # Unlock button
        self.btn_unlock = QPushButton("Unlock Private Vault")
        self.btn_unlock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_unlock.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_unlock.clicked.connect(self._on_unlock_clicked)
        card_layout.addWidget(self.btn_unlock)

        # Footer security badge
        lbl_footer = QLabel("🔒 100% Local-First Protection • Zero Cloud Exposure")
        lbl_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_footer.setStyleSheet("color: #475569; font-size: 10px; margin-top: 8px;")
        card_layout.addWidget(lbl_footer)

        layout.addWidget(card)

    def focus_pin_input(self) -> None:
        """Clear previous text and focus the PIN entry field."""
        self.txt_pin.clear()
        self.lbl_error.setText("")
        self.txt_pin.setFocus()

    def _on_unlock_clicked(self) -> None:
        pin = self.txt_pin.text().strip()
        if self.auth_service.unlock(pin):
            self.lbl_error.setText("")
            self.txt_pin.clear()
            self.unlocked.emit()
        else:
            self.lbl_error.setText("Incorrect security PIN. Please try again.")
            self.txt_pin.clear()
            self.txt_pin.setFocus()
