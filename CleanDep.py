import geopandas as gpd
import unicodedata, re
from typing import Dict, Optional

def guess_column_name(columns):
    for col in columns:
        if "name" in col.lower() or "dep" in col.lower():
            return col
    return columns[0]

def normalize_string(text: str) -> str:
    return re.sub(r"\s+", " ",
                  unicodedata.normalize("NFKD", text)
                             .encode("ascii", "ignore")
                             .decode()
                             .lower()
                             .strip())

def clean_department_names(
    shapefile_path: str,
    clean_names: Dict[str, str],
    dep_col: Optional[str] = None
) -> str:
    gdf = gpd.read_file(shapefile_path)
    if gdf.empty:
        raise ValueError("The shapefile appears to be empty.")

    # 1) Determine default column:
    default_col = dep_col or guess_column_name(gdf.columns)
    print("🔍 Available columns:", list(gdf.columns))
    # 2) Prompt user to confirm or override:
    choice = input(f"Enter column name to clean (default = '{default_col}'): ").strip()
    dep_col = choice or default_col
    print(f"🔍 Cleaning using column: {dep_col}")

    # 3) Build normalized replacement map:
    unique_raw = sorted(gdf[dep_col].dropna().unique())
    normalized_map = {normalize_string(k): v for k, v in clean_names.items()}
    cleaned_map = {
        orig: normalized_map.get(normalize_string(orig), orig)
        for orig in unique_raw
    }

    # 4) Apply and write out
    gdf["cleaned_name"] = gdf[dep_col].map(cleaned_map)
    output = shapefile_path.replace(".shp", "_cleaned.shp")
    gdf.to_file(output)
    print(f"✅ Cleaned shapefile saved as: {output}")
    return output
