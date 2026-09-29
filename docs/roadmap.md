# Sarthika Code — Product Roadmap

This document outlines the delivery roadmap for Sarthika Code, clearly separating the active Version 0.1 milestones from future, strictly out-of-scope Version 0.2 ideas.

---

## 1. Version 0.1 Milestones

Version 0.1 focuses strictly on a dependable, local-first coding assistant using a local GGUF model via llama.cpp.

| Milestone | Focus | Deliverables & Acceptance Criteria |
| :--- | :--- | :--- |
| **Milestone 0** | **Architecture** *(Active)* | Comprehensive architecture document, dependency record, database schema, service contracts, explicit state machine, UI screen map, and skeleton docs. *(No app code)* |
| **Milestone 1** | **Application Foundation** | Package structure, PySide6 bootstrap, settings service, local logging, SQLite database initialization via SQLAlchemy 2.0, base unit test runner. App opens without llama-server. |
| **Milestone 2** | **Model Manager** | GGUF file validation, executable verification, `LlamaServerManager` subprocess lifecycle, 8-state machine, health checking, and diagnostics integration. |
| **Milestone 3** | **LLM Provider** | `LLMProvider` protocol, `LlamaCppProvider` (HTTP SSE client), streaming, cancellation, error handling, and `MockLLMProvider` for testing/demo mode. |
| **Milestone 4** | **Chat Experience** | Chat persistence, message history, streaming UI display, cancellation button, conversation rename/delete, and JSON/Markdown export. |
| **Milestone 5** | **Developer Workflows** | Curated workflow registry (Explain Code, Debug Code, Refactor Code, Generate Tests, Implementation Plan, etc.), structured prompts, and deterministic output constraints. |
| **Milestone 6** | **Code Context** | Dedicated multiline code editor, syntax selection, explicit file selection, security denylist filter, token count estimation, and context review dialog. |
| **Milestone 7** | **UX Polish** | Welcome/onboarding screen, model configuration dialog, responsive layouts, empty/loading/error states, dark/light theme, and diagnostics viewer. |
| **Milestone 8** | **Automated Testing** | Comprehensive unit test suite, integration tests with `MockLLMProvider`, in-memory database tests, and CI test pipeline. No GGUF weights needed for CI. |
| **Milestone 9** | **Desktop Packaging** | PyInstaller build configuration for Windows and Linux, application metadata, desktop icons, and reproducible release automation scripts. |
| **Milestone 10**| **Docs & Static Website** | Comprehensive README, user installation guide, local benchmarking dataset/script, and static informational GitHub Pages website. |

---

## 2. Version 0.2 — Roadmap Only (Out of Scope for v0.1)

The following capabilities are **explicitly not supported in Version 0.1** and must not be implemented at this time:

* **Automated Project Indexing & Embeddings (RAG)**: Generating vector embeddings for entire repositories.
* **Vector Databases**: Integration with Chroma, Qdrant, LanceDB, or SQLite-vss.
* **Autonomous Coding Agents**: Multi-step tool use, automatic replanning, or recursive agent loops.
* **Terminal & Shell Execution**: Executing commands (`git`, `npm`, `composer`, `python`, `bash`) directly on the host machine.
* **Direct File System Modification**: Writing generated patches or editing project files automatically.
* **Git Version Control Integration**: Reading commit history, creating branches, or staging commits.
* **External AI APIs & Cloud Inference**: OpenAI, Anthropic, Gemini, Groq, or self-hosted remote endpoints.
* **Multimodal Features**: Speech-to-text (Whisper), text-to-speech, or vision model integration.
* **User Accounts & Cloud Sync**: Synchronization across devices, cloud backups, or user authentication.

Any future consideration of automated execution in Version 0.2+ will require a comprehensive security audit, sandboxed execution environments, and explicit per-action user approval gates.
