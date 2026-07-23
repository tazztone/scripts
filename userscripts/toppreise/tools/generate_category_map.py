#!/usr/bin/env python3
"""
Toppreise Full Category Hierarchy Generator Tool
Extracts category mappings from both /produktsuche/ breadcrumbs AND /preisvergleich/ product links
across all 23 root category trees to achieve complete coverage and auto-inject into toppreise.user.js.
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
    ("Foto-c1316", "Foto & Video"),
    ("Haus-Garten-c650", "Garten & Baumarkt"),
    ("Haushalt-Kueche-c644", "Haushalt & Küche"),
    ("HiFi-Audio-c653", "HiFi & Audio"),
    ("Lust-Liebe-c3009", "Drogerie"),
    ("Musikinstrumente-Pro-Audio-c2490", "HiFi & Audio"),
    ("Navigation-c2057", "Computer & Zubehör"),
    ("Schmuck-c1788", "Uhren"),
    ("Smartphones-Mobiltelefone-c1346", "Smartphones & Mobiltelefone"),
    ("Spielwaren-c901", "Spielwaren"),
    ("Sport-Freizeit-c563", "Sport & Freizeit"),
    ("Telefon-VoIP-c652", "Smartphones & Mobiltelefone"),
    ("TV-Video-c654", "TV & Video"),
    ("Uhren-c1783", "Uhren"),
    ("Videogames-c900", "Videogames"),
    ("Wein-Spirituosen-c2458", "Haushalt & Küche"),
    ("Werkzeuge-Werkstatt-c772", "Garten & Baumarkt")
]

CANONICAL_GROUPS = {
    'auto motorrad': 'Auto & Motorrad',
    'bekleidung schuhe': 'Bekleidung & Schuhe',
    'buerobedarf schreibwaren': 'Bürobedarf & Schreibwaren',
    'computer zubehoer': 'Computer & Zubehör',
    'drogerie': 'Drogerie',
    'filme': 'Filme',
    'foto': 'Foto & Video',
    'haus garten': 'Garten & Baumarkt',
    'haushalt kueche': 'Haushalt & Küche',
    'hifi audio': 'HiFi & Audio',
    'smartphones mobiltelefone': 'Smartphones & Mobiltelefone',
    'spielwaren': 'Spielwaren',
    'sport freizeit': 'Sport & Freizeit',
    'tv video': 'TV & Video',
    'uhren': 'Uhren',
    'videogames': 'Videogames'
}

# Standard Offline Seed Dictionary for 100% Instant Guarantee
SEED_LOOKUP = {
    # Filme
    "abenteuer": "Filme", "krimi": "Filme", "anime": "Filme", "mehr komoedie": "Filme",
    "tv serien": "Filme", "fantasy": "Filme", "mehr drama": "Filme", "thriller": "Filme",
    "dvd filme": "Filme", "blu ray filme": "Filme", "dvd kinder familie": "Filme",
    "science fiction": "Filme", "klassisches drama": "Filme", "biografie": "Filme", "horror": "Filme",
    
    # Computer & Zubehör
    "komplettsysteme": "Computer & Zubehör", "grafikkarten": "Computer & Zubehör", 
    "tablets": "Computer & Zubehör", "maeuse": "Computer & Zubehör", 
    "pc gehaeuse": "Computer & Zubehör", "notebooks": "Computer & Zubehör",
    "gehaeuseluefter": "Computer & Zubehör", "sd speicherkarten": "Computer & Zubehör",
    "externe festplatten hdd": "Computer & Zubehör", "monitore": "Computer & Zubehör",
    "prozessorkuehler": "Computer & Zubehör", "headsets mikrofone": "Computer & Zubehör",
    "multifunktionsgeraete": "Computer & Zubehör",
    
    # Spielwaren
    "lego architecture": "Spielwaren", "schleich": "Spielwaren", "action figuren": "Spielwaren",
    "kinderspiele": "Spielwaren", "hot wheels": "Spielwaren", "disney": "Spielwaren",
    "puzzles": "Spielwaren", "barbie": "Spielwaren", "cobi": "Spielwaren",
    "playmobil wiltopia": "Spielwaren", "tabletop spiele": "Spielwaren",
    "playmobil action": "Spielwaren", "playmobil novelmore": "Spielwaren", "lego": "Spielwaren",
    "playmobil my life": "Spielwaren", "playmobil asterix": "Spielwaren", "lego duplo": "Spielwaren",
    "lego city": "Spielwaren", "vtech": "Spielwaren", "fischertechnik": "Spielwaren",
    "experimentierkaesten": "Spielwaren", "kartenspiele": "Spielwaren", "mega construx": "Spielwaren",
    "familienspiele": "Spielwaren",
    
    # Videogames
    "strategie rollenspiele": "Videogames", "zubehoer fuer nintendo switch": "Videogames",
    "jump n run geschicklichkeit": "Videogames", "actionspiele": "Videogames",
    "rollenspiele adventures": "Videogames", "action": "Videogames", "nintendo switch games": "Videogames",
    "sonstige handheld konsolen": "Videogames",
    
    # HiFi & Audio / TV & Video
    "kopfhoerer": "HiFi & Audio", "plattenspieler": "HiFi & Audio", "bluetooth lautsprecher": "HiFi & Audio",
    "lautsprecher": "HiFi & Audio",
    "tv geraete": "TV & Video", "beamer": "TV & Video",
    
    # Drogerie
    "eau de parfum": "Drogerie", "elektrozahnbuersten": "Drogerie", "hautpflege": "Drogerie",
    "lockenstaebe buersten": "Drogerie", "ersatzbuersten": "Drogerie", "koerperpflege": "Drogerie",
    
    # Haushalt & Küche
    "saug und wischroboter": "Haushalt & Küche", "abfallsysteme": "Haushalt & Küche",
    "zubehoer fuer haushaltsgeraete": "Haushalt & Küche", "thermoskannen bidons": "Haushalt & Küche",
    "kaffee espressomaschinen": "Haushalt & Küche", "staubsauger": "Haushalt & Küche",
    "klimageraete": "Haushalt & Küche", "raumduft": "Haushalt & Küche", "senseo maschinen": "Haushalt & Küche",
    
    # Sport & Freizeit
    "skihelme": "Sport & Freizeit", "koffer": "Sport & Freizeit", "ventilatoren heizgeraete": "Sport & Freizeit",
    "einkaufstrolleys taschen": "Sport & Freizeit", "sportbrillen goggles": "Sport & Freizeit",
    "velotaschen": "Sport & Freizeit", "rucksaecke": "Sport & Freizeit", "inline skates rollschuhe": "Sport & Freizeit",
    "ski lawinenrucksaecke airbags": "Sport & Freizeit", "reise sporttaschen": "Sport & Freizeit",
    "zubehoer fuer sportgeraete": "Sport & Freizeit", "veloanhaengerzubehoer": "Sport & Freizeit",
    "pedale": "Sport & Freizeit", "taschenlampen": "Sport & Freizeit", "skibrillen": "Sport & Freizeit",
    "protektoren": "Sport & Freizeit", "activity tracker smartwatches": "Sport & Freizeit",
    
    # Smartphones & Mobiltelefone / Auto / Uhren
    "huellen": "Smartphones & Mobiltelefone", "oberschalen cover": "Smartphones & Mobiltelefone",
    "taschen cover fuer iphone": "Smartphones & Mobiltelefone", "smartphones": "Smartphones & Mobiltelefone",
    "webcams": "Computer & Zubehör", "naehmaschinen": "Haushalt & Küche",
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
        with urllib.request.urlopen(req, timeout=8) as resp:
            return url, resp.read().decode('utf-8', errors='ignore')
    except Exception:
        return url, ""

def generate_deep_map(max_workers=32):
    print("🚀 Starting Comprehensive Category & Product Link Crawl of Toppreise.ch...", flush=True)
    
    lookup_map = dict(SEED_LOOKUP)
    detailed_map = {}
    
    root_slug_to_name = {slug.split('-c')[0].lower(): name for slug, name in ROOT_CATEGORIES}
    
    visited_urls = set()
    to_visit = set(f"https://www.toppreise.ch/produktsuche/{slug}" for slug, name in ROOT_CATEGORIES)
    
    depth_round = 0
    while to_visit:
        depth_round += 1
        current_urls = list(to_visit - visited_urls)
        if not current_urls:
            break
        
        visited_urls.update(current_urls)
        print(f"📡 Crawl Round {depth_round}: Processing {len(current_urls)} category pages (Visited total: {len(visited_urls)})...", flush=True)
        
        next_urls = set()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_url, url): url for url in current_urls}
            for future in as_completed(futures):
                url, html = future.result()
                if not html:
                    continue
                
                # Determine root category from current URL path
                url_path = url.split('toppreise.ch/produktsuche/')[-1]
                root_slug = url_path.split('/')[0].split('-c')[0].lower()
                root_title = root_slug_to_name.get(root_slug, CANONICAL_GROUPS.get(root_slug.replace('-', ' '), format_title(url_path.split('/')[0])))
                
                # 1. Parse produktsuche links
                ps_matches = re.findall(r'href=["\'](/produktsuche/[^"\']+)["\']', html)
                for m in ps_matches:
                    clean_path = m.split('?')[0]
                    parts = clean_path.strip('/').split('/')
                    if len(parts) >= 2 and parts[0] == 'produktsuche':
                        if '-c' in parts[-1]:
                            full_url = f"https://www.toppreise.ch{clean_path}"
                            if full_url not in visited_urls:
                                next_urls.add(full_url)
                        
                        segments = parts[1:]
                        cur_root_slug = segments[0].split('-c')[0].lower()
                        cur_root_title = root_slug_to_name.get(cur_root_slug, CANONICAL_GROUPS.get(cur_root_slug.replace('-', ' '), root_title))
                        
                        for seg in segments[1:]:
                            leaf_title = format_title(seg)
                            leaf_key = leaf_title.lower()
                            slug_key = seg.split('-c')[0].lower().replace('-', ' ')
                            raw_slug = seg.split('-c')[0].lower()
                            
                            lookup_map[leaf_key] = cur_root_title
                            lookup_map[slug_key] = cur_root_title
                            lookup_map[raw_slug] = cur_root_title
                            
                            detailed_map[slug_key] = {
                                "root": cur_root_title,
                                "title": leaf_title,
                                "path": [format_title(s) for s in segments]
                            }

                # 2. Parse preisvergleich product card links to extract leaf category slugs
                pv_matches = re.findall(r'href=["\'](/preisvergleich/([^/]+)/[^"\']+\-p\d+)["\']', html)
                for full_pv, cat_slug in pv_matches:
                    raw_cat = cat_slug.split('-c')[0].lower()
                    cat_title = format_title(raw_cat)
                    cat_key = cat_title.lower()
                    space_key = raw_cat.replace('-', ' ')
                    
                    lookup_map[raw_cat] = root_title
                    lookup_map[cat_key] = root_title
                    lookup_map[space_key] = root_title
                    
                    if space_key not in detailed_map:
                        detailed_map[space_key] = {
                            "root": root_title,
                            "title": cat_title,
                            "path": [root_title, cat_title]
                        }
        
        to_visit = next_urls

    print(f"✅ Comprehensive Crawl Complete! Visited {len(visited_urls)} pages and generated {len(lookup_map)} category mappings.", flush=True)
    return lookup_map, detailed_map

def main():
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    json_out_path = os.path.join(tools_dir, "category_map.json")
    js_out_path = os.path.join(tools_dir, "category_lookup_generated.js")
    user_js_path = os.path.abspath(os.path.join(tools_dir, "..", "toppreise.user.js"))
    
    lookup_map, detailed_map = generate_deep_map()
    
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(detailed_map, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved category JSON map to: {json_out_path}", flush=True)
    
    with open(js_out_path, "w", encoding="utf-8") as f:
        f.write("// Auto-generated Toppreise Category Lookup Table\n")
        f.write("const GENERATED_CATEGORY_LOOKUP = ")
        json.dump(lookup_map, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"💾 Saved JS lookup code to: {js_out_path}", flush=True)
    
    # Auto-inject into toppreise.user.js if present
    if os.path.exists(user_js_path):
        print(f"💉 Injecting updated CATEGORY_LOOKUP into {user_js_path}...", flush=True)
        with open(user_js_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        json_str = json.dumps(lookup_map, ensure_ascii=False, indent=4)
        replacement = f"const CATEGORY_LOOKUP = {json_str};"
        
        updated_content = re.sub(
            r'const CATEGORY_LOOKUP = \{[\s\S]*?\};',
            replacement,
            content,
            count=1
        )
        
        with open(user_js_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        print("🎉 Successfully injected CATEGORY_LOOKUP into toppreise.user.js!", flush=True)

if __name__ == "__main__":
    main()
