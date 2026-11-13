# Identity Studio — local review workspace

Run a static server bound to localhost from this directory, for example:

```sh
python -m http.server 8765 --bind 127.0.0.1
```

Open `http://127.0.0.1:8765/`. ES modules require serving through HTTP rather than opening the HTML with `file://` in many browsers.

## What works

- Session-only reference and result previews using object URLs. No image upload API, telemetry, external assets, storage, or remote generation requests.
- Adult subject, consent and image-rights checkboxes before preparing a brief.
- Four pose presets, imagined clothing or optional garment-reference image, scene and lighting brief.
- Manual transfer workflow to an image generator chosen by the user. Copying the prompt does **not** transfer photographs.
- Side-by-side comparison and five human-review fields. No biometric claims or resemblance score.
- JSON review export that deliberately omits photo bytes, filenames, subject identifiers, and all free-text fields.
- One-click session reset. This does not erase files already downloaded to the device or uploaded elsewhere.

This static workspace is **not** a connected image generator, an identity verifier, or a garment-fit simulator. It does not train a LoRA. Checkboxes record user intent in memory, not legally verified consent. Use only on a trusted device. The actual original image remains local; if the user manually uploads it elsewhere, metadata/privacy handling depends on that service.

## Tests

```sh
node --test core.test.mjs
node --check app.mjs
```

12 unit tests pass as of initial implementation. Optional integration test:

```sh
# Requires Playwright and Chromium installed by the operator.
CHROMIUM_PATH=/usr/bin/chromium node ui.test.cjs
```

The integration test uses synthetic one-pixel images only. It tests consent, upload, prompt invalidation, clothing mode, export privacy, reset, and mobile/desktop horizontal overflow. It saves `qa-*.png` screenshots locally. Browser launch was blocked by this build environment's process/socket restrictions, so integration tests and visual review were **not completed here**. Do not report them as passed.
