"""Explicit integration gate. Requires installed Playwright and Chromium."""
import os
import sys
import unittest
from pathlib import Path
os.environ['SEO_KIT_TEST_BROWSER'] = '1'
tests_directory = Path(__file__).resolve().parents[1] / 'tests'
sys.path.insert(0, str(tests_directory))
suite = unittest.defaultTestLoader.discover(str(tests_directory), pattern='test_browser_integration.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
