# HisnLabs tajweed rule engine

`imam.py` is copied unchanged from https://github.com/HisnLabs/tajweed (commit 74cd9f5, 6 November 2026),
by HISNLABS CYBER AI FZCO, under the Apache License 2.0 (see `LICENSE` in this folder).

The model it works with, Hisnlabs/tajweed-v2 (Apache-2.0), is served from this website as
`public/models/tajweed-v2-int8.onnx` (a re-quantized build: see `public/models/NOTICE.md`), with Hugging Face as a fallback.
It is built on tarteel-ai/whisper-base-ar-quran (Apache-2.0) and was distilled from obadx/muaalem-model-v3_2 (MIT).
