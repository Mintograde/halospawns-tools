"""

    Input:  mapname.scenario
    Output: mapname.obj

    Use inspect.exe for control info

    Note: the data/ and tags/ directories must be present for Aether to start

"""
import glob
import os
import shutil
import time

import pywinauto
from pywinauto.application import Application

from obj_cleanup import aether_postprocess

print(f'pywinauto version {pywinauto.__version__}')

CLEAN_PROJECT_FILES = True
CLEAN_DATA_FOLDER = True

aether_path = r"C:\Users\minto\Downloads\Aether\Aether.exe"
ce_path = r"L:\ce"
current_time = str(time.time()).replace(".","")
aeth_project_name = f'{current_time}.aeth'


def collect_images(image_filenames, destination_folder):
    """
    Copy all images into the specified folder, with new names
    """
    copied_files = {}
    for source_path in image_filenames:
        destination_filename = os.path.basename(source_path).replace(' ', '-')
        destination_path = shutil.copy2(source_path, os.path.join(destination_folder, destination_filename))
        copied_files[source_path] = destination_path
    return copied_files


def scenario_to_obj(scenario_path):

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
    export_bsp_obj = dialog.child_window(auto_id="bspObjFilenameText", control_type="Edit").get_value()
    export_lightmaps_obj = dialog.child_window(auto_id="lightmapObjFilenameText", control_type="Edit").get_value()
    export_portals_obj = dialog.child_window(auto_id="portalsObjFilenameText", control_type="Edit").get_value()
    export_fog_obj = dialog.child_window(auto_id="fogPlanesObjFilenameText", control_type="Edit").get_value()

    export_bsp_mtl = export_bsp_obj[:export_bsp_obj.find('.')] + '.mtl'
    export_lightmaps_mtl = export_lightmaps_obj[:export_lightmaps_obj.find('.')] + '.mtl'
    export_portals_mtl = export_portals_obj[:export_portals_obj.find('.')] + '.mtl'
    export_fog_mtl = export_fog_obj[:export_fog_obj.find('.')] + '.mtl'

    print('\n== obj files generated ==')
    print(' + ' + os.path.join(ce_path, export_save_folder, export_bsp_obj))
    print(' + ' + os.path.join(ce_path, export_save_folder, export_lightmaps_obj))
    print(' + ' + os.path.join(ce_path, export_save_folder, export_portals_obj))
    print(' + ' + os.path.join(ce_path, export_save_folder, export_fog_obj))

    print('\n== mtl files generated ==')
    print(' + ' + os.path.join(ce_path, export_save_folder, export_bsp_mtl))
    print(' + ' + os.path.join(ce_path, export_save_folder, export_lightmaps_mtl))
    print(' + ' + os.path.join(ce_path, export_save_folder, export_portals_mtl))
    print(' + ' + os.path.join(ce_path, export_save_folder, export_fog_mtl))

    app.Aether.Export.ExportButton.click()
    app.Aether.Export.close()
    app.Aether.close()

    print('\n== Images generated ==')
    images = []
    for filename in glob.glob(os.path.join(ce_path, 'data') + '/**/bitmaps/*.png', recursive=True):
        images.append(filename)
        print(f' + {filename}')

    print('\n== Markers generated ==')
    markers = []
    print(f'finding markers in {os.path.join(ce_path)}/**/*.aemk')
    for filename in glob.glob(os.path.join(ce_path) + '/**/*.aemk', recursive=True):
        print(f' + {filename}')
        markers.append(filename)

    if CLEAN_PROJECT_FILES:
        print('\n== Removing Aether project files ==')
        for filename in glob.glob(os.path.join(ce_path, 'tags') + f'/**/{aeth_project_name}', recursive=True):
            print(f' - {filename}')
            os.remove(filename)

    renamed_files = collect_images(images, os.path.join(ce_path, export_save_folder))
    print(f'\nCopied {len(renamed_files)} images to {os.path.join(ce_path, export_save_folder)}')

    obj_filename, mtl_filename = aether_postprocess(os.path.join(ce_path, export_save_folder, export_bsp_obj))

    return dict(
        project_name=aeth_project_name,
        map_name=export_bsp_obj[:export_bsp_obj.find('.')],
        obj=obj_filename,
        mtl=mtl_filename,
        images=list(renamed_files.values()),
        markers=markers
    )


if __name__ == '__main__':

    scenario_to_obj(scenario_path=r"L:\ce\tags\levels\test\chillout\chillout.scenario")
