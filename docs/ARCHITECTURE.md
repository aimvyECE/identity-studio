# Architecture and scope

1. **Reference:** a local image in memory, not a public dataset.
2. **Brief:** independent textual pose, wardrobe and scene requests; identity preservation instruction.
3. **Execution:** manual export today; optional offline local Qwen adapter. No paid API connector.
4. **Review:** human checks of face, proportions, anatomy, pose and garment; no fabricated numerical identity score.
5. **Provenance:** exported parameters and review status; no embedded images or biometric embeddings.

Future experiments (not implemented): held-out evaluation of LoRA versus reference-only editing; compatible pose/depth conditioning; clothing-image conditioning; selective inpainting; model and revision pinning; hardware benchmarks; automatic QA with explicit false-positive/false-negative evaluation. A generic ControlNet is not automatically compatible with Qwen.

Safety boundaries: local UI only, no credential storage, no upload service, no silent provider switch, no automatic account creation, no public references. Client-side UI controls cannot stop a determined user from modifying source code. Training and generation cannot guarantee body geometry, clothing fit or exact likeness.
