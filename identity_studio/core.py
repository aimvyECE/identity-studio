"""Backend-neutral job validation. No network or model downloads."""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

MODEL = 'Qwen/Qwen-Image-Edit'

@dataclass(frozen=True)
class Job:
    pose: str
    clothing: str
    scene: str
    adult_consent: bool
    seed: int = 42
    steps: int = 30
    model: str = MODEL

    def validate(self):
        if self.adult_consent is not True:
            raise ValueError('Explicit consent from the depicted adult is required.')
        for key in ('pose', 'clothing', 'scene'):
            value = getattr(self, key)
            if not isinstance(value, str) or not value.strip() or len(value) > 2000:
                raise ValueError(f'{key} must contain 1–2000 characters.')
        if type(self.seed) is not int or not 0 <= self.seed <= 2**32 - 1:
            raise ValueError('seed must be a 32-bit unsigned integer.')
        if type(self.steps) is not int or not 1 <= self.steps <= 100:
            raise ValueError('steps must be between 1 and 100.')
        if self.model != MODEL:
            raise ValueError('Unsupported model. Review its license before adding another.')
        return self

    def prompt(self):
        self.validate()
        return (
            'Edit the supplied image of a consenting adult for a non-deceptive fashion visualization. '
            'Preserve the same person: facial features, apparent age, skin tone and visible body proportions. '
            'Do not silently slim, enlarge, beautify or alter distinctive features. '
            f'Pose: {self.pose.strip()}. Clothing: {self.clothing.strip()}. Scene: {self.scene.strip()}. '
            'Keep clothing opaque and the subject clothed. Render plausible anatomy, hands and contact shadows. '
            'Do not claim exact garment fit or guaranteed identity. A human will review the result.'
        )

    def manifest(self):
        self.validate()
        return {'schema_version': 1, 'job': asdict(self), 'status': 'prepared-not-generated',
                'privacy': 'No source image, image path or biometric embedding included. Free text may still be private.',
                'review': {k: 'not-reviewed' for k in ('face', 'body_proportions', 'anatomy', 'garment', 'pose')},
                'limitations': ['No exact likeness guarantee', 'Not a body measurement or garment-fit simulation']}

def read_job(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Job document must be a JSON object')
    payload = data.get('job', data)
    if not isinstance(payload, dict):
        raise ValueError('job must be a JSON object')
    try:
        return Job(**payload).validate()
    except TypeError as error:
        raise ValueError('Invalid job fields') from error

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def write_new_json(path, data):
    """Never overwrite an existing result or manifest."""
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
