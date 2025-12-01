#!python
import numpy as np
import sys
from cubit_utils import *

# 1. Update Imports to PySide6
from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, \
                       QLineEdit, QDialogButtonBox, QPushButton, QMessageBox

#
# Draw rebar block edge orientation.
#
class TireRebarDirection(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.resize(239, 150)
        self.setWindowTitle("Draw Rebar Blocks")
        self.setObjectName("TireDrawRebar")

        self.gridLayout = QGridLayout(self)
        self.rebarBlockLabel = QLabel(u"Select Rebar Blocks:")
        self.gridLayout.addWidget(self.rebarBlockLabel, 0, 0)
        self.rebarBlockLineEdit = QLineEdit()
        self.gridLayout.addWidget(self.rebarBlockLineEdit, 0, 1)
        self.blockSelect = QPushButton()
        self.blockSelect.setText("Add Selected Blocks")
        self.gridLayout.addWidget(self.blockSelect, 0, 2) 
        self.blockSelect.clicked.connect(self.GetSelected)
        self.rebarScaleLabel = QLabel(u"Arrow Scale (1.0 is edge length)):")
        self.gridLayout.addWidget(self.rebarScaleLabel, 1, 0)
        self.rebarScaleLineEdit = QLineEdit()
        self.gridLayout.addWidget(self.rebarScaleLineEdit, 1, 1)
        self.rebarScaleLineEdit.setText("1.0")

        # 2. Update Dialog Button Enums
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("Draw")
        self.buttonBox.accepted.connect(self.DrawRebarDirection)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.gridLayout.addWidget(self.buttonBox, 2, 1)
        self.setLayout(self.gridLayout)
        QMetaObject.connectSlotsByName(self)
        # Assuming cubit object is available globally/in scope
        cubit.set_pick_type('Block')
    # end init -- create GUI

    def GetSelected(self):
        ids = cubit.get_selected_ids()
        if not ids:
            # Using ErrorWindow from cubit_utils
            ErrorWindow("Select the Blocks Containing Rebar.")
            return
        current_block_str = self.rebarBlockLineEdit.text()
        current_blocks = cubit.parse_cubit_list('block', current_block_str)
        block_str = cubit.string_from_id_list(current_blocks + ids)
        self.rebarBlockLineEdit.setText(block_str)
        
    def GetRebarLineEdit(self):
        rebar_block_str = self.rebarBlockLineEdit.text()
        if not rebar_block_str:
            return []
        rebar_blocks = cubit.parse_cubit_list('block', rebar_block_str)
        return rebar_blocks 

    def DrawRebarDirection(self):
        # Access 'claro' via global keyword here
        global claro
        
        block_ids = self.GetRebarLineEdit()
        scale_str = self.rebarScaleLineEdit.text()
        if scale_str: 
            try:
                scale = float(scale_str)
                assert(scale != 0)
            except ValueError: # Catch ValueError from float(scale_str) if input is non-numeric
                ErrorWindow("Scale must be a nonzero value.")
                return
            except AssertionError: # Catch if scale is 0
                ErrorWindow("Scale must be a nonzero value.")
                return
        else:
            ErrorWindow("Scale must contain a real nonzero value.")
            return

        # 3. Update Qt.WaitCursor to PySide6 Enum syntax
        claro.setCursor(Qt.CursorShape.WaitCursor)
        
        for block_id in block_ids:
            edges = cubit.get_block_edges(block_id)
            for edge in edges:
                conn = cubit.get_connectivity('edge', edge)
                loc1 = np.array(cubit.get_nodal_coordinates(conn[0]))
                loc2 = np.array(cubit.get_nodal_coordinates(conn[1]))
                dir = loc2 - loc1
                length = np.linalg.norm(dir) * scale
                cubit.silent_cmd(f'draw axis direction {dir[0]} {dir[1]} {dir[2]} origin node {conn[0]} length {length}')
        
        claro.unsetCursor()
            
def main():
    # 'claro' must be defined in the calling scope
    global claro
    dlg = TireRebarDirection(claro)
    dlg.show() 

if __name__ == "__coreformcubit__":
    global claro
    claro = find_claro()
    
    main()
