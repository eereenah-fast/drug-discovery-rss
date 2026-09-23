"""Exercise durable archive storage against a temporary Git remote."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'collector/state.py'

class StateTests(unittest.TestCase):
    def test_archive_survives_fresh_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            origin = root / 'origin.git'
            checkout = root / 'checkout'
            subprocess.run(['git','init','--bare',str(origin)],check=True,capture_output=True)
            subprocess.run(['git','clone',str(origin),str(checkout)],check=True,capture_output=True)
            path = checkout / 'public/data/feed.json'
            path.parent.mkdir(parents=True)
            content = json.dumps({'schema_version':1,'items':[{'id':'test-paper'}]})
            path.write_text(content)
            def run(mode):
                return subprocess.run([sys.executable,str(SCRIPT),mode],cwd=checkout,capture_output=True,text=True,check=True)
            run('save')
            run('save')
            path.unlink()
            run('restore')
            self.assertEqual(json.loads(path.read_text())['items'],[{'id':'test-paper'}])
            listing = subprocess.run(['git','--git-dir',str(origin),'ls-tree','--name-only','radar-data'],capture_output=True,text=True,check=True)
            self.assertEqual(listing.stdout.strip(),'feed.json')
