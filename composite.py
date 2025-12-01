#!python
"""
    Get all the curves that form a continuous list and create
    composites where we can. In older versions of Cubit this
    may create error messages. In newer versions this has been
    changed to a warning.

    We also handle compositing around the blunt tangencies.

    We track all composites that are created in this process by
    a notification event COMPOSITE_CREATE_COMPLETED. The undo_for_cutlines
    routine uses the global auto_composite_curves variable to determine
    the composites that must be recreated manually.
"""
import math

# Define a global variable and make sure that the automatically composited 
# curves are always reset at the beginning of this routine. The global is
# read in undo_for_cutlines.py. This is the only routine that should modify it.
if "auto_composite_curves" in locals():
    del auto_composite_curves
auto_composite_curves = []

# Create a method to track the creation of composite curves 
# This is not currently working but is retained here for future work
class TrackComposites(cubit.CIObserve):
    def __init__(self):
        self.start_id = -1

    # called when composite operations start
    def notify_composite_creation_start(self):
        self.start_id = cubit.get_last_id('curve')
                
    # called when composite operations are completed
    def notify_composite_creation_complete(self):
        last_id = cubit.get_last_id('curve')
        if self.start_id > 0:
            # a single operation may create multiple composite curves. 
            # Get the range of curves created. They will be sequentially numbered
            curves = [c for c in range(self.start_id+1, last_id+1) if cubit.entity_exists('curve', c) and cubit.is_virtual('curve', c)]
            auto_composite_curves += curves

# create a class to isolate the event listener and register it
# with each instantiation.
class AutoComposite():

    # Given a list of tuples where each tuple contains a curve length (float)
    # and a curve id (int) find the two tuples that are nearly the same length
    # There _should_ only ever be three edges in the list
    def find_short_edge_pairs(self, edges: list[tuple[float, int]], tolerance=1e-6) -> tuple[float, int]:
        # Sort the tuples based on the floating point values
        try:
            assert(len(edges) == 3)
        except:
            print('Error: Too many edges attached to blunt vertex')
            return None

        sorted_edges = sorted(edges, key=lambda x: x[0])

        short_edges = []
        for i in range(len(sorted_edges) - 1):
            if math.isclose(sorted_edges[i][0], sorted_edges[i + 1][0], abs_tol=tolerance):
                short_edges.append(sorted_edges[i])
                short_edges.append(sorted_edges[i + 1])
                try:
                    assert(len(short_edges) == 2)
                    return short_edges
                except:
                    pass
        return None

    def CreateAutoComposites(self):
        # create and register a listener to track composite curve creation
        #self.listener = TrackComposites()
        #self.listener.register_observer()

        cubit.cmd('undo group begin')
        processed = 0

        # get all the curves in the model
        all_curves = set(cubit.get_entities('curve'))
        num_curves = len(all_curves)
        while (all_curves):
            # find all the curves that are continuous to this curve and composite around it
            curve = all_curves.pop()
            continuous = set(cubit.parse_cubit_list('curve', f'{curve} include continuous'))
            if len(continuous) > 1:
                try:
                    id_string = cubit.string_from_id_list(list(continuous))
                    val = cubit.cmd(f'composite create curve {id_string}')
                except Exception as e:
                    print("Error creating composites:", id_string, e)

            if processed > num_curves:
                print('Number processed exceeds num_curves')
                break
            
            all_curves = all_curves - continuous
            processed = processed + 1

        # composite around the blunted vertices
        blunted_vertices = cubit.parse_cubit_list('vertex', 'with name "blunt_vertex_*"')
        for vertex in blunted_vertices:
            try:
                # The vertex at the tip of blunt was named. Find the short curves in the named vertex
                short_curves = cubit.parse_cubit_list('curve', f'in vertex {vertex} in surface with name "blunted_surface*"')
                assert(len(short_curves) == 2)
            except Exception as e:
                # if there are two blunted surfaces adjacent to one another, we may
                # get three curves around the vertex. We actually want the two that
                # are the same length (within some small tolerance). Create the list of
                # tuples pair down the tuples to two surviving tuples and then get the
                # curve ids back out of the tuples
                short_curve_pairs = [(cubit.curve(c).length(), c) for c in short_curves]
                short_curve_pairs = self.find_short_edge_pairs(short_curve_pairs)
                # note that the function ensures that there are two tuples found
                if not short_curve_pairs:
                    print(f"Error compositing around vertex {vertex}")
                    continue
                short_curves = [c[1] for c in short_curve_pairs]
            
            # get the surface that is shared by both short curves. We have ensured that there are exactly 2 short edges
            try:
                surfaces_1 = set(cubit.parse_cubit_list('surface', f'in curve {short_curves[0]}'))
                surfaces_2 = set(cubit.parse_cubit_list('surface', f'in curve {short_curves[1]}'))
                surface_set = surfaces_1.intersection(surfaces_2)
                assert(len(surface_set) == 1)
                surface = surface_set.pop()
            except Exception as e:
                print(f'Error: Unable to create composite at blunt vertex {vertex}')
                continue

            # Now get the short curve in the blunt and composite it with the correct curve in the adjacent surface
            for curve in short_curves:
                try:
                    other_vertex = cubit.parse_cubit_list('vertex', f'in curve {curve} except vertex with name "blunt_vertex_*"')
                    assert(len(other_vertex) == 1)
                    cubit.cmd(f'composite create curve in surf {surface} in vertex {other_vertex[0]}')
                except Exception as e:
                    print(f"Error compositing curve {curve}")
                    continue

        #self.listener.unregister_observer()

        cubit.cmd('undo group end')

def main():
    composite = AutoComposite()
    composite.CreateAutoComposites()

if __name__ == "__coreformcubit__":
    main()
    

