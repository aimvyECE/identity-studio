"""Read-only preflight diagnostics; never downloads or loads model weights."""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import queue
import threading
import time

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


PROBE_OUTPUT_LIMIT = 65536
PROBE_TIMEOUT = 30


class ProbeOutputLimit(ValueError):
    """The diagnostic child exceeded the allowed output size."""


def run_probe():
    """Capture at most 64 KiB; discard stderr and reap the child on every path.

    A reader thread supports both Windows and POSIX anonymous pipes. It stops
    reading at the byte limit. The main thread enforces the wall-clock deadline
    even if the child produces no output, or closes stdout but keeps running.
    This is resource bounding, not a sandbox for untrusted installed packages.
    """
    deadline = time.monotonic() + PROBE_TIMEOUT
    with subprocess.Popen([sys.executable, '-c', CUDA_PROBE], stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, bufsize=0) as process:
        result = queue.Queue(maxsize=1)

        def read_output():
            try:
                data = bytearray()
                while len(data) <= PROBE_OUTPUT_LIMIT:
                    chunk = process.stdout.read(min(4096, PROBE_OUTPUT_LIMIT + 1 - len(data)))
                    if not chunk:
                        break
                    data.extend(chunk)
                result.put(bytes(data))
            except (OSError, ValueError):
                result.put(None)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        try:
            try:
                raw = result.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty:
                raise subprocess.TimeoutExpired('CUDA probe', PROBE_TIMEOUT) from None
            if raw is None:
                raise OSError('Probe output unavailable')
            if len(raw) > PROBE_OUTPUT_LIMIT:
                raise ProbeOutputLimit('Probe output exceeded limit')
            process.wait(timeout=max(0, deadline - time.monotonic()))
            return subprocess.CompletedProcess('CUDA probe', process.returncode, raw)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            # A normal probe has no descendants inheriting stdout. Do not wait
            # indefinitely if an installed package unexpectedly spawned one.
            reader.join(timeout=0.1)


def probe_cuda():
    try:
        result = run_probe()
        if result.returncode != 0:
            return {'status': 'probe-failed'}
        data = json.loads(result.stdout)
        if (not isinstance(data, dict) or data.get('status') not in ('available', 'unavailable')
                or not isinstance(data.get('devices'), list)):
            return {'status': 'probe-failed'}
        devices = []
        indices = set()
        for device in data['devices']:
            if (not isinstance(device, dict) or type(device.get('index')) is not int
                    or device['index'] < 0 or device['index'] in indices
                    or type(device.get('vram_bytes')) is not int or device['vram_bytes'] <= 0):
                return {'status': 'probe-failed'}
            indices.add(device['index'])
            devices.append({'index': device['index'], 'vram_bytes': device['vram_bytes']})
        if (data['status'] == 'available') != bool(devices):
            return {'status': 'probe-failed'}
        return {'status': data['status'], 'devices': devices}
    except subprocess.TimeoutExpired:
        return {'status': 'probe-timed-out'}
    except (OSError, ValueError, RecursionError):
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
