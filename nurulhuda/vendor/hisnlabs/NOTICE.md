# HisnLabs tajweed rule engine

`imam.py` is copied unchanged from https://github.com/HisnLabs/tajweed (commit 74cd9f5, 6 November 2026),
by HISNLABS CYBER AI FZCO, under the Apache License 2.0 (see `LICENSE` in this folder).

The model it works with, Hisnlabs/tajweed-v2 (`onnx/model-int8.onnx`, Apache-2.0), is not stored here: the Practice
check page (`static/practice-check.js`) loads it in the browser from https://huggingface.co/Hisnlabs/tajweed-v2.
It is built on tarteel-ai/whisper-base-ar-quran (Apache-2.0) and was distilled from obadx/muaalem-model-v3_2 (MIT).
