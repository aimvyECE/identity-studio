# Identity Studio

A local-first, open-source workbench for **consenting adult fashion visualization**: prepare an identity-preserving edit, compare reference and result, and record a human review. A prototype, not a trained identity model, production service, biometric verifier, or exact garment-fit simulator.

## What works now

- Browser workbench: local image preview, separate pose/outfit/scene controls, explicit consent, copyable brief, reference/result comparison and human review.
- A private manual workflow for your existing image editor; no browser-session token extraction, unofficial OAuth bridge or automated ChatGPT/Gemini scraping.
- Python job validation, reproducible seeds, manifests and an **optional offline Qwen-Image-Edit adapter**.
- No paid API calls, accounts, automatic model download or third-party telemetry.

**Generation status:** The workbench does not contain a bundled generator. Its local Qwen adapter requires a separately installed compatible CUDA environment and model snapshot. The adapter is tested with test doubles; real image inference and identity quality have NOT been validated in this environment. Training a personal LoRA is a later experiment, not an implemented feature.

## Start with Python, without extra dependencies

From the complete source checkout run (a local server is required for browser JavaScript modules):

```sh
python -m identity_studio serve
# http://127.0.0.1:8765
```

The server binds only to loopback and serves the `web` directory. Keep this directory free of private files and symlinks. Photos remain in browser memory; closing/reloading loses the session. Do not expose this development server to the network. Free text and exported manifests can contain private information, so review them before sharing.

## Optional local image editing

The base CLI needs Python 3.10+ and no third-party dependencies:

```sh
python -m identity_studio prepare examples/job.json --output prepared.json
```

To use local inference, independently provision a supported CUDA GPU, PyTorch, Diffusers, Transformers, Accelerate and Pillow from their official distributions, and download a trusted, safetensors-only snapshot of [Qwen/Qwen-Image-Edit](https://huggingface.co/Qwen/Qwen-Image-Edit) under its license. This is a 20B-parameter model: hardware, RAM, VRAM and disk requirements must be assessed for the chosen precision/offloading configuration. This project does not claim a minimum tested GPU or guaranteed speed.

```sh
python -m identity_studio generate examples/job.json \
  --image private/reference.png --model-dir /path/to/local/model-snapshot \
  --output private/result.png
```

The adapter uses `local_files_only=True`, requires explicit consent in the job, refuses existing output files, re-encodes output without inherited EXIF and writes a review manifest. Store output in a private folder. Do not use the synthetic example consent value for a real person without obtaining their consent. Model input is a **single reference image**; pose and clothing are text controls, not an implemented skeleton or garment-image conditioning pipeline.

## Quality, not magical likeness scores

Keep held-out reference images and use the [evaluation protocol](docs/EVALUATION.md). Check facial structure, body proportions, anatomy, garment details, requested pose and unwanted modifications. Mark uncertainty and reject failures. A flattering image is not evidence that the person or product is reproduced accurately. Image similarity is not consent or identity authentication.

## Privacy and responsible use

Never commit source portraits, personally trained adapters, credentials, private measurements or customer exports. `.gitignore` is a guardrail, not a security boundary. Work only with consenting adults and rights-cleared inputs; do not use for impersonation, intimate imagery, identity-document creation or deceptive endorsements. Clearly identify generated imagery when publishing. The local consent checkbox is a reminder, **not a technical verification of consent**. No content classifier is bundled; external generators retain their own safeguards.

ChatGPT/Gemini subscriptions do not automatically include API credits or permission to automate their consumer interfaces. In manual mode you choose whether and where to upload each image. Review each provider's current privacy/retention terms. API support must be explicit, with cost and data-sharing approval, and is not implemented here.

## Tests

```sh
python -m unittest discover -s tests -v
node --test web/*.test.mjs
```

See [verification](docs/VERIFICATION.md), [architecture](docs/ARCHITECTURE.md), [licenses](docs/MODELS.md), and [contributing](CONTRIBUTING.md).

## License and attribution

New application code: MIT. Qwen is developed by the Qwen team, not by this project; its model card specifies Apache-2.0. Model weights are not redistributed. Third-party components and future adapters keep their own licenses. Built with AI coding assistance and reviewed through automated and manual checks; no claim of original invention of diffusion, LoRA or identity conditioning.
