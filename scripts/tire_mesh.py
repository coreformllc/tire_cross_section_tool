#!python
"""
    Get the meshing parameters from the GUI and create the mesh.
    The rebar surfaces must be meshed with a mapped meshing scheme
    and be two elements thick. Other surfaces are meshed with a 
    tripave scheme by default, this is a quad dominant meshing scheme
    that can add a few triangles.
"""
import math
import sys

# Update Imports to PySide6
from PySide6.QtCore import QMetaObject, Qt

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, \
    QLineEdit, QDialogButtonBox, QPushButton, QMessageBox, QDockWidget

import cubit_utils


class TireMesh(QDialog):
    # Create the Qt GUI panel
    def __init__(self, parent):
        super().__init__(parent)
        self.resize(239, 160)
        self.setObjectName("TireMesh")
        self.setWindowTitle("Mesh Tire Surfaces")

        self.gridLayout = QGridLayout(self)
        self.surfaceMappedLabel = QLabel(u"Mapped Surfaces:")
        self.gridLayout.addWidget(self.surfaceMappedLabel, 0, 0)
        self.surfaceMappedLineEdit = QLineEdit()
        self.gridLayout.addWidget(self.surfaceMappedLineEdit, 0, 1)
        self.surfaceMappedSelect = QPushButton()
        self.surfaceMappedSelect.setAutoDefault(False)
        self.surfaceMappedSelect.setText("Add Selected")
        self.gridLayout.addWidget(self.surfaceMappedSelect, 0, 2) 
        self.surfaceMappedSelect.clicked.connect(self.GetSelected)

        self.surfaceAreaLabel = QLabel(u"Total Surface Area:")
        self.gridLayout.addWidget(self.surfaceAreaLabel, 1, 0)
        self.surfaceAreaData = QLabel()
        #  Update Qt.LinksAccessibleByMouse|Qt.TextSelectableByMouse to PySide6 syntax
        self.surfaceAreaData.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.gridLayout.addWidget(self.surfaceAreaData, 1, 1)
        self.surface_area = self.SurfaceArea()
        self.surfaceAreaData.setText("%.3f" % self.surface_area)

        self.meshSizeLabel = QLabel("Mesh Size")
        self.gridLayout.addWidget(self.meshSizeLabel, 2, 0)
        self.meshSize = QLineEdit()
        self.gridLayout.addWidget(self.meshSize, 2, 1)
        self.meshSize.editingFinished.connect(self.CalculateElementBudget)

        surfaces = cubit.get_entities("surface")
        mesh_size = cubit.get_mesh_size("surface", surfaces[0])
        self.meshSize.setText("%.2f" % mesh_size)

        self.elementBudgetLabel = QLabel(u"Approximate element count:")
        self.gridLayout.addWidget(self.elementBudgetLabel, 3, 0)
        self.elementBudgetData = QLabel()
        # Update Qt.LinksAccessibleByMouse|Qt.TextSelectableByMouse to PySide6 syntax
        self.elementBudgetData.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.gridLayout.addWidget(self.elementBudgetData, 3, 1)
        cubit.set_pick_type('Surface')

        self.CalculateElementBudget()
        
        # Update Dialog Button Enums
        QBtn = QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        
        # Note: button() needs the StandardButton enum in PySide6
        self.buttonBox.button(QDialogButtonBox.StandardButton.Yes).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Yes).setText("Mesh")
        
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.accepted.connect(self.MeshTireSurfaces)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.CalculateElementBudget)

        self.gridLayout.addWidget(self.buttonBox, 4, 1)

        self.setLayout(self.gridLayout)
        QMetaObject.connectSlotsByName(self)
    # init -- end create GUI

    # Get the selected entity in Cubit and add it to the dialog. Note that these must be
    # a mappable surface
    def GetSelected(self):
        ids = cubit.get_selected_ids()
        if not ids:
            # Assuming cubit_utils.ErrorWindow is updated to PySide6
            cubit_utils.ErrorWindow("Select mapped surfaces in the model and then add them to the dialog.")
            return
        current_surf_str = self.surfaceMappedLineEdit.text()
        current_surfaces = cubit.parse_cubit_list('surface', current_surf_str)
        surface_str = cubit.string_from_id_list(current_surfaces + ids)
        self.surfaceMappedLineEdit.setText(surface_str.strip())

    # calculate the total surface area
    def SurfaceArea(self):
        surfaces = cubit.get_entities("surface")
        area = 0.0
        for surf in surfaces:
            area += cubit.get_surface_area(surf)
        return area

    # Check to see if the selected mapped surfaces are really mappable
    def CheckMappedSurfaces(self):
        rebar_surface_str = self.surfaceMappedLineEdit.text()
        if not rebar_surface_str:
            # Assuming cubit_utils.ErrorWindow is updated to PySide6
            cubit_utils.ErrorWindow("Add select surfaces and add the selected surfaces prior to meshing")
            return
        
        # The Cubit submap algorithm classifies vertices by the corner type
        # We want surfaces that only have end and side vertices. Other types
        # make this a non-mappable surface for rebar purposes. See the documentation
        rebar_surfaces = [int(id) for id in rebar_surface_str.split()]
        bad_surfaces = []
        mappable_surfaces = [] # list of (surface_id,[ends], [sides])
        for surf in rebar_surfaces:
            corner_types = cubit.get_submap_corner_types(surf)
            end_vertices = [t[0] for t in corner_types if t[1] == 1]
            side_vertices = [t[0] for t in corner_types if t[1] == 2]
            corner_vertices = [t[0] for t in corner_types if t[1] == 3]
            reversal_vertices = [t[0] for t in corner_types if t[1] == 4]
            triangle_vertices = [t[0] for t in corner_types if t[1] == 5]
            non_triangle_vertices = [t[0] for t in corner_types if t[1] == 6]
        
            # Note: Python's list doesn't have a .count() method, but len() is often used for size
            # The original code likely meant len() or relied on a custom cubit list type
            if (len(corner_vertices) + len(reversal_vertices) +
                len(triangle_vertices) + len(non_triangle_vertices)) > 0:
                bad_surfaces.append(surf)
            else:
                mappable_surfaces.append((surf, end_vertices, side_vertices))
        
        if bad_surfaces: # Note: Assuming bad_surfaces() in original was a typo for bad_surfaces
            # Assuming cubit_utils.ErrorWindow is updated to PySide6
            cubit_utils.ErrorWindow(f"Surface(s) {bad_surfaces} are not mappable and must be cut into mappable areas prior to creating rebar regions")

        return mappable_surfaces
        
    # Given a curve and one vertex find the vertex at the opposite end
    def GetOtherVertex(self, curve, vertex):
        vertices = list(cubit.parse_cubit_list('vertex', f'in curve {curve}'))
        try:
            vertices.remove(vertex)
            return vertices[0]
        except ValueError:
            print(f'Vertex {vertex} not in curve {curve}.')
            return -1
    
    # Get the curve shared by a vertex in the given surface
    def GetConnectedCurve(self, surface, curve, vertex):
        curves = list(cubit.parse_cubit_list('curve', f'in vertex {vertex} in surface {surface}'))
        try:
            curves.remove(curve)
            assert len(curves) == 1
            return curves[0]
        except:
            print(f'Vertex {vertex} not in curve {curve}.')
            return -1

    # returns either the shortest curve bounded by two end vertices
    # or the shortest chain of curves bounded by two end vertices.
    def FindShortSide(self, surface, end_vertices, side_vertices):
        curves_with_two_end_vertices = set()
        for vertex in end_vertices:
            curves = cubit.parse_cubit_list('curve', f'in vertex {vertex} in surface {surface}')
            for curve in curves:
                other_vertex = self.GetOtherVertex(curve, vertex)
                if other_vertex == -1:
                    continue
                elif other_vertex in end_vertices:
                    curves_with_two_end_vertices.add(curve)
                else:
                    chain = [curve]
                    current_vertex = other_vertex
                    current_curve = curve
                    while current_vertex in side_vertices:
                        next_curve = self.GetConnectedCurve(surface, current_curve, current_vertex)
                        current_vertex = self.GetOtherVertex(next_curve, current_vertex)
                        chain.append(next_curve)
                        current_curve = next_curve
                    
                    if tuple(list(reversed(chain))) not in curves_with_two_end_vertices:
                        curves_with_two_end_vertices.add(tuple(chain)) 
        
        shortest_curve_length = 1e+12
        shortest_curve = -1
        for curve in curves_with_two_end_vertices:
            if type(curve) is tuple and len(curve) > 1: #if it is a tuple, it should always be > 1
                vertices = cubit.parse_cubit_list('vertex', f'in curve {curve[0]}')
                start_vertex = [v for v in vertices if v in end_vertices][0]
                vertices = cubit.parse_cubit_list('vertex', f'in curve {curve[-1]}')
                end_vertex = [v for v in vertices if v in end_vertices][0]
                assert(start_vertex != end_vertex)
                dist_info = cubit.measure_between_entities('vertex', start_vertex, 'vertex', end_vertex)
                distance = dist_info[0]
            else:
                distance = cubit.get_curve_length(curve)
        
            if distance < shortest_curve_length:
                shortest_curve_length = distance
                shortest_curve = curve
        
        return shortest_curve

    # Get the contents of the GUI mapped surface list
    def GetMappedLineEdit(self):
        map_surface_str = self.surfaceMappedLineEdit.text()
        if not map_surface_str:
            return []
        map_surfaces = cubit.parse_cubit_list('surface', map_surface_str)
        return map_surfaces

    # Verify that the given surfaces are mappable
    def CheckMappableSurfaces(self):
        map_surfaces = self.GetMappedLineEdit()
        if not map_surfaces:
            print("error getting mapped surfaces")
            # The original assertion was against map_surface, fixing to map_surfaces
            assert(len(map_surfaces) > 0) 

        bad_surfaces = []
        mappable_surfaces = [] # list of (surface_id,[ends], [sides])
        for surf in map_surfaces:
            try:
                # correct for blunt vertex types first
                blunt_vertices = cubit.parse_cubit_list('vertex', f'in surface {surf} with name "blunt_vertex_*"')
                if blunt_vertices:
                    blunt_vertex_str = cubit.string_from_id_list(blunt_vertices)
                    cubit.cmd(f"surface {surf} vertex {blunt_vertex_str.strip()} type side")
            except Exception as e:
                print(f"Warning: Unable to set side type on surface {surf}")

            try:
                corner_types = cubit.get_submap_corner_types(surf)
            except Exception as e:
                print("Unable to get corner types:", e)
                return mappable_surfaces

            end_vertices = [t[0] for t in corner_types if t[1] == 1]
            side_vertices = [t[0] for t in corner_types if t[1] == 2]
            corner_vertices = [t[0] for t in corner_types if t[1] == 3]
            reversal_vertices = [t[0] for t in corner_types if t[1] == 4]
            triangle_vertices = [t[0] for t in corner_types if t[1] == 5]
            non_triangle_vertices = [t[0] for t in corner_types if t[1] == 6]
        
            if len(corner_vertices) + len(reversal_vertices) + \
               len(triangle_vertices) + len(non_triangle_vertices) > 0:
                bad_surfaces.append(surf)
            else:
                mappable_surfaces.append((surf, end_vertices, side_vertices))
        
        return mappable_surfaces

    # set the meshing scheme on the mappable surfaces and set the
    # short side to have two elements (intervals).
    def SetMappableSurfaces(self):
        mappable_surfaces = self.CheckMappableSurfaces()
        selected_surfaces = set(self.GetMappedLineEdit())

        if not selected_surfaces:
            # Assuming cubit_utils.WarningWindow is updated to PySide6
            cubit_utils.WarningWindow("No surfaces will be set as mapped.")
            return

        mappable_ids = set([id[0] for id in mappable_surfaces])
        bad_surfaces = selected_surfaces - mappable_ids
        if bad_surfaces:
            # Assuming cubit_utils.WarningWindow is updated to PySide6
            cubit_utils.WarningWindow(f"Unable to map mesh surface {' '.join([str(s) for s in bad_surfaces])}. Try cutting surfaces prior to meshing.")

        for map_surf in mappable_surfaces:
            try:
                short_curve = self.FindShortSide(map_surf[0], map_surf[1], map_surf[2])
                cubit.cmd(f"curve {short_curve} interval 2")
                cubit.cmd(f"surface {map_surf[0]} scheme map")
            except Exception as e:
                print("Exception in FindShortSide", e)


    # Approximate the number of elements by taking the surface area / average element area
    def CalculateElementBudget(self):
        if not self.meshSize.text():
            # Assuming cubit_utils.ErrorWindow is updated to PySide6
            cubit_utils.ErrorWindow("Mesh Size must be set.")
            return
        element_budget = 0
        if self.meshSize.text():
            mesh_size = float(self.meshSize.text())
            element_budget = self.surface_area/(mesh_size * mesh_size)
        self.elementBudgetData.setText("%i" % element_budget)

        # also on apply gather surfaces in blocks that require rebar
        belt_surfaces = cubit.parse_cubit_list('surface', 'in volume in block with name "*Belt*" except surf in volume in block with name "*filler*"')
        ply_surfaces = cubit.parse_cubit_list('surface', 'in volume in block with name "*Bodyply*"')
        chafer_surfaces = cubit.parse_cubit_list('surface', 'in volume in block with name "*Chafer*"')
        # Duplicate line in original, keeping the second one
        chafer_surfaces = cubit.parse_cubit_list('surface', 'in volume in block with name "*Chafer*"') 
        cap_surfaces = cubit.parse_cubit_list('surface', 'in volume in block with name "*Set-Rubber-Cap*"')
        map_surfaces = cubit.string_from_id_list(belt_surfaces + ply_surfaces + chafer_surfaces + cap_surfaces)
        self.surfaceMappedLineEdit.setText(map_surfaces.strip())
        
    # Main algorithm for meshing
    def MeshTireSurfaces(self):
        cubit.cmd("undo group begin")
        
        surfaces = cubit.get_entities("surface")
        if not surfaces:
            # Assuming cubit_utils.ErrorWindow is updated to PySide6
            cubit_utils.ErrorWindow("Surfaces must exist prior to meshing.")
            cubit.cmd("undo group end")
            return
        try:
            meshed = any([cubit.is_meshed("surface", s ) for s in surfaces])
        except Exception as e:
            print("Failed getting mesh state:", e)
            cubit.cmd("undo group end")
            return

        if meshed:
            # 4. Access QMessageBox.Yes using the PySide6 Enum syntax
            result = cubit_utils.QuestionWindow("Surfaces are already meshed. Delete the existing mesh?")
            if result == QMessageBox.StandardButton.Yes:
                cubit.cmd('delete mesh')
            else:
                cubit.cmd("undo group end")
                return

        # set all surfaces to scheme tripave and then overwrite the mapped surfaces
        try:
            cubit.cmd('surface all except surface with has_scheme "pave" scheme tripave')
        except Exception as e:
            print("Failed setting mesh scheme as tripave:", e)

        # set up the mapped surfaces
        try:
            self.SetMappableSurfaces()
        except Exception as e:
            print("Failed setting map scheme:", e)
            cubit.cmd("undo group end")
            return

        mesh_size = self.meshSize.text()
        try:
            cubit.cmd(f'surface all size {mesh_size}')
        except Exception as e:
            print("Failed setting mesh size:", e)

        # Set the default element type for Abaqus
        try:
            cubit.cmd('create solver_element "abaqus" "CGAX4H" from "QUAD4"')
            cubit.cmd('create solver_element "abaqus" "CGAX4H" from "QUAD"')
            cubit.cmd('create solver_element "abaqus" "CGAX3H" from "TRI3"')
            cubit.cmd('create solver_element "abaqus" "CGAX3H" from "TRI"')
            cubit.cmd('create solver_element "abaqus" "SFMGAX1" from "BEAM"')
            cubit.cmd('create solver_element "abaqus" "SFMGAX1" from "BAR2"')
            cubit.cmd('create solver_element "abaqus" "SFMGAX1" from "BAR"')
        except Exception as e:
            print("Failed setting solver_element:", e)
        try:
            cubit.cmd("mesh surface all")
        except Exception as e:
            print("Unable to mesh surfaces:", e)

        cubit.cmd("undo group end")


def main():
    # 'claro' must be defined in the calling scope (the __main__ block)
    global claro
    dlg = TireMesh(claro)
    
    # Original commented out code for moving the dialog is omitted for brevity,
    # but the necessary PySide6 classes for that (QTabWidget, QPoint) exist.
    
    # The original code used show()
    dlg.show()

if __name__ == "__coreformcubit__":
    claro = cubit_utils.find_claro()
    
    # findChild requires the class object QDockWidget
    try:
        ccp = claro.findChild(QDockWidget, "CubitCommandPanel")
        ccl = claro.findChild(QDockWidget, "ClaroCommandWindow")
    except Exception as e:
        # Handle cases where claro is None or findChild fails
        pass
        
    main()

