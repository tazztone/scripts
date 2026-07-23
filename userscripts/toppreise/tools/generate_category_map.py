#!/usr/bin/env python3
"""
Toppreise Category Hierarchy Generator Tool
Crawls and extracts category hierarchies from Toppreise.ch using megamenu parsing
and fast parallel crawling to build category_map.json and category_lookup_generated.js.
"""

import urllib.request
import re
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'de-CH,de;q=0.9,en;q=0.8',
}

# Root categories on Toppreise
ROOT_CATEGORIES = [
    ("Auto-Motorrad-c651", "Auto & Motorrad"),
    ("Bekleidung-Schuhe-c655", "Bekleidung & Schuhe"),
    ("Buerobedarf-Schreibwaren-c1816", "Bürobedarf & Schreibwaren"),
    ("Computer-Zubehoer-c200", "Computer & Zubehör"),
    ("Drogerie-c643", "Drogerie"),
    ("Filme-c1388", "Filme"),
    ("Foto-c1316", "Foto"),
    ("Haus-Garten-c650", "Haus & Garten"),
    ("Haushalt-Kueche-c644", "Haushalt & Küche"),
    ("HiFi-Audio-c653", "HiFi & Audio"),
    ("Lust-Liebe-c3009", "Lust & Liebe"),
    ("Musikinstrumente-Pro-Audio-c2490", "Musikinstrumente & Pro Audio"),
    ("Navigation-c2057", "Navigation"),
    ("Schmuck-c1788", "Schmuck"),
    ("Smartphones-Mobiltelefone-c1346", "Smartphones & Mobiltelefone"),
    ("Spielwaren-c901", "Spielwaren"),
    ("Sport-Freizeit-c563", "Sport & Freizeit"),
    ("Telefon-VoIP-c652", "Telefon & VoIP"),
    ("TV-Video-c654", "TV & Video"),
    ("Uhren-c1783", "Uhren"),
    ("Videogames-c900", "Videogames"),
    ("Wein-Spirituosen-c2458", "Wein & Spirituosen"),
    ("Werkzeuge-Werkstatt-c772", "Werkzeuge & Werkstatt")
]

# Standard Offline Seed Dictionary for Instant Guarantee
SEED_LOOKUP = {
    "abenteuer": "Filme", "krimi": "Filme", "anime": "Filme", "mehr komoedie": "Filme",
    "tv serien": "Filme", "fantasy": "Filme", "mehr drama": "Filme", "thriller": "Filme",
    "dvd filme": "Filme", "blu ray filme": "Filme", "dvd kinder familie": "Filme",
    
    "komplettsysteme": "Computer & Zubehör", "grafikkarten": "Computer & Zubehör", 
    "tablets": "Computer & Zubehör", "maeuse": "Computer & Zubehör", 
    "pc gehaeuse": "Computer & Zubehör", "notebooks": "Computer & Zubehör",
    "gehaeuseluefter": "Computer & Zubehör", "sd speicherkarten": "Computer & Zubehör",
    "externe festplatten hdd": "Computer & Zubehör", "monitore": "Computer & Zubehör",
    
    "lego architecture": "Spielwaren", "schleich": "Spielwaren", "action figuren": "Spielwaren",
    "kinderspiele": "Spielwaren", "hot wheels": "Spielwaren", "disney": "Spielwaren",
    "puzzles": "Spielwaren", "barbie": "Spielwaren", "cobi": "Spielwaren",
    "playmobil wiltopia": "Spielwaren", "tabletop spiele": "Spielwaren",
    "playmobil action": "Spielwaren", "playmobil novelmore": "Spielwaren", "lego": "Spielwaren",
    
    "strategie rollenspiele": "Videogames", "zubehoer fuer nintendo switch": "Videogames",
    "jump n run geschicklichkeit": "Videogames", "actionspiele": "Videogames",
    "rollenspiele adventures": "Videogames", "action": "Videogames", "nintendo switch games": "Videogames",
    
    "kopfhoerer": "HiFi & Audio", "plattenspieler": "HiFi & Audio", "bluetooth lautsprecher": "HiFi & Audio",
    "tv geraete": "TV & Video", "beamer": "TV & Video",
    
    "eau de parfum": "Drogerie", "elektrozahnbuersten": "Drogerie", "hautpflege": "Drogerie",
    "lockenstaebe buersten": "Drogerie", "ersatzbuersten": "Drogerie",
    
    "saug und wischroboter": "Haushalt & Küche", "abfallsysteme": "Haushalt & Küche",
    "zubehoer fuer haushaltsgeraete": "Haushalt & Küche", "thermoskannen bidons": "Haushalt & Küche",
    "kaffee espressomaschinen": "Haushalt & Küche",
    
    "skihelme": "Sport & Freizeit", "koffer": "Sport & Freizeit", "ventilatoren heizgeraete": "Sport & Freizeit",
    "einkaufstrolleys taschen": "Sport & Freizeit", "sportbrillen goggles": "Sport & Freizeit",
    "velotaschen": "Sport & Freizeit", "rucksaecke": "Sport & Freizeit", "inline skates rollschuhe": "Sport & Freizeit",
    
    "huellen": "Smartphones & Mobiltelefone", "oberschalen cover": "Smartphones & Mobiltelefone",
    "taschen cover fuer iphone": "Smartphones & Mobiltelefone", "smartphones": "Smartphones & Mobiltelefone",
    
    "reifen": "Auto & Motorrad", "autos": "Auto & Motorrad", "uhren": "Uhren"
}

def format_title(slug):
    if not slug:
        return ""
    clean = slug.split('-c')[0].replace('-', ' ').strip()
    return ' '.join(w.capitalize() for w in clean.split())

def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return url, resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return url, ""

def generate_map(max_workers=8):
    print("Extracting category hierarchy from Toppreise...", flush=True)
    
    lookup_map = dict(SEED_LOOKUP)
    detailed_map = {}
    
    root_title_by_slug = {slug.split('-c')[0].lower(): name for slug, name in ROOT_CATEGORIES}
    urls = [f"https://www.toppreise.ch/produktsuche/{slug}" for slug, name in ROOT_CATEGORIES]
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_url, url): url for url in urls}
        for future in as_completed(futures):
            url, html = future.result()
            if not html:
                continue
                
            matches = re.findall(r'href=["\'](/produktsuche/[^"\']+-c\d+[^"\']*)["\']', html)
            for m in matches:
                clean_path = m.split('?')[0]
                parts = clean_path.strip('/').split('/')
                if len(parts) >= 2 and parts[0] == 'produktsuche':
                    segments = parts[1:]
                    root_slug = segments[0].split('-c')[0].lower()
                    leaf_segment = segments[-1].split('-c')[0]
                    
                    root_title = root_title_by_slug.get(root_slug, format_title(segments[0]))
                    leaf_title = format_title(leaf_segment)
                    leaf_key = leaf_title.lower()
                    slug_key = leaf_segment.lower().replace('-', ' ')
                    
                    breadcrumb = [format_title(s) for s in segments]
                    
                    lookup_map[leaf_key] = root_title
                    lookup_map[slug_key] = root_title
                    lookup_map[leaf_segment.lower()] = root_title
                    
                    detailed_map[slug_key] = {
                        "root": root_title,
                        "title": leaf_title,
                        "path": breadcrumb
                    }

    print(f"Extraction complete! Generated {len(lookup_map)} category mappings.", flush=True)
    return lookup_map, detailed_map

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_out_path = os.path.join(script_dir, "category_map.json")
    js_out_path = os.path.join(script_dir, "category_lookup_generated.js")
    
    lookup_map, detailed_map = generate_map()
    
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(detailed_map, f, ensure_ascii=False, indent=2)
    print(f"Saved category JSON map to: {json_out_path}", flush=True)
    
    with open(js_out_path, "w", encoding="utf-8") as f:
        f.write("// Auto-generated Toppreise Category Lookup Table\n")
        f.write("const GENERATED_CATEGORY_LOOKUP = ")
        json.dump(lookup_map, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"Saved JS lookup code to: {js_out_path}", flush=True)

if __name__ == "__main__":
    main()
