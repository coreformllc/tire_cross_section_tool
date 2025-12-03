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
from collections import Counter
import cubit_utils 

from PySide6.QtCore import QMetaObject, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, \
                       QLineEdit, QDialogButtonBox, QPushButton, QMessageBox


class TireRebar(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.resize(239, 150)
        self.setWindowTitle("Create Rebar Blocks")
        self.setObjectName("TireRebar")

        self.gridLayout = QGridLayout(self)
        self.blockRebarLabel = QLabel(u"Select Blocks with Rebar:")
        self.gridLayout.addWidget(self.blockRebarLabel, 0, 0)
        self.blockRebarLineEdit = QLineEdit()
        self.gridLayout.addWidget(self.blockRebarLineEdit, 0, 1)
        self.blockSelect = QPushButton()
        self.blockSelect.setText("Add Selected Blocks")
        self.gridLayout.addWidget(self.blockSelect, 0, 2) 
        self.blockSelect.clicked.connect(self.GetSelected)

        # 2. Update Dialog Button Enums
        QBtn = QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        
        self.buttonBox.button(QDialogButtonBox.StandardButton.Yes).setText("Create Rebar")
        self.buttonBox.accepted.connect(self.CreateRebarBlocks)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.gridLayout.addWidget(self.buttonBox, 1, 1)
        self.setLayout(self.gridLayout)
        QMetaObject.connectSlotsByName(self)
        
        # Assuming cubit object is available globally/in scope
        cubit.set_pick_type('Block')

        # before the rebar blocks are created convert body blocks
        # to surface blocks for export. This also helps with picking.
        self.ResolveSheetBodyBlocks()

    # init -- create GUI

    def GetSelected(self):
        ids = cubit.get_selected_ids()
        if not ids:
            # Using ErrorWindow from cubit_utils
            cubit_utils.ErrorWindow("Select the Blocks Containing Rebar.") 
            return
        current_block_str = self.blockRebarLineEdit.text()
        current_blocks = cubit.parse_cubit_list('block', current_block_str)
        block_str = cubit.string_from_id_list(current_blocks + ids)
        self.blockRebarLineEdit.setText(block_str)
        
    def GetRebarLineEdit(self):
        rebar_block_str = self.blockRebarLineEdit.text()
        if not rebar_block_str:
            return []
        rebar_blocks = cubit.parse_cubit_list('block', rebar_block_str)
        return rebar_blocks 

    # The Cubit command to get the center edges misses the first
    # and last edge in the surface. The next two functions are used
    # to find the first and last edge.
    def GetNextEdge(self, start_node, edge):
        start_faces = set(cubit.get_node_faces(start_node))
        end_faces = set(cubit.parse_cubit_list("face", f"in edge {edge}"))
        next_faces = start_faces - end_faces
        # The assumption here is that we are in a mapped surface and an
        # edge is only shared by two quadrilateral faces
        quad1_edges = set(cubit.parse_cubit_list("edge", f"in face {next_faces.pop()}"))
        quad2_edges = set(cubit.parse_cubit_list("edge", f"in face {next_faces.pop()}"))
        edge = quad1_edges.intersection(quad2_edges)
        assert(len(edge) == 1)
        return edge[0]

    def GetLastEdge(self, start_node, edge_list):
        first_edge = [e for e in edge_list if start_node in cubit.get_connectivity('edge', e)]
        assert(len(first_edge) == 1)
        start_faces = set(cubit.parse_cubit_list("face", f"in node {start_node}"))
        end_faces = set(cubit.parse_cubit_list("face", f"in edge {first_edge[0]}"))
        start_faces = list(start_faces - end_faces)
        assert(len(start_faces) == 2)
        start_edge = cubit.parse_cubit_list('edge', f'in face {start_faces[0]} in face {start_faces[1]}')
        assert(len(start_edge) == 1)
        return start_edge[0]

    # Given a surface with four face elements (quad surface) that starts
    # or ends a rebar chain, the center node of the quad surface and
    # an edge connected to the rebar chain, find the remaining edge.
    def GetNextQuadEdge(self, center_node, connected_edge):
        try:
            quad_faces = set(cubit.parse_cubit_list('face', f'in node {center_node}'))
            assert(len(quad_faces) == 4)
            edge_faces = set(cubit.parse_cubit_list('face', f'in edge {connected_edge}'))
            remaining_faces = list(quad_faces - edge_faces)
            assert(len(remaining_faces) == 2)
            next_edge = cubit.parse_cubit_list('edge', f'in face {remaining_faces[0]} in face {remaining_faces[1]}')
            assert(len(next_edge) == 1)
        except Exception as e:
            print(f"Failed to find Quad Surface edge: {e}")
            return -1

        return next_edge[0]

    # we can't guarantee that edges are ordered although testing
    # shows that they normally are. Find the nodes that aren't shared
    # and the edges they belong to. 
    def GetFirstLastEdgeInList(self, edge_list):
        nodes = [cubit.get_connectivity('edge', e) for e in edge_list]
        # flatten the nodes
        node_list = [node for sublist in nodes for node in sublist]
        unique_nodes = [n for n,v in Counter(node_list).items() if v == 1]
        assert(len(unique_nodes) == 2)
        try:
            first_edge = self.GetLastEdge(unique_nodes[0], edge_list)
            last_edge = self.GetLastEdge(unique_nodes[1], edge_list)
        except Exception as e:
            print(f"Error: {e}")
            first_edge = last_edge = -1

        return first_edge, last_edge

    def GetRebarBlockName(self, base_block_id):
        base_block_name = cubit.get_block_name(base_block_id)
        split_name = base_block_name.split('-')
        suffix = "-".join(split_name[3:]) # remove tire-1_Set-Rubber
        rebar_block_name = "reinf-1_Set-Rebar-" + suffix
        return rebar_block_name

    # There is a deficiency in Cubit when working with blocks of sheet
    # bodies. After we have everything else taken care of convert the
    # blocks of bodies to blocks of surfaces.
    def ResolveSheetBodyBlocks(self):
        bodies = cubit.get_entities('body')
        # blocks were created body ids. So body id == block id
        for body in bodies:
            if cubit.entity_exists('block', body) and cubit.parse_cubit_list('volume', f'in block {body}'):
                cubit.cmd(f'block {body} remove volume in body {body}')
                cubit.cmd(f'block {body} add surface in body {body}')
                cubit.cmd(f'block {body} element type QUAD')
        
        # and pre-populate the selection dialog with the default surfaces require rebar
        belt_blocks = cubit.parse_cubit_list('block', 'with name "*Belt*" except block with name "*filler*"')
        ply_blocks = cubit.parse_cubit_list('block', 'with name "*Bodyply*"')
        chafer_blocks = cubit.parse_cubit_list('block', 'with name "*Chafer*"')
        cap_blocks = cubit.parse_cubit_list('block', 'with name "*Set-Rubber-Cap*"')
        rebar_blocks = cubit.string_from_id_list(belt_blocks + ply_blocks + chafer_blocks + cap_blocks)

        self.blockRebarLineEdit.setText(rebar_blocks)

    # After reflection we need to rename some of the blocks to reflect left and right.
    # Find the blocks, split them, and rename them. 
    # For example, the right chafer is located on the negative Z side.
    def ModifyBlockNames(self, block_name):
        try:
            block_tuple = cubit.parse_cubit_list('block', f'with name "{block_name}"') 
            assert(len(block_tuple) == 1)
            block = block_tuple[0]
        except Exception:
            return

        # get the edges in the block on the +Y side
        pos_y_block_edges = cubit.parse_cubit_list('edge', f'in block {block} with y_coord > 0')
        pos_y_edge_str = cubit.string_from_id_list(pos_y_block_edges)
        # remove the positive y edges from the block
        cubit.cmd(f'block {block} remove edge {pos_y_edge_str}')

        # make sure that the block name is not already left or right
        if "-left" in block_name:
            block_name = block_name.replace('-left', '')
        if "-right" in block_name:
            block_name = block_name.replace('-right', '')

        # rename the negative y block
        block_right = block_name + "-right"
        cubit.cmd(f'block {block} name "{block_right}"')

        # create the positive y block
        next_block = cubit.get_next_block_id()
        cubit.cmd(f'block {next_block} add edge {pos_y_edge_str}')
        block_left = block_name + "-left"
        cubit.cmd(f'block {next_block} name "{block_left}"')

    # the assumption is that rebar surfaces are only 
    # two elements thick. We might be given only one surface
    def CreateRebarBlocks(self):
        rebar_blocks = self.GetRebarLineEdit()
        if not rebar_blocks:
            cubit_utils.ErrorWindow("Select blocks and add the selected blocks prior to creating rebar blocks") 
            return
        try:
            all_rebar_surfaces = cubit.parse_cubit_list('surface', f'in block {" ".join(str(b) for b in rebar_blocks)}') 
            assert(len(all_rebar_surfaces) > 0)
        except Exception as e:
            print(f"Failed getting all_rebar_surfaces\n{e}")

        meshed = [cubit.is_meshed("surface", s) for s in all_rebar_surfaces]
        if not all(meshed):
            # Using ErrorWindow from cubit_utils
            cubit_utils.ErrorWindow("Surfaces must be meshed with two elements through the thickness to create rebar elements") 
            return

        rebar_chain_edges = []
        for block in rebar_blocks:
            surfaces = cubit.parse_cubit_list('surface', f'in block {block}') 
            quad_surfaces = []
            for surface in surfaces:
                try:
                    rebar_edges = cubit.parse_cubit_list("edge", f"in node in surface {surface} except edge in node in curve in surface {surface}")
                    if rebar_edges:
                        first_edge, last_edge = self.GetFirstLastEdgeInList(rebar_edges)
                        rebar_chain_edges = rebar_chain_edges + list(rebar_edges)
                        rebar_chain_edges.append(first_edge)
                        rebar_chain_edges.append(last_edge)
                    else: # this is a 4x4 quad surface with no internal edges.
                        quad_surfaces.append(surface)
                except Exception as e:
                    print(f"Error creating rebar on surface {surface}, {e}")
            
            for surface in quad_surfaces: # if quad_surfaces are empty, this is skipped
                try:
                    center_node = cubit.parse_cubit_list('node', f'in surface {surface} except node in curve in surface {surface}')
                    assert(len(center_node) == 1)
                    center_node = center_node[0]
                    rebar_nodes = [cubit.get_connectivity('edge',e) for e in rebar_chain_edges]
                    rebar_node_set = set([node for sublist in rebar_nodes for node in sublist])
                    pinwheel_set = set(cubit.parse_cubit_list('node', f'in edge in node {center_node} except node {center_node}'))
                    rebar_nodes = pinwheel_set.intersection(rebar_node_set)
                    rebar_edges = [cubit.parse_cubit_list('edge',f'in node {center_node} in node {e}') for e in rebar_node_set]
                    rebar_edges = [t for t in rebar_edges if t] # remove empty tuples
                    if len(rebar_edges) == 2:
                        for edge in rebar_edges:
                            rebar_chain_edges.append(edge[0])
                    elif len(rebar_edges) == 1:
                        # the quad surface starts or ends the chain so we only found one edge.
                        # now we have to find the other edge
                        found_edge = rebar_edges[0][0]
                        next_edge = self.GetNextQuadEdge(center_node, found_edge)
                        rebar_chain_edges.append(found_edge)
                        rebar_chain_edges.append(next_edge)

                except Exception as e:
                    cubit_utils.WarningWindow(f'Unable to create rebar elements on surface {surface}\n  {e}') 
            try:
                block_id = cubit.get_next_block_id()
                cubit.cmd(f"block {block_id} edge {' '.join([str(e) for e in rebar_chain_edges])}")
                cubit.cmd(f"block {block_id} element type BAR2")
                name = self.GetRebarBlockName(block)
                cubit.cmd(f"block {block_id} name '{name}'")
            except Exception as e:
                block_name = cubit.get_block_name(block)
                print(f"Error adding rebar on block {block} named {block_name}")
                print(e)
            rebar_chain_edges = []


        # modify blocks that are left and right oriented
        self.ModifyBlockNames("reinf-1_Set-Rebar-Chafer")
        self.ModifyBlockNames("reinf-1_Set-Rebar-Chafer-nylon1")
        self.ModifyBlockNames("reinf-1_Set-Rebar-Chafer-nylon2")

        # renumber and reorder so that blocks contain contiguous ids oriented
        # in the correct direction
        self.RenumberRebarNodesAndEdges()

    def RenumberRebarNodesAndEdges(self):
        # get all the block ids
        rebar_blocks = cubit.parse_cubit_list('block', 'with name "reinf*')
        
        # make sure that node and edge groups will fit into the desired sequence
        # 1) Check for the maximum element id
        # 2) TODO: renumber rebar should default to uniqueids false and have a
        # uniqueids option to turn it on.
        error_blocks = []
        for block in rebar_blocks:  
            elem_start = max(cubit.get_last_id('quad'), cubit.get_last_id('tri'), cubit.get_last_id('edge')) + 1
            max_node_id = cubit.get_last_id('node') + 1
            node_start = elem_start + max_node_id
            # execute the cubit commands to modify the edges in the mesh database
            # Use the cubit extended filtering syntax "edge in block <id>" option to specify the edges
            initial_nodes = self.RenumberStartNode(block)
            if -1 not in initial_nodes:
                try:
                    initial_node_str = " ".join([str(n) for n in initial_nodes])
                    cubit.cmd(f'renumber rebar block {block} initial node {initial_node_str} node_start_id {node_start} elem_start_id {elem_start}')
                    cubit.silent_cmd('compress')
                except Exception as e:
                    error_blocks.append(block)
                    print(f"Error renumbering rebar block {block}")
                    print(e)
            else:
                print(f"Unable to find the initial node for reordering block {block}.")
                print(f"    Check merge status of curves in block.")
                error_blocks.append(block)

        if (error_blocks):
            # Using WarningWindow from cubit_utils
            cubit_utils.WarningWindow(f"Unable to renumber the following blocks: {' '.join([str(e) for e in error_blocks])}")
    
    
    # Get the start node for reordering rebar blocks. The general trend is 
    # clockwise ordering. However, the ply bends back on itself so it starts
    # counter-clockwise. We can avoid this by finding the rebar start node with
    # maximum y value. We can also have discontinuities in the rebar block. Return
    # a list of start nodes.
    def RenumberStartNode(self, block_id):
        endpoint_nodes = []
        start_nodes = []
        nodes = cubit.parse_cubit_list("node", f"in edge in block {block_id}")
        for n in nodes:
            edges = cubit.parse_cubit_list("edge", f"in node {n} in edge in block {block_id}")
            if len(edges) == 1:
                endpoint_nodes.append(n)
        
        if len(endpoint_nodes) % 2 == 0:
            for i in range(0, len(endpoint_nodes), 2):
                coords1 = cubit.get_nodal_coordinates(endpoint_nodes[i])
                coords2 = cubit.get_nodal_coordinates(endpoint_nodes[i+1])
                # The logic for appending start_nodes needs fixing, as it was outside the loop 
                # and relying on the last iteration's coords1/coords2. I'm inferring the intent:
                if coords1[1] > coords2[1]:
                    start_nodes.append(endpoint_nodes[i])
                else:
                    start_nodes.append(endpoint_nodes[i+1])
        else:
            return [-1] # Return a list containing -1 if the number of endpoints is odd
        
        return start_nodes


def main():
    claro = cubit_utils.find_claro()
    dlg = TireRebar(claro)
    dlg.show() # The original code used show()

if __name__ == "__coreformcubit__":
    main()

