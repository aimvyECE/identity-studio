"""Adapter contract tests using in-memory doubles. No GPU, downloads or inference."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock, patch
import tempfile
from contextlib import nullcontext

from identity_studio.core import Job
from identity_studio.qwen import generate_local


class FakeImage:
    width, height = 64, 80
    size = (64, 80)
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def convert(self, mode): return self
    def paste(self, image): self.pasted = image
    def save(self, stream, format):
        if format != 'PNG': raise AssertionError(format)
        stream.write(b'FAKE-PNG-FOR-ADAPTER-TEST-ONLY')


class AdapterTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.image = self.folder/'private-reference.jpg'
        self.image.write_bytes(b'fake source')
        self.model = self.folder/'model'
        self.model.mkdir()
        (self.model/'model_index.json').write_text('{}')
        self.output = self.folder/'result.png'
        self.job = Job('standing', 'opaque jacket', 'studio', True, seed=10, steps=12)
        self.source = FakeImage(); self.result = FakeImage(); self.clean = FakeImage()
        self.pipeline = Mock(return_value=SimpleNamespace(images=[self.result]))
        self.loader = Mock(return_value=self.pipeline)
        self.generator = Mock(); self.generator.manual_seed.return_value = self.generator
        self.torch = SimpleNamespace(
            cuda=SimpleNamespace(is_available=lambda: True), bfloat16='bf16',
            inference_mode=nullcontext, Generator=Mock(return_value=self.generator), __version__='test-torch')
        self.diffusers = SimpleNamespace(QwenImageEditPipeline=SimpleNamespace(from_pretrained=self.loader), __version__='test-diffusers')
        self.pil = SimpleNamespace(open=Mock(return_value=self.source), new=Mock(return_value=self.clean))
        self.modules = {'torch': self.torch, 'diffusers': self.diffusers, 'PIL.Image': self.pil,
                        'PIL.ImageOps': SimpleNamespace(exif_transpose=lambda image: image)}
        self.env = patch.dict(os.environ); self.env.start(); self.addCleanup(self.env.stop)
        self.importer = patch('identity_studio.qwen.importlib.import_module', side_effect=lambda name: self.modules[name])
        self.importer.start(); self.addCleanup(self.importer.stop)

    def run_adapter(self):
        generate_local(self.job, self.image, self.output, self.model)

    def test_offline_loading_and_generation_contract(self):
        self.run_adapter()
        self.assertEqual(os.environ['HF_HUB_OFFLINE'], '1')
        self.loader.assert_called_once()
        self.assertTrue(self.loader.call_args.kwargs['local_files_only'])
        self.assertEqual(self.loader.call_args.args[0], str(self.model))
        self.assertEqual(self.loader.call_args.kwargs['torch_dtype'], 'bf16')
        self.pipeline.enable_model_cpu_offload.assert_called_once()
        kwargs = self.pipeline.call_args.kwargs
        self.assertEqual(kwargs['num_inference_steps'], 12)
        self.assertEqual(kwargs['true_cfg_scale'], 4.0)
        self.assertEqual(kwargs['negative_prompt'], ' ')
        self.assertIn('body proportions', kwargs['prompt'])
        self.generator.manual_seed.assert_called_once_with(10)
        self.torch.Generator.assert_called_once_with(device='cpu')

    def test_output_is_new_pixel_image_and_manifest_requires_review(self):
        self.run_adapter()
        self.pil.new.assert_called_once_with('RGB', (64, 80))
        self.assertIs(self.clean.pasted, self.result)
        manifest = json.loads(self.output.with_suffix('.manifest.json').read_text())
        self.assertEqual(manifest['status'], 'generated-awaiting-human-review')
        self.assertTrue(all(value == 'not-reviewed' for value in manifest['review'].values()))
        self.assertEqual(manifest['runtime']['diffusers'], 'test-diffusers')
        self.assertEqual(len(manifest['output_sha256']), 64)
        self.assertNotIn('private-reference', json.dumps(manifest))
        self.assertNotIn(str(self.folder), json.dumps(manifest))

    def test_cuda_failure_does_not_load_model_or_create_result(self):
        self.torch.cuda.is_available = lambda: False
        with self.assertRaisesRegex(RuntimeError, 'CUDA'):
            self.run_adapter()
        self.loader.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_oversized_image_does_not_load_model(self):
        self.source.width = 10000; self.source.height = 10000
        with self.assertRaisesRegex(ValueError, 'megapixels'):
            self.run_adapter()
        self.loader.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_inference_exception_does_not_claim_completion(self):
        self.pipeline.side_effect = RuntimeError('out of memory')
        with self.assertRaisesRegex(RuntimeError, 'memory'):
            self.run_adapter()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_suffix('.manifest.json').exists())

    def test_model_load_failure_does_not_create_output(self):
        self.loader.side_effect = RuntimeError('missing model weight')
        with self.assertRaises(RuntimeError):
            self.run_adapter()
        self.assertFalse(self.output.exists())

    def test_existing_manifest_is_never_overwritten(self):
        path = self.output.with_suffix('.manifest.json'); path.write_text('keep me')
        with self.assertRaises(FileExistsError): self.run_adapter()
        self.assertEqual(path.read_text(), 'keep me')
        self.loader.assert_not_called()

    def test_reference_not_overwritten(self):
        self.output = self.folder/'source.png'; self.output.write_bytes(b'original')
        self.image = self.output
        with self.assertRaises(FileExistsError): self.run_adapter()
        self.assertEqual(self.image.read_bytes(), b'original')

    def test_repeated_run_cannot_replace_result(self):
        self.run_adapter()
        before = self.output.read_bytes()
        with self.assertRaises(FileExistsError): self.run_adapter()
        self.assertEqual(self.output.read_bytes(), before)
        self.loader.assert_called_once()

    def test_consent_rejected_before_load(self):
        self.job = Job('standing', 'jacket', 'studio', False)
        with self.assertRaisesRegex(ValueError, 'consent'): self.run_adapter()
        self.loader.assert_not_called()
        self.assertFalse(self.output.exists())


if __name__ == '__main__': main()
