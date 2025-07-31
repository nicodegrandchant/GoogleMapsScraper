"""
This module defines the structure for a scraped business item from Google Maps.

Note:
- Variables like `card`, `coords`, `kw`, `anchor`, `safe_get_text`, and `clean_text` are **not defined in this file**.
- They are expected to be passed in from the main scraper (`GoogleMapsScraper.py`) where they are already defined.
- This separation allows for cleaner, modular code that makes the item structure easier to maintain and reuse.

Usage example (inside GoogleMapsScraper):
    from item_template import build_item
    item = build_item(card, coords, kw, anchor, safe_get_text, clean_text)
"""

import re

def build_item(version, card, coords, kw, anchor, safe_get_text, clean_text):
    """
    Builds a business item dictionary based on the specified version of field extraction logic.
    """
    if version == "loc1":
        # --- 0) Base fields ---
        name = safe_get_text(card.select_one("div.qBF1Pd"))
        link = anchor.get("href", "")

        # collect all W4Efsd blocks
        w4_blocks = card.select("div.W4Efsd")

        # ——— PRICE & RATING BLOCK ——————————————————————————————————
        price = ""
        w4_blocks = card.select("div.W4Efsd")
        if w4_blocks:
            first = w4_blocks[0]
            container = first.select_one("div.AJB7ye")
            if container:
                # select only the direct-span children: [0]=icon‑only, [1]=rating, [2]=dot+price]
                children = container.select(":scope > span")
                # 1) rating
                if len(children) > 1:
                    rating = safe_get_text(children[1].select_one("span.ZkP5Je"))
                # 2) price in the third span
                if len(children) > 2:
                    # inside that span there’s an inner <span role="img" aria-label="…">
                    icon = children[2].select_one("span[role='img'][aria-label]")
                    if icon and icon.has_attr("aria-label"):
                        price = icon["aria-label"]
                    else:
                        # fallback to any ₲-prefixed text in that block
                        for sp in children[2].select("span"):
                            txt = sp.get_text(strip=True)
                            if txt.startswith("₲"):
                                price = txt
                                break

        # --- 2) Category & Address (second W4Efsd -> first nested) ---
        category = ""
        address = ""
        if len(w4_blocks) > 1:
            nested_blocks = w4_blocks[1].select("div.W4Efsd")
            if nested_blocks:
                # 1) Category always comes from the first nested block
                cat_span = nested_blocks[0].select_one("span span")
                if cat_span:
                    category = re.sub(r"\d+", "", cat_span.get_text(strip=True)).strip()

                # 2) Only extract address if there are at least 2 direct <span> children
                direct_spans = nested_blocks[0].find_all("span", recursive=False)
                if len(direct_spans) >= 2:
                    # the last direct span holds "· Address…", so strip leading dots/spaces
                    raw_addr = direct_spans[-1].get_text(strip=True)
                    address = re.sub(r'^[·\s]+', '', raw_addr)
                else:
                    address = ""

        '''
        # --- 3) Hours & Phone (second nested) ---
        hours = ""
        phone = ""
        if len(w4_blocks) > 1:
            # grab the two inner W4Efsd blocks (hours+phone live in the 2nd one)
            nested = w4_blocks[1].select("div.W4Efsd")
            if len(nested) > 1:
            # --- HOURS (unchanged) ---
                for span in nested[1].select("span"):
                    txt = span.get_text(strip=True)
                    if any(tok in txt.lower() for tok in ["a.m.", "p.m.", "horas"]):
                        hours = txt
                        break

                # --- PHONE (tuned) ---
                phone_tag = nested[1].select_one("span.UsdlK")
                if phone_tag:
                    phone = phone_tag.get_text(strip=True)
        '''

        # --- 4) Services & Amenities (unchanged) ---
        '''
        services = [
            clean_text(s.get_text(strip=True))
            for s in card.select("span")
            if "Retiro" in s.text or "Entrega" in s.text
        ]
        '''
        amenities = [
            clean_text(tag.get("aria-label", ""))
            for tag in card.select("div.ktbgEf div[role='img']")
            if tag.has_attr("aria-label")
        ]

        return {
            "latitude": coords[0],
            "longitude": coords[1],
            "keyword": kw,
            "name": name,
            "link": link,
            "rating": rating,
            "price": price,
            "category": category,
            "address": address,
            #"hours": hours,
            #"phone": phone,
            #"services": services,
            "amenities": amenities,
        }

