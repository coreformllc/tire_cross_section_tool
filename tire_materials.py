#!python
"""
    Define the elment blocks (ELSETs) for different material regions.
    The primary tool used is to fire a ray from a "center" point of the 
    tire region and then determine materials that lie along that ray.
    There are many materials that are not identified. 
"""
from itertools import chain
from math import *
import sys

from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel
from PySide6.QtWidgets import QLineEdit, QDialogButtonBox, QMessageBox

# Use general cubit_utils
import cubit_utils


class TireMaterials(QDialog):
    # create the GUI
    def __init__(self, parent):
        super().__init__(parent)
        self.resize(239, 150)
        self.setWindowTitle("Create Element Sets (Blocks)")
        self.setObjectName("TireMaterials")

        self.gridLayout = QGridLayout(self) # Pass self to the layout
        self.plyLabel = QLabel(u"Number of plys")
        self.gridLayout.addWidget(self.plyLabel, 0, 0)
        self.plyLineEdit = QLineEdit()
        self.gridLayout.addWidget(self.plyLineEdit, 0, 1)

        # Set Dialog Button Enums
        QBtn = QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        
        # Note: button() needs the StandardButton enum in PySide6
        self.buttonBox.button(QDialogButtonBox.StandardButton.Yes).setText("Create Blocks")
        
        self.buttonBox.accepted.connect(self.AssignMaterials)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.gridLayout.addWidget(self.buttonBox, 1, 1)
        self.setLayout(self.gridLayout)
        QMetaObject.connectSlotsByName(self)
    # init -- create GUI

    # given a set of curves find the bodies in the curves ordered
    # from inside to outside.
    def get_bodies_from_curves(self, curves):
        body_list = []
        for curve in curves:
            bodies = cubit.parse_cubit_list('body', f'in curve {curve}')
            body_list.append(bodies)
    
        # remove tuples from list
        body_list = list(chain(*body_list))
    
        # ordered sort. Inside body is first, outside body is last
        body_list = list(dict.fromkeys(body_list))
        return body_list

    # Assign Material names
    def AssignMaterials(self):
        bodies = cubit.get_entities("body")
        bbox = cubit.get_total_bounding_box("body", bodies)
        xmin = bbox[0]
        xmax = bbox[1]
        xcenter = (xmin + xmax)/2
        ycenter = (bbox[3] + bbox[4])/2

        # set up blocks
        for body in bodies:
            # make sure block numbering matches the body numbering
            cubit.cmd(f'block {body} body {body}')
            #cubit.cmd(f'block {body} element type QUAD4')
    
        all_curves = cubit.get_entities('curve')
        origin = [xcenter, ycenter, 0]
        # bodies in the -Y direction
        direction = [0, -1, 0]
        # We can't get the bodies since they are planar intersections so get the curves instead
        _, curves =  cubit.fire_ray(origin, direction, 'curve', all_curves, 0, .1) 
        ordered_bodies = self.get_bodies_from_curves(curves)
    
        ply_text = self.plyLineEdit.text()
        try:
            print(ply_text)
            number_plys = int(ply_text)
        except Exception as e:
            # Assuming 'claro' is available or the function is updated to be standalone
            WarningWindow("Unable to get number of plys. Assuming one ply.", parent_widget=self) 
            number_plys = 1

        cubit.cmd(f'block {ordered_bodies[0]} name "tire-1_Set-Rubber-Inner"')
        if number_plys == 1:
            cubit.cmd(f'block {ordered_bodies[1]} name "tire-1_Set-Rubber-Bodyply"')
        else:
            for i in range(number_plys):
                cubit.cmd(f'block {ordered_bodies[i+1]} name "tire-1_Set-Rubber-Bodyply-{i+1}"')

        cubit.cmd(f'block {ordered_bodies[-1]} name "tire-1_Set-Rubber-Side"')
    
        # bodies in the +X direction
        origin = [0, -1, 0]    # just move a little off the y x axis
        direction = [1, 0, 0]
        _, curves =  cubit.fire_ray(origin, direction, 'curve', all_curves, 0, .1) 
        ordered_bodies = self.get_bodies_from_curves(curves)
        # the inside body is already assigned a name
        cubit.cmd(f'block {ordered_bodies[-1]} name "tire-1_Set-Rubber-TRD"')
        cubit.cmd(f'block {ordered_bodies[-2]} name "tire-1_Set-Rubber-Base"')

        # assign all layers between the inner rubber and the rubber base as belts
        # this may not be right, but it may be easier to edit if there is something
        # there.
        decrement = 0
        for counter, body in enumerate(ordered_bodies[1:-2]):
            block_name = cubit.get_block_name(body)
            if 'tire' in block_name:
                decrement = decrement + 1
            else:
                cubit.cmd(f'block {body} name "tire-1_Set-Rubber-Belt{counter+1-decrement}"')
    
        # find the tip at the bead
        bead_tuple = cubit.parse_cubit_list("body", f"in vertex with x_coord < {ceil(xmin)}") 
        if len(bead_tuple) == 1:
            bead_tip = bead_tuple[0]
            cubit.cmd(f'block {bead_tip} name "tire-1_Set-Rubber-RC"')

            bead_center = cubit.get_center_point("body", bead_tip)
            origin = [xmin-50, bead_center[1], 0]
            direction = [1, 0, 0]
            _, curves =  cubit.fire_ray(origin, direction, 'curve', all_curves, 0, .1) 
            ordered_bodies = self.get_bodies_from_curves(curves)

            ordered_materials = [
                'tire-1_Set-Rubber-Chafer',
                'tire-1_Set-Rubber-Bead',
                'tire-1_Set-Rubber-DownApex',
                'tire-1_Set-Rubber-UpApex']

            # this is not very accurate so skip it
            #decrement = 0
            #for counter, body in enumerate(ordered_bodies[1:-2]):
            #   block_name = cubit.get_block_name(body)
            #   if 'tire' in block_name:
            #       decrement = decrement + 1
            #   else:
            #       cubit.cmd(f'block {body} name "{ordered_materials[counter-decrement]}"')

def main():
    cubit.cmd("undo group begin")
    # You must ensure 'claro' is defined or imported when main() is called
    # In this context, claro is defined in the __main__ block right before main() is called.
    global claro 
    dlg = TireMaterials(claro)
    # The return value of show() is typically None; you likely want the dialog result, 
    # but the original code just stored the result of the QDialog.show() method.
    dlg.show() 
    cubit.cmd("undo group end")

if __name__ == "__coreformcubit__":
    claro = cubit_utils.find_claro() 
    main()

