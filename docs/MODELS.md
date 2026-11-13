# Model choices and licensing

Reviewed 2026-11-13. Check upstream again before distribution or commercial use.

| Candidate | Upstream | Status here |
|---|---|---|
| Qwen-Image-Edit | https://huggingface.co/Qwen/Qwen-Image-Edit | Apache-2.0 model card; optional offline adapter; no weights included; no inference validation |
| DreamBooth / LoRA | https://huggingface.co/docs/diffusers/training/dreambooth | Training method, not a universal model license; future experiment |
| ControlNet | https://huggingface.co/docs/diffusers/using-diffusers/controlnet | Future structural-control investigation; architecture compatibility required |

Do not assume code licensing covers weights, training datasets, identity encoders or bundled assets. InstantID's default InsightFace components have non-commercial research constraints; OOTDiffusion uses CC-BY-NC-SA; FLUX.1-dev has separate non-commercial model terms. None are bundled or silently selected. These notes are engineering constraints, not legal advice.
