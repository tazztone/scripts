import time
import sys
import os
from pathlib import Path
import shutil

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))
from organize import _unique_destination

# Create a dummy directory with many duplicates
test_dir = current_dir / "test_benchmark_dir"
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir(exist_ok=True)

try:
    dest = test_dir / "file.txt"
    dest.touch()
    for i in range(1, 2000):
        (test_dir / f"file_{i}.txt").touch()

    start_time = time.time()
    # Find the unique destination for another duplicate
    res = _unique_destination(dest)
    end_time = time.time()

    print(f"Time taken to find destination {res.name} among 2000 duplicates: {end_time - start_time:.4f} seconds")

    # Measure for multiple files
    start_time = time.time()
    for j in range(2000, 2010):
        res = _unique_destination(dest)
        res.touch()
    end_time = time.time()
    print(f"Time taken to find destination for 10 files among 2000 duplicates: {end_time - start_time:.4f} seconds")
finally:
    if test_dir.exists():
        shutil.rmtree(test_dir)
