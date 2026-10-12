import os
import re
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.i18n import LanguageManager

def audit_i18n():
    tr_keys = set(LanguageManager.TRANSLATIONS.get('tr', {}).keys())
    en_keys = set(LanguageManager.TRANSLATIONS.get('en', {}).keys())
    
    print(f"=== I18N STATS ===")
    print(f"TR Keys: {len(tr_keys)}, EN Keys: {len(en_keys)}")
    diff_tr_en = tr_keys - en_keys
    diff_en_tr = en_keys - tr_keys
    if diff_tr_en:
        print(f"ERROR: Keys in TR but not EN ({len(diff_tr_en)}): {diff_tr_en}")
    if diff_en_tr:
        print(f"ERROR: Keys in EN but not TR ({len(diff_en_tr)}): {diff_en_tr}")
    if not diff_tr_en and not diff_en_tr:
        print("OK: TR and EN dictionaries are 100% symmetric!")

    # Scan codebase for LanguageManager.tr calls
    pattern = re.compile(r'LanguageManager\.tr\(\s*[\'\"]([a-zA-Z0-9_\-]+)[\'\"]')
    missing_in_dict = {}
    
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith('.py') and f != 'i18n.py':
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                matches = pattern.findall(content)
                for m in matches:
                    if m not in tr_keys:
                        missing_in_dict.setdefault(m, []).append(os.path.relpath(path, src_dir))

    print(f"\nMissing Keys in i18n dictionaries ({len(missing_in_dict)}):")
    for k in sorted(missing_in_dict.keys()):
        print(f"  '{k}' called in: {missing_in_dict[k]}")
    return missing_in_dict

if __name__ == '__main__':
    audit_i18n()
