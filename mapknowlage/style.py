"""Общие цвета и таблицы стилей."""

from __future__ import annotations


def app_stylesheet(text: str, display: str) -> str:
    return f"""
    QToolTip {{
        background: #f4e6c0;
        color: #2b1e12;
        border: 1px solid #4a3420;
        padding: 4px 6px;
        font-family: "{text}";
        font-size: 15px;
    }}
    QMenu {{
        background: #f4e6c0;
        color: #2b1e12;
        border: 2px solid #4a3420;
        padding: 4px 0;
        font-family: "{text}";
        font-size: 16px;
    }}
    QMenu::item {{
        padding: 6px 22px;
    }}
    QMenu::item:selected {{
        background: #e0c27a;
    }}
    QMenu::separator {{
        height: 1px;
        background: #8c6b1f;
        margin: 4px 8px;
    }}
    """


def journal_stylesheet(text: str) -> str:
    return f"""
    QDialog, QScrollArea, QWidget#page {{
        background: transparent;
        color: #24180f;
    }}
    QLabel, QCheckBox {{
        font-family: "{text}";
        color: #24180f;
        background: transparent;
    }}
    QLabel#name {{
        font-size: 34px;
        font-weight: 600;
        color: #1c140e;
    }}
    QLabel#meta {{
        font-size: 18px;
        font-style: italic;
        color: #3a2c20;
    }}
    QLabel#section {{
        font-size: 18px;
        font-weight: 700;
        color: #1c140e;
    }}
    QLabel#bio, QLabel#family, QLabel#book {{
        font-size: 16px;
        color: #24180f;
    }}
    QLabel#bullet {{
        font-size: 16px;
        color: #1c140e;
    }}
    QComboBox, QTextEdit {{
        font-family: "{text}";
        font-size: 15px;
        background: rgba(255, 248, 230, 150);
        color: #24180f;
        border: 1px solid #8a6a3a;
        padding: 3px 6px;
    }}
    QPushButton {{
        font-family: "{text}";
        font-size: 15px;
        background: transparent;
        color: #24180f;
        border: none;
        padding: 4px 0;
        text-align: left;
    }}
    QPushButton:hover {{
        color: #6a4a16;
    }}
    QPushButton#star {{
        border: none;
        background: transparent;
        padding: 0;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(80, 52, 24, 90);
        border-radius: 4px;
    }}
    """
