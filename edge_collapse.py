#!python
import numpy as np
import sys

from PySide6.QtCore import QMetaObject, Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, QLineEdit, \
    QDialogButtonBox, QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy, QDockWidget

import cubit_utils
import logging
import os

class SelectLineEdit(QLineEdit):
    def __init__(self, type, parent=None):
        self.type = type # The type must have first letter capitalized, "Vertex" or "Surface"
        super().__init__(parent)

    def focusInEvent(self, event):
        try:
            # Assuming cubit object is available globally/in scope
            cubit.set_pick_type(self.type)
        except Exception as e:
            print("Error setting pick type", e, flush=True)
        # Use standard Python 3 super() call
        super().focusInEvent(event)

class CollapseEdge(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.resize(239, 150)
        self.setWindowTitle("Collapse Edge")
        self.setObjectName("CollapseEdge")

        self.gridLayout = QGridLayout(self)

        self.zoomLayout = QHBoxLayout()
        self.badTriangle = QPushButton()
        self.badTriangle.setText("Zoom to bad triangle")
        self.zoomLayout.addWidget(self.badTriangle) 
        self.badTriangle.clicked.connect(self.ZoomToBadTriangle)

        self.badTriangleLabel = QLabel(u"Bad Triangle: ")  
        self.zoomLayout.addWidget(self.badTriangleLabel) 

        self.badTriangleValue = QLabel("0")  
        self.zoomLayout.addWidget(self.badTriangleValue) 

        self.badQualityLabel = QLabel(u"Scaled Jacobian: ")  
        self.zoomLayout.addWidget(self.badQualityLabel) 
        self.badQualityValue = QLabel("0.000")  
        self.zoomLayout.addWidget(self.badQualityValue) 

        self.gridLayout.addLayout(self.zoomLayout, 0, 0, 1, 4)
        self.gridLayout.setColumnStretch(0, 1)

        self.collapseEdgeLabel = QLabel("Select Edge to Collapse")
        self.gridLayout.addWidget(self.collapseEdgeLabel, 1, 0)
        self.collapseEdge = SelectLineEdit("Edge", self)
        self.gridLayout.addWidget(self.collapseEdge, 1, 1)

        self.edgeSelect = QPushButton()
        self.edgeSelect.setText("Add Selected Edge")
        self.gridLayout.addWidget(self.edgeSelect, 1, 2) 
        self.edgeSelect.clicked.connect(self.GetSelectedEdge)

        # 3. Update Dialog Button Enums
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)

        apply_button = self.buttonBox.button(QDialogButtonBox.StandardButton.Apply)
        apply_button.clicked.connect(self.DoCollapseEdge)

        self.buttonBox.accepted.connect(self.DoCollapseEdge)
        self.buttonBox.accepted.connect(self.accept)

        self.buttonBox.rejected.connect(self.reject)

        self.gridLayout.addWidget(self.buttonBox, 2, 2)

        # 4. Update QSizePolicy enums and use QSize for QSpacerItem (optional, but cleaner)
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.gridLayout.addItem(self.verticalSpacer, 3, 0, 1, 1)

        self.setLayout(self.gridLayout)
    # init -- create GUI


    # Put the selected edge into the GUI
    def GetSelectedEdge(self):
        try:
            ids = cubit.get_selected_ids()
            if not ids:
                cubit_utils.ErrorWindow("Select an edge to collapse.")
                raise ValueError("No edge selected.")
            if len(ids) > 1:
                cubit_utils.ErrorWindow("Select only one edge.")
                raise ValueError("More than one edge selected.")
            self.collapseEdge.setText(str(ids[0]))
        except Exception as e:
            # Note: The original f-string was malformed; correcting it to display the exception or a generic message.
            cubit_utils.ErrorWindow(f"Error getting selected edge: {e}")


    # Get the edge from the GUI
    def GetCollapsedEdge(self):
        edge_str = self.collapseEdge.text().strip()
        if not edge_str:
            cubit_utils.ErrorWindow("No edge provided.")
            return None
        try:
            edges = cubit.parse_cubit_list("edge", edge_str)
            if not edges:
                raise ValueError(f"Invalid edge ID: {edge_str}")
            if len(edges) != 1:
                raise ValueError(f"More than one edge ID provided: {edge_str}")
        except Exception as e:
            raise ValueError(f"Error parsing edge ID: {e}")

        return edges[0]

    # Zoom to the bad triangle
    def ZoomToBadTriangle(self):
        try:
            id_list = cubit.parse_cubit_list('tri', 'all')
            if not id_list:
                raise ValueError("No triangles found.")
            # Assuming cubit.get_elem_quality_stats returns the minimum quality value at index 0 and element ID at index 4
            quality_stats = cubit.get_elem_quality_stats('tri', id_list, 'scaled jacobian', 0.0, False, 0.0, 0.0, False)
            if not quality_stats:
                raise ValueError("Could not get triangle quality stats.")
        
            min_val = quality_stats[0]
            tri_id = int(quality_stats[4])

            self.badTriangleValue.setText(str(tri_id))
            self.badQualityValue.setText(f"{min_val:.3f}")

            # Zoom to the bad triangle
            cubit.cmd(f'zoom tri {tri_id}')
        except Exception as e:
            cubit_utils.ErrorWindow(f"Error zooming to triangle. Error: {e}")

    # remove the duplicate node from the connectivity.
    def QuadToTriConnectivity(self, conn):
        # Simplify this by using a python 3.7+ dict
        new_conn = list(dict.fromkeys(conn))
        if len(new_conn) != 3:
          raise ValueError("More than one edge selected.")
        return new_conn
        
    # Collapse an edge between two 2D mesh entities
    def DoCollapseEdge(self):
        """
        Collapse an edge between two 2D mesh entities.
        """
        try:
            edge = self.GetCollapsedEdge()
            if edge is None: 
                cubit_utils.ErrorWindow("Select a valid edge to collapse.")
                return
        except ValueError as e:
            cubit_utils.ErrorWindow(f"Invalid edge selection: {e}")
            return

        try:
            nodes = cubit.parse_cubit_list('node', f'in edge {edge}')
            # 'is_merged' check is often for geometric entities, but used here on curves.
            outside_nodes = cubit.parse_cubit_list('node', f'in edge {edge} in curve with not is_merged') 
            primary_node = min(nodes)
            secondary_node = max(nodes)

            # We must merge to the outer node if there is one
            if len(outside_nodes) == 1:
                if primary_node != outside_nodes[0]:
                    secondary_node, primary_node = primary_node, secondary_node
            elif len(outside_nodes) == 0:
                pass
            else:
                cubit_utils.ErrorWindow("More than one exterior node found. Cannot collapse edge.")
                print("More than one exterior node found. Cannot collapse edge.", flush=True)
                return

            tris = cubit.parse_cubit_list('tri', f'in edge {edge}')
            quads = cubit.parse_cubit_list('face', f'in edge {edge}')

            # these commands are not undoable and they don't account for
            # all the 3D cases so they are behind a developer flag
            cubit.cmd('set dev on')

            # The merge commands merges the secondary node into the primary node
            cubit.cmd(f'merge node {secondary_node} {primary_node}')
    
            # there could have been multiple tris on the edge, delete them all
            for tri in tris:
                cubit.cmd(f'delete tri {tri}')
                print(f'delete tri {tri}', flush=True)

            # I don't think the user would want to collapse multiple quads, but 
            # handle it just in case.
            print('before QuadToTriConnectivity for loop', flush=True)
            for quad in quads:
                conn = cubit.get_connectivity('face', quad)
                owner = cubit.get_geometric_owner('face', str(quad))
                owner_string = ''
                if owner:
                    owner_string = "owner " + owner[0]
                # Get the connectivity of the quad and remove the merged node
                try:
                    # find and remove the duplicate node after merging
                    tri_conn = self.QuadToTriConnectivity(conn)
                  
                    cubit.cmd(f'delete face {quad}')
                    cubit.cmd(f'create tri node {tri_conn[0]} {tri_conn[1]} {tri_conn[2]} {owner_string}')
                except Exception as e:
                    print(f"Error creating triangle from quad: {e}", flush=True)
                    cubit_utils.ErrorWindow(f"Error creating triangle from quad: {e}", e)
                    return

            cubit.cmd('set dev off')

            # clear the selected edge in the GUI
            self.collapseEdge.clear()

        except Exception as e:
            cubit_utils.ErrorWindow(f"Error collapsing edge: {e}", e)


def main():
    #log_file = os.path.join(os.getcwd(), 'collapse_edge.log')
    #logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    #logging.info("Starting Collapse Edge dialog")
    
    # 'claro' must be defined in the calling scope
    global claro
    dlg = CollapseEdge(claro)
    dlg.show()

if __name__ == "__coreformcubit__":
    # Use find_claro from cubit_utils and set claro as global
    global claro
    claro = cubit_utils.find_claro()
    
    # findChild requires the class object QDockWidget
    try:
        ccp = claro.findChild(QDockWidget, "CubitCommandPanel")
        ccl = claro.findChild(QDockWidget, "ClaroCommandWindow")
    except AttributeError:
        # Handle case where claro is None
        print("Warning: Failed to find Claro application window/dock widgets.")
        pass
        
    main()

