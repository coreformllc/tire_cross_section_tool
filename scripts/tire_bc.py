#!python

# create boundary sets nodeset and sidesets (NSET and ELSET in Abaqus).
# Use geometric reasoning and connectedness to find the sets.

from itertools import chain
from math import *

import cubit_utils

from PySide6.QtCore import QMetaObject, Qt

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, \
                              QLabel, QLineEdit, QDialogButtonBox, QPushButton

class BoundaryConditions(QDialog):
    # Define the GUI using PySide6
    def __init__(self, parent):
        super().__init__(parent)
        self.resize(230, 130)
        self.setWindowTitle("Create Boundary Conditions")
        self.setObjectName("TireBCs")

        self.gridLayout = QGridLayout(self)
        self.surfaceVertexLabel = QLabel(u"Select Tip Vertex for Inside/Outside Node sets")
        self.gridLayout.addWidget(self.surfaceVertexLabel, 0, 0)
        self.vertexLineEdit = QLineEdit()
        self.gridLayout.addWidget(self.vertexLineEdit, 1, 0)

        self.vertexSelect = QPushButton()
        self.vertexSelect.setText("Add Selected Vertex")
        self.gridLayout.addWidget(self.vertexSelect, 1, 1) 
        self.vertexSelect.clicked.connect(self.GetSelected)

        # Update Dialog Button Enums
        QBtn = QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        
        # Note: button() needs the StandardButton enum in PySide6
        self.buttonBox.button(QDialogButtonBox.StandardButton.Yes).setText("Create BCs")
        self.buttonBox.accepted.connect(self.CreateBCs)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.gridLayout.addWidget(self.buttonBox, 3, 1)
        self.setLayout(self.gridLayout)
        
        # Initial setup commands (assuming cubit is available)
        cubit.set_pick_type("Vertex")
        bodies = cubit.get_entities("body")
        bbox = cubit.get_total_bounding_box("body", bodies)
        self.xmin = bbox[0]
        self.xmax = bbox[1]
        self.ymin = bbox[3]
        self.ymax = bbox[4]
        self.xcenter = (self.xmin + self.xmax)/2
        self.ycenter = (self.ymin + self.ymax)/2

        # clear all existing sidests
        cubit.cmd("delete sideset all")
        cubit.cmd("delete nodeset all")
    # end __init__

    # Get the selected id from Cubit and insert it into the GUI
    def GetSelected(self):
        ids = cubit.get_selected_ids()
        # Fixed logic: if no id or more than one id
        if not ids or len(ids) > 1:
            cubit_utils.ErrorWindow("Select one tip vertex.")
            return
        self.vertexLineEdit.setText(str(ids[0]))

    # Get the vertex from the GUI
    def GetVertexLineEdit(self):
        vertex = self.vertexLineEdit.text()
        return int(vertex)

    # create the  nodeset on the inside of the tire
    def inside_bc_nodeset(self):
        origin = [self.xcenter, self.ycenter, 0]
        direction = [0, -1, 0]
        all_curves = cubit.get_entities('curve')
        try:
            _, curves =  cubit.fire_ray(origin, direction, 'curve', all_curves, 0, .001) 
            cubit.cmd(f"nodeset auto_id add curve {curves[0]} include continuous with num_parents=1")
            nodeset_id = cubit.get_next_nodeset_id()-1
            print(f"Creating inside bc: {nodeset_id}")
            cubit.cmd(f'nodeset {nodeset_id} name "tire-1_inside"')
        except Exception as e:
            print('Unable to create inside bc nodeset')
            
        try:
            vertex = self.GetVertexLineEdit()
            cubit.cmd(f'nodeset {nodeset_id} remove node in vertex {vertex}')
        except Exception as e:
            cubit_utils.ErrorWindow("A tip vertex must be specified prior to creating boundary conditions.")

    # define the nodeset outside of the tire
    def outside_bc_nodeset(self):
        exterior_curves = set(cubit.parse_cubit_list("curve", "with num_parents=1"))
        inside_curves = set(cubit.parse_cubit_list("curve", "in nodeset with name 'tire-1_inside'"))
        outside_curves = exterior_curves - inside_curves
        outside_curve_str = " ".join([str(c) for c in outside_curves])
        cubit.cmd(f"nodeset auto_id add curve {outside_curve_str} except curve in nodeset with name 'tire-1_symm-nodes'")
        nodeset_id = cubit.get_next_nodeset_id()-1
        cubit.cmd(f'nodeset {nodeset_id} name "tire-1_outside"')

    # create a nodeset at the tip. Note that a tip vertex must be specified via the GUI.
    def tip_bc_nodeset(self):
        try:
            vertex = self.GetVertexLineEdit()
            coord = cubit.get_center_point('vertex', vertex)
            cubit.cmd(f"nodeset auto_id add curve in surface in vertex {vertex} with num_parents=1 except curve with y_coord > {coord[1]}")
            nodeset_id = cubit.get_next_nodeset_id()-1
            cubit.cmd(f'nodeset {nodeset_id} name "tire-1_Set-contact-R/L"')
        except Exception as e:
            cubit_utils.ErrorWindow("A tip vertex must be specified prior to creating boundary conditions.") 
            
    # create the nodes containing all nodes
    def all_nodes(self): 
        cubit.cmd("nodeset auto_id add surface all")
        nodeset_id = cubit.get_next_nodeset_id()-1
        cubit.cmd(f'nodeset {nodeset_id} name "Set-all-nodes"')        

    # create the nodeset on the axisymmetric boundary
    def axisymmetric(self):
        # This needs a tolerance and not be exactly y=0.0
        cubit.cmd("nodeset auto_id add curve with y_coord > -0.006")
        nodeset_id = cubit.get_next_nodeset_id()-1
        cubit.cmd(f'nodeset {nodeset_id} name "tire-1_symm-nodes"')

    # create the sideset inside the tire
    def inside_contact_sideset(self):
        cubit.cmd("sideset auto_id add curve in nodeset with name 'tire-1_inside'")
        sideset_id = cubit.get_next_sideset_id()-1
        cubit.cmd(f'sideset {sideset_id} name "tire-1_Surf-inflation"')

    # create a nodeset in the tread based on the curves in the previously defined tread sideset
    def tread_nodeset(self):
        cubit.cmd(f"nodeset auto_id add curve in sideset with name 'tire-1_Surf-contact-TRD'")
        nodeset_id = cubit.get_next_nodeset_id()-1
        cubit.cmd(f'nodeset {nodeset_id} name "tire-1_Set-contact-TRD"')

    # find the curves at maximum X direction.
    def simple_tread_sideset(self):
        # find the center point of the bounding box of all bodies
        bodies = cubit.get_entities("body")
        bbox = cubit.get_total_bounding_box("body", bodies)
        xmin = bbox[0]
        xmax = bbox[1]
        xcenter = (xmin + xmax)/2
        ycenter = (bbox[3] + bbox[4])/2

        # fire a ray from the center point in the positive x direction
        # find the last intersecting curve. This will be a curve on the tread
        # then find the surface in that curve. That will be the tread surface.
        all_curves = cubit.get_entities('curve')
        origin = [xcenter, ycenter, 0]
        # surfaces in the -Y direction
        direction = [1, 0, 0]
        # We can't get the surfaces since they are planar intersections
        _, curves =  cubit.fire_ray(origin, direction, 'curve', all_curves, 0, .1) 
        # the surface in the last curve
        tread_surface_list = cubit.parse_cubit_list("surface", f"in curve {curves[-1]}")
        try:
            tread_surface = tread_surface_list[0]
        except Exception as e:
            cubit_utils.ErrorWindow(f"Unable to create simple tread mesh\n {e}")
            return

        # Now find the curves that are exterior (number of parents = 1) on the tread surface.
        # These are the curves in the tread surface. Exclude the axisymmetric curve.
        cubit.cmd(f"sideset auto_id add curve in surface {tread_surface} with num_parents=1 except curve in nodeset with name 'tire-1_symm-nodes'")
        sideset_id = cubit.get_next_sideset_id()-1
        cubit.cmd(f'sideset {sideset_id} name "tire-1_Surf-contact-TRD"')

    # create the required sets
    def CreateBCs(self):            
        try:
            self.axisymmetric()
            self.inside_bc_nodeset()
            self.outside_bc_nodeset()
            self.tip_bc_nodeset()
            self.all_nodes()
            self.inside_contact_sideset()
            self.simple_tread_sideset()
            self.tread_nodeset()
        except Exception as e:
            print(e)


def main():
    # 'claro' must be globally defined or passed to main
    global claro
    dlg = BoundaryConditions(claro)
    dlg.show()

if __name__ == "__coreformcubit__":
    # cubit_utils.find_claro() has been updated to return a PySide6 QMainWindow
    claro = cubit_utils.find_claro()
    main()
