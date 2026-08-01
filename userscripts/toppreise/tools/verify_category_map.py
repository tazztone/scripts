#!/usr/bin/env python3
"""
Verification Script for Toppreise Category Lookup Engine
Tests category mapping accuracy against benchmark site category terms.
"""

import json
import os
import sys

BENCHMARK_CATEGORIES = [
    'CaDA', 'Heissluftfritteusen', 'Vollautomaten', 'Haarglaetter',
    'Haar Bartschneider', 'USB SpeicherSticks', 'Smartringe',
    'Home Cinema AV Receiver', 'Zubehoer Fuer Kuechengeraete',
    'GPS Navigations Geraete', 'Parfum', 'Externe Solid State Drives SSD',
    'Western', 'Ladegeraete Netzadapter', 'Amiibo',
    'Lego City', 'Lego Architecture', 'Lego Duplo', 'Lego Marvel',
    'Playmobil', 'Schleich', 'Hot Wheels', 'Barbie',
    'Kopfhoerer', 'Bluetooth Lautsprecher', 'Plattenspieler',
    'Eau De Parfum', 'Elektrozahnbuersten', 'Haartrockner',
    'Staubsauger', 'Saugroboter', 'Kaffee Espressomaschinen',
    'TV Geraete', 'Beamer', 'Notebooks', 'Grafikkarten', 'Monitore',
    'Smartphones', 'Reifen', 'Skihelme', 'Koffer',
    'Nintendo Switch Games', 'PS5 Konsolen', 'Actionspiele',
    'Puzzles', 'Kartenspiele', 'Familienspiele',
    'Aktenvernichter', 'Webcams', 'Activity Tracker Smartwatches',
    'Fitness Krafttraining', 'Schwingschleifer',
    'Bau Konstruktionsspielzeug', 'Outdoor Spielzeug',
    'Experimentierkaesten', 'Tabletop Spiele',
    'Saug Und Wischroboter', 'Klimageraete',
    'Senseo Maschinen', 'Sonstige Kuechengeraete',
    'Oberschalen Cover', 'Huellen',
    'Dachboxen', 'Dachtraeger', 'Kindersitze',
    'Car HiFi Car Video', 'RC Modelle', 'Multicopter', 'Spielzeugroboter',
]

def main():
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    js_lookup_path = os.path.join(tools_dir, "category_lookup_generated.js")
    
    if not os.path.exists(js_lookup_path):
        print(f"❌ Error: {js_lookup_path} not found.")
        sys.exit(1)

    with open(js_lookup_path, "r", encoding="utf-8") as f:
        content = f.read()

    json_str = content.split('= ', 1)[1].rstrip(';\n')
    lookup = json.loads(json_str)

    mapped = []
    unmapped = []
    
    for cat in BENCHMARK_CATEGORIES:
        norm = cat.strip().lower()
        slug = norm.replace(' ', '')
        space_slug = norm.replace('-', ' ')
        
        root = lookup.get(norm) or lookup.get(slug) or lookup.get(space_slug)
        if root:
            mapped.append((cat, root))
        else:
            unmapped.append(cat)

    print("==================================================")
    print("📊 TOPPREISE CATEGORY MAP VERIFICATION SUMMARY")
    print("==================================================")
    print(f"Total Benchmark Terms : {len(BENCHMARK_CATEGORIES)}")
    print(f"Mapped Terms          : {len(mapped)} ({len(mapped)/len(BENCHMARK_CATEGORIES)*100:.1f}%)")
    print(f"Unmapped (Sonstiges)  : {len(unmapped)}")
    print(f"Total Generated Keys  : {len(lookup)}")
    print("==================================================")

    if unmapped:
        print("\n⚠️ Unmapped categories (fall back to regex/card URL):")
        for u in unmapped:
            print(f"  • {u}")

    print("\n✅ Sample Mapped Categories:")
    for cat, root in sorted(mapped[:20], key=lambda x: x[1]):
        print(f"  • {cat:35s} => {root}")

if __name__ == '__main__':
    main()
