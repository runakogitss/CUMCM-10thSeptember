import os
import pandas as pd

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "Annex5_Templates")

def export_result(file_name, data_dict):
    """
    Writes data arrays directly into Annex 5 submission spreadsheets[cite: 1].
    If the target file is locked (open in Excel), falls back to a copy with
    a `_generated` suffix instead of crashing.
    """
    target_path = os.path.join(TEMPLATES_DIR, file_name)
    df = pd.DataFrame(data_dict)
    try:
        df.to_excel(target_path, index=False)
        print(f"[SUCCESS] Formatted energy outputs saved to: {target_path}")
    except PermissionError:
        base, ext = os.path.splitext(file_name)
        fallback = os.path.join(TEMPLATES_DIR, f"{base}_generated{ext}")
        df.to_excel(fallback, index=False)
        print(f"[WARNING] {file_name} is open in Excel; results saved to: {fallback}")