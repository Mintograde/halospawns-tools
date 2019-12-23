"""

    Use inspect.exe for control info

"""
import glob
import os
import shutil
import time
import pywinauto
from pywinauto.application import Application

print(f'pywinauto version {pywinauto.__version__}')

CLEAN_PROJECT_FILES = True
CLEAN_DATA_FOLDER = True

aether_path = r"C:\Users\minto\Downloads\Aether\Aether.exe"
scenario_path = r"L:\ce\tags\levels\test\chillout\chillout.scenario"
ce_path = r"L:\ce"
aeth_project_name = f'{str(time.time()).replace(".","")}.aeth'

if CLEAN_DATA_FOLDER:
    try:
        shutil.rmtree(os.path.join(ce_path, 'data/levels'), ignore_errors=True)
    except OSError as e:
        print('Warning: could not clean data folder.')
        print(e)


app = Application(backend="uia").start(f'{aether_path} {scenario_path}')

app.Dialog.FileameEdit.set_text(f"{aeth_project_name}")
app.Dialog.Save.click()

app.Aether.restore()
app.Aether.ExportBsp.click_input()

# TODO: read filenames from export dialog
dialog = app.Aether.Export.BSPExport
# dialog.print_control_identifiers()
# export_save_folder = dialog.SaveFolderEdit.get_value()
# export_bsp_file = dialog.BSPFileEdit.get_value()
# export_lightmaps_file = dialog.LightmapsFileEdit.get_value()
# export_portals_file = dialog.PortalsFileEdit.get_value()
# export_fog_file = dialog.FogPlanesFileEdit.get_value()
export_save_folder = dialog.child_window(title="Errors occured during the last export", auto_id="saveFolderText", control_type="Edit").get_value()
export_bsp_file = dialog.child_window(auto_id="bspObjFilenameText", control_type="Edit").get_value()
export_lightmaps_file = dialog.child_window(auto_id="lightmapObjFilenameText", control_type="Edit").get_value()
export_portals_file = dialog.child_window(auto_id="portalsObjFilenameText", control_type="Edit").get_value()
export_fog_file = dialog.child_window(auto_id="fogPlanesObjFilenameText", control_type="Edit").get_value()
print(export_save_folder)
print(export_bsp_file)
print(export_lightmaps_file)
print(export_portals_file)
print(export_fog_file)

app.Aether.Export.ExportButton.click()
app.Aether.Export.close()
app.Aether.close()

print('== Images generated ==')
for filename in glob.glob(os.path.join(ce_path, 'data') + '/**/bitmaps/*.png', recursive=True):
    print(f' + {filename}')

print('\n== Markers generated ==')
for filename in glob.glob(os.path.join(ce_path, export_save_folder) + '*.aemk', recursive=True):
    print(f' + {filename}')

if CLEAN_PROJECT_FILES:
    print('\n== Removing Aether project files ==')
    for filename in glob.glob(os.path.join(ce_path, 'tags') + f'/**/{aeth_project_name}', recursive=True):
        print(f' - {filename}')
        os.remove(filename)
