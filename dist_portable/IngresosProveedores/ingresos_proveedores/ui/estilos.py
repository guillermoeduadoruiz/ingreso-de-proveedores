QSS_GLOBAL = '''
QMainWindow {
    background-color: #f5f5f5;
}
QLabel {
    color: #333;
}
QLineEdit, QDateEdit, QSpinBox, QComboBox {
    padding: 6px 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
    background-color: white;
    font-size: 13px;
}
QLineEdit:focus, QDateEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #2196F3;
}
QPushButton {
    padding: 8px 20px;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#btnPrimary {
    background-color: #2196F3;
    color: white;
}
QPushButton#btnPrimary:hover {
    background-color: #1976D2;
}
QPushButton#btnPrimary:disabled {
    background-color: #90CAF9;
}
QPushButton#btnSuccess {
    background-color: #4CAF50;
    color: white;
}
QPushButton#btnSuccess:hover {
    background-color: #388E3C;
}
QPushButton#btnDanger {
    background-color: #f44336;
    color: white;
}
QPushButton#btnDanger:hover {
    background-color: #D32F2F;
}
QPushButton#btnWarning {
    background-color: #FF9800;
    color: white;
}
QPushButton#btnWarning:hover {
    background-color: #F57C00;
}
QPushButton#btnSecondary {
    background-color: #9E9E9E;
    color: white;
}
QPushButton#btnSecondary:hover {
    background-color: #757575;
}
QTableWidget {
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: white;
    gridline-color: #eee;
    selection-background-color: #BBDEFB;
    selection-color: #333;
}
QTableWidget::item {
    padding: 6px 10px;
}
QHeaderView::section {
    background-color: #f0f0f0;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #ddd;
    font-weight: bold;
    color: #555;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #ddd;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    background-color: white;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #555;
}
QStatusBar {
    background-color: #e0e0e0;
    color: #555;
}
QMenuBar {
    background-color: #f0f0f0;
    border-bottom: 1px solid #ddd;
}
QMenuBar::item:selected {
    background-color: #2196F3;
    color: white;
}
QMenu {
    background-color: white;
    border: 1px solid #ddd;
}
QMenu::item:selected {
    background-color: #2196F3;
    color: white;
}
'''
