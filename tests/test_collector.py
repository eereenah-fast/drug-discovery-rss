import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('collector', ROOT / 'collector/collect.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
CONFIG = json.loads((ROOT / 'config/topics.json').read_text())

class CollectorTests(unittest.TestCase):
    def make(self, title, text='', doi=''):
        return c.record(title, 'https://example.org/paper', '2026-09-19', 'Journal of Chemical Information and Modeling', 'Journals', text, doi)

    def test_rejects_unrelated_ai_and_materials(self):
        for title in ['A graph neural network for traffic prediction', 'Generative design of solar cell materials', 'An antibody response to routine vaccination']:
            self.assertIsNone(c.classify(self.make(title), CONFIG))

    def test_rejects_incidental_docking_in_excluded_journal(self):
        item = self.make('Britanin improved high-fat diet-induced obesity by regulating the MAPK signaling pathway',
                         'Molecular docking and network pharmacology study of a plant extract.')
        item['source'] = 'Pakistan journal of pharmaceutical sciences'
        self.assertIsNone(c.classify(item, CONFIG))

    def test_rejects_routine_application_in_broad_journal(self):
        item = self.make('Molecular docking study of a plant extract against an enzyme',
                         'Drug discovery molecular docking and antioxidant activity.')
        item['source'] = 'A broad pharmaceutical journal'
        self.assertIsNone(c.classify(item, CONFIG))

    def test_keeps_reusable_method_from_broad_journal(self):
        item = self.make('A benchmark for protein-ligand binding affinity prediction',
                         'We introduce a new method and dataset for evaluating binding affinity prediction models.')
        item['source'] = 'A broad pharmaceutical journal'
        self.assertIsNotNone(c.classify(item, CONFIG))

    def test_keeps_routine_paper_from_specialist_journal(self):
        item = self.make('Molecular docking study of a kinase inhibitor',
                         'Molecular docking and binding affinity analysis.')
        item['source'] = 'Journal of Chemical Information and Modeling'
        self.assertIsNotNone(c.classify(item, CONFIG))

    def test_covers_all_modalities(self):
        cases = [('RDKit cheminformatics release', 'Small molecules'),
                 ('Peptide design for therapeutic discovery', 'Peptides'),
                 ('Antibody engineering for improved therapeutics', 'Antibodies'),
                 ('Generative protein design', 'Protein design'),
                 ('Target validation for drug discovery', 'Target discovery'),
                 ('Drug discovery using molecular glues', 'Other modalities')]
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertIn(expected, c.classify(self.make(title), CONFIG)['subjects'])

    def test_doi_identity_preserves_first_discovery(self):
        first = c.classify(self.make('Molecular docking study', doi='https://doi.org/10.1234/ABC'), CONFIG)
        old = c.merge([], [first]); old[0]['first_seen'] = '2026-09-01T00:00:00+00:00'
        new = c.classify(self.make('Molecular docking study', doi='10.1234/abc'), CONFIG)
        merged = c.merge(old, [new])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['first_seen'], '2026-09-01T00:00:00+00:00')

    def test_missing_source_retains_previous_items(self):
        old = c.merge([], [c.classify(self.make('RDKit release'), CONFIG)])
        self.assertEqual(c.merge(old, []), old)

    def test_clean_encoded_markup_and_keep_code_link(self):
        item = self.make('&lt;b&gt;Drug discovery&lt;/b&gt; &amp; tools', 'Code: https://github.com/rdkit/rdkit.')
        self.assertEqual(item['title'], 'Drug discovery & tools')
        self.assertEqual(item['code_url'], 'https://github.com/rdkit/rdkit')
        self.assertNotIn('_text', c.classify(item, CONFIG))

    def test_unsafe_url_is_rejected(self):
        self.assertIsNone(c.record('Drug discovery', 'javascript:alert(1)', None, 'Bad', 'Blogs'))

    def test_preprint_and_paper_keep_distinct_identifiers(self):
        a = c.classify(self.make('Molecular docking study', doi='10.1234/a'), CONFIG)
        a['kind'] = 'Preprints'; a['url'] = 'https://doi.org/10.1234/a'
        b = c.classify(self.make('Molecular docking study', doi='10.1234/b'), CONFIG)
        b['url'] = 'https://doi.org/10.1234/b'
        result = c.merge([], [a, b])
        self.assertEqual(len(result), 2)
        self.assertTrue(all(x.get('related_url') for x in result))

    def test_invalid_api_payload_is_not_a_quiet_day(self):
        with patch.object(c, 'request', return_value={'error': 'quota exceeded'}):
            with self.assertRaises(ValueError):
                c.europe({'query':'cheminformatics'}, '2026-09-09', '2026-09-23')

    def test_all_sources_fail_without_overwriting_last_feed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'config').mkdir()
            (root / 'config/topics.json').write_text(json.dumps(CONFIG))
            (root / 'config/sources.json').write_text(json.dumps([{'id':'test','name':'Test source','type':'europepmc'}]))
            output = root / 'feed.json'
            original = json.dumps({'items':[], 'sources':[], 'updated_at':'2026-09-01'})
            output.write_text(original)
            with patch.object(c,'ROOT',root), patch.object(c,'europe',side_effect=TimeoutError('source unavailable')):
                self.assertEqual(c.run(SimpleNamespace(output='feed.json',days=14)),1)
            self.assertEqual(output.read_text(),original)

if __name__ == '__main__':
    unittest.main()
