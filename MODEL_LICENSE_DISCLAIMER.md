# Model License & Attribution Disclaimer

## 1. Application License vs. Model Weight Licenses

**Sarthika Code** application source code is distributed under the **Apache License 2.0**.

However, **model weights and binaries used with Sarthika Code are NOT part of Sarthika Code and are never distributed, hosted, or bundled within this repository.**

Users download GGUF model weights separately from third-party model creators and repositories (such as Hugging Face). Each language model family carries its own specific license terms, acceptable use policies, and commercial usage restrictions.

---

## 2. Common Model Families and Their Respective Licenses

When downloading and using local GGUF models, you are responsible for complying with the respective model's license agreement:

| Model Family | Creator / Vendor | Upstream License | Commercial Use Allowed | Reference URL |
| :--- | :--- | :--- | :--- | :--- |
| **Qwen 2.5 Coder** (1.5B, 3B, 7B, 14B, 32B) | Alibaba Cloud / Qwen Team | Apache License 2.0 | Yes (under Apache 2.0) | [Qwen Licenses](https://github.com/QwenLM/Qwen2.5) |
| **DeepSeek Coder** (1.3B, 6.7B, 33B) | DeepSeek AI | DeepSeek Model License | Yes (per terms) | [DeepSeek License](https://github.com/deepseek-ai/DeepSeek-Coder) |
| **Llama 3.2** (1B, 3B) | Meta Platforms, Inc. | Llama 3.2 Community License | Yes (with MAU < 700M condition) | [Meta Llama 3.2 License](https://github.com/meta-llama/llama-models) |
| **StarCoder 2** (3B, 7B, 15B) | BigCode Project | OpenRAIL-M v1 | Yes (subject to RAIL restrictions) | [BigCode OpenRAIL](https://huggingface.co/spaces/bigcode/bigcode-model-license-agreement) |
| **Gemma 2** (2B, 9B, 27B) | Google LLC | Gemma Terms of Use | Yes (subject to terms) | [Gemma Terms](https://ai.google.dev/gemma/terms) |

*Disclaimer: The above summary is provided for developer convenience only and does not constitute legal advice. Please review the official upstream license files before deploying models in commercial environments.*

---

## 3. Third-Party Dependencies

* **llama.cpp**: The underlying inference engine developed by Georgi Gerganov and contributors is licensed under the **MIT License**.
* **PySide6**: The official Python bindings for Qt are developed by The Qt Company and licensed under the **LGPLv3 / Commercial** license.
* **SQLAlchemy**: Licensed under the **MIT License**.
* **httpx**: Licensed under the **BSD 3-Clause License**.
