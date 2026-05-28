from __future__ import annotations


APP_QSS = """
QMainWindow {
    background: #101418;
    color: #eef2f3;
}
QWidget {
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 13px;
}
QPushButton {
    background: #0f766e;
    border: 0;
    border-radius: 6px;
    color: white;
    min-height: 34px;
    padding: 6px 12px;
}
QPushButton:hover {
    background: #0d9488;
}
QTextEdit, QLineEdit, QPlainTextEdit, QTableWidget {
    background: #182026;
    border: 1px solid #334047;
    border-radius: 6px;
    color: #eef2f3;
    padding: 6px;
}
QLabel#MetricCard {
    background: #182026;
    border: 1px solid #334047;
    border-radius: 8px;
    padding: 12px;
}
QFrame#Sidebar {
    background: #0b1115;
    border-right: 1px solid #27323a;
}
QPlainTextEdit#ActivityConsole {
    background: #080c0f;
    color: #a7f3d0;
}
"""
