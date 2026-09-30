"""Diagnostics dialog for Sarthika Code.

Displays system metrics, model status, database paths, and log locations,
with a one-click button to copy a privacy-redacted report to the clipboard.
"""

from __future__ import annotations

from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.services.diagnostics import DiagnosticsService


class DiagnosticsDialog(QDialog):
    """Dialog showing real-time technical diagnostics with copy capabilities."""

    def __init__(
        self,
        diagnostics_service: DiagnosticsService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.diagnostics_service = diagnostics_service

        self.setWindowTitle("System Diagnostics — Sarthika Code")
        self.resize(720, 520)

        self._init_ui()
        self._refresh_report()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.txt_diagnostics = QPlainTextEdit()
        self.txt_diagnostics.setReadOnly(True)
        mono_font = QFont("Courier New", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.txt_diagnostics.setFont(mono_font)
        self.txt_diagnostics.setStyleSheet(
            "background-color: #0f172a; color: #38bdf8; border: 1px solid #334155; border-radius: 6px; padding: 12px;"
        )
        layout.addWidget(self.txt_diagnostics)

        btn_row = QHBoxLayout()

        self.chk_redact = QCheckBox("Redact Home Directory Paths (Safe Sharing)")
        self.chk_redact.setChecked(True)
        self.chk_redact.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        self.chk_redact.stateChanged.connect(self._refresh_report)
        btn_row.addWidget(self.chk_redact)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_report)
        btn_row.addWidget(self.btn_refresh)

        self.btn_copy = QPushButton("Copy Diagnostics")
        self.btn_copy.setStyleSheet(
            "background-color: #2563eb; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px;"
        )
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(self.btn_copy)

        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    def _refresh_report(self) -> None:
        """Fetch updated diagnostics report and render into text view."""
        report = self.diagnostics_service.collect_diagnostics()
        should_redact = getattr(self, "chk_redact", None) is None or self.chk_redact.isChecked()
        formatted_text = report.to_formatted_text(redact=should_redact)
        self.txt_diagnostics.setPlainText(formatted_text)

    def _copy_to_clipboard(self) -> None:
        """Copy the redacted diagnostics text to the system clipboard."""
        # Ensure we always copy the redacted version for safety
        report = self.diagnostics_service.collect_diagnostics()
        text = report.to_formatted_text(redact=True)
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            self.btn_copy.setText("Copied (Redacted)!")
            # Reset button text after short delay
            from PySide6.QtCore import QTimer

            QTimer.singleShot(2000, lambda: self.btn_copy.setText("Copy Diagnostics"))
