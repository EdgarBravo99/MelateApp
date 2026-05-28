from __future__ import annotations


APP_QSS = """
QMainWindow, QWidget#AppRoot {
    background: #f4f7f6;
    color: #10201f;
}
QWidget {
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 13px;
}
QWidget#MainSurface {
    background: #f4f7f6;
}
QLabel {
    color: #10201f;
}
QLabel#PageTitle {
    color: #082f2e;
    font-size: 24px;
    font-weight: 700;
}
QLabel#PageSubtitle {
    color: #496765;
    font-size: 13px;
}
QFrame#Panel {
    background: #ffffff;
    border: 1px solid #dce8e5;
    border-radius: 8px;
}
QPushButton {
    background: #0f766e;
    border: 0;
    border-radius: 6px;
    color: #ffffff;
    min-height: 34px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background: #14b8a6;
}
QPushButton:pressed {
    background: #0b5f58;
}
QPushButton:disabled {
    background: #cddbd8;
    color: #9fbab5;
}
QFrame#Sidebar {
    background: #073b3a;
    border-right: 1px solid #062f2e;
}
QLabel#SidebarBrand {
    color: #ffffff;
    font-size: 22px;
    font-weight: 800;
    padding: 0 0 18px 2px;
}
QPushButton#SidebarButton {
    background: transparent;
    border-radius: 6px;
    color: #c6f7ee;
    min-height: 38px;
    padding: 8px 12px;
    text-align: left;
    font-weight: 650;
}
QPushButton#SidebarButton:hover {
    background: rgba(20, 184, 166, 0.18);
    color: #ffffff;
}
QPushButton#SidebarButton:checked {
    background: #14b8a6;
    color: #042524;
}
QTextEdit, QLineEdit, QPlainTextEdit, QTableWidget {
    background: #ffffff;
    border: 1px solid #cddbd8;
    border-radius: 6px;
    color: #10201f;
    padding: 6px;
    selection-background-color: #14b8a6;
    selection-color: #042524;
}
QTextEdit:focus, QLineEdit:focus, QPlainTextEdit:focus, QTableWidget:focus {
    border: 1px solid #0f766e;
}
QLabel#MetricCard {
    background: #ffffff;
    border: 1px solid #dce8e5;
    border-radius: 8px;
    color: #10201f;
    font-weight: 700;
    min-height: 58px;
    padding: 12px;
}
QPlainTextEdit#ActivityConsole {
    background: #071312;
    border: 1px solid #073b3a;
    color: #a7f3d0;
    font-family: Consolas, Cascadia Mono, monospace;
}
QProgressBar {
    background: #ffffff;
    border: 1px solid #cddbd8;
    border-radius: 6px;
    color: #10201f;
    height: 14px;
    text-align: center;
}
QProgressBar::chunk {
    background: #14b8a6;
    border-radius: 5px;
}
QTableWidget#DataTable {
    alternate-background-color: #edf7f5;
    gridline-color: #dce8e5;
}
QHeaderView::section {
    background: #e5efed;
    border: 0;
    border-right: 1px solid #cddbd8;
    color: #082f2e;
    font-weight: 700;
    min-height: 32px;
    padding: 6px;
}
QScrollBar:vertical {
    background: #edf3f1;
    width: 12px;
}
QScrollBar::handle:vertical {
    background: #9fbab5;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar:horizontal {
    background: #edf3f1;
    height: 12px;
}
QScrollBar::handle:horizontal {
    background: #9fbab5;
    border-radius: 5px;
    min-width: 24px;
}
"""
