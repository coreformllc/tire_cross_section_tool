#!python
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QDockWidget

# I'm not sure why findChild doesn't work
def find_claro():
    qApp = QApplication.instance()
    top_widgets = qApp.topLevelWidgets()
    for w in top_widgets:
        if "Claro" in w.objectName() and type(w).__name__ == 'QMainWindow':
            return w
    return None

def ErrorWindow(error_msg):
    claro = find_claro()
    msg = QMessageBox(claro)
    msg.setIcon(QMessageBox.Critical)
    msg.setText("Error")
    msg.setInformativeText(error_msg)
    msg.setWindowTitle("Error")
    msg.exec_()

def QuestionWindow(error_msg):
    claro = find_claro()
    msg = QMessageBox(claro)
    msg.setIcon(QMessageBox.Question )
    msg.setText(error_msg)
    msg.setWindowTitle("Already Meshed")
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    #msg.setIcon(QMessageBox.Question)
    return msg.exec_()  

def WarningWindow(error_msg):
    claro = find_claro()
    msg = QMessageBox(claro)
    msg.setIcon(QMessageBox.Warning)
    msg.setText("Warning")
    msg.setInformativeText(error_msg)
    msg.setWindowTitle("Warning")
    msg.exec_()


def find_CommandPanel():
    claro = find_claro()
    return claro.findChild(QDockWidget, "CubitCommandPanel")

