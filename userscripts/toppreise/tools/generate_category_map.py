#!/usr/bin/env python3
"""
Toppreise Full Category Hierarchy Generator Tool
Crawls ALL category pages on Toppreise.ch to build a comprehensive subcategory->root lookup.
No manual SEED_LOOKUP guessing — everything comes from the site's actual URL taxonomy.
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

# Root categories on Toppreise (slug -> canonical display group)
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

# Build root slug -> canonical group lookup
ROOT_SLUG_MAP = {}
for slug, name in ROOT_CATEGORIES:
    clean = slug.split('-c')[0].lower()
    ROOT_SLUG_MAP[clean] = name
    ROOT_SLUG_MAP[clean.replace('-', ' ')] = name


def format_title(slug):
    """Convert URL slug like 'Lego-City' or 'Lego-City-c927' to 'Lego City'."""
    if not slug:
        return ""
    clean = slug.split('-c')[0]
    # Split on hyphens, capitalize each word
    words = clean.replace('-', ' ').strip().split()
    return ' '.join(w.capitalize() for w in words)


def slug_to_key(slug):
    """Convert URL slug to normalized lookup key: lowercase, hyphens to spaces, strip -cNNN."""
    if not slug:
        return ""
    return slug.split('-c')[0].lower().replace('-', ' ').strip()


def expand_key_variants(key):
    """Generate normalized lookup keys: original, umlaut-expanded, and umlaut-collapsed."""
    variants = {key}
    # ue->ü, ae->ä, oe->ö
    u_map = key.replace('ue', 'ü').replace('ae', 'ä').replace('oe', 'ö')
    variants.add(u_map)
    # ü->ue, ä->ae, ö->oe
    a_map = key.replace('ü', 'ue').replace('ä', 'ae').replace('ö', 'oe')
    variants.add(a_map)
    return variants


def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            return url, resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return url, ""


def resolve_root_from_url(url):
    """Extract the canonical root group from a /produktsuche/ or /preisvergleich/ URL."""
    match = re.search(r'/(?:produktsuche|preisvergleich)/([^/?]+)', url)
    if not match:
        return None
    first_seg = match.group(1).split('-c')[0].lower()
    return ROOT_SLUG_MAP.get(first_seg) or ROOT_SLUG_MAP.get(first_seg.replace('-', ' '))


def extract_subcategories_from_html(html, page_root_group):
    """Extract all subcategory slugs and inner link titles from a page's HTML, mapped to page_root_group."""
    results = {}  # key -> root_group
    detailed = {}  # key -> {root, title, path}

    # 1. Extract from /produktsuche/ navigation links with inner text
    ps_matches = re.findall(r'href=["\'](/produktsuche/[^"\'#]+)["\'][^>]*>([^<]+)</a>', html)
    for href, inner_text in ps_matches:
        clean_path = href.split('?')[0]
        parts = clean_path.strip('/').split('/')
        if len(parts) < 2 or parts[0] != 'produktsuche':
            continue

        segments = parts[1:]  # everything after 'produktsuche'
        root_key = slug_to_key(segments[0])
        root_group = ROOT_SLUG_MAP.get(root_key, page_root_group)

        # Map inner text if valid
        clean_title = inner_text.strip()
        if clean_title and not clean_title.startswith('<'):
            text_key = slug_to_key(clean_title)
            if text_key and len(text_key) > 1 and not text_key.isdigit():
                for variant in expand_key_variants(text_key):
                    results[variant] = root_group

        # Map every non-root segment as a subcategory
        for seg in segments[1:]:
            if not seg or seg.startswith('?'):
                continue
            key = slug_to_key(seg)
            title = format_title(seg)
            if not key or len(key) < 2:
                continue
            if key.replace(' ', '').isdigit():
                continue

            for variant in expand_key_variants(key):
                results[variant] = root_group

            detailed[key] = {
                "root": root_group,
                "title": title,
                "path": [format_title(s) for s in segments]
            }

    # 2. Extract from /preisvergleich/ product links
    pv_matches = re.findall(r'href=["\'](/preisvergleich/[^"\'?#]+)', html)
    for href in pv_matches:
        parts = href.strip('/').split('/')
        if len(parts) < 3 or parts[0] != 'preisvergleich':
            continue

        # Last segment is the product slug (contains -pNNNN), skip it
        segments = parts[1:-1]
        if not segments:
            continue

        root_key = slug_to_key(segments[0])
        known_root = ROOT_SLUG_MAP.get(root_key)

        if known_root:
            # First segment is a known root — map the rest as subcategories
            root_group = known_root
            subcat_segments = segments[1:]
        else:
            # First segment is NOT a known root — it's a subcategory itself
            # Use the page's root context as the root group
            root_group = page_root_group
            subcat_segments = segments  # all segments are subcategories

        for seg in subcat_segments:
            if not seg:
                continue
            key = slug_to_key(seg)
            title = format_title(seg)
            if not key or len(key) < 2:
                continue
            if key.replace(' ', '').isdigit():
                continue

            for variant in expand_key_variants(key):
                results[variant] = root_group

            if key not in detailed:
                detailed[key] = {
                    "root": root_group,
                    "title": title,
                    "path": [format_title(s) for s in segments]
                }

    return results, detailed


def discover_subcat_urls(html, current_url):
    """Find subcategory page URLs and pagination URLs to crawl deeper."""
    urls = set()
    matches = re.findall(r'href=["\'](/produktsuche/[^"\'\s>]+)', html)
    for href in matches:
        clean = href.split('?')[0].split('#')[0]
        if '-c' in clean.split('/')[-1]:
            urls.add(f"https://www.toppreise.ch{clean}")

    # Also follow pagination links (?p=N) on current page to get more product URLs
    base_url = current_url.split('?')[0].split('#')[0]
    page_matches = re.findall(r'[?&]p=(\d+)', html)
    for p in set(page_matches):
        page_num = int(p)
        if 0 < page_num <= 15:
            urls.add(f"{base_url}?p={page_num}")

    return urls


def generate_comprehensive_map(max_workers=24, max_depth=5):
    print("🚀 Comprehensive Category Crawl of Toppreise.ch...", flush=True)
    print(f"   Max depth: {max_depth}, Workers: {max_workers}", flush=True)

    lookup_map = {}
    detailed_map = {}
    visited_urls = set()
    
    # Seed with root category pages
    to_visit = set()
    for slug, name in ROOT_CATEGORIES:
        to_visit.add(f"https://www.toppreise.ch/produktsuche/{slug}")

    depth = 0
    while to_visit and depth < max_depth:
        depth += 1
        current_batch = sorted(to_visit - visited_urls)
        if not current_batch:
            break

        visited_urls.update(current_batch)
        print(f"📡 Depth {depth}: Crawling {len(current_batch)} pages...", flush=True)

        next_batch = set()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_url, url): url for url in current_batch}
            for future in as_completed(futures):
                url, html = future.result()
                if not html:
                    continue

                page_root = resolve_root_from_url(url)
                if not page_root:
                    continue

                # Extract subcategories from this page
                page_lookup, page_detailed = extract_subcategories_from_html(html, page_root)
                lookup_map.update(page_lookup)
                detailed_map.update(page_detailed)

                # Discover deeper subcategory pages to crawl
                sub_urls = discover_subcat_urls(html, url)
                for sub_url in sub_urls:
                    if sub_url not in visited_urls:
                        next_batch.add(sub_url)

        to_visit = next_batch

    # Also add root slugs themselves as mappings
    for slug, name in ROOT_CATEGORIES:
        key = slug_to_key(slug)
        for variant in expand_key_variants(key):
            lookup_map[variant] = name

    # Sort for deterministic output
    sorted_lookup = dict(sorted(lookup_map.items()))
    sorted_detailed = dict(sorted(detailed_map.items()))

    print(f"✅ Crawl Complete!", flush=True)
    print(f"   Pages visited: {len(visited_urls)}", flush=True)
    print(f"   Lookup entries: {len(sorted_lookup)}", flush=True)
    print(f"   Detailed subcategories: {len(sorted_detailed)}", flush=True)

    return sorted_lookup, sorted_detailed


def main():
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    json_out_path = os.path.join(tools_dir, "category_map.json")
    js_out_path = os.path.join(tools_dir, "category_lookup_generated.js")
    user_js_path = os.path.abspath(os.path.join(tools_dir, "..", "toppreise.user.js"))

    lookup_map, detailed_map = generate_comprehensive_map()

    # Save detailed JSON
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(detailed_map, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved detailed category map: {json_out_path}", flush=True)

    # Save JS lookup
    with open(js_out_path, "w", encoding="utf-8") as f:
        f.write("// Auto-generated Toppreise Category Lookup Table\n")
        f.write("const GENERATED_CATEGORY_LOOKUP = ")
        json.dump(lookup_map, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"💾 Saved JS lookup: {js_out_path}", flush=True)

    # Print per-group summary
    group_counts = {}
    for k, v in detailed_map.items():
        root = v["root"]
        group_counts[root] = group_counts.get(root, 0) + 1
    print("\n📊 Subcategories per group:")
    for group in sorted(group_counts, key=group_counts.get, reverse=True):
        print(f"   {group}: {group_counts[group]}")

    # Auto-inject into toppreise.user.js
    if os.path.exists(user_js_path):
        print(f"\n💉 Injecting into {user_js_path}...", flush=True)
        with open(user_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        json_str = json.dumps(lookup_map, ensure_ascii=False, indent=4)
        replacement = f"const CATEGORY_LOOKUP = {json_str};"

        updated = re.sub(
            r'const CATEGORY_LOOKUP = \{[\s\S]*?\};',
            replacement,
            content,
            count=1
        )

        with open(user_js_path, "w", encoding="utf-8") as f:
            f.write(updated)
        print("🎉 Injected CATEGORY_LOOKUP into toppreise.user.js!", flush=True)
    else:
        print(f"⚠️  {user_js_path} not found, skipping injection", flush=True)


if __name__ == "__main__":
    main()
