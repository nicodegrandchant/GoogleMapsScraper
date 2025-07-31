import csv
import os
from typing import List, Tuple
import logging

def export_grid_to_csv(points: List[Tuple[float, float]], output_path: str, force: bool = False) -> None:
    """
    Exports grid points to a CSV file with 'latitude' and 'longitude' columns.
    
    Args:
        points: List of (latitude, longitude) tuples.
        output_path: Path to save the CSV.
        force: If True, overwrite the file without asking. Default is False, and it will prompt the user.
    """
    if os.path.exists(output_path) and not force:
        if input(f"Overwrite '{output_path}'? [y/n]: ").strip().lower() != 'y':
            logging.info("Export aborted.")
            return
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['latitude','longitude'])
        w.writerows(points)
    logging.info(f"Exported {len(points)} grid points to {output_path}")
