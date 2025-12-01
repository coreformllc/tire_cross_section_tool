### Coreform Cubit toolbar for meshing 2D tire cross-sections. 

## Toolbar Installation:
  1. Download the tarball.
  2. Open Coreform Cubit. 
  3. Go to Tools/Custom Toolbar Editor.
  4. Right click in the upper left frame labeled Toolbars.
  5. Select Import.
  6. Using the Package option, select the downloaded tarball and a destination directory.
  7. Click on the Import push button.
  8. Click on the Finish push button.
*NOTE:* Requires Coreform Cubit 2025.11 or greater for PySide6 support.

## Usage
Once the toolbar is installed fourteen new icons will be displayed in the Coreform Cubit toolbar.
![surface create](icons/surface_create.png) - Create surfaces given curves.
![assign materials](icons/assign_materials.png) - Create blocks assign some default names.
![blunt tangency](icons/blunttangent.png) - Modify the geometry to remove sharp tangencies.
![cut lines](icons/cutlines.png) - Opens the Geometry/Surface/Split Surface command panel. The most commonly used option is "Close To Vertex". This option allows the user to specify multiple surfaces, a curve on one side of the split, and a curve on the opposite side. The split will occur along the closest point on the curve to the selected point.
![curve merge](icons/curvemerge.png) - Invokes the Cubit imprint and merge operations to ensure a conformal mesh.
![mesh](icons/mesh_1.png) - Creates a quad dominant mesh on all surfaces.
![assign bcs](icons/assign_bcs.png) - Assigns element groups based on the "tip" of the tire near the bead.
![reflect](icons/reflect.png) - Reflects a part created in the XY plane.
![add rebar](icons/rebar.png) - Defines rebar on 2xN mapped surfaces with a predefined block names, for example, any mapped block continaining the string "Belt."
![move node](icons/move_node.png) - Opens the Mesh/Node/Move Node command panel.
![undo to cut lines](icons/undo.png) - Does an undo back to cut lines. Note that manually defined composite curves may be lost.
![rebar sense](icons/edgesense.png) - Draw the sense of the rebar elements.
![collapse edge](icons/collapse.png) - Collapse an edge and remove bad triangles.

## Creating an updated tarball
  1. Ensure that all changes to toolbar scripts are functioning in Cubit.
  2. Go to Tools/Custom Toolbar Editor.
  3. Right click in the upper left frame labeled Toolbars and Select Export.
  5. Select the export file location and name. The .tar.gz extension will be automatically added. The ... on the right hand side will open a file browser.
  6. Click on Next
  7. Check only the DAGMC toolbar and click Next.
  8. Click on Add Files. Browse into the scripts directory and select the __init__ and utils python files. 
  9. Click on Open. This will add a new folder called files.
  10. Open the files folder and drag __init__.py and utils.py into the scripts folder.
  11. Right click on the files folder and select Remove selected.
  12. Click on Finish.

