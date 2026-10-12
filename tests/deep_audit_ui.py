import os
import re
import sys
from PyQt6.QtWidgets import QApplication, QLabel, QDialog

app = QApplication.instance() or QApplication(sys.argv)

dialog_dir = r"src/ui/dialogs"
files = [os.path.join(dialog_dir, f) for f in os.listdir(dialog_dir) if f.endswith(".py")]

print("=== DEEP AUDIT: LABELS WITHOUT WORD WRAP & HARDCODED INFO BOXES ===")

for fpath in sorted(files):
    fname = os.path.basename(fpath)
    with open(fpath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        # 1. Check for hardcoded styles like rgba(56, 189, 248), #38bdf8, rgba(0, 0, 0, 0.2), #242426, #1a1a1e
        if ("setStyleSheet" in line or "background:" in line or "background-color:" in line) and any(
            c in line for c in ["rgba(56, 189, 248", "rgba(0, 0, 0, 0.2)", "#38bdf8", "border-left: 3px solid", "rgba(255, 255, 255, 0.05)", "rgba(255, 255, 255, 0.1)"]
        ):
            print(f"[HARDCODED_BOX] {fname}:{i} -> {line.strip()[:100]}")

        # 2. Check for labels that have long text or LanguageManager.tr(...) and lack setWordWrap(True)
        if "QLabel(" in line and ("LanguageManager.tr" in line or len(line) > 60):
            # check the next 5 lines
            chunk = "".join(lines[i-1:min(len(lines), i+6)])
            var_match = re.search(r'(\w+)\s*=\s*QLabel\(', line)
            if var_match:
                var = var_match.group(1)
                if not re.search(rf'{var}\.setWordWrap\(\s*True\s*\)', chunk):
                    # Check if text is descriptive (hint/desc/info/note/tip/warn)
                    if any(k in var.lower() or k in line.lower() for k in ["hint", "desc", "info", "tip", "note", "warn", "help", "detail", "sub"]):
                        print(f"[NO_WORD_WRAP] {fname}:{i} ({var}) -> {line.strip()[:90]}")
