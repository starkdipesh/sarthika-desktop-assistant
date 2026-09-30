"""Dedicated code editor widget for Sarthika Code.

Provides multi-line code input, line numbers, syntax highlighting, token counting,
and privacy disclosures stating that pasted code remains strictly on the local machine.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QTextFormat
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sarthika_code.prompts.context_builder import estimate_tokens
from sarthika_code.ui.editor.syntax_highlighter import CodeSyntaxHighlighter


class LineNumberArea(QWidget):
    """Gutter widget displaying line numbers adjacent to the code editor."""

    def __init__(self, editor: CodeEditorTextEdit) -> None:
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self.code_editor.line_number_area_paint_event(event)


class CodeEditorTextEdit(QPlainTextEdit):
    """Text editor with custom line number area and monospace font."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        font = QFont("Monospace", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #030712;
                color: #e2e8f0;
                border: 1px solid #1e293b;
                border-radius: 4px;
                padding: 4px;
            }
        """)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(max(1, self.blockCount()))))
        space = 10 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def update_line_number_area_width(self, _: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self) -> None:
        extra_selections: list[QTextEdit.ExtraSelection] = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#0f172a")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event: QPaintEvent) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#0b1120"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#475569"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


class DedicatedCodeEditor(QWidget):
    """Full-featured code input component with syntax highlighting, token count, and privacy notices."""

    snippet_submitted = Signal(str, str)  # code, language

    LANGUAGES: tuple[tuple[str, str], ...] = (
        ("Python", "python"),
        ("PHP", "php"),
        ("JavaScript", "javascript"),
        ("TypeScript", "typescript"),
        ("SQL", "sql"),
        ("HTML", "html"),
        ("CSS", "css"),
        ("JSON", "json"),
        ("Bash", "bash"),
    )

    def __init__(self, parent: QWidget | None = None, initial_language: str = "python") -> None:
        super().__init__(parent)
        self._init_ui()
        if initial_language:
            self.set_language(initial_language)

    @property
    def language(self) -> str:
        return self.get_language()

    def set_language(self, language: str) -> None:
        idx = self.combo_lang.findData(language.lower())
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # Language dropdown
        lbl_lang = QLabel("Language:")
        lbl_lang.setStyleSheet("color: #94a3b8; font-size: 11px;")
        toolbar.addWidget(lbl_lang)

        self.combo_lang = QComboBox()
        self.combo_lang.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
            }
            QComboBox::drop-down { border: none; }
        """)
        for display, key in self.LANGUAGES:
            self.combo_lang.addItem(display, key)
        self.combo_lang.currentIndexChanged.connect(self._on_language_changed)
        toolbar.addWidget(self.combo_lang)

        # Copy button
        self.btn_copy = QPushButton("Copy")
        self.btn_copy.setStyleSheet("""
            QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; padding: 3px 10px; border-radius: 4px; font-size: 11px; }
            QPushButton:hover { background-color: #334155; }
        """)
        self.btn_copy.clicked.connect(self._copy_code)
        toolbar.addWidget(self.btn_copy)

        # Paste button
        self.btn_paste = QPushButton("Paste")
        self.btn_paste.setStyleSheet("""
            QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; padding: 3px 10px; border-radius: 4px; font-size: 11px; }
            QPushButton:hover { background-color: #334155; }
        """)
        self.btn_paste.clicked.connect(self._paste_code)
        toolbar.addWidget(self.btn_paste)

        # Clear button
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setStyleSheet("""
            QPushButton { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; padding: 3px 10px; border-radius: 4px; font-size: 11px; }
            QPushButton:hover { background-color: #334155; }
        """)
        self.btn_clear.clicked.connect(self.clear)
        toolbar.addWidget(self.btn_clear)

        toolbar.addStretch()

        # Insert / Attach button
        self.btn_insert = QPushButton("Attach Code to Prompt →")
        self.btn_insert.setStyleSheet("""
            QPushButton { background-color: #0284c7; color: white; border: none; padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background-color: #0369a1; }
        """)
        self.btn_insert.clicked.connect(self._on_insert_clicked)
        toolbar.addWidget(self.btn_insert)

        layout.addLayout(toolbar)

        # Code Editor
        self.editor = CodeEditorTextEdit()
        self.editor.setPlaceholderText("Paste or type code snippet here for local-only analysis...")
        self.editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.editor, stretch=1)

        # Syntax highlighter
        self.highlighter = CodeSyntaxHighlighter(self.editor.document(), language="python")

        # Footer stats & privacy statement
        footer = QHBoxLayout()
        footer.setSpacing(12)

        self.lbl_stats = QLabel("Chars: 0 | Tokens: ~0")
        self.lbl_stats.setStyleSheet("color: #94a3b8; font-size: 11px;")
        footer.addWidget(self.lbl_stats)

        footer.addStretch()

        # Clear local-only privacy label
        lbl_privacy = QLabel("🔒 Local-first: Pasted code is processed only by your local llama-server, never cloud services.")
        lbl_privacy.setStyleSheet("color: #38bdf8; font-size: 10px; font-style: italic;")
        footer.addWidget(lbl_privacy)

        layout.addLayout(footer)

    def get_code(self) -> str:
        """Return the current code content."""
        return self.editor.toPlainText()

    def get_language(self) -> str:
        """Return the currently selected language key."""
        return str(self.combo_lang.currentData())

    def set_code(self, code: str, language: str | None = None) -> None:
        """Set editor code and optionally update language."""
        self.editor.setPlainText(code)
        if language:
            idx = self.combo_lang.findData(language.lower())
            if idx >= 0:
                self.combo_lang.setCurrentIndex(idx)

    def clear(self) -> None:
        """Clear the editor content."""
        self.editor.clear()

    def _copy_code(self) -> None:
        text = self.editor.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _paste_code(self) -> None:
        text = QApplication.clipboard().text()
        if text:
            self.editor.setPlainText(text)

    def _on_text_changed(self) -> None:
        text = self.editor.toPlainText()
        lines = len(text.splitlines()) if text else 0
        chars = len(text)
        tokens = estimate_tokens(text)
        self.lbl_stats.setText(f"Lines: {lines} | Chars: {chars:,} | Est. Tokens: ~{tokens:,}")

    def _on_language_changed(self, index: int) -> None:
        lang = self.combo_lang.itemData(index)
        if lang:
            self.highlighter.set_language(str(lang))

    def _on_insert_clicked(self) -> None:
        code = self.get_code()
        if code.strip():
            self.snippet_submitted.emit(code, self.get_language())
