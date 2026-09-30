"""Product limitations and realities dialog for Sarthika Code.

Communicates candid, honest limitations regarding model accuracy, hardware
performance expectations, non-autonomy, and security responsibilities.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class LimitationsDialog(QDialog):
    """Dialog disclosing realistic product boundaries, accuracy caveats, and hardware dependencies."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Product Realities & Limitations — Sarthika Code")
        self.resize(680, 560)
        self.setMinimumSize(540, 420)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Header
        title_lbl = QLabel("Product Realities & Engineering Limitations")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet("color: #f59e0b;")
        layout.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Sarthika Code is an assistive software tool, not an autonomous engineer. "
            "Please review the following essential engineering realities before using the product."
        )
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(sub_lbl)

        # Scroll Area for Caveats
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #1e293b; background-color: #0f172a; border-radius: 6px; }")

        container = QWidget()
        container.setStyleSheet("background-color: #0f172a;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(14, 14, 14, 14)
        c_layout.setSpacing(12)

        c_layout.addWidget(
            self._create_card(
                "1. Generated Code Requires Human Review and Testing",
                "Small local language models (such as Qwen2.5-Coder 3B) can produce subtle bugs, syntax errors, "
                "outdated library calls, or security oversights. Sarthika Code does not guarantee correctness, "
                "and you must verify, inspect, and unit-test all suggestions prior to production deployment."
            )
        )

        c_layout.addWidget(
            self._create_card(
                "2. Not AGI and Not an Autonomous Agent",
                "Sarthika Code does not possess general intelligence, self-directed agency, or long-horizon autonomy. "
                "It executes turn-by-turn prompts according to curated workflow templates."
            )
        )

        c_layout.addWidget(
            self._create_card(
                "3. Hardware Performance & Memory Dependencies",
                "Inference speed and capability depend entirely on your computer's CPU instructions, memory bandwidth, "
                "model quantization, and selected context size:\n"
                "• 8 GB RAM: Best-effort tier. Restricted to low-memory mode (2,048 tokens). Heavy system memory pressure can cause slowdowns.\n"
                "• 16 GB RAM: Recommended tier for standard 4,096-token development workflows.\n"
                "• Higher Contexts: Presets of 8,192+ tokens demand significant RAM for the KV-cache and prolong CPU generation times."
            )
        )

        c_layout.addWidget(
            self._create_card(
                "4. No Web Browsing or Unselected Repository Access",
                "In Version 0.1, the application cannot browse the Internet, fetch live documentation, "
                "or index your entire disk. The model only receives the explicit file snippets you attach in the Context panel."
            )
        )

        c_layout.addWidget(
            self._create_card(
                "5. No Code Execution or File Modification",
                "Sarthika Code will never run commands in your shell, compile your binaries, execute generated code, "
                "or modify existing files on disk. You retain complete control over all file modifications."
            )
        )

        c_layout.addWidget(
            self._create_card(
                "6. No Security Guarantee",
                "Model-generated code does not come with security guarantees. It may suggest insecure patterns, "
                "hardcoded credentials, or vulnerable dependencies if prompted without appropriate constraints."
            )
        )

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        # Footer Button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("I Understand")
        btn_close.setStyleSheet("background-color: #2563eb; color: white; padding: 6px 18px; font-weight: bold; border-radius: 4px;")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    def _create_card(self, title: str, text: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background-color: #1e293b; border-radius: 4px; padding: 10px; border: 1px solid #334155;")
        flayout = QVBoxLayout(frame)
        flayout.setContentsMargins(8, 6, 8, 6)
        flayout.setSpacing(4)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-weight: bold; color: #f8fafc; font-size: 11px;")
        flayout.addWidget(lbl_t)

        lbl_b = QLabel(text)
        lbl_b.setWordWrap(True)
        lbl_b.setStyleSheet("color: #cbd5e1; font-size: 11px; line-height: 1.4;")
        flayout.addWidget(lbl_b)

        return frame
