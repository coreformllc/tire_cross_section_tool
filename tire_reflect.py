#! python
from math import fabs, floor, log10
"""
    Reflect the model about the XZ plane. Make sure that blocks get renamed
    as left and right (top/bottom in our orientation). Also, work around an 
    issue in Cubit so that the blocks output the correct element topology.
"""

# There is a deficiency in Cubit where blocks containing bodies are
# always interpreted as 3D entities. Move the surfaces into the blocks
# and set the element type to a 2D surface. 
# TODO: could this be a source of a bug? What happens when we undo this?
# Do we undo the body to surface conversion? Need to fix Cubit.
def ResolveSheetBodyBlocks():
    bodies = cubit.get_entities('body')
    # blocks were created body ids. So body id == block id
    for body in bodies:
        if cubit.parse_cubit_list('volume', f'in block {body}'):
            cubit.cmd(f'block {body} remove volume in body {body}')
            cubit.cmd(f'block {body} add surface in body {body}')
            cubit.cmd(f'block {body} element type QUAD')
        

def ReflectAboutY():
    # Set cubit to copy the blocks on reflection
    cubit.cmd("set copy_block_on_geometry_copy use_original")
    cubit.cmd("set copy_nodeset_on_geometry_copy use_original")
    cubit.cmd("set copy_sideset_on_geometry_copy use_original")

    # AutoCAD doesn't create symmetry vertices at y == 0. Find
    # difference so that we can set a merge tolerance.
    # First, find the vertices near the symmetry plane
    vertices = cubit.get_entities("vertex")
    bbox = cubit.get_total_bounding_box("vertex", vertices)
    y_max = bbox[4]
    # Second, find the curvein the vertices at the symmetry plane
    curves = cubit.parse_cubit_list("curve", f"with y_coord > {-2.0*y_max} and y_coord < {2.0*y_max}")
    # Third, get the bounding box of the vertices in the curves at the symmetry plane
    vertices = cubit.parse_cubit_list("vertex", f"in curve {cubit.string_from_id_list(curves)}")
    print(vertices)
    bbox = cubit.get_total_bounding_box("vertex", vertices)
    # Finally, caluclate the merge tolerance
    y_min = math.fabs(bbox[3])

    if y_min > 0.1:
        WarningWindow("Check the values of the vertices in the symmetry plane.\n The merge tolerance may be incorrect.")

    # The merge tolerance is to the nearest larger power of 10 higher than the gap
    # .0073 goes to .01, .0001 goes to .001, etc.  
    print(f"y_min: {y_min}")
    old_merge = cubit.get_merge_tolerance()
    if y_min > 0.0: 
        exponent = math.floor(math.log10(y_min * 2.0))  # Get the exponent of the range
        merge_tolerance = 10 ** (exponent + 1)  # Calculate the ceiling
        if merge_tolerance > old_merge:
            cubit.cmd(f"merge tolerance {merge_tolerance}")

    # do the reflection
    cubit.cmd("surface all copy reflect y ")

    # reset the copy back to the original state
    cubit.cmd("set copy_block_on_geometry_copy OFF")
    cubit.cmd("set copy_nodeset_on_geometry_copy OFF")
    cubit.cmd("set copy_sideset_on_geometry_copy OFF")

    # this is a really odd hack due to a graphics issue
    cubit.cmd("merge all")
    cubit.cmd("undo")
    cubit.cmd("merge all")
    cubit.cmd(f"merge tolerance {old_merge}")


def main():
    ResolveSheetBodyBlocks()
    ReflectAboutY()

if __name__ == "__coreformcubit__":
    main()

