"""Read-only preflight diagnostics; never downloads or loads model weights."""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

PACKAGES = ('torch', 'diffusers', 'transformers', 'accelerate', 'Pillow', 'safetensors')
# Fixed program, no user-provided code/path interpolation. GPU import is opt-in.
CUDA_PROBE = '''import json, torch
available = torch.cuda.is_available()
print(json.dumps({"status": "available" if available else "unavailable",
 "devices": [{"index": i, "vram_bytes": torch.cuda.get_device_properties(i).total_memory}
 for i in range(torch.cuda.device_count())] if available else []}))
'''


def inspect_model(model_dir):
    if model_dir is None:
        return {'status': 'not-checked'}
    try:
        index = Path(model_dir) / 'model_index.json'
        if not index.is_file():
            return {'status': 'missing-index'}
        # Bound the config read. Do not traverse weights or report local paths.
        with index.open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            return {'status': 'invalid-index'}
        config = json.loads(raw)
        if not isinstance(config, dict) or config.get('_class_name') != 'QwenImageEditPipeline':
            return {'status': 'unexpected-pipeline'}
        return {'status': 'config-recognized', 'weights_verified': False}
    except (OSError, ValueError, UnicodeError, RecursionError):
        return {'status': 'unreadable-or-invalid-index'}


def probe_cuda():
    try:
        result = subprocess.run([sys.executable, '-c', CUDA_PROBE], capture_output=True,
                                text=True, timeout=30, check=False)
        if result.returncode != 0:
            return {'status': 'probe-failed'}
        data = json.loads(result.stdout)
        if (not isinstance(data, dict) or data.get('status') not in ('available', 'unavailable')
                or not isinstance(data.get('devices'), list)):
            return {'status': 'probe-failed'}
        devices = []
        for device in data['devices']:
            if (not isinstance(device, dict) or type(device.get('index')) is not int
                    or type(device.get('vram_bytes')) is not int or device['vram_bytes'] <= 0):
                return {'status': 'probe-failed'}
            devices.append({'index': device['index'], 'vram_bytes': device['vram_bytes']})
        return {'status': data['status'], 'devices': devices}
    except subprocess.TimeoutExpired:
        return {'status': 'probe-timed-out'}
    except (OSError, ValueError):
        return {'status': 'probe-failed'}


def diagnose(model_dir=None, check_cuda=False):
    packages = {}
    for name in PACKAGES:
        try:
            packages[name] = {'status': 'installed', 'version': importlib.metadata.version(name)}
        except importlib.metadata.PackageNotFoundError:
            packages[name] = {'status': 'missing'}
    cuda = probe_cuda() if check_cuda else {'status': 'not-checked'}
    model = inspect_model(model_dir)
    blockers = [f'Missing dependency: {name}' for name, info in packages.items() if info['status'] == 'missing']
    if cuda['status'] not in ('available', 'not-checked'):
        blockers.append('CUDA runtime not confirmed available')
    if model['status'] not in ('config-recognized', 'not-checked'):
        blockers.append('Expected Qwen-Image-Edit configuration not found')
    checks_pending = [name for name, result in (('cuda', cuda), ('model', model))
                      if result['status'] == 'not-checked']
    return {
        'schema_version': 1,
        'status': 'blocked' if blockers else ('incomplete' if checks_pending else 'needs-inference-test'),
        'checks_pending': checks_pending,
        'packages': packages, 'cuda': cuda, 'model': model, 'blockers': blockers,
        'limitations': [
            'Installed packages are not proof of version compatibility.',
            'Recognized configuration is not proof of complete, trusted or licensed weights.',
            'Available CUDA and reported VRAM do not prove the model fits in memory.',
            'No inference, identity-quality test, installation or download performed.',
        ],
        'next_step': 'Use manual mode, or resolve missing prerequisites and run a consented local inference test.',
    }
