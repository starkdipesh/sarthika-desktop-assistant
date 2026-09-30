"""Welcome and workflow selection widget for Sarthika Code.

Provides the 'What are you working on?' entry point allowing developers to select
a curated workflow when starting or viewing a new conversation.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.domain.workflow import Workflow
from sarthika_code.prompts.registry import WorkflowRegistry


class WorkflowCard(QFrame):
    """Interactive card representing a single curated workflow."""

    clicked = Signal(str)  # workflow_id

    def __init__(self, workflow: Workflow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workflow = workflow
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("WorkflowCard")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet("""
            QFrame#WorkflowCard {
                background-color: #0c1424;
                border: 1px solid #1a273e;
                border-radius: 12px;
                padding: 12px;
            }
            QFrame#WorkflowCard:hover {
                background-color: #111d33;
                border: 1px solid #0284c7;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        # Header: Name & Language badge
        header_layout = QHBoxLayout()
        name_lbl = QLabel(self.workflow.name)
        name_font = QFont()
        name_font.setPointSize(11)
        name_font.setBold(True)
        name_lbl.setFont(name_font)
        name_lbl.setStyleSheet("color: #f1f5f9; font-weight: 600;")
        header_layout.addWidget(name_lbl)

        header_layout.addStretch()

        if self.workflow.recommended_language:
            lang_text = self.workflow.recommended_language[0]
            lang_badge = QLabel(f" {lang_text} ")
            lang_badge.setStyleSheet(
                "background-color: #0c2b4d; color: #7dd3fc; border: 1px solid #0284c7; border-radius: 4px; font-size: 10px; font-weight: bold; padding: 2px 6px;"
            )
            header_layout.addWidget(lang_badge)

        layout.addLayout(header_layout)

        # Description
        desc_lbl = QLabel(self.workflow.description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; line-height: 1.5;")
        layout.addWidget(desc_lbl)

        layout.addStretch()

        # Action button
        btn_action = QPushButton("Select →")
        btn_action.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_action.setStyleSheet("""
            QPushButton {
                background-color: #0c1e36;
                color: #38bdf8;
                border: 1px solid #0284c7;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0284c7;
                color: #ffffff;
            }
        """)
        btn_action.clicked.connect(lambda: self.clicked.emit(self.workflow.id))
        layout.addWidget(btn_action, alignment=Qt.AlignmentFlag.AlignRight)

    def mousePressEvent(self, event: object) -> None:
        self.clicked.emit(self.workflow.id)


class WorkflowSelectionWidget(QWidget):
    """Grid of curated developer workflows presented on empty/new conversations."""

    workflow_selected = Signal(str)  # workflow_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 28, 24, 20)
        main_layout.setSpacing(20)

        # Centered Sarthika Welcome Hero
        header_box = QVBoxLayout()
        header_box.setSpacing(8)
        header_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        heading = QLabel("✦ Sarthika Code")
        heading_font = QFont()
        heading_font.setPointSize(20)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        heading.setStyleSheet("color: #38bdf8; letter-spacing: 0.5px;")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_box.addWidget(heading)

        subheading = QLabel("How can I help you code?")
        subheading_font = QFont()
        subheading_font.setPointSize(14)
        subheading_font.setBold(True)
        subheading.setFont(subheading_font)
        subheading.setStyleSheet("color: #f8fafc;")
        subheading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_box.addWidget(subheading)

        tagline = QLabel(
            "Private, local-first desktop AI coding assistant. Choose a workflow below or start typing in the composer."
        )
        tagline.setStyleSheet("color: #64748b; font-size: 12px;")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_box.addWidget(tagline)

        main_layout.addLayout(header_box)

        # Scrollable container for workflow cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        cards_container = QWidget()
        cards_container.setStyleSheet("background-color: transparent;")
        grid = QGridLayout(cards_container)
        grid.setSpacing(12)
        grid.setContentsMargins(12, 8, 12, 8)

        workflows = WorkflowRegistry.list_workflows()
        cols = 2
        for idx, wf in enumerate(workflows):
            card = WorkflowCard(wf)
            card.clicked.connect(self.workflow_selected.emit)
            r = idx // cols
            c = idx % cols
            grid.addWidget(card, r, c)

        scroll.setWidget(cards_container)
        main_layout.addWidget(scroll, stretch=1)
