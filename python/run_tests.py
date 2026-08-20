#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock exifread for environments missing it
if "exifread" not in sys.modules:
    sys.modules["exifread"] = MagicMock()

import pytest

python_dir = Path(__file__).resolve().parent
sys.exit(pytest.main([str(python_dir)]))
