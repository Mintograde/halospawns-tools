
import os
import re
import sys

def patch_file(file_path, pattern, replacement):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    if content == new_content:
        print(f"No changes made to {file_path}")
    else:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Patched {file_path}")

site_packages = sys.argv[1] if len(sys.argv) > 1 else os.path.join("venv314", "Lib", "site-packages")

handler_path = os.path.join(site_packages, "reclaimer", "hek", "handler.py")

patch_file(handler_path,
           r'print\("Ignore me if you.*?\n\s+print\(format_exc\(\)\)', 
           'pass')

patch_file(handler_path,
           r'cond = lambda desc, f_types=cond: desc\.get\(\'TYPE\'\) in f_types',
           'cond = lambda desc, f_types=cond: (desc.get(\'TYPE\') in f_types) if hasattr(desc, "get") else False')

patch_file(handler_path,
           r'(?<!return nodepath_ref\n        )for key in desc:',
           'if not hasattr(desc, "__iter__") or isinstance(desc, type):\n            return nodepath_ref\n        for key in desc:')

anim_path = os.path.join(site_packages, "reclaimer", "animation", "animation_decompilation.py")
patch_file(anim_path,
           r'print\("WARNING: Animation tag missing nodes\..*?node names won\'t match\."\)',
           'pass')

halo_map_path = os.path.join(site_packages, "reclaimer", "meta", "wrappers", "halo_map.py")
patch_file(halo_map_path,
           r'exec\("from %s\.%s import get" % \(self\.tag_defs_module, fcc2\)\)\n\s+exec\("defs\[\'%s\'\] = get\(\)" % fcc\)',
           'exec("from %s.%s import get; defs[\'%s\'] = get()" % (self.tag_defs_module, fcc2, fcc))')

halo_map_path = os.path.join(site_packages, "reclaimer", "meta", "objs", "halo1_rsrc_map.py")
patch_file(halo_map_path,
           r'exec\("from reclaimer\.hek\.defs.%s import %s_def" %\n\s+\(fcc2, fcc2\)\)\n\s+exec\("defs\[\'%s\'\] = %s_def" % \(fcc, fcc2\)\)',
           'exec("from reclaimer.hek.defs.%s import %s_def; defs[\'%s\'] = %s_def" % (fcc2, fcc2,fcc, fcc2))')




print("Patching complete.")
