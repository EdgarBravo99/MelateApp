from __future__ import annotations


APP_QSS = """
QMainWindow { background: #f4f7f6; color: #10201c; }
QWidget { color: #10201c; font-family: Segoe UI, Arial, sans-serif; font-size: 13px; }
QFrame#Sidebar { background: #073b3a; border-right: 1px solid #062f2f; }
QLabel#SidebarTitle { color: #f0fdfa; font-size: 16px; font-weight: 700; padding: 10px 6px; }
QPushButton { background: #0f766e; border: 0; border-radius: 8px; color: #ffffff; min-height: 34px; padding: 8px 12px; }
QPushButton:hover { background: #0d9488; }
QPushButton:disabled { background: #94a3b8; color: #e2e8f0; }
QPushButton#SidebarButton { background: transparent; border-radius: 8px; color: #ccfbf1; font-weight: 600; text-align: left; padding: 10px 14px; }
QPushButton#SidebarButton:hover { background: #0f766e; }
QPushButton#SidebarButton[active="true"] { background: #14b8a6; color: #052e2b; }
QFrame#Card { background: #ffffff; border: 1px solid #d6e3df; border-radius: 12px; }
QLabel#PageTitle { color: #10201c; font-size: 22px; font-weight: 700; }
QLabel#PageSubtitle { color: #5b6b66; }
QLabel#SectionTitle { color: #10201c; font-size: 15px; font-weight: 700; }
QLabel#MetricCard { background: #ffffff; border: 1px solid #d6e3df; border-radius: 10px; color: #10201c; font-weight: 600; padding: 14px; }
QLineEdit, QTextEdit, QPlainTextEdit, QTableWidget { background: #ffffff; border: 1px solid #cbd8d4; border-radius: 8px; color: #10201c; selection-background-color: #99f6e4; padding: 6px; }
QPlainTextEdit#ActivityConsole { background: #0b1115; border: 1px solid #1f2937; color: #a7f3d0; font-family: Consolas, Cascadia Mono, monospace; }
QHeaderView::section { background: #e7f3ef; border: 0; color: #10201c; font-weight: 700; padding: 6px; }
QProgressBar { background: #e2e8f0; border: 0; border-radius: 6px; color: #10201c; height: 10px; text-align: center; }
QProgressBar::chunk { background: #0f766e; border-radius: 6px; }
"""
