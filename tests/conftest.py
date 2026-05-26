"""Shared test fixtures and configuration."""

import os
import sys

# Ensure src/ is on the path so we import the package under src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

