import os
import shutil
import subprocess
import sys
from pathlib import Path
from pprint import pprint

# replace packages removed from python in 3.12 (imp) and 3.13 (audioop), which are still used by reclaimer
try:
    import zombie_imp
except ImportError:
    pass

try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules['audioop'] = audioop
    except ImportError:
        pass

from map_to_scenario import map_to_scenario
from scenario_to_obj import scenario_to_obj

BLENDER_PATH = os.environ.get(
    'BLENDER_EXECUTABLE_PATH',
    r"C:\Program Files\Blender Foundation\Blender 2.93\blender.exe"
)
# BLENDER_PATH = r"L:\Program Files\Blender Foundation\Blender\blender.exe"
# BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"


def map_to_glb(map_filename, base_directory, output_directory, keep_blend_files=False):

    print(f'Converting {map_filename}')
    print(f'Base directory: {base_directory}')
    print(f'Output directory: {output_directory}')

    scenario_filename, meta_filename = map_to_scenario(map_filename, base_directory)

    files = scenario_to_obj(scenario_path=scenario_filename, meta_filename=meta_filename, remove_lights=False)
    destination = os.path.join(output_directory, files['map_name'])
    destination_files = {}
    # remove duplicates with list(dict.fromkeys())
    source_files = list(dict.fromkeys([files['bsp_obj'],
                                       files['bsp_mtl'],
                                       files['lightmaps_obj'],
                                       files['lightmaps_mtl'],
                                       *files['markers'],
                                       *files['images'],
                                       meta_filename]))
    for file in source_files:
        os.makedirs(destination, exist_ok=True)
        destination_files[file] = shutil.move(file, os.path.join(destination, os.path.basename(file)))
    print(f'Moved {len(destination_files)} to {destination}')
    pprint(destination_files)

    # blender --background test.blend --python mytest.py -- example args 123
    args = [
        BLENDER_PATH,
        '--background',
        '--python',
        # 'blender.py',
        'blender_293.py',
        '--',
        destination_files[files['bsp_obj']],
        destination_files[files['lightmaps_obj']],
        destination_files[meta_filename],
    ]
    print(args)
    results = subprocess.run(args, capture_output=True, encoding='utf8')
    print('=== stdout ===')
    print(results.stdout)
    if results.stderr:
        print('=== stderr ===')
        print(results.stderr)

    return dict(
        glb=Path(destination_files[files['bsp_obj']]).with_suffix('.glb'),
        blend=Path(destination_files[files['bsp_obj']]).with_suffix('.blend'),
        meta=Path(destination_files[meta_filename]),
        map_name=files['map_name'],
    )


def test_blender(mapname):

    args = ['C:\\Program Files\\Blender Foundation\\Blender 2.93\\blender.exe',
            '--python',
            'blender.py',
            '--',
            f'L:/ce/output/{mapname}\\{mapname}.obj',
            f'L:/ce/output/{mapname}\\{mapname}_Lightmap.obj',
            f'L:\\ce\\output\\{mapname}\\{mapname}.json']
    results = subprocess.run(args, capture_output=True, encoding='utf8')
    print('=== stdout ===')
    print(results.stdout)
    print('=== stderr ===')
    print(results.stderr)


if __name__ == '__main__':

    base_directory = r'L:\ce'
    output_directory = r'L:/ce/output/'
    map_filenames = [
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\chillout.map',
        r"L:\bens_stuff\xbox mod\Games\Halo 1 - Pro Edition v2.0\Games\Halo 1 - Pro 2.0\maps\chillout.map"
        # r"L:\ce\input\fbebefb2-b089-4a71-b52d-11cc9e978426",
        # r"L:\ce\input\fbebefb2-b089-4a71-b52d-11cc9e978426.map",
        # r"C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\fbebefb2-b089-4a71-b52d-11cc9e978426.map",  # FIXME: works from within programfiles customedition folder, but not L ce input
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\prisoner.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\hangemhigh.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\damnation.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\bloodgulch.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\beavercreek.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\boardingaction.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\carousel.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\dangercanyon.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\deathisland.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\gephyrophobia.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\icefields.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\infinity.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\longest.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\putput.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\ratrace.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\sidewinder.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\timberland.map',
        # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\wizard.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\decidia.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\doubletake.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\downrush.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\exhibit.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\hotbox.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\imminent.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\madhouse.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\outbnd.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\overflow.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\redshift.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\tinker.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\zerohour.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\atlas.map',
        # r'C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\calamity.map',
        # r"L:\bens_stuff\downloads\Halo 1 - Patch Edition v1.2\Games\Halo 1 - PE\maps\badcreek.map",
        # r"L:\bens_stuff\downloads\Halo 1 - Patch Edition v1.2\Games\Halo 1 - PE\maps\chillout.map",
        # r"L:\bens_stuff\downloads\Halo 1 - Patch Edition v1.2\Games\Halo 1 - PE\maps\dammy.map",
        # r"L:\bens_stuff\downloads\Halo 1 - Patch Edition v1.2\Games\Halo 1 - PE\maps\derelict.map",
        # r"L:\bens_stuff\downloads\Halo 1 - Patch Edition v1.2\Games\Halo 1 - PE\maps\downrush.map",
        # r"L:\bens_stuff\downloads\Halo 1 - Patch Edition v1.2\Games\Halo 1 - PE\maps\hangemhigh.map",
        # r"L:\bens_stuff\downloads\Halo 1 - Patch Edition v1.2\Games\Halo 1 - PE\maps\imminent.map",
        # r"L:\bens_stuff\downloads\Halo 1 - Patch Edition v1.2\Games\Halo 1 - PE\maps\overflow.map",
        # r"L:\bens_stuff\downloads\Halo 1 - Patch Edition v1.2\Games\Halo 1 - PE\maps\prisoner.map",
        # r"L:\bens_stuff\downloads\Halo 1 - Patch Edition v1.2\Games\Halo 1 - PE\maps\ratrace.map",
        # r"L:\bens_stuff\xbox mod\Games\Halo Plus\maps\carousel.map",
        # r"L:\bens_stuff\xbox mod\Games\Halo Plus\maps\boardingaction.map",
        # r"L:\bens_stuff\xbox mod\Games\Halo Plus\maps\bloodgulch.map",
        # r"L:\bens_stuff\xbox mod\Games\Halo Plus\maps\putput.map",
        # r"L:\bens_stuff\xbox mod\Games\Halo Plus\maps\sidewinder.map",
        # r"C:\Users\minto\Downloads\Halo 1 - PE v1.4\Games\Halo 1 - PE\maps\badcreek.map",
        # r"C:\Users\minto\Downloads\Halo 1 - PE v1.4\Games\Halo 1 - PE\maps\chillout.map",
        # r"C:\Users\minto\Downloads\Halo 1 - PE v1.4\Games\Halo 1 - PE\maps\dammy.map",
        # r"C:\Users\minto\Downloads\Halo 1 - PE v1.4\Games\Halo 1 - PE\maps\derelict.map",
        # r"C:\Users\minto\Downloads\Halo 1 - PE v1.4\Games\Halo 1 - PE\maps\downrush.map",
        # r"C:\Users\minto\Downloads\Halo 1 - PE v1.4\Games\Halo 1 - PE\maps\hangemhigh.map",
        # r"C:\Users\minto\Downloads\Halo 1 - PE v1.4\Games\Halo 1 - PE\maps\longshot.map",
        # r"C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE\maps\ui.map",
        # r"C:\Users\minto\Downloads\Halo 1 - PE v1.4\Games\Halo 1 - PE\maps\ratrace.map",
        # r"C:\Users\minto\Downloads\Halo 1 - PE v1.4\Games\Halo 1 - PE\maps\temple.map",
        # r"C:\Users\minto\Downloads\hugeass\hugeass.map",
    ]
    # map_filenames = [
    #     # r'C:\Program Files (x86)\Microsoft Games\Halo Custom Edition\maps\prisoner.map',
    #     # r"L:\bens_stuff\xbox mod\Games\Halo\maps\prisoner.map",
    #     r"C:\Users\minto\Downloads\Halo_1_NHE_1.0\Games\Halo 1 - NHE - Copy\maps\prisoner.map",
    # ]

    # test_blender('prisoner')

    for map_filename in map_filenames:
        pprint(map_to_glb(map_filename, base_directory, output_directory))

