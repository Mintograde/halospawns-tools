
map conversion process

```

    Input:  mapname.map
    Output: mapname.glb

    refinery:               .map -> .scenario + .scenario_structure_bsp                 also check reclaimer/meta/wrappers/halo_map.py
    guerilla/kornman00:     .scenario -> mapname.txt
    halospawns-tools:       mapname.txt -> itemlocations.json                           (spawns/teles/etc) -- note, refinery can also display metadata (double click .scenario tag, "display metadata")
    aether:                 scenario_structure_bsp -> .obj + .mtl + .png
    halospawns-tools:       post process .obj + .mtl
    blender:                .obj + .mtl + .png -> .glb                                  https://blender.stackexchange.com/a/57921
    halospawns:             .glb -> three.js


mek (refinery) -> aether -> blender -> gltf -> threejs
                        |
                         -> remove quotes from mtllib/usemtl lines in .obj file
                            and maybe newmtl in .mtl file
                            also -- imported object name can be set in .obj on line starting with 'g '
                            ^ this should all be scripted before importing (pywinauto for aether control?)

also need scenario mapname.txt from guerilla for spawn locations


aether-postprocess
    in .mtl:
        for map_Kd, change
            "metal plate floor.png"
        to
            metal-plate-floor.png
        (remove quotes and spaces, and rename actual exported .png file)

```