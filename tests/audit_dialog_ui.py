import os
import re

dialog_dir = r"src/ui/dialogs"
files = [os.path.join(dialog_dir, f) for f in os.listdir(dialog_dir) if f.endswith(".py")]

print("=== CHECKING INFO BOXES, BANNERS, HARDCODED FRAMES IN DIALOGS ===")
for fpath in sorted(files):
    fname = os.path.basename(fpath)
    with open(fpath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    for idx, line in enumerate(lines, 1):
        # Look for hardcoded background-color on frames/labels/boxes
        if "setStyleSheet" in line and any(k in line.lower() for k in ["background", "background-color", "border", "border-radius"]):
            if any(term in line.lower() for term in ["rgba(0, 0, 0", "#1", "#2", "#3", "rgba(255, 255, 255, 0.0", "#e", "#f"]):
                # check if it looks like an info card or panel frame
                print(f"[{fname}:{idx}] {line.strip()[:110]}")

        # Look for fixedWidth on labels or dialogs
        if "setFixedWidth" in line and any(w in line.lower() for w in ["lbl", "label", "text", "info", "title", "desc"]):
            print(f"[FIXED_WIDTH_LBL in {fname}:{idx}] {line.strip()}")
