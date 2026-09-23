import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'collector/prepare_pages.py'

class ExportTests(unittest.TestCase):
    def test_project_path_is_unwrapped_without_rewriting_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'dist/client'
            nested = root / 'discovery-radar'
            (nested / '_next').mkdir(parents=True)
            page = '<script src="/discovery-radar/_next/test.js"></script>'
            (nested / 'index.html').write_text(page)
            (nested / '_next/test.js').write_text('')
            subprocess.run([sys.executable,str(SCRIPT)], cwd=directory,
                           env={**os.environ,'PAGES_BASE_PATH':'/discovery-radar'},check=True,capture_output=True)
            self.assertEqual((root / 'index.html').read_text(),page)
            self.assertTrue((root / '_next/test.js').exists())
            self.assertTrue((root / '.nojekyll').exists())
            self.assertFalse(nested.exists())
