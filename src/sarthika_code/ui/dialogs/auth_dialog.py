"""Local authentication and security dialogs for Sarthika Code.

Provides SetPinDialog for configuring local vault PIN, and UnlockVaultDialog
for unlocking the private workspace.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.services.auth_service import LocalAuthService


class SetPinDialog(QDialog):
    """Dialog allowing users to set, update, or remove their local security PIN."""

    def __init__(self, auth_service: LocalAuthService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.auth_service = auth_service
        self.setWindowTitle("Local Vault Security PIN")
        self.setFixedSize(440, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #080b13;
                color: #f1f5f9;
            }
        """)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Header with icon
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        lbl_icon = QLabel("🔒")
        lbl_icon.setStyleSheet("font-size: 26px;")
        header_layout.addWidget(lbl_icon)

        title_vbox = QVBoxLayout()
        lbl_title = QLabel("Local Security PIN")
        font_title = QFont()
        font_title.setPointSize(14)
        font_title.setBold(True)
        lbl_title.setFont(font_title)
        lbl_title.setStyleSheet("color: #38bdf8;")
        title_vbox.addWidget(lbl_title)

        lbl_subtitle = QLabel("Protect your private conversations on this device")
        lbl_subtitle.setStyleSheet("color: #94a3b8; font-size: 11px;")
        title_vbox.addWidget(lbl_subtitle)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Explanatory card
        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame {
                background-color: #0c1424;
                border: 1px solid #1c2e4a;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(4)

        lbl_info = QLabel(
            "✦ 100% Local Protection\n"
            "✦ Zero cloud sync or external servers\n"
            "✦ Requires PIN entry whenever vault is locked"
        )
        lbl_info.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.4;")
        info_layout.addWidget(lbl_info)
        layout.addWidget(info_card)

        # Current PIN (if already set)
        has_pin = self.auth_service.is_pin_configured()
        self.txt_current_pin = QLineEdit()
        self.txt_current_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_current_pin.setPlaceholderText("Enter current PIN")
        self.txt_current_pin.setStyleSheet(self._input_style())
        if has_pin:
            lbl_cur = QLabel("Current PIN:")
            lbl_cur.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600;")
            layout.addWidget(lbl_cur)
            layout.addWidget(self.txt_current_pin)

        # New PIN
        lbl_new = QLabel("New Security PIN (at least 4 digits):")
        lbl_new.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600;")
        layout.addWidget(lbl_new)

        self.txt_new_pin = QLineEdit()
        self.txt_new_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_new_pin.setPlaceholderText("Enter new 4-8 digit PIN")
        self.txt_new_pin.setStyleSheet(self._input_style())
        layout.addWidget(self.txt_new_pin)

        # Confirm PIN
        lbl_confirm = QLabel("Confirm New PIN:")
        lbl_confirm.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 600;")
        layout.addWidget(lbl_confirm)

        self.txt_confirm_pin = QLineEdit()
        self.txt_confirm_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_confirm_pin.setPlaceholderText("Confirm new PIN")
        self.txt_confirm_pin.setStyleSheet(self._input_style())
        layout.addWidget(self.txt_confirm_pin)

        # Checkbox: Lock on start
        self.chk_lock_on_start = QCheckBox("Automatically lock vault when application launches")
        self.chk_lock_on_start.setChecked(True)
        self.chk_lock_on_start.setStyleSheet("color: #94a3b8; font-size: 11px; margin-top: 4px;")
        layout.addWidget(self.chk_lock_on_start)

        # Error label
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.lbl_error)

        layout.addStretch()

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        if has_pin:
            self.btn_remove = QPushButton("Remove PIN")
            self.btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_remove.setStyleSheet("""
                QPushButton {
                    background-color: #3b1419;
                    color: #f87171;
                    border: 1px solid #7f1d1d;
                    padding: 8px 14px;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #5c1b22;
                    color: #fca5a5;
                }
            """)
            self.btn_remove.clicked.connect(self._on_remove_clicked)
            btn_layout.addWidget(self.btn_remove)

        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #121c2d;
                color: #94a3b8;
                border: 1px solid #1e2e4a;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1b2a44;
                color: #f1f5f9;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save PIN")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                padding: 8px 18px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #0b111e;
                color: #f8fafc;
                border: 1px solid #162238;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #0284c7;
                background-color: #0e1627;
            }
        """

    def _on_save_clicked(self) -> None:
        has_pin = self.auth_service.is_pin_configured()
        if has_pin:
            cur = self.txt_current_pin.text()
            if not self.auth_service.unlock(cur):
                self.lbl_error.setText("Current PIN is incorrect.")
                return

        new_pin = self.txt_new_pin.text().strip()
        confirm_pin = self.txt_confirm_pin.text().strip()

        if len(new_pin) < 4:
            self.lbl_error.setText("New PIN must be at least 4 digits.")
            return

        if new_pin != confirm_pin:
            self.lbl_error.setText("New PIN and Confirm PIN do not match.")
            return

        self.auth_service.set_pin(new_pin, lock_on_start=self.chk_lock_on_start.isChecked())
        QMessageBox.information(
            self,
            "Security PIN Set",
            "Your local vault security PIN has been successfully saved.\n\n"
            "Use Ctrl+L or click the Lock icon anytime to lock the private vault.",
        )
        self.accept()

    def _on_remove_clicked(self) -> None:
        cur = self.txt_current_pin.text()
        if not self.auth_service.remove_pin(cur):
            self.lbl_error.setText("Current PIN is incorrect.")
            return

        QMessageBox.information(
            self,
            "Security PIN Removed",
            "Your security PIN has been removed. Vault locking is now disabled.",
        )
        self.accept()


class UnlockVaultDialog(QDialog):
    """Modal dialog prompting for PIN to unlock the local vault."""

    def __init__(self, auth_service: LocalAuthService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.auth_service = auth_service
        self.setWindowTitle("Unlock Private Vault")
        self.setFixedSize(380, 260)
        self.setStyleSheet("""
            QDialog {
                background-color: #080b13;
                color: #f1f5f9;
            }
        """)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        lbl_icon = QLabel("🔒")
        lbl_icon.setStyleSheet("font-size: 28px;")
        header_layout.addWidget(lbl_icon)

        title_vbox = QVBoxLayout()
        lbl_title = QLabel("Vault Locked")
        font_title = QFont()
        font_title.setPointSize(14)
        font_title.setBold(True)
        lbl_title.setFont(font_title)
        lbl_title.setStyleSheet("color: #38bdf8;")
        title_vbox.addWidget(lbl_title)

        lbl_sub = QLabel("Enter your local PIN to unlock")
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 11px;")
        title_vbox.addWidget(lbl_sub)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        self.txt_pin = QLineEdit()
        self.txt_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pin.setPlaceholderText("Enter PIN")
        self.txt_pin.setStyleSheet("""
            QLineEdit {
                background-color: #0b111e;
                color: #f8fafc;
                border: 1px solid #162238;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                letter-spacing: 3px;
            }
            QLineEdit:focus {
                border-color: #0284c7;
            }
        """)
        self.txt_pin.returnPressed.connect(self._on_unlock_clicked)
        layout.addWidget(self.txt_pin)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.lbl_error)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #121c2d;
                color: #94a3b8;
                border: 1px solid #1e2e4a;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1b2a44;
                color: #f1f5f9;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_unlock = QPushButton("Unlock Vault")
        self.btn_unlock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_unlock.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                padding: 8px 18px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_unlock.clicked.connect(self._on_unlock_clicked)
        btn_layout.addWidget(self.btn_unlock)

        layout.addLayout(btn_layout)

    def _on_unlock_clicked(self) -> None:
        pin = self.txt_pin.text().strip()
        if self.auth_service.unlock(pin):
            self.accept()
        else:
            self.lbl_error.setText("Incorrect PIN. Please try again.")
            self.txt_pin.clear()
            self.txt_pin.setFocus()

