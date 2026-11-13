"""Optional adapter. Integration tested with doubles; real inference requires a GPU."""
import importlib
import os
from pathlib import Path
from .core import sha256_file, write_new_json

def generate_local(job, image_path, output_path, model_dir):
    job.validate()
    image_path, output_path, model_dir = map(Path, (image_path, output_path, model_dir))
    if not image_path.is_file():
        raise ValueError('Reference image is missing')
    if output_path.suffix.lower() != '.png':
        raise ValueError('Output must be a PNG file')
    manifest_path = output_path.with_suffix('.manifest.json')
    if output_path.exists() or manifest_path.exists():
        raise FileExistsError('Output or manifest already exists; select a new filename')
    if not model_dir.is_dir() or not (model_dir / 'model_index.json').is_file():
        raise ValueError('A complete, separately downloaded Qwen model snapshot is required')
    # Offline by default: a typo or missing file must never trigger a large download.
    os.environ['HF_HUB_OFFLINE'] = '1'
    torch = importlib.import_module('torch')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU unavailable. Use the manual workflow; no paid provider is called.')
    diffusers = importlib.import_module('diffusers')
    pil = importlib.import_module('PIL.Image')
    with pil.open(image_path) as source:
        if source.width * source.height > 20_000_000:
            raise ValueError('Reference image exceeds 20 megapixels')
        image_ops = importlib.import_module('PIL.ImageOps')
        image = image_ops.exif_transpose(source).convert('RGB')
    pipeline = diffusers.QwenImageEditPipeline.from_pretrained(
        str(model_dir), torch_dtype=torch.bfloat16, local_files_only=True, use_safetensors=True)
    pipeline.enable_model_cpu_offload()
    with torch.inference_mode():
        output = pipeline(image=image, prompt=job.prompt(), negative_prompt=' ',
                          true_cfg_scale=4.0, num_inference_steps=job.steps,
                          generator=torch.Generator(device='cpu').manual_seed(job.seed)).images[0]
    # Re-encode pixels without inheriting EXIF or personal metadata from the reference.
    clean = pil.new('RGB', output.size)
    clean.paste(output.convert('RGB'))
    with output_path.open('xb') as stream:
        clean.save(stream, format='PNG')
    manifest = job.manifest()
    manifest.update(status='generated-awaiting-human-review', output_sha256=sha256_file(output_path),
                    runtime={'torch': torch.__version__, 'diffusers': diffusers.__version__},
                    model_index_sha256=sha256_file(model_dir / 'model_index.json'),
                    reproducibility_note='Model config hash only; weight revision not verified. Record snapshot revision separately.')
    write_new_json(manifest_path, manifest)
