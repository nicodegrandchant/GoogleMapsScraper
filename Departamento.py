import geopandas as gpd
import shapely.geometry as geom
import numpy as np
import sys, unicodedata, re
from typing import List, Tuple

AREANAME = "ADM1_ES"
CODENAME = "ADM1_PCODE"

def normalize_string(text: str) -> str:
    return re.sub(
        r"\s+", " ",
        unicodedata.normalize("NFKD", text)
                   .encode("ascii", "ignore")
                   .decode()
                   .lower().strip()
    )

def build_grid_from_shapefile(
    shapefile_path: str,
    spacing: float = 1000
) -> Tuple[List[Tuple[float, float]], str]:
    gdf = gpd.read_file(shapefile_path)
    clean_cols = [c for c in gdf.columns if c.lower().startswith("cleaned")]
    match_col = clean_cols[0] if clean_cols else AREANAME

    # Let user pick by name/code
    print("Available departments:")
    print(gdf.drop(columns="geometry")[[match_col, CODENAME]]
          .drop_duplicates().to_string(index=False))
    choice = input("Enter [1] for Name or [2] for Code: ").strip()
    col = match_col if choice == "1" else CODENAME
    key = normalize_string(input("Enter code/name of department: ").strip())
    mask = gdf[col].astype(str).apply(normalize_string) == key
    if not mask.any():
        sys.exit(f"No department matching '{key}'")

    city_name = gdf.loc[mask, match_col].iloc[0]
    geom_union = gdf.loc[mask].geometry.unary_union
    ecity = (
        gpd.GeoSeries([geom_union], crs=gdf.crs)
        .to_crs(epsg=5880).iloc[0]
    )
    minx, miny, maxx, maxy = ecity.bounds
    xs = np.arange(minx, maxx + spacing, spacing)
    ys = np.arange(miny, maxy + spacing, spacing)
    pts = [
        geom.Point(x, y)
        for x in xs for y in ys
        if ecity.contains(geom.Point(x, y))
    ]

    grid = gpd.GeoSeries(pts, crs="EPSG:5880").to_crs(epsg=4326)
    coords = [(round(pt.y, 5), round(pt.x, 5)) for pt in grid]
    print(f"Retained {len(coords)} grid points inside {city_name}.")
    return coords, city_name