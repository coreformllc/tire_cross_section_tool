#!python
"""
    Given an existing set of curves. Find the bounding extent of the curves and
    create a surface that extends somewhat larger than the curves. Use the tolerant
    imprint option to imprint the curves onto the surface. Then separate each surface
    so that they become their own bodies. 
"""
import math
import sys

from PySide6.QtCore import QMetaObject, Qt

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, \
    QLineEdit, QDialogButtonBox, QMessageBox

import cubit_utils

class TireGeometry(QDialog):
    # Create the GUI
    def __init__(self, parent):
        super().__init__(parent)
        self.resize(239, 124)
        self.setWindowTitle("Create Tire Surfaces")

        self.gridLayout = QGridLayout(self)
        self.smallestCurveIDLabel = QLabel(u"Smallest Curve ID:")
        self.gridLayout.addWidget(self.smallestCurveIDLabel, 0, 0)
        self.smallestCurveIDData = QLabel()
        # 2. Update Qt.LinksAccessibleByMouse|Qt.TextSelectableByMouse to PySide6 syntax
        self.smallestCurveIDData.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.gridLayout.addWidget(self.smallestCurveIDData, 0, 1)

        self.smallestCurveLengthLabel = QLabel(u"Smallest Curve Length:")
        self.gridLayout.addWidget(self.smallestCurveLengthLabel, 1, 0)
        self.smallestCurveLengthData = QLabel()
        # 2. Update Qt.LinksAccessibleByMouse|Qt.TextSelectableByMouse to PySide6 syntax
        self.smallestCurveLengthData.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.gridLayout.addWidget(self.smallestCurveLengthData, 1, 1)

        self.mergeToleranceLabel = QLabel("Merge Tolerance")
        self.gridLayout.addWidget(self.mergeToleranceLabel, 2, 0)
        self.mergeTolerance = QLineEdit()
        self.mergeTolerance.setText(".03")
        self.gridLayout.addWidget(self.mergeTolerance, 2, 1)

        # 3. Update Dialog Button Enums
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.accepted.connect(self.CreateTireGeometry)
        self.buttonBox.rejected.connect(self.reject)
        self.gridLayout.addWidget(self.buttonBox, 3, 1)

        self.setLayout(self.gridLayout)
        # QMetaObject.connectSlotsByName(self) is typically only needed if you rely on auto-connecting named slots
        
        self.all_curves = ()
    # end init -- create GUI

    # Get all the curves, and the lengths, then get the curve with the minimum length
    def FindSmallestCurve(self):
        if not self.all_curves:
            self.all_curves = cubit.get_entities("curve")
        if not self.all_curves:
            # Assumes ErrorWindow is defined below
            cubit_utils.ErrorWindow("Curves must be read from file before creating the geometry")
            return ()
        lengths = [cubit.get_curve_length(c) for c in self.all_curves]
        min_length = min(lengths)
        index = lengths.index(min_length)
        min_id = self.all_curves[index]
        return (min_id, min_length) 
        
    # Implement the algorithm defined at the start of the module.
    def CreateTireGeometry(self):
        # curves should previously exist
        if not self.all_curves:
            self.all_curves = cubit.get_entities("curve")
        if not self.all_curves:
            ErrorWindow("Curves must be read from file before creating the geometry.")
            return

        cubit.cmd("undo group begin")
        cubit.cmd("graphics off")
        # get the bounding box and define the width and height to be 10% larger
        bbox = cubit.get_total_bounding_box("curve", self.all_curves)
        width = bbox[2] * 1.1
        height = bbox[5] * 1.1
        xdisp = (bbox[0] + bbox[1])/2
        ydisp = (bbox[3] + bbox[4])/2
    
        # Create the bounding surface
        # we know that at this point this is surface 1
        cubit.cmd(f'create surface rectangle width {width} height {height}')
        last_vertex = cubit.get_last_id("vertex")
        cubit.cmd(f'move surface 1 x {xdisp} y {ydisp}')
        
        if self.mergeTolerance.text():
            self.merge_tolerance = float(self.mergeTolerance.text())
            if self.merge_tolerance <= 0.0:
                cubit_utils.ErrorWindow("Merge Tolerance must be > 0.0")
                cubit.cmd("undo group end")
                return
        else:
            cubit_utils.ErrorWindow("Merge Tolerance must be set. Half of the smallest curve length may be an appropriate value.")
            cubit.cmd("undo group end")
            return

        # Do a tolerant imprint to close small gaps in the model
        cubit.cmd(f"merge tolerance {self.merge_tolerance}")
        cubit.cmd("imprint tolerant surface 1 with curve all except curve in surf 1") 
        cubit.cmd("merge tolerance 5.000000e-04")
        cubit.cmd("imprint surface 1 with curve all")

        # separate the surfaces into individual bodies
        surfs = cubit.get_entities("surface")
        for surf in surfs:
            cubit.cmd(f'separate surface {surf}')

        # clean up
        cubit.cmd(f'delete surface in vertex {last_vertex}') 
        cubit.cmd('delete curve all') # remove free curves
    
        # make sure everything is merged and finish
        original_tolerance = cubit.get_merge_tolerance()
        cubit.cmd(f"merge tolerance {self.merge_tolerance}")
        cubit.cmd("merge all")
        cubit.cmd(f"merge tolerance {original_tolerance}")
        cubit.cmd("graphics on")
        cubit.cmd("undo group end")



def main():
    # 'claro' must be defined in the calling scope (the __main__ block)
    global claro
    dlg = TireGeometry(claro)
    min_data = dlg.FindSmallestCurve()
    if min_data:
        dlg.smallestCurveIDData.setText(str(min_data[0]))
        dlg.smallestCurveLengthData.setText("%.4f" % min_data[1])
        suggested_tolerance = math.floor(min_data[1]*50)/100 # ((length/2)*100)/100
        dlg.mergeTolerance.setText(str(suggested_tolerance))
        dlg.show()

if __name__ == "__coreformcubit__":
    global claro
    claro = cubit_utils.find_claro()
    main()

