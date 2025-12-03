#!python

"""
    This module contains algorithms to blunt sharp tangencies. Note that this 
    algorithm assumes that there are three surfaces at the blunt tip. The 
    algorithm will not work in cases where the sharp tangency is at an outside 
    vertex where the vertex is only connected to two surfaces.

    The basic algorithm consists of cutting the tangent surface at a distance
    from the blunt point that splitting that cut surface in half and uniting the
    two resulting surfaces with the adjacent surfaces. 

    In the compositing operation the small curves from the blunt are composited 
    and the the blunt point is set as a side type for mapped mesh operations.
"""

from math import *
import numpy as np
from scipy.spatial.transform import Rotation
import sys
import cubit_utils

from PySide6.QtCore import QMetaObject, Qt

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, QLineEdit, \
                              QDialogButtonBox, QPushButton, QWidget, QDockWidget



class SelectLineEdit(QLineEdit):
    def __init__(self, type, parent=None):
        self.type = type # The type must have first letter capitalized, "Vertex" or "Surface"
        super().__init__(parent)

    def focusInEvent(self, event):
        try:
            # Assuming 'cubit' is globally available
            cubit.set_pick_type(self.type)
        except Exception as e:
            print("Error setting pick type", e, flush=True)
        # Standard Python 3 super() call is cleaner and preferred over super(Class, self)
        super().focusInEvent(event)

# --- Main Dialog ---

class TireBlunt(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.resize(239, 150)
        self.setWindowTitle("Blunt Tangency")
        self.setObjectName("TireBlunt")

        # Pass self to the layout
        self.gridLayout = QGridLayout(self) 
        self.bluntVertexLabel = QLabel(u"Select Tangent Vertex")
        self.gridLayout.addWidget(self.bluntVertexLabel, 0, 0)
        try:
            self.bluntVertex = SelectLineEdit("Vertex")
        except Exception as e:
            print(e, flush=True)
        self.gridLayout.addWidget(self.bluntVertex, 0, 1)

        self.vertexSelect = QPushButton()
        self.vertexSelect.setText("Add Selected Vertex")
        self.gridLayout.addWidget(self.vertexSelect, 0, 2) 
        self.vertexSelect.clicked.connect(self.GetSelectedVertex)

        self.bluntSurfaceLabel = QLabel(u"Select Surface to Modify")
        self.gridLayout.addWidget(self.bluntSurfaceLabel, 1, 0)
        try:
            self.bluntSurface = SelectLineEdit("Surface")
        except Exception as e:
            print(e)
        self.gridLayout.addWidget(self.bluntSurface, 1, 1)

        self.surfaceSelect = QPushButton()
        self.surfaceSelect.setText("Add Selected Surface")
        self.gridLayout.addWidget(self.surfaceSelect, 1, 2) 
        self.surfaceSelect.clicked.connect(self.GetSelectedSurface)

        self.bluntDistanceLabel = QLabel(u"Distance")
        self.gridLayout.addWidget(self.bluntDistanceLabel, 2, 0)
        self.bluntDistance = QLineEdit()
        self.gridLayout.addWidget(self.bluntDistance, 2, 1)

        QWidget.setTabOrder(self.bluntVertex, self.bluntSurface)
        QWidget.setTabOrder(self.bluntSurface, self.bluntDistance)

        # Update Dialog Button Enums
        QBtn = (QDialogButtonBox.StandardButton.Yes | 
                QDialogButtonBox.StandardButton.Apply | 
                QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox = QDialogButtonBox(QBtn)
        
        # Note: button() needs the StandardButton enum in PySide6
        self.buttonBox.button(QDialogButtonBox.StandardButton.Yes).setText("Preview")
        self.buttonBox.accepted.connect(self.Preview)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).setText("Blunt")
        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.BluntTangency)

        self.gridLayout.addWidget(self.buttonBox, 3, 1)
        self.setLayout(self.gridLayout)
        QMetaObject.connectSlotsByName(self)
    # init -- create GUI

    # Get the vertex from the GUI
    def GetBluntVertex(self):
        vertex_str = self.bluntVertex.text()
        try:
            assert(vertex_str)
            vertex = cubit.parse_cubit_list("vertex", vertex_str)
            assert(len(vertex) == 1)
        except Exception as e:
            return None
        return vertex[0]

    # Get the surface from the GUI
    def GetBluntSurface(self):
        surface_str = self.bluntSurface.text()
        try:
            assert(surface_str)
            surface = cubit.parse_cubit_list("surface", surface_str)
            assert(len(surface) == 1)
        except Exception as e:
            return None
        return surface[0]

    # Put the selected vertex into the GUI
    def GetSelectedVertex(self):
        try:
            ids = cubit.get_selected_ids()
            assert(ids)
        except Exception as e:
            cubit_utils.ErrorWindow("Select a vertex to blunt connected to three surfaces.")
            return 
        if len(ids) > 1:
            cubit_utils.ErrorWindow("Select only one tangent vertex to blunt.")
            return 
        self.bluntVertex.setText(str(ids[0]))
        self.bluntSurface.setFocus()

    # Put the selected surface into the GUI
    def GetSelectedSurface(self):
        try:
            ids = cubit.get_selected_ids()
            assert(ids)
        except Exception as e:
            cubit_utils.ErrorWindow("Select a surface to blunt.")
            return
        if len(ids) > 1:
            cubit_utils.ErrorWindow("Select only one surface to blunt.")
            return
        self.bluntSurface.setText(str(ids[0]))
        self.bluntDistance.setFocus()

    # if a curve at the start vertex is shorter than the desired length
    # we have to move into the next curve, perhaps n times. However,
    # we can't extend past the surface
    def GetPosition(self, curve: cubit.Curve, start_vertex: cubit.Vertex, distance: float)-> tuple[bool, tuple[float, float, float]]: 
        err_max = np.finfo(np.float64).max # return a double max on error
        remaining_distance = distance
        current_curve = curve
        current_start_vertex = start_vertex
        while current_curve.length() < remaining_distance:
            try:
                remaining_distance -= current_curve.length()
                next_vertex = set([v.id() for v in current_curve.vertices()]) - set([current_start_vertex.id()])
                assert(len(next_vertex) == 1)
                next_vertex = next_vertex.pop()
                next_curve = set([c.id() for c in cubit.vertex(next_vertex).curves()]) - set([current_curve.id()])
                assert(len(next_curve) == 1)
                current_curve = cubit.curve(next_curve.pop())
                current_start_vertex = cubit.vertex(next_vertex)
            except:
                print(f'Unable to get a position from start curve {curve.id()}')
                return False, (err_max, err_max, err_max)

        fraction = current_curve.fraction_from_arc_length(current_start_vertex, remaining_distance)
        position = current_curve.position_from_fraction(fraction)
        return True, position
    # end GetPosition

    # Draw the preview of the cutline
    def Preview(self):
        cubit.clear_preview() 
        try:
            dist_str = self.bluntDistance.text()
            distance = float(dist_str)
        except Exception as e:
            cubit_utils.ErrorWindow("Must define a blunt distance.")
            return
        if distance <= 0.0:
            cubit_utils.ErrorWindow("Error getting distance.")
            return

        try:
            vertex = self.GetBluntVertex()
            assert(vertex)
        except Exception as e:
            print("Error getting vertex")
            return
        start_vertex = cubit.vertex(vertex)

        try:
            surface = self.GetBluntSurface()
            assert(surface)
        except Exception as e:
            print("Error getting surface")
            return

        original_body = cubit.parse_cubit_list('body', f'in surface {surface}')
        assert(len(original_body) == 1)
        try:
            original_body = original_body[0]
        except Exception as e:
            print("Error finding body", e)
            return

        try:
            curves = cubit.parse_cubit_list("curve", f"in surface {surface} in vertex {start_vertex.id()}")
            assert(len(curves) == 2)
            curve_1 = curves[0]
            curve_2 = curves[1]
        except Exception as e:
            cubit_utils.ErrorWindow("Can't find only 2 attached curves in the surface") 
            return

        # get curve positions, traversing multiple curve if necessary
        curve_1 = cubit.curve(curve_1)
        try:
            success, pos_1 = self.GetPosition(curve_1, start_vertex, distance)
            assert(success)
        except Exception as e:
            print(f'Unable to get position on curve {curve_1.id()}', e)
            return
        pos_1 = np.array(pos_1)

        curve_2 = cubit.curve(curve_2)
        try:
            success, pos_2 = self.GetPosition(curve_2, start_vertex, distance)
            assert(success)
        except Exception as e:
            print(f'Unable to get position on curve {curve_2.id()}', e)
            return
        pos_2 = np.array(pos_2)

        pos_3 = pos_2 + np.array([0,0,1])

        v1 = pos_1 - pos_2
        v2 = pos_3 - pos_2
        normal = np.cross(v1, v2)
        normal = normal / np.linalg.norm(normal)

        try:
            cubit.cmd(f"webcut body {original_body} with general plane location position {pos_1[0]} {pos_1[1]} {pos_1[2]} direction {normal[0]} {normal[1]} {normal[2]} preview")
        except Exception as e:
            print("Error generating preview: ", e)
    # end Preview

    # Create the acutal blunt tangency
    def BluntTangency(self):

        cubit.clear_preview() 
        cubit.cmd("undo group begin")

        # make sure that we are picking only one vertex at blunt point
        cubit.cmd("imprint all")
        cubit.cmd("merge all")
        try:
            dist_str = self.bluntDistance.text()
            distance = float(dist_str)
        except Exception as e:
            cubit_utils.ErrorWindow("Must define a blunt distance.")
            cubit.cmd("undo group end")
            return
        if distance <= 0.0:
            cubit_utils.ErrorWindow("Error must be greater than zero.")
            cubit.cmd("undo group end")
            return

        try:
            vertex = self.GetBluntVertex()
            start_vertex = cubit.vertex(vertex)
        except Exception as e:
            print("Error getting vertex")
            cubit.cmd("undo group end")
            return

        try:
            surface = self.GetBluntSurface()
        except Exception as e:
            print("Error getting surface")
            cubit.cmd("undo group end")
            return

        if cubit.contains_virtual('surface', surface):
            cubit_utils.ErrorWindow("Surface contains composited curves.\n Use the tire undo function prior to creating the blunt tangency.")
            return

        # name the surface for later composite operation
        try:
            cubit.cmd(f"surface {surface} name 'blunted_surface_{surface}'")
        except Exception as e:
            cubit_utils.ErrorWindow("Error naming surface. Automatic compositing will fail")

        start_coord = np.array(start_vertex.coordinates())
        original_body = cubit.parse_cubit_list('body', f'in surface {surface}')
        assert(len(original_body) == 1)
        try:
            original_body = original_body[0]
        except Exception as e:
            print("Error finding body", e)
            cubit.cmd("undo group end")
            return

        try:
            curves = cubit.parse_cubit_list("curve", f"in surface {surface} in vertex {start_vertex.id()}")
            assert(len(curves) == 2)
            curve_1 = curves[0]
            curve_2 = curves[1]
        except Exception as e:
            cubit_utils.ErrorWindow("Can't find only 2 attached curves in the surface") 
            cubit.cmd("undo group end")
            return

        # get curve position at the offset, traverse multiple curves if needed
        curve_1 = cubit.curve(curve_1)
        try:
            success, pos_1 = self.GetPosition(curve_1, start_vertex, distance)
            assert(success)
        except Exception as e:
            print(f'Unable to get position associated with curve {curve_1.id()}')
            cubit.cmd("undo group end")
            return

        curve_2 = cubit.curve(curve_2)
        try:
            success, pos_2 = self.GetPosition(curve_2, start_vertex, distance)
            assert(success)
        except Exception as e:
            print(f'Unable to get position associated with curve {curve_2.id()}')
            cubit.cmd("undo group end")
            return

        try:
            cubit.cmd(f"split surface {surface} across location position {pos_1[0]} {pos_1[1]}, {pos_1[2]} location position {pos_2[0]} {pos_2[1]}, {pos_2[2]}")
            new_surface = cubit.parse_cubit_list('surface', f'in body {original_body}, in vertex {start_vertex.id()}')
            assert(len(new_surface) == 1)
            new_surface = new_surface[0]
            cubit.cmd(f'separate surface {new_surface}')
        except Exception as e:
            print("Error doing first surface split", e)
            cubit.cmd("undo group end")
            return

        mid_point = (np.array(pos_1) + np.array(pos_2)) / 2.0
        try:
            cubit.cmd(f"split surface {new_surface} across location vertex {start_vertex.id()} location position {mid_point[0]} {mid_point[1]}, {mid_point[2]}")
            newest_surface = cubit.get_last_id('surface')
            cubit.cmd(f'separate surface {newest_surface}')
        except Exception as e:
            print("Error doing second surface split", e)
            cubit.cmd("undo group end")
            return

        try:
            cubit.cmd('imprint all')
            cubit.cmd('merge all')
        except Exception as e:
            print("Error in imprint and merge", e)
            cubit.cmd("undo group end")
            return

        # unite the split blunted tangencies into the adjacent surfaces
        try:
            pos_1_vertex = cubit.parse_cubit_list("vertex", f"at {pos_1[0]} {pos_1[1]} {pos_1[2]} ordinal 1")
            assert(len(pos_1_vertex) == 1)
            #side_1 = cubit.parse_cubit_list('surface', f'in vertex {pos_1_vertex[0]} except surface in body {original_body}')
            side_1 = cubit.parse_cubit_list('body', f'in vertex {pos_1_vertex[0]} except body {original_body}')
            assert(len(side_1) == 2)
            side_1_str = cubit.string_from_id_list(side_1)
            cubit.cmd(f'unite body {side_1_str}')
        except Exception as e:
            print("Unable to unite side 1")
            cubit.cmd(f'unite surface {side_1_str} include_connected')

        try:
            pos_2_vertex = cubit.parse_cubit_list("vertex", f"at {pos_2[0]} {pos_2[1]} {pos_2[2]} ordinal 1")
            assert(len(pos_2_vertex) == 1)
            #side_2 = cubit.parse_cubit_list('surface', f'in vertex {pos_2_vertex[0]} except surface in body {original_body}')
            side_2 = cubit.parse_cubit_list('body', f'in vertex {pos_2_vertex[0]} except  body {original_body}')
            assert(len(side_2) == 2)
            side_2_str = cubit.string_from_id_list(side_2)
            cubit.cmd(f'unite body {side_2_str}')
        except Exception as e:
            print("Unable to unite side 2")
            cubit.cmd(f'unite surface {side_2_str} include_connected')

        # The blunt vertices are tracked by the name "blunt_vertex_*". This name
        # is used in the compositing section to automatically 
        try:
            mid_vertex = cubit.parse_cubit_list("vertex", f"at {mid_point[0]} {mid_point[1]}, {mid_point[2]} ordinal 1")
            assert(len(mid_vertex) == 1)
            cubit.cmd(f'vertex {mid_vertex[0]} name "blunt_vertex_{mid_vertex[0]}"')
        except Exception as e:
            print('Warning: unable to assign blunt vertex name')

        cubit.cmd("undo group end")
    
        # clear dialog on completion and set focus to first line edit
        self.bluntVertex.setText("")
        self.bluntSurface.setText("")
        self.bluntDistance.setText("")
        self.bluntVertex.setFocus()
# end BluntTangency


def find_CommandPanel():
    # 'claro' must be in scope
    global claro
    # Pass the class object QDockWidget, not a string
    return claro.findChild(QDockWidget, "CubitCommandPanel")

def main():
    # 'claro' must be defined in the calling scope (the __main__ block)
    global claro
    dlg = TireBlunt(claro)
    # The original code used show()
    dlg.show()

if __name__ == "__coreformcubit__":
    claro = cubit_utils.find_claro()
    
    # findChild requires the class object
    try:
        ccp = claro.findChild(QDockWidget, "CubitCommandPanel")
        ccl = claro.findChild(QDockWidget, "ClaroCommandWindow")
    except Exception as e:
        # Handle cases where claro is None or findChild fails
        pass
        
    main()

