# PostProcess.py

import pandas as pd
import ast
import re

def process_scraped_csv(filename):
    df = pd.read_csv(filename)

    # Create a new column with num id
    if 'num_id' not in df.columns:
        df['num_id'] = range(1, len(df) + 1)

    # Extract the ChIJ property ID
    def extract_prop_id(url):
        match = re.search(r'(ChIJ[^\?]+)', str(url))
        return match.group(1) if match else None

    if 'prop_id' not in df.columns:
        df['prop_id'] = df['link'].apply(extract_prop_id)

    # Extract rating and num_rating from "4.5(2)"
    if 'num_rating' not in df.columns:
        extracted = df['rating'].str.extract(r'([\d.]+)\((\d+)\)')
        df['rating'] = pd.to_numeric(extracted[0], errors='coerce')
        df['num_rating'] = pd.to_numeric(extracted[1], errors='coerce')
        df['num_rating'] = df['num_rating'].fillna(0).astype('int64')

    # Process amenities if present
    if 'amenities' in df.columns:
        df['amenities'] = df['amenities'].apply(
            lambda x: ast.literal_eval(str(x)) if pd.notnull(x) else [])

        df_exploded = df[['prop_id', 'amenities']].explode('amenities')
        df_exploded = df_exploded[
            df_exploded['amenities'].notnull() & (df_exploded['amenities'].str.strip() != '')
        ]
        df_exploded.rename(columns={'amenities': 'amenity'}, inplace=True)
        df_exploded.to_csv(filename.replace(".csv", "_amenities.csv"), index=False)

        # Optionally drop the column (safe after file is written)
        df.drop(columns='amenities', inplace=True)

    # Reorder columns if present
    expected = ['num_id', 'prop_id', 'latitude', 'longitude', 'keyword', 'name',
                'link', 'num_rating', 'rating', 'price', 'category', 'address']
    if all(col in df.columns for col in expected):
        df = df[expected]

    # Rewrite processed file (now with num_rating as int64)
    df.to_csv(filename, index=False)

process_scraped_csv("results_ASUNCIÓN.csv")  # Replace with actual filename