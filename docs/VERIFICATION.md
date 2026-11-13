# Verification status

2026-11-13, prototype v0.1.0.

- 25 Python unit/mock integration tests pass locally.
- 20 JavaScript unit/event-wiring tests pass locally.
- Python adapter tests use doubles, not a loaded Qwen model.
- No GPU/CUDA/PyTorch model runtime is available in the build environment. No model weights downloaded, no personal training, no real inference or identity-quality claim.
- Browser end-to-end test script is included but local Chromium execution encountered a sandbox socket restriction. Visual review is not yet completed.
- Independent static privacy/UX review completed. A stale-review bug on changing images was fixed and covered by event-wiring tests.
- No real source portraits, private measurements, credentials or biometric embeddings included.
- No paid account/API, purchase or automated browser login used.

Run the tests yourself before deployment. This repository is an inspectable prototype, not a production guarantee.
