# Third-party notices

**5x8 display font** (`firmware/auri/font.py`), derived from the glcdfont table of the Adafruit GFX Library.
Copyright (c) 2012 Adafruit Industries. BSD License: redistribution and use in source and binary forms, with or without modification, are permitted provided that the copyright notice, this list of conditions and the disclaimer are retained. THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED.

**MicroPython** (loaded at runtime by the web simulator), MIT License, Copyright (c) Damien P. George and contributors.

**Archivo Black** (loaded from Google Fonts by the web simulator), SIL Open Font License 1.1, Copyright Omnibus-Type.

**WebLLM** (`@mlc-ai/web-llm`, loaded at runtime by the web simulator from jsDelivr), Apache License 2.0, Copyright MLC-AI and contributors.

# AurI brain models (downloaded at runtime by the visitor's browser or by a setup script, not stored in this repository)

**Qwen2.5 and Qwen3** language models, Apache License 2.0, Copyright Alibaba Cloud / Qwen team. In the web simulator they are the MLC builds published by mlc-ai on Hugging Face; on the bridge they are the GGUF builds published by unsloth.
**SmolLM2**, Apache License 2.0, Hugging Face (HuggingFaceTB).
**llama.cpp** and **llama-server**, MIT License, Copyright (c) 2023-2026 The ggml authors. Downloaded by `bridge/setup_llm.ps1` / `.sh` into `bridge/models/llm`; removing that folder removes everything.
**llama2.c** checkpoint and tokenizer formats, MIT License, Copyright (c) 2023 Andrej Karpathy. `hardware/cervello/auri_llm/auri_llm.c` and `hardware/cervello/prova_llm.py` are original code that reads those formats; no llama2.c source is included here. The **tinyllamas** weights (stories260K, stories15M) are MIT as well and are downloaded by `hardware/cervello/prepara_sd.py` only when asked.
**Web Speech API**: speech recognition in the web simulator is the browser's own. In Chrome it sends the recorded audio to Google's servers; text input with T9 stays entirely on the device. Reading answers aloud uses the voices installed on the device.

# Trademarks

Nokia and 3310 are trademarks of Nokia Corporation. Claude and Claude Code are trademarks of Anthropic. Gemini and Google are trademarks of Google LLC.
They are used here only to describe compatibility. This is an independent personal project, not affiliated with or endorsed by any of these companies.
No Nokia firmware, manuals, logos or artwork are included in this repository.

# Voice (bridge, downloaded by setup into bridge/models, not stored in this repository)

**Piper** text-to-speech, MIT License. Voice **it_IT-paola-medium** from rhasspy/piper-voices: dataset CC0 (OHF-Voice voice-datasets), fine-tuned from a base model trained on the Hi-Fi TTS dataset (speaker 92), CC BY 4.0.
**faster-whisper**, MIT License (SYSTRAN). Whisper models by OpenAI, MIT License.
**Claude Agent SDK**, used under Anthropic's terms; it requires your own Claude login or API key.
**Google Gemini API**, a Google service used by the AurI assistant under the Google APIs Terms and the Gemini API Additional Terms of Service. It needs your own API key, kept in an environment variable on the bridge. On the free tier Google may use prompts and answers to improve its products, so don't say anything to AurI you wouldn't want stored.
