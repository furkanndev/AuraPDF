import os
import re

dialog_dir = r"src/ui/dialogs"
files = [os.path.join(dialog_dir, f) for f in os.listdir(dialog_dir) if f.endswith(".py")]
files.append(r"src/ui/dialog_theme.py")

print("=== SEARCHING ALL HINT/INFO/TIP/CARD WIDGETS ===")
for fpath in sorted(files):
    fname = os.path.basename(fpath)
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    # Search for variable names or labels containing hint, info, tip, note, desc, callout, warning
    matches = re.finditer(r'([a-zA-Z0-9_]*(?:hint|info|tip|note|desc|callout|warning|banner|notice|alert)[a-zA-Z0-9_]*)\s*=\s*(QLabel|QFrame|QWidget)\((.*?)\)', content, re.I)
    for m in matches:
        var_name = m.group(1)
        wtype = m.group(2)
        arg = m.group(3).strip()
        # Find lines following this to see if it sets styling or word wrap
        start_pos = m.start()
        surrounding = content[start_pos:start_pos+350]
        has_wrap = "setWordWrap" in surrounding
        has_ss = "setStyleSheet" in surrounding
        print(f"[{fname}] {var_name} ({wtype}): wrap={has_wrap}, style={has_ss}")
        if has_ss:
            ss_match = re.search(r'setStyleSheet\((.*?)\)', surrounding, re.DOTALL)
            if ss_match:
                print(f"    Style: {ss_match.group(1).strip()[:100]}")
