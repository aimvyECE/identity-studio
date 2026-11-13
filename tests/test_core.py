import json
from pathlib import Path
import tempfile
import unittest
from identity_studio.core import Job, read_job, write_new_json, sha256_file
from identity_studio.qwen import generate_local

class CoreTests(unittest.TestCase):
    def job(self, **kw):
        return Job(**dict(pose='standing', clothing='blue jacket', scene='studio', adult_consent=True, **kw))
    def test_prompt_preserves_identity(self):
        self.assertIn('visible body proportions', self.job().prompt())
    def test_false_consent(self):
        for consent in (False, 'true', 1, None):
            with self.assertRaises(ValueError): Job('p','c','s',consent).validate()
    def test_text_validation(self):
        for text in ('', ' ', 'x'*2001, None, 3):
            with self.assertRaises(ValueError): Job(text,'c','s',True).validate()
    def test_seed_validation(self):
        for seed in (-1,2**32, True, '42'):
            with self.assertRaises(ValueError): self.job(seed=seed).validate()
    def test_step_validation(self):
        for steps in (0,101,True,1.5):
            with self.assertRaises(ValueError): self.job(steps=steps).validate()
    def test_model_allowlist(self):
        with self.assertRaises(ValueError): self.job(model='unreviewed').validate()
    def test_manifest_has_no_source_or_embedding(self):
        manifest = self.job().manifest()
        self.assertEqual(manifest['status'],'prepared-not-generated')
        self.assertNotIn('source_image', manifest)
        self.assertTrue(all(v=='not-reviewed' for v in manifest['review'].values()))
    def test_write_does_not_clobber(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'job.json'; write_new_json(path,self.job().manifest())
            with self.assertRaises(FileExistsError): write_new_json(path,{})
            self.assertEqual(read_job(path),self.job())
    def test_unknown_fields_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'job.json'; path.write_text('{"unexpected":1}')
            with self.assertRaises(ValueError): read_job(path)
    def test_non_object_json_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json'
            for data in ([], None, 1, {'job': []}):
                p.write_text(json.dumps(data))
                with self.assertRaises(ValueError): read_job(p)
    def test_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';p.write_bytes(b'abc')
            self.assertEqual(sha256_file(p),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
    def test_missing_input_fails_without_dependencies(self):
        with self.assertRaises(ValueError): generate_local(self.job(),'missing','out.png','missing')
    def test_snapshot_required_without_download(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source';p.write_bytes(b'not-an-image')
            with self.assertRaises(ValueError): generate_local(self.job(),p,Path(d)/'out.png',d)
    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source';p.write_bytes(b'x');o=Path(d)/'out.png';o.write_bytes(b'important')
            with self.assertRaises(FileExistsError): generate_local(self.job(),p,o,d)
            self.assertEqual(o.read_bytes(),b'important')
    def test_output_type(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source';p.write_bytes(b'x')
            with self.assertRaises(ValueError): generate_local(self.job(),p,Path(d)/'out.jpg',d)

if __name__=='__main__': unittest.main()
