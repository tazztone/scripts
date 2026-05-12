import sys
from unittest.mock import MagicMock
sys.modules['exifread'] = MagicMock()

import pytest
pytest.main(["python/"])
