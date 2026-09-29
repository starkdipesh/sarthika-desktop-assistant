# Sarthika Code — System Architecture Specification (Version 0.1)

## 1. Architecture Rationale

Sarthika Code is a private, local-first desktop AI coding assistant engineered for ordinary developer laptops without requiring dedicated GPUs, external cloud APIs, accounts, telemetry, or network-bound infrastructure. The design choices below prioritize absolute local privacy, zero operating cost, crash isolation, CPU performance, and long-term maintainability.

### 1.1 Python 3.11
* **Ecosystem Maturity & Stability**: Python 3.11 provides substantial performance improvements (10–60% faster CPython interpreter via the Faster CPython initiative) over Python 3.10.
* **Modern Typing & Asynchronous Primitives**: Native support for `asyncio.TaskGroup`, `typing.Self`, Variadic Generics, and exception groups enables clean async concurrent control flows (managing background HTTP SSE streams alongside the Qt event loop).
* **Cross-Platform PyInstaller Compatibility**: Python 3.11 has battle-tested, stable binary compilation support on both Windows and Linux, avoiding packaging regression issues observed in newer release branches (such as C extension changes in 3.13).

### 1.2 PySide6 Desktop UI
* **Official Qt for Python (LGPLv3)**: PySide6 is developed by the Qt Company under the LGPLv3 license, enabling open distribution without the restrictive copyleft constraints of PyQt (GPLv3).
* **Native Desktop Integration**: Delivers native windowing, hardware-accelerated rendering, standard platform dialogs, clipboard management, and robust accessibility across Windows and Linux.
* **Thread-Safe Architecture**: Qt's Signals and Slots mechanism (`QObject`, `QThread`, `Signal`, `Slot`) guarantees safe asynchronous messaging between background processing (HTTP client, child processes) and the GUI rendering thread, preventing UI lockups during inference.

### 1.3 SQLite + SQLAlchemy 2.0
* **Local-First Zero-Config Persistence**: SQLite operates entirely in-process as a single local file on disk, requiring zero external server setup, no networking, and minimal memory overhead.
* **SQLAlchemy 2.0 Modern Declarative Mappings**: Full static typing support with `Mapped[...]` and `mapped_column(...)`, query safety against injection, clear migration paths, and deterministic session isolation.
* **Test Isolation**: Enables instant in-memory testing (`sqlite:///:memory:`) for automated test suites without disk side effects or mock complexity.

### 1.4 llama.cpp / llama-server
* **State-of-the-Art CPU Vectorization**: Native C/C++ SIMD optimizations (AVX2, AVX-512, NEON) deliver practical token generation speeds on standard consumer CPUs without requiring a dedicated discrete GPU.
* **Quantized GGUF Format**: Models quantized to 4-bit (specifically `Q4_K_M`) fit a 3B parameter model into ~1.9 GB of RAM/VRAM, allowing comfortable operation on 16 GB laptops and best-effort low-context execution on 8 GB laptops.
* **Decoupled Server Process**: Running inference via `llama-server` provides complete memory and fault isolation. If a native crash or memory allocation failure occurs during inference, the desktop UI remains responsive, captures diagnostics, and handles recovery gracefully.

### 1.5 HTTP Communication to Localhost (127.0.0.1)
* **Standardized Stream Protocol**: Server-Sent Events (SSE) over HTTP allow incremental token streaming directly to the UI using asynchronous non-blocking I/O (`httpx`).
* **Strict Loopback Binding**: Binding exclusively to `127.0.0.1` ensures that no external network interfaces or adjacent LAN devices can access the inference server.
* **Process Resilience**: Clean IPC boundary separates Python's Global Interpreter Lock (GIL) from the native C++ inference execution.

### 1.6 Provider Abstraction (`LLMProvider`)
* **Decoupled Architecture**: Domain services and UI depend exclusively on the `LLMProvider` protocol rather than raw llama.cpp endpoints.
* **Zero-Cost Headless Testing**: Allows `MockLLMProvider` to simulate realistic token streaming, latency, error states, and cancellation in automated CI pipelines and offline UI demo mode without downloading multi-gigabyte model weights or invoking compilers.

### 1.7 Static Local Website vs. Hosted Public AI Inference
* **Product Honesty & Zero Attack Surface**: Sarthika Code is strictly local-first. Providing a public hosted AI inference endpoint would contradict the core privacy guarantee and introduce hosting costs, telemetry temptations, and security attack vectors.
* **Educational & Installation Hub**: A GitHub Pages static website serves exclusively as a documentation portal, installation guide, benchmark repository, and architecture walkthrough.

---

## 2. Final Repository Tree (Version 0.1)

```text
sarthika-code/
├── .github/
│   ├── workflows/
│   │   └── tests.yml               # Automated multi-OS CI testing matrix
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── assets/                         # Static UI icons, logos, brand vectors
├── docs/
│   ├── architecture.md             # Complete system architecture specification
│   ├── benchmarks.md               # Local hardware benchmark methodology & 50-task dataset
│   ├── installation.md             # OS setup guide (Python, llama-server, GGUF)
│   ├── limitations.md              # Hardware, context, and capability boundaries
│   ├── master-product-spec.md      # Upstream master product & engineering specification
│   ├── privacy.md                  # Strict privacy policy and telemetry-free manifesto
│   ├── roadmap.md                  # Version 0.1 deliverables and v0.2 out-of-scope backlog
│   └── troubleshooting.md          # Diagnostic guides, crash resolution, common errors
├── pyproject.toml                  # Packaging, dependency definitions, tool configurations
├── README.md                       # Comprehensive project overview and quickstart
├── scripts/
│   ├── benchmark_local.py          # Reproducible local benchmark harness
│   ├── build_release.py            # PyInstaller build automation script
│   └── start_llama_server.py       # Standalone testing server launcher
├── src/
│   └── sarthika_code/
│       ├── __init__.py
│       ├── main.py                 # Application bootstrap entrypoint
│       ├── app/
│       │   ├── __init__.py
│       │   ├── application.py      # Application lifecycle, DI container & event coordinator
│       │   └── paths.py            # OS-standard data, config, database, and log directories
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── chat.py             # Chat, Message, and Role domain entities
│       │   ├── config.py           # ModelConfiguration and GenerationSettings entities
│       │   ├── context.py          # SelectedFileContext and ContextMetrics entities
│       │   ├── errors.py           # Domain exception hierarchy
│       │   ├── server.py           # ServerState and ServerStatus domain models
│       │   └── workflow.py         # Workflow and WorkflowRegistry definitions
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py             # LLMProvider protocol and data transfer types
│       │   ├── llama_cpp.py        # LlamaCppProvider (HTTP SSE client implementation)
│       │   ├── manager.py          # LlamaServerManager (subprocess lifecycle & health checks)
│       │   └── mock.py             # MockLLMProvider (deterministic mock for tests & demo)
│       ├── prompts/
│       │   ├── __init__.py
│       │   └── registry.py         # Curated workflow prompt templates and rules
│       ├── security/
│       │   ├── __init__.py
│       │   ├── filter.py           # FileScanner and sensitive file exclusion filter
│       │   └── redaction.py        # Log and export sanitizer for sensitive tokens
│       ├── services/
│       │   ├── __init__.py
│       │   ├── chat_service.py     # Conversation lifecycle, prompt assembly, stream handling
│       │   ├── context_service.py  # User-selected file management and context metrics
│       │   ├── diagnostics.py      # System, hardware, and runtime diagnostics compiler
│       │   ├── model_service.py    # GGUF validation, executable verification, server binding
│       │   ├── settings_service.py # Persistent application settings manager
│       │   └── workflow_service.py # Workflow execution rules and parameter adapter
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py         # SQLAlchemy engine, session maker, and schema setup
│       │   ├── models.py           # Declarative database table models
│       │   └── repositories.py     # Chat, Message, Setting, Context CRUD repositories
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── controllers.py      # UI Controllers / ViewModels separating Qt from services
│       │   ├── main_window.py      # Main desktop window container
│       │   ├── theme.py            # Desktop styles, palette, typography, visual constants
│       │   ├── dialogs/            # Modal dialogs (settings, model setup, export)
│       │   └── widgets/            # Reusable widgets (chat view, editor, status bar, files)
│       └── utils/
│           ├── __init__.py
│           ├── async_qt.py         # QThread / asyncio bridging mechanism
│           ├── logging.py          # Structured JSON/text local logging configuration
│           └── network.py          # Local port availability discovery utilities
├── tests/
│   ├── fixtures/                   # Test fixtures (sample prompts, mock responses)
│   ├── integration/                # Service and database integration tests
│   └── unit/                       # Unit tests for domain, security, providers, workflows
└── website/
    ├── index.html                  # Informational static homepage
    ├── script.js                   # Client-side tab navigation & copy utilities
    └── styles.css                  # Responsive modern static styling
```

---

## 3. Component Responsibility Matrix

| Component | Primary Responsibilities | Prohibited Responsibilities |
| :--- | :--- | :--- |
| **PySide6 UI Views** | Render widgets, display state, capture user input events, present markdown/syntax highlighting, trigger controller actions. | Direct subprocess management, direct SQLite access, raw HTTP calls, file system directory crawling, prompt construction logic. |
| **Controllers / ViewModels** | Bridge Qt Signals/Slots with application services, manage UI view state, map domain exceptions to human-readable UI notices. | Executing raw SQL statements, spawning native processes, executing shell commands, storing permanent domain state. |
| **ChatService** | Coordinate chat session lifecycle, manage message sequencing, build final prompts combining workflows and file context, manage streaming and cancellation. | Interacting directly with Qt widgets, launching external executables, mutating files on disk, executing generated code. |
| **WorkflowService** | Maintain registry of 11 curated workflows, validate required inputs for selected workflows, assemble specialized system prompts. | Writing directly to SQLite, executing user code, formatting Qt UI elements. |
| **ModelService** | Validate GGUF file integrity/size, verify llama-server binary executable permissions, coordinate server startup/shutdown via manager. | Streaming token generation HTTP requests directly, manipulating chat records. |
| **ProjectContextService** | Manage user-explicitly selected files, compute token/character counts, invoke security filters, enforce file size and context limits. | Recursively scanning directories without explicit selection, writing or modifying project files, executing git commands. |
| **SettingsService** | Provide typed read/write access to application settings, manage default configurations, validate setting boundaries. | Executing business operations, communicating across network interfaces. |
| **DiagnosticsService** | Aggregate OS metrics, CPU architecture, RAM capacity, model attributes, server status, and token throughput; format redacted diagnostic reports. | Running fix/repair scripts, sending diagnostic data over the network, exposing user credentials or private file contents. |
| **LLMProvider** (Protocol) | Define contract for health checking, token generation, streaming (`AsyncIterator[str]`), generation cancellation, and metadata retrieval. | Persisting database records, managing child process lifecycles. |
| **LlamaCppProvider** | Implement `LLMProvider` using `httpx.AsyncClient` against `http://127.0.0.1:<port>`, parse SSE streaming chunks, handle timeouts and connection failures. | Spawning or killing `llama-server` processes, accessing application databases. |
| **MockLLMProvider** | Deterministic mock implementation yielding simulated streaming tokens for automated tests, offline UI verification, and CI pipelines. | Making network requests, interacting with native binaries, reading local models. |
| **LlamaServerManager** | Manage `llama-server` subprocess lifecycle (start, monitor, stop, force terminate), discover open ports, capture stdout/stderr, detect crashes. | Handling chat logic, modifying SQLite records, interacting directly with PySide6 widgets. |
| **SQLite Repositories** | Perform transactional CRUD operations for Chats, Messages, Settings, and Contexts using SQLAlchemy 2.0 sessions. | Network I/O, process handling, prompt assembly, calling LLM providers. |
| **FileScanner / SecurityFilter** | Inspect selected file paths against sensitive deny-patterns (`.env`, `*.key`, `id_rsa`, `node_modules`, etc.), enforce byte limits, verify UTF-8 encoding. | Writing or altering files, silently omitting blocked files without notifying the user. |

---

## 4. Domain Design

All domain entities are defined as pure, framework-agnostic Python classes (using dataclasses or Pydantic V2) with comprehensive type annotations.

### 4.1 Chat
Represents an ongoing or historical conversation session.
* `id: str` (UUIDv4 string)
* `title: str` (User-defined or auto-generated conversation title)
* `workflow_id: str` (ID of the initial or active workflow, e.g., `"explain_code"`)
* `model_name: str` (Name of the GGUF model configured when the chat was created)
* `model_path: str` (Absolute path to the GGUF model file on the local machine)
* `created_at: datetime` (UTC timestamp of chat creation)
* `updated_at: datetime` (UTC timestamp of last message or title update)

### 4.2 Message
Represents an individual message turn within a chat.
* `id: str` (UUIDv4 string)
* `chat_id: str` (Foreign key reference to parent Chat)
* `role: MessageRole` (Enum: `SYSTEM`, `USER`, `ASSISTANT`)
* `content: str` (Markdown / code text payload)
* `token_count: int | None` (Computed or reported token count, if available)
* `generation_duration_ms: int | None` (Time taken to generate the response in milliseconds)
* `created_at: datetime` (UTC timestamp of message creation)

### 4.3 Setting
Represents a persisted key-value application configuration setting.
* `key: str` (Unique configuration key identifier, e.g., `"model_path"`, `"context_size"`)
* `value: str` (Serialized JSON string representing the setting value)
* `updated_at: datetime` (UTC timestamp of last update)

### 4.4 SelectedFileContext
Represents an explicitly user-selected source code file attached as read-only context.
* `id: str` (UUIDv4 string)
* `chat_id: str` (Foreign key reference to parent Chat)
* `file_path: str` (Absolute path on the local filesystem)
* `display_name: str` (Relative or shortened file path for UI presentation)
* `language: str` (Identified programming or markup language, e.g., `"python"`, `"php"`)
* `content: str` (UTF-8 decoded source code snapshot)
* `line_start: int | None` (1-indexed start line, if subset selected)
* `line_end: int | None` (1-indexed end line, if subset selected)
* `byte_size: int` (File size in bytes)
* `created_at: datetime` (UTC timestamp of file addition)

### 4.5 ModelConfiguration
Represents local model setup parameters.
* `model_path: str` (Absolute path to local GGUF file)
* `model_name: str` (Extracted model filename, e.g., `Qwen2.5-Coder-3B-Instruct-Q4_K_M.gguf`)
* `model_size_bytes: int` (Exact size on disk in bytes)
* `executable_path: str` (Absolute path to `llama-server` binary)
* `context_size: int` (Active context window: default `4096`, low-memory `2048`, optional `8192`, advanced `16384`/`32768`)
* `threads: int` (CPU execution threads allocated, defaults to `max(1, physical_cores - 1)`)
* `host: str` (Localhost binding IP: strictly `"127.0.0.1"`)
* `port: int` (Local port: default `8080`, or dynamically discovered available port)

### 4.6 GenerationSettings
Represents inference hyper-parameters passed per generation request.
* `temperature: float` (Sampling temperature, default `0.3` for deterministic code output)
* `top_p: float` (Nucleus sampling threshold, default `0.8`)
* `max_tokens: int` (Maximum generation tokens, default `2048`)
* `repeat_penalty: float` (Repetition penalty factor, default `1.1`)
* `stop_tokens: list[str]` (Stop sequence tokens, e.g., `["<|im_end|>", "<|endoftext|>"]`)

### 4.7 Workflow
Represents a curated developer task template.
* `id: str` (Unique slug, e.g., `"explain_code"`, `"debug_code"`, `"refactor_code"`)
* `name: str` (Human-readable title, e.g., `"Explain Code"`)
* `description: str` (Short explanation of what the workflow performs)
* `system_prompt: str` (Guiding instructions enforcing honesty, assumptions, and formatting)
* `input_requirements: list[str]` (Expected user inputs, e.g., `["Source code or function snippet"]`)
* `output_format: str` (Expected response layout, e.g., `"Analysis, Step-by-Step Breakdown, Caveats"`)
* `recommended_temperature: float` (Suggested temperature for this workflow)

### 4.8 ServerStatus / ServerState
Represents the runtime status of the local `llama-server`.
* `state: ServerState` (One of the 8 explicit states: `STOPPED`, `STARTING`, `READY`, `GENERATING`, `STOPPING`, `START_FAILED`, `CRASHED`, `UNAVAILABLE`)
* `host: str` (Host address, e.g., `"127.0.0.1"`)
* `port: int` (Bound local port)
* `pid: int | None` (Operating system process ID)
* `uptime_seconds: float` (Continuous uptime since successful health check)
* `last_health_check: datetime | None` (Timestamp of most recent successful poll)
* `error_message: str | None` (Descriptive error message when in a failure state)

---

## 5. Database Schema Design (SQLite + SQLAlchemy 2.0)

The persistence tier uses SQLite with SQLAlchemy 2.0 declarative models. SQLite foreign key constraints are enforced explicitly on every connection via the `PRAGMA foreign_keys = ON;` directive.

```text
┌───────────────────────────────────────┐
│                 chats                 │
├───────────────────────────────────────┤
│ PK  id               VARCHAR(36)      │
│     title            VARCHAR(255)     │
│     workflow         VARCHAR(64)      │
│     model_name       VARCHAR(255)     │
│     model_path       TEXT             │
│     created_at       TIMESTAMP (UTC)  │
│     updated_at       TIMESTAMP (UTC)  │
└──────────────────┬────────────────────┘
                   │ 1
                   │
                   │ N
┌──────────────────▼────────────────────┐       ┌───────────────────────────────────────┐
│               messages                │       │        selected_file_contexts         │
├───────────────────────────────────────┤       ├───────────────────────────────────────┤
│ PK  id               VARCHAR(36)      │       │ PK  id               VARCHAR(36)      │
│ FK  chat_id          VARCHAR(36)      │◄──────┤ FK  chat_id          VARCHAR(36)      │
│     role             VARCHAR(16)      │   1:N │     file_path        TEXT             │
│     content          TEXT             │       │     display_name     VARCHAR(255)     │
│     token_count      INTEGER (NULL)   │       │     language         VARCHAR(32)      │
│     duration_ms      INTEGER (NULL)   │       │     content          TEXT             │
│     created_at       TIMESTAMP (UTC)  │       │     line_start       INTEGER (NULL)   │
└───────────────────────────────────────┘       │     line_end         INTEGER (NULL)   │
                                                │     byte_size        INTEGER          │
┌───────────────────────────────────────┐       │     created_at       TIMESTAMP (UTC)  │
│               settings                │       └───────────────────────────────────────┘
├───────────────────────────────────────┤
│ PK  key              VARCHAR(64)      │
│     value            TEXT             │
│     updated_at       TIMESTAMP (UTC)  │
└───────────────────────────────────────┘
```

### Table Definitions & Constraints

#### 1. `chats`
* `id`: `VARCHAR(36)` Primary Key (UUIDv4).
* `title`: `VARCHAR(255)` NOT NULL, indexed.
* `workflow`: `VARCHAR(64)` NOT NULL.
* `model_name`: `VARCHAR(255)` NOT NULL.
* `model_path`: `TEXT` NOT NULL.
* `created_at`: `TIMESTAMP` NOT NULL (Defaults to UTC now).
* `updated_at`: `TIMESTAMP` NOT NULL, indexed.
* **Indexes**: `ix_chats_updated_at` (DESC) for ordering recent chat history.

#### 2. `messages`
* `id`: `VARCHAR(36)` Primary Key (UUIDv4).
* `chat_id`: `VARCHAR(36)` NOT NULL. Foreign Key referencing `chats.id` with `ON DELETE CASCADE`.
* `role`: `VARCHAR(16)` NOT NULL (`'system'`, `'user'`, `'assistant'`).
* `content`: `TEXT` NOT NULL.
* `token_count`: `INTEGER` NULLABLE.
* `generation_duration_ms`: `INTEGER` NULLABLE.
* `created_at`: `TIMESTAMP` NOT NULL (Defaults to UTC now).
* **Indexes**: `ix_messages_chat_id_created_at` on `(chat_id, created_at ASC)`.

#### 3. `selected_file_contexts`
* `id`: `VARCHAR(36)` Primary Key (UUIDv4).
* `chat_id`: `VARCHAR(36)` NOT NULL. Foreign Key referencing `chats.id` with `ON DELETE CASCADE`.
* `file_path`: `TEXT` NOT NULL.
* `display_name`: `VARCHAR(255)` NOT NULL.
* `language`: `VARCHAR(32)` NOT NULL.
* `content`: `TEXT` NOT NULL.
* `line_start`: `INTEGER` NULLABLE.
* `line_end`: `INTEGER` NULLABLE.
* `byte_size`: `INTEGER` NOT NULL.
* `created_at`: `TIMESTAMP` NOT NULL.
* **Indexes**: `ix_file_contexts_chat_id` on `chat_id`.

#### 4. `settings`
* `key`: `VARCHAR(64)` Primary Key.
* `value`: `TEXT` NOT NULL (JSON-encoded value payload).
* `updated_at`: `TIMESTAMP` NOT NULL.

---

## 6. LLM Provider Design

The LLM interface decouples client interaction from concrete model inference runtimes.

```python
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMProvider(Protocol):
    async def health_check(self) -> bool:
        """Verify that the underlying provider/server is available and responsive."""
        ...

    async def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        settings: GenerationSettings | None = None,
    ) -> AsyncIterator[str]:
        """Stream generated response tokens asynchronously as text chunks."""
        ...

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        settings: GenerationSettings | None = None,
    ) -> str:
        """Generate a complete text response asynchronously."""
        ...

    async def cancel(self) -> None:
        """Cancel any active in-flight text generation."""
        ...

    async def get_metadata(self) -> dict[str, str | int | float | bool]:
        """Retrieve model and provider operational metadata."""
        ...
```

### Provider Implementations

#### 1. `LlamaCppProvider`
* **Transport**: Uses `httpx.AsyncClient` communicating over HTTP to `http://127.0.0.1:<port>`.
* **Streaming Protocol**: Connects to the llama-server `/v1/chat/completions` or `/completion` endpoint with `stream=True`. Reads incoming SSE `data: {"content": "..."}` payloads and yields token fragments.
* **Cancellation**: Cancels the active `httpx` streaming response and optionally invokes the llama-server `/cancel` or slot release endpoint.
* **Structured Error Hierarchy**:
  * `LLMError`: Base exception for LLM operations.
  * `LLMConnectionError`: Server is unreachable, refused connection, or crashed.
  * `LLMTimeoutError`: Health check or generation timed out.
  * `LLMGenerationCancelled`: User explicitly aborted generation.
  * `LLMModelError`: llama-server returned an HTTP 4xx/5xx error (e.g. context limit exceeded).

#### 2. `MockLLMProvider`
* **Purpose**: Offline testing, automated CI suites, and UI development without GGUF weights.
* **Behavior**: Yields realistic pre-defined or generated tokens with a configurable delay (e.g. 15ms per token) to simulate streaming. Supports immediate cancellation upon request and emits simulated error states when configured.

---

## 7. llama-server Lifecycle Design

The `LlamaServerManager` encapsulates all low-level OS child process mechanics:

```text
┌────────────────────────┐
│   ModelService / UI    │
└───────────┬────────────┘
            │ start_server(config)
            ▼
┌────────────────────────────────────────────────────────┐
│                  LlamaServerManager                    │
│                                                        │
│ 1. Validate executable exists & has exec permission   │
│ 2. Validate GGUF path exists, readable & >= 50MB       │
│ 3. Discover available local port (127.0.0.1:8080-8099) │
│ 4. Construct safe argv list (No shell=True)            │
│ 5. Spawn subprocess with redirected stdout/stderr      │
│ 6. Poll /health endpoint with 30s timeout              │
│ 7. Transition to READY                                 │
└────────────────────────────────────────────────────────┘
```

1. **Executable Validation**: Verifies that the specified binary exists, is an ordinary file, possesses executable permissions (`os.access(path, os.X_OK)`), and passes a `--version` sanity probe.
2. **Model Path Validation**: Confirms the GGUF file exists, is non-empty, ends in `.gguf`, is readable, and meets a minimum size threshold (> 50 MB) to prevent loading corrupted files.
3. **Safe Subprocess Argument Arrays**: Spawns processes strictly using `list[str]` arguments. Never passes commands as raw strings or uses `shell=True`.
   ```python
   args = [
       executable_path,
       "--model", model_path,
       "--ctx-size", str(context_size),
       "--threads", str(threads),
       "--host", "127.0.0.1",
       "--port", str(port),
       "--log-disable",  # Structured local capture via pipes
   ]
   ```
4. **Localhost Binding**: Explicitly passes `--host 127.0.0.1` to prevent binding to external or public network interfaces.
5. **Available Local Port Discovery**: Scans local ephemeral ports starting at 8080 up to 8099 by testing local socket bindings before spawning the server.
6. **Startup Monitoring & Health Checks**: Spawns the process asynchronously, then polls `GET http://127.0.0.1:<port>/health` every 250ms up to a configurable timeout (default 30 seconds).
7. **Graceful Stop**: Sends `SIGTERM` (on Linux) or `CTRL_BREAK_EVENT` / `WM_CLOSE` (on Windows). Waits up to 5 seconds for clean exit.
8. **Forced Termination**: If the process fails to exit within the graceful timeout, issues `SIGKILL` (or `TerminateProcess` on Windows) to prevent orphaned processes.
9. **Crash Detection**: Uses background thread/async task monitoring process exit codes. If the process terminates unexpectedly while in `READY` or `GENERATING`, immediately transitions to `CRASHED`.
10. **Log Capture**: Asynchronously reads stdout and stderr pipes into a circular memory buffer (last 500 lines) and writes to `sarthika_server.log` in the standard user log directory.
11. **Prevention of Duplicate Server Processes**: Employs an in-process lock and checks for existing active instances before spawning a new server.

---

## 8. Explicit Server State Machine

The server runtime state is strictly governed by an 8-state deterministic finite state machine:

```text
               ┌───────────────┐
               │    STOPPED    │◄───────────────────────┐
               └───────┬───────┘                        │
                       │ start()                        │
                       ▼                                │
               ┌───────────────┐                        │
               │   STARTING    │                        │
               └───┬───────┬───┘                        │
  health check ok │       │ timeout / exec error       │
                   ▼       ▼                            │
        ┌─────────────┐ ┌──────────────┐                │
        │    READY    │ │ START_FAILED │───────────────►│
        └───┬─────▲───┘ └──────────────┘    dismiss     │
  generate()│     │ stream ended                        │
            ▼     │                                     │
       ┌──────────┴────┐                                │
       │  GENERATING   │                                │
       └───────┬───────┘                                │
               │ stop()                                 │
               ▼                                        │
        ┌─────────────┐                                 │
        │  STOPPING   │─────────────────────────────────┤
        └─────────────┘          process exited         │
               ▲                                        │
               │ crash detected / process dead          │
        ┌──────┴──────┐                                 │
        │   CRASHED   │─────────────────────────────────┤
        └─────────────┘          reset / clean          │
               ▲                                        │
               │ unreachable endpoint                   │
        ┌──────┴──────┐                                 │
        │ UNAVAILABLE │─────────────────────────────────┘
        └─────────────┘
```

### State Definitions
* **`STOPPED`**: Initial state. No server subprocess is running.
* **`STARTING`**: Subprocess has been spawned; awaiting health check endpoint readiness.
* **`READY`**: Server is running, healthy, and idling; ready to accept generation requests.
* **`GENERATING`**: Server is actively processing an in-flight prompt and streaming tokens.
* **`STOPPING`**: Graceful termination signal sent; waiting for process exit.
* **`START_FAILED`**: Server process failed to launch, timed out, or returned an error code during startup.
* **`CRASHED`**: Server process terminated unexpectedly during idle or active generation.
* **`UNAVAILABLE`**: External local server endpoint could not be reached or lost network connectivity.

### Allowed & Invalid State Transitions

| From State | Allowed Target States | Prohibited Target States |
| :--- | :--- | :--- |
| `STOPPED` | `STARTING`, `UNAVAILABLE` | `READY`, `GENERATING`, `STOPPING`, `CRASHED` |
| `STARTING` | `READY`, `START_FAILED`, `STOPPING` | `GENERATING`, `STOPPED` |
| `READY` | `GENERATING`, `STOPPING`, `CRASHED`, `UNAVAILABLE` | `STARTING`, `START_FAILED` |
| `GENERATING` | `READY`, `STOPPING`, `CRASHED`, `UNAVAILABLE` | `STARTING`, `START_FAILED` |
| `STOPPING` | `STOPPED`, `CRASHED` | `READY`, `GENERATING`, `STARTING` |
| `START_FAILED`| `STOPPED`, `STARTING` | `READY`, `GENERATING` |
| `CRASHED` | `STOPPED`, `STARTING` | `READY`, `GENERATING` |
| `UNAVAILABLE` | `STOPPED`, `STARTING` | `READY`, `GENERATING` |

---

## 9. UI Screen Map & User Flows

The PySide6 desktop interface is structured around a focused workspace designed for local software engineering tasks:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Sarthika Code v0.1                     [● Model: Ready (3B Q4_K_M)]   │
├─────────────────┬──────────────────────────────────────────────────────┤
│ CHATS           │ WORKFLOW: [ Explain Code ▼ ]     [Settings] [Diag]   │
│                 ├──────────────────────────────────────────────────────┤
│ [+ New Chat]    │ CONVERSATION HISTORY                                 │
│                 │                                                      │
│ • UserAuth.php  │ User: Explain this query and suggest indexes...      │
│ • TestSuite     │                                                      │
│ • DatabaseMigration│ Assistant: The query performs a full table scan...  │
│                 │ ```sql                                               │
│                 │ CREATE INDEX idx_users_active ON users(status);      │
│                 │ ```                                                  │
│                 ├──────────────────────────────────────────────────────┤
│                 │ CODE / CONTEXT PANEL (Read-Only)                     │
│                 │ Files: [app/Models/User.php (142 lines)] [Review Context]│
│                 ├──────────────────────────────────────────────────────┤
│                 │ PROMPT INPUT                                         │
│                 │ [ Enter your instructions...               ] [Send]  │
└─────────────────┴──────────────────────────────────────────────────────┘
```

### Screen Responsibilities & Flows

1. **Welcome / Onboarding Screen**:
   * *Flow*: First-run launch when no model or server is configured.
   * *Responsibilities*: Explain the local-first, privacy-focused nature of Sarthika Code. Guide the user through selecting a GGUF model and the `llama-server` binary, or starting in Offline Mock Demo Mode.
2. **Model Setup Dialog / View**:
   * *Flow*: Triggered from Onboarding or Settings.
   * *Responsibilities*: File pickers for `.gguf` weights and `llama-server` binary; display model size; context window selector (2048, 4096, 8192, 16384) with memory warnings; thread count; test connection button.
3. **Main Chat Workspace**:
   * *Flow*: Primary day-to-day screen.
   * *Responsibilities*: Left sidebar for chat session management; top workflow selector; conversation viewport with markdown and syntax-highlighted code blocks; copy buttons; stop/cancel generation button; prompt input.
4. **Workflow Selection Dropdown**:
   * *Responsibilities*: Provides one-click access to the 11 curated workflows (e.g. *Explain Code*, *Debug Code*, *Generate Unit Tests*). Displays workflow requirements and auto-adjusts system instructions.
5. **Code Editor / Context Panel**:
   * *Responsibilities*: Dedicated multiline code input box with language selection (Python, PHP, JS, SQL, HTML, etc.), line numbers, clear button, and character/token estimation indicator.
6. **Selected Files Review Dialog**:
   * *Responsibilities*: Explicit file selection list. Shows accepted files with line counts, file size, and syntax tags. Highlights and blocks sensitive files (`.env`, `credentials.json`, `id_rsa`) with clear exclusion badges.
7. **Chat History Management**:
   * *Responsibilities*: Rename chat, delete chat, and export chat to Markdown or JSON.
8. **Settings Screen**:
   * *Responsibilities*: Default context size, temperature, theme preferences (dark/light), default model paths, database management, and cache clearance.
9. **Diagnostics Screen**:
   * *Responsibilities*: Displays real-time OS info, CPU, RAM usage, active model path, server PID, server port, token generation speed (tokens/sec), log file viewer, and `[Copy Diagnostics]` button.
10. **Privacy and Limitations Screen**:
    * *Responsibilities*: Explains local-only network boundary, non-AGI reality disclaimer, model fallibility, and the requirement for developers to review generated code.
11. **Offline Mock / Demo Mode**:
    * *Responsibilities*: Allows full interactive testing of the UI, streaming, cancellation, and workflow mechanisms without requiring a model download or native compiler.

---

## 10. Security and Privacy Model

Sarthika Code operates under a strict **Zero-Trust Local Boundary** security model.

1. **Local-Only Network Policy**:
   * Outbound internet access is strictly prohibited. The application makes zero external HTTP, DNS, or socket requests.
   * No analytics, telemetry, crash reporting, update checks, or usage statistics exist in the codebase.
2. **Localhost-Only llama-server Binding**:
   * The local inference subprocess is bound strictly to `127.0.0.1`. Binding to `0.0.0.0` or external network adapters is blocked.
3. **No Automatic File Selection**:
   * Sarthika Code never recursively scans project folders or automatically includes files without explicit user action via the file selection dialog.
4. **No Automatic Code or Command Execution**:
   * Sarthika Code will never execute shell commands, terminal scripts, build tools (`npm`, `composer`, `pip`), or Git operations (`git commit`, `git push`), regardless of model recommendations.
5. **No Automatic File Writing**:
   * The application is read-only regarding user projects. It will never silently write or modify project files.
6. **Sensitive File Filtering (Denylist)**:
   * Any file matching the following patterns is blocked from selection:
     * Secrets/Environment: `.env`, `.env.*`, `*.pem`, `*.key`, `*.cert`, `credentials.json`, `secrets.toml`
     * Cryptographic keys: `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`
     * Dependencies/Metadata: `node_modules/`, `vendor/`, `.git/`, `.svn/`, `.hg/`
     * Databases & Binaries: `*.db`, `*.sqlite`, `*.sqlite3`, `*.exe`, `*.dll`, `*.so`, `*.bin`, `*.tar`, `*.gz`, `*.zip`
     * Non-UTF8: Any binary or non-text format.
7. **Log Redaction Rules**:
   * Logs written to disk redact local user home directories (e.g. `/home/username/` -> `~/`), auth tokens, and full source code contents. Only error messages, component names, and status codes are preserved.
8. **Chat Export Privacy**:
   * When exporting conversations to Markdown or JSON, absolute filesystem paths can be sanitized or stripped on demand.

---

## 11. Performance and Hardware Plan

Sarthika Code is specifically engineered to run on standard, non-GPU developer laptops.

### Hardware Targets & Memory Allocations

| Configuration | Supported Mode | Default Context | Model Recommendation | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **8 GB RAM (No GPU)** | **Best-Effort** | **2048 tokens** | Qwen2.5-Coder 3B (Q4_K_M) | Low-memory mode. System memory is tight; user advised to close heavy apps. |
| **16 GB RAM (No GPU)**| **Recommended** | **4096 tokens** | Qwen2.5-Coder 3B (Q4_K_M) | Comfortable performance. Fast prompt evaluation and steady token generation. |
| **32 GB+ RAM / GPU**  | **Optimal** | **8192+ tokens** | Qwen2.5-Coder 3B / 7B | Can allocate larger context windows with warning notifications. |

### Context Window & Memory Usage Rules
* **Low-Memory Mode (2048 Context)**: Automatically recommended if available system RAM is below 10 GB.
* **Standard Context (4096 Context)**: Default for 16 GB machines.
* **High Context (8192 Context)**: Optional setting; displays a warning regarding increased RAM consumption and slower prompt evaluation.
* **Extended Context (16384 / 32768 Context)**: Gated behind an explicit confirmation warning: *"Context windows above 8192 tokens consume significant memory for KV-cache and may cause swapping or sluggish inference on CPU."*
* **Single Model Rule**: Sarthika Code will never load more than one model simultaneously. Any model change cleanly terminates the prior server process before launching a new one.

### UI Responsiveness Guarantee
* The PySide6 UI event loop operates strictly on the main thread at 60 FPS.
* All long-running operations—including GGUF validation, server health polling, HTTP SSE streaming, SQLite queries, and file loading—execute in asynchronous background worker threads (`asyncio` loop running in a dedicated `QThread`).

---

## 12. Risk Register

| Risk ID | Description | Severity | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **RSK-01** | **CPU-Only Slow Inference**<br>Complex prompts on older CPUs result in slow token generation (< 5 t/s). | Medium | High | Recommend 3B Q4_K_M quantization; display real-time token throughput diagnostics; provide prompt token count estimates; optimize thread allocation to match physical CPU cores. |
| **RSK-02** | **8 GB RAM System OOM**<br>Concurrent browser/IDE usage with 3B model causes OS paging or memory exhaustion. | High | High | Enforce 2048 default context for 8 GB systems; prompt user with low-memory guidance; monitor memory before startup; cleanly abort if memory is critically low. |
| **RSK-03** | **KV-Cache Memory Bloat**<br>Large context windows (16K+) exhaust available RAM. | High | Medium | Cap default context to 4096; require explicit user confirmation for contexts > 8192; calculate and display estimated KV-cache memory in Model Setup. |
| **RSK-04** | **llama-server Startup Failure**<br>Missing dynamic libraries, invalid paths, or corrupt GGUF prevents server launch. | High | Medium | Validate binary executable permissions and model file size before spawning; capture stderr into diagnostic log; display human-friendly explanation instead of crashing. |
| **RSK-05** | **Incompatible llama.cpp Flags**<br>User's local llama.cpp version has different CLI arguments. | Medium | Medium | Use only core, stable CLI arguments (`--model`, `--port`, `--host`, `--ctx-size`, `--threads`); avoid deprecated or experimental flags. |
| **RSK-06** | **Windows Subprocess Management**<br>Orphaned `llama-server.exe` processes remain after application crashes or abrupt termination. | High | Medium | Use Windows Job Objects (`SetInformationJobObject` with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) to guarantee child process termination on parent exit. |
| **RSK-07** | **Localhost Port Conflicts**<br>Configured port (e.g. 8080) is already occupied by web servers or dev tools. | Medium | High | Dynamically scan a range of local ports (8080–8099) to find an available port before binding; allow manual port override in Settings. |
| **RSK-08** | **Model Licensing Uncertainty**<br>Distributing model weights could violate intellectual property or licensing terms. | High | Low | Never bundle model weights in the repository or application installers; provide clear download guidance directly pointing to official upstream HuggingFace repositories. |
| **RSK-09** | **PyInstaller Packaging Bloat/Failure**<br>Desktop bundle fails to find Qt plugins or dynamic libraries. | Medium | Medium | Define explicit PyInstaller `.spec` files; isolate dependencies; test automated packaging on both Windows and Linux in CI workflows. |
| **RSK-10** | **Sensitive File Exposure**<br>User accidentally includes `.env`, API keys, or private certificates in prompt context. | Critical | Medium | Multi-layer file scanner blocks sensitive extensions and patterns by default; displays explicit confirmation dialog highlighting accepted and blocked files. |
| **RSK-11** | **Inaccurate Model Output / Hallucination**<br>User blindly trusts generated code containing security vulnerabilities or logical errors. | High | High | Display prominent UI disclaimers; enforce workflow prompt rules requiring the model to state assumptions, cite uncertainties, and remind the user to test locally. |

---

## 13. Dependency Decision Record

Every planned runtime and development dependency is vetted for necessity, licensing, and overhead:

| Package | Category | Version | Justification | Alternatives Considered & Rejected |
| :--- | :--- | :--- | :--- | :--- |
| **PySide6** | Runtime | `>=6.6.0` | Official Qt for Python under LGPLv3; native desktop styling, cross-platform widgets, robust thread-safe signal/slot architecture. | *PyQt6*: Rejected due to commercial/GPLv3 copyleft licensing.<br>*Tkinter*: Rejected due to poor styling, missing rich text formatting, and weak async event integration.<br>*Electron/Tauri*: Rejected to avoid multi-hundred megabyte web view runtimes and dual-language IPC overhead. |
| **SQLAlchemy** | Runtime | `>=2.0.25` | Modern typed ORM with DeclarativeBase; clean transaction management; robust SQLite support; enables instant in-memory unit testing. | *Raw sqlite3*: Rejected due to lack of type safety, schema migrations, and manual relational mapping overhead.<br>*Peewee*: Rejected due to weaker typing and smaller ecosystem compared to SQLAlchemy 2.x. |
| **httpx** | Runtime | `>=0.27.0` | High-performance HTTP client with native `asyncio` support and standard Server-Sent Events (SSE) streaming capabilities. | *requests*: Rejected because it is purely synchronous and blocks the event loop.<br>*aiohttp*: Rejected because httpx provides a cleaner API and standard parity between sync and async calls. |
| **platformdirs** | Runtime | `>=4.2.0` | Determines standard OS locations for application data, logs, and configuration (`AppData` on Windows, `~/.local/share` on Linux). | *Custom path logic*: Rejected because standard OS directory rules across Windows/Linux/macOS have complex edge cases. |
| **pydantic** | Runtime | `>=2.6.0` | Fast, type-safe data validation and JSON serialization for domain entities and generation settings. | *dataclasses*: Useful, but Pydantic V2 provides instant robust JSON schema parsing and constraint validation. |
| **pytest** | Development| `>=8.0.0` | De-facto Python testing framework with rich fixture and parametrization ecosystem. | *unittest*: Less expressive, verbose assertion syntax. |
| **pytest-asyncio**| Development| `>=0.23.0` | Native support for testing `async def` test functions and async generators (`stream`). | Handcrafted async runners: Error-prone and fragile. |
| **pytest-qt** | Development| `>=4.4.0` | Specialized Qt event loop testing, signal spy, and widget interaction validation. | Manual Qt event pumping: Prone to test deadlocks. |
| **ruff** | Development| `>=0.3.0` | Ultra-fast linter and code formatter written in Rust; replaces Flake8, Black, isort, and pyupgrade in a single tool. | *Black/Flake8*: Significantly slower and requires maintaining multiple tool configurations. |
| **mypy** | Development| `>=1.9.0` | Strict static type checking to catch type inconsistencies and protocol violations ahead of runtime. | Running untyped: Unacceptable for production-grade desktop architecture. |
| **PyInstaller** | Packaging | `>=6.5.0` | Creates standalone desktop executables for Windows and Linux without requiring users to install Python runtimes. | *Nuitka*: Higher compilation complexity and longer build times. |
