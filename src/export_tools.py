import os
import pandas as pd

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "Annex5_Templates")

def export_result(file_name, data_dict):
    """
    Writes data arrays directly into Annex 5 submission spreadsheets[cite: 1].
    """
    target_path = os.path.join(TEMPLATES_DIR, file_name)
    df = pd.DataFrame(data_dict)
    df.to_excel(target_path, index=False)
    print(f"[SUCCESS] Formatted energy outputs saved to: {target_path}")