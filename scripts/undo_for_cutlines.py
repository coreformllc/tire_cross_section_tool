#!python
"""
    If the process has been completed once and you want to start over
    we have to get back to a place where we can insert cutlines.
    1) Unmerge everything
    2) Remove the reflected geometry
    3) Delete the mesh
    4) Remove all composites. There is an issue here. We want to
       be able to recover composites that the user added manually.
       I still don't know how to track those although a potential 
       algorithm is fleshed out here.
    5) Clean up duplicate vertex names (new Cubit should fix this)
    6) Remove the rebar blocks
    7) Put bodies back in blocks (this is a work-around)
    8) Replace the "-right" designation on some blocks
"""

# this requires a new version of Cubit and is still under development
# but this captures the algorithm. The variable automatic_composite_curves is 
# a global variable defined in composite.py. Here it should be used as a 
# read-only value. 
def recover_manual_composites():
    try:
        composite_curves = set(cubit.parse_cubit_list('curve', 'with is_virtual'))
        manual_curves = composite_curves - set(automatic_composite_curves)
    except:
        print("Unable to recreate manually created composite curves.")
    error_found = 0
    for curve in manual_curves:
        try:
            hidden_curves = cubit.get_hidden_by_virtual('curve', curve)
            # this has to be a two step operation.
            # we have to recover and store the manual composites and then
            # after all composites have been deleted we need to recreate them.
            # This brings up a potential problem. The whole reason we are deleting
            # composites is because we can't do a surface split operation on 
            # surfaces with composite curves. If we recreate the composites
            # we may not be able to add cutlines in that region. This is 
            # something to ponder. Maybe the right thing to do is to get
            # split surface to work on composites!
        except:
            error_found += 1
    if error_found > 0:
        print(f'Unable to recover {error_found} composite curves')
        print(f'    You may need an updated version of Coreform Cubit')


cubit.cmd("unmerge all")
reflected_ids = cubit.parse_cubit_list('surface', 'with y_coord > 0')
if reflected_ids:
    reflected_surfaces = cubit.string_from_id_list(reflected_ids)
    cubit.cmd(f'delete surface {reflected_surfaces}')

ids = cubit.parse_cubit_list('surface', 'with is_meshed')
ids += cubit.parse_cubit_list('curve', 'with is_meshed')
ids += cubit.parse_cubit_list('vertex', 'with is_meshed')
if ids:
    cubit.cmd(f"delete mesh")

# remove the composited curves
cubit.cmd("virtual remove body all")

# This is a work-around for a Cubit bug with names
blunt_vertices = cubit.parse_cubit_list('vertex', 'with name "blunt_vertex_*"')
for vertex in blunt_vertices:
    name = cubit.get_entity_name('vertex', vertex)
    if str(vertex) not in name:
        cubit.cmd(f'vertex {vertex} remove name all')
    

cubit.cmd("merge all") # this is needed to be ready to do manual composites

# delete the boundary sets
if cubit.get_sideset_count():
    val = cubit.cmd("delete sideset all")
if cubit.get_nodeset_count():
    val = cubit.cmd("delete nodeset all")

# delete the rebar blocks
rebar_blocks = cubit.parse_cubit_list('block', 'with name "reinf*"')
if rebar_blocks:
    rebar_block_str = cubit.string_from_id_list(rebar_blocks)
    val = cubit.cmd(f'delete block {rebar_block_str}')

# remove surfaces and put bodies back. This should be
# fixed in Cubit so that this is not required.
blocks = cubit.parse_cubit_list('block', 'all')
for block in blocks:
    val = cubit.cmd(f'block {block} remove surface all')
    val = cubit.cmd(f'block {block} add body {block}')
    block_name = cubit.get_entity_name('block', block)
    if block_name.endswith("-right"):
        block_name.replace('-right', '')
    if block_name.endswith("-left"):
        cubit.cmd(f'delete block {block}')
