import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from identity_studio.doctor import diagnose, inspect_model, probe_cuda


class DoctorTests(unittest.TestCase):
    def test_default_does_not_probe_or_load_modules(self):
        with patch('identity_studio.doctor.importlib.metadata.version', return_value='1.0'), \
             patch('identity_studio.doctor.run_probe') as run:
            report = diagnose()
        run.assert_not_called()
        self.assertEqual(report['status'], 'incomplete')
        self.assertEqual(report['checks_pending'], ['cuda', 'model'])
        self.assertEqual(report['cuda']['status'], 'not-checked')
        self.assertEqual(report['model']['status'], 'not-checked')

    def test_missing_dependencies_are_blockers(self):
        with patch('identity_studio.doctor.importlib.metadata.version', side_effect=importlib.metadata.PackageNotFoundError):
            report = diagnose()
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(len(report['blockers']), 6)

    def test_config_recognized_not_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'model_index.json').write_text('{"_class_name":"QwenImageEditPipeline"}')
            self.assertEqual(inspect_model(tmp), {'status': 'config-recognized', 'weights_verified': False})

    def test_deeply_nested_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'model_index.json').write_text('[' * 10000 + '0' + ']' * 10000)
            self.assertEqual(inspect_model(tmp)['status'], 'unreadable-or-invalid-index')

    def test_missing_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(inspect_model(tmp)['status'], 'missing-index')

    def test_invalid_and_unexpected_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'model_index.json')
            for content, status in [('bad', 'unreadable-or-invalid-index'), ('[]', 'unexpected-pipeline'),
                                     ('{}', 'unexpected-pipeline'), ('{"_class_name":"Other"}', 'unexpected-pipeline'),
                                     (' ' * 65537, 'invalid-index')]:
                path.write_text(content)
                self.assertEqual(inspect_model(tmp)['status'], status)

    def test_config_unicode_error_does_not_leak_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'model_index.json').write_bytes(b'\xff')
            result = inspect_model(tmp)
            self.assertEqual(result['status'], 'unreadable-or-invalid-index')
            self.assertNotIn(tmp, json.dumps(result))

    def test_cuda_available_and_probe_bounded(self):
        raw = '{"status":"available","devices":[{"index":0,"vram_bytes":8589934592}]}'
        with patch('identity_studio.doctor.run_probe', return_value=SimpleNamespace(returncode=0, stdout=raw)) as run:
            result = probe_cuda()
        self.assertEqual(result['devices'][0]['vram_bytes'], 8589934592)
        run.assert_called_once_with()

    def test_cuda_unavailable(self):
        with patch('identity_studio.doctor.run_probe', return_value=SimpleNamespace(returncode=0, stdout='{"status":"unavailable","devices":[]}')):
            self.assertEqual(probe_cuda()['status'], 'unavailable')

    def test_probe_errors_are_redacted(self):
        for error, status in [(subprocess.TimeoutExpired('private command', 30), 'probe-timed-out'),
                              (OSError('/private/path'), 'probe-failed')]:
            with patch('identity_studio.doctor.run_probe', side_effect=error):
                self.assertEqual(probe_cuda(), {'status': status})
        with patch('identity_studio.doctor.run_probe', return_value=SimpleNamespace(returncode=1, stdout='/private/path')):
            self.assertEqual(probe_cuda(), {'status': 'probe-failed'})

    def test_bad_probe_output(self):
        for output in ['not-json', '[]', '{}', '{"status":"ready","devices":[]}',
                       '{"status":"available","devices":[{"index":0,"vram_bytes":-1}]}',
                       '{"status":"available","devices":[]}',
                       '{"status":"unavailable","devices":[{"index":0,"vram_bytes":1}]}',
                       '{"status":"available","devices":[{"index":-1,"vram_bytes":1}]}',
                       '{"status":"available","devices":[{"index":0,"vram_bytes":1},{"index":0,"vram_bytes":1}]}',
                       '[' * 10000 + '0' + ']' * 10000]:
            with patch('identity_studio.doctor.run_probe', return_value=SimpleNamespace(returncode=0, stdout=output)):
                self.assertEqual(probe_cuda()['status'], 'probe-failed')

    def test_full_checks_never_claim_inference_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'model_index.json').write_text('{"_class_name":"QwenImageEditPipeline"}')
            with patch('identity_studio.doctor.importlib.metadata.version', return_value='1.0'), \
                 patch('identity_studio.doctor.probe_cuda', return_value={'status': 'available', 'devices': [{'index': 0, 'vram_bytes': 1024}]}):
                report = diagnose(tmp, True)
            self.assertEqual(report['status'], 'needs-inference-test')
            self.assertNotIn(tmp, json.dumps(report))

    def test_cli_json(self):
        result = subprocess.run([sys.executable, '-m', 'identity_studio', 'doctor'], capture_output=True, text=True, check=True)
        report = json.loads(result.stdout)
        self.assertEqual(report['schema_version'], 1)
        self.assertEqual(report['cuda']['status'], 'not-checked')

class ProbeProcessTests(unittest.TestCase):
    """Exercise real child processes without importing torch or touching a GPU."""

    def run_program(self, program, timeout=2):
        with patch('identity_studio.doctor.CUDA_PROBE', program), \
             patch('identity_studio.doctor.PROBE_TIMEOUT', timeout):
            return probe_cuda()

    def test_real_valid_output_and_stderr_redaction(self):
        self.assertEqual(self.run_program(
            'import sys; print("private", file=sys.stderr); '
            "print('{\"status\":\"unavailable\",\"devices\":[]}')"),
            {'status': 'unavailable', 'devices': []})

    def test_real_oversized_output(self):
        self.assertEqual(self.run_program('print("x" * 1000000)'), {'status': 'probe-failed'})

    def test_real_hung_child(self):
        self.assertEqual(self.run_program('import time; time.sleep(60)', 0.2),
                         {'status': 'probe-timed-out'})

    def test_real_closed_stdout_but_live_child(self):
        self.assertEqual(self.run_program('import os,time; os.close(1); time.sleep(60)', 0.2),
                         {'status': 'probe-timed-out'})

    def test_real_overflow_then_sleep(self):
        self.assertEqual(self.run_program(
            'import sys,time; sys.stdout.write("x" * 1000000); sys.stdout.flush(); time.sleep(60)'),
            {'status': 'probe-failed'})

    def test_real_nonzero_and_invalid_encoding(self):
        for program in ['raise SystemExit(1)', 'import os; os.write(1, bytes([255]))']:
            self.assertEqual(self.run_program(program), {'status': 'probe-failed'})


if __name__ == '__main__':
    unittest.main()
