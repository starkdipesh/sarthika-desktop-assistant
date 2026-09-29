# SARTHIKA CODE

## Master Product & Engineering Implementation Prompt — Version 0.1

You are a **Principal Software Architect, Senior Python Engineer, Desktop Application Engineer, Local-LLM Systems Engineer, Product Manager, UI/UX Engineer, Security Engineer, QA Engineer, and Open-Source Maintainer**.

Your task is to **design and implement a production-quality Version 0.1 desktop application called “Sarthika Code”**.

Do not treat this as a simple coding exercise.

You must reason about:

* product requirements
* architecture
* maintainability
* user experience
* local AI inference
* CPU/RAM limitations
* privacy
* security
* failure recovery
* testing
* packaging
* documentation
* release quality

The goal is to create a **real, usable, reproducible desktop product**, not a prototype full of placeholders.

---

# 1. PRODUCT DEFINITION

## Product

**Sarthika Code**

Working tagline:

> A private, local AI coding assistant that runs on your computer.

Sarthika Code is a **local-first desktop AI coding assistant** for developers who want useful AI coding assistance without requiring:

* cloud AI APIs
* API keys
* subscriptions
* accounts
* telemetry
* GPU hardware
* cloud source-code uploads

The application uses a locally stored **GGUF coding model** through **llama.cpp / llama-server**.

---

# 2. IMPORTANT PRODUCT REALITY

Never present Sarthika Code as:

* AGI
* human-level intelligence
* an autonomous software engineer
* a replacement for programmers
* 100% accurate
* guaranteed bug-free
* an online AI chatbot

The application must clearly communicate that generated code can be incorrect and must be reviewed and tested.

The product must work within ordinary laptop constraints.

Assume the primary user may have:

* no dedicated GPU
* 8 GB RAM
* limited CPU performance
* limited disk space
* no paid cloud services
* limited technical knowledge of local AI infrastructure

Design accordingly.

---

# 3. PRIMARY TARGET USERS

Prioritize:

1. Students
2. Junior developers
3. Freelancers
4. Developers with ordinary/lower-configuration laptops
5. PHP/Laravel developers
6. Python developers
7. Developers concerned about source-code privacy

The UX must be approachable without making the product feel childish or overly simplified.

---

# 4. VERSION 0.1 PRODUCT GOAL

Version 0.1 must allow the user to:

1. Install Sarthika Code.
2. Configure a local GGUF model.
3. Configure the llama.cpp executable.
4. Start a local llama-server.
5. Verify the server is healthy.
6. Chat with the local model.
7. Stream responses.
8. Cancel generation.
9. Save conversations locally.
10. Rename/delete/export conversations.
11. Use curated developer workflows.
12. Paste code into a dedicated code editor.
13. Explicitly select project files as read-only context.
14. Prevent sensitive files from being selected.
15. Review selected files before submitting them.
16. Generate explanations, debugging suggestions, refactoring suggestions, tests, and implementation plans.
17. View diagnostics.
18. Delete local chat history.
19. Run without an API key.
20. Run without cloud inference.
21. Use an offline mock/demo mode for UI testing.

---

# 5. HARD VERSION 0.1 BOUNDARIES

DO NOT implement these in Version 0.1:

* web browsing
* embeddings
* vector databases
* RAG
* autonomous agents
* autonomous coding
* shell command execution
* terminal integration
* Git commits
* Git push
* Git write operations
* automatic file modification
* automatic code execution
* browser automation
* email integration
* external APIs
* voice
* vision
* ROS
* cloud inference
* telemetry
* user accounts
* advertisements

The model may **generate text that looks like a command**, but Sarthika Code must never automatically execute it.

The model may generate code, but Sarthika Code must never silently write generated code into project files.

---

# 6. MODEL REQUIREMENTS

Primary supported model:

**Qwen2.5-Coder 3B Instruct**

Expected format:

```text
GGUF
```

Preferred quantization:

```text
Q4_K_M
```

Expected approximate size:

```text
3B parameters
```

The model may support a large context window, but Sarthika Code must NOT default to maximum context.

Use conservative UI defaults:

```text
Default context: 4096 tokens
Optional: 8192
Advanced: 16384
Maximum where supported: 32768
```

Explain to users that larger contexts require more memory and can reduce performance.

The application must never automatically download an unknown model.

The GGUF model must never be committed to Git.

---

# 7. CORE ARCHITECTURE

Use a clean layered architecture.

Required high-level architecture:

```text
┌───────────────────────────────┐
│           PySide6 UI          │
└───────────────┬───────────────┘
                │
┌───────────────▼───────────────┐
│      Application Services     │
│                               │
│ ChatService                   │
│ WorkflowService               │
│ ModelService                  │
│ ProjectContextService         │
│ SettingsService               │
│ DiagnosticsService            │
└───────────────┬───────────────┘
                │
┌───────────────▼───────────────┐
│       Domain / Contracts      │
│                               │
│ Chat                         │
│ Message                      │
│ ModelConfiguration           │
│ Workflow                     │
│ SelectedFile                 │
│ GenerationSettings           │
└───────────────┬───────────────┘
                │
┌───────────────▼───────────────┐
│       Infrastructure          │
│                               │
│ SQLite Repository             │
│ LlamaServerManager            │
│ LlamaCppProvider              │
│ MockLLMProvider               │
│ FileScanner                   │
│ SettingsRepository            │
└───────────────┬───────────────┘
                │
                ▼
          llama-server
                │
                ▼
             GGUF
```

The UI must not directly:

* launch subprocesses
* access SQLite
* construct raw HTTP requests
* manipulate model files
* perform project scanning

Those responsibilities belong to services/infrastructure.

---

# 8. LLM ABSTRACTION

Create an abstraction such as:

```python
class LLMProvider(Protocol):
    async def health_check(self) -> bool:
        ...

    async def generate(...):
        ...

    async def stream(...):
        ...

    async def cancel(...):
        ...
```

Implement at minimum:

```text
LLMProvider
├── LlamaCppProvider
└── MockLLMProvider
```

The rest of the application must depend on the abstraction, not directly on llama.cpp.

This is mandatory.

---

# 9. LLAMA SERVER MANAGEMENT

Create:

```text
LlamaServerManager
```

Responsibilities:

* validate executable
* validate model path
* construct safe command arguments
* start process
* monitor process
* detect startup failure
* detect crash
* expose server status
* perform health checks
* stop process
* terminate gracefully
* force terminate if required
* capture local logs
* expose diagnostics
* prevent multiple model processes

Do not block the PySide6 UI thread.

Never use unsafe shell command strings.

Prefer subprocess argument arrays.

Example conceptual command:

```text
llama-server
  --model
  /path/to/model.gguf
  --ctx-size
  4096
  --host
  127.0.0.1
  --port
  <available-local-port>
```

Bind only to localhost by default.

Do not expose the inference server publicly.

---

# 10. SERVER STATE MACHINE

Represent server state explicitly.

Required states:

```text
STOPPED
STARTING
READY
GENERATING
STOPPING
START_FAILED
CRASHED
UNAVAILABLE
```

The UI must react to state changes.

Example:

```text
STOPPED
   ↓
STARTING
   ↓
READY
   ↓
GENERATING
   ↓
READY
```

Failure example:

```text
STARTING
   ↓
START_FAILED
```

Failure to start llama-server must never crash the application.

Provide a human-readable error.

---

# 11. DESKTOP TECHNOLOGY STACK

Use:

```text
Python >= 3.11
PySide6
SQLite
SQLAlchemy 2.x
httpx
asyncio
pytest
Ruff
mypy where practical
PyInstaller
```

Do not add unnecessary frameworks.

Use standard Python libraries wherever they are sufficient.

---

# 12. DATABASE

Use SQLite + SQLAlchemy 2.x.

Create at minimum:

```text
Chat
Message
Setting
SelectedFileContext
```

Recommended structure:

### Chat

```text
id
title
workflow
created_at
updated_at
model_name
model_path
```

### Message

```text
id
chat_id
role
content
created_at
token_count nullable
generation_duration nullable
```

Roles:

```text
system
user
assistant
```

### Setting

```text
key
value
updated_at
```

### SelectedFileContext

```text
id
chat_id
file_path
display_name
language
content
line_start
line_end
created_at
```

Use foreign keys appropriately.

Add indexes where useful.

Do not store unnecessary sensitive information.

---

# 13. APPLICATION DATA LOCATION

Do not store application data inside the source repository by default.

Use OS-appropriate application data directories.

Provide a diagnostics page showing:

```text
Database location
Logs location
Configuration location
```

Document these locations.

---

# 14. MODEL MANAGER

Model Manager must allow:

* GGUF file selection
* path validation
* extension validation
* file existence validation
* file size display
* model path persistence
* llama-server executable selection
* executable validation
* connection to an existing local server
* start server
* stop server
* health check

Never upload the model.

Never automatically download models.

Never scan the user's entire filesystem looking for models.

---

# 15. CHAT EXPERIENCE

Main workspace:

```text
┌──────────────────────────────────────────────────┐
│ Sarthika Code                    ● Model Ready   │
├──────────────┬───────────────────────────────────┤
│              │                                   │
│ Chats        │          Conversation             │
│              │                                   │
│ + New Chat   │  User                             │
│              │  Assistant                        │
│ Chat 1       │                                   │
│ Chat 2       │                                   │
│ Chat 3       │                                   │
│              │                                   │
│              ├───────────────────────────────────┤
│              │ Code / Context                    │
│              │                                   │
│              ├───────────────────────────────────┤
│              │ Prompt                            │
│              │ [ Ask Sarthika... ]        [Send] │
└──────────────┴───────────────────────────────────┘
```

Support:

* streaming
* cancellation
* retry
* copy response
* copy code block
* new chat
* rename chat
* delete chat
* export chat

Do not automatically execute generated code.

---

# 16. PRIMARY UX

Do not make generic chat the only experience.

Provide workflow-first actions:

```text
Explain Code
Debug Code
Refactor Code
Generate Tests
Implementation Plan
Review Git Diff
API Design
Database Schema
```

The welcome screen should communicate:

```text
What are you working on?
```

Then present workflow choices.

---

# 17. CURATED WORKFLOWS

Create a prompt registry.

Each workflow should contain:

```text
id
name
description
system_prompt
input_requirements
output_format
```

Required workflows:

```text
Explain Code
Debug Code
Refactor Code
Generate Unit Tests
Laravel Component Draft
Python Component Draft
Explain SQL Query
Requirement → Implementation Plan
Review Git Diff
API Design Draft
Database Schema Draft
```

Every workflow prompt must instruct the model to:

1. State assumptions.
2. Identify uncertainty.
3. Avoid pretending to have executed code.
4. Avoid claiming tests passed unless evidence is provided.
5. Produce reviewable output.
6. Prefer small, understandable changes.
7. Explain potentially risky changes.
8. Encourage local testing.

---

# 18. CODE EDITOR

Provide a dedicated code input area.

Requirements:

* multiline editor
* language selection
* syntax highlighting where practical
* line numbers if practical
* code length indicator
* copy button
* clear button
* paste support

Support common languages:

```text
Python
PHP
JavaScript
TypeScript
SQL
HTML
CSS
JSON
Bash
```

Do not add a heavy IDE framework.

---

# 19. PROJECT CONTEXT

Version 0.1 project context must be:

**READ ONLY.**

The user must explicitly select files.

Never automatically recursively scan a project.

Never automatically include all files.

Before submission, display:

```text
Selected files:

✓ app/Services/UserService.php
✓ routes/api.php
✓ tests/UserTest.php

Blocked:

✗ .env
✗ credentials.json
✗ id_rsa
```

Sensitive patterns should include:

```text
.env
.env.*
.pem
.key
credentials
credential
secret
secrets
token
tokens
id_rsa
id_dsa
node_modules
vendor
.git
*.db
*.sqlite
*.sqlite3
*.zip
*.tar
*.gz
binary files
```

Allow the security filter to be configured carefully without making dangerous files easy to include.

---

# 20. CONTEXT LIMITS

Before submitting project context:

Calculate:

```text
file count
total characters
estimated tokens
```

Display a warning when context becomes large.

Never silently truncate source code.

If truncation is required, tell the user exactly what was truncated.

---

# 21. PRIVACY

Default behavior:

```text
LOCAL ONLY
```

The application must have:

* no telemetry
* no analytics
* no advertisements
* no accounts
* no login
* no cloud inference
* no hidden network requests

All inference must use localhost unless the user explicitly chooses the existing-local-server connection option.

Do not silently send files anywhere.

---

# 22. NETWORK POLICY

The application should not make arbitrary outbound network calls.

Document every network capability.

For v0.1:

```text
Allowed:
localhost llama-server communication

Not allowed:
external AI APIs
analytics
telemetry
remote code execution
cloud file upload
```

---

# 23. SECURITY

Never execute model output.

Never allow model output to become a shell command automatically.

Never automatically modify project files.

Never automatically run:

```text
git
npm
pip
composer
php
python
bash
powershell
```

Generated code is always treated as untrusted text.

---

# 24. PERFORMANCE

The application must remain responsive during inference.

Never perform long-running operations on the Qt GUI thread.

Use appropriate Qt-safe worker/thread/async architecture.

Potentially long-running tasks:

```text
model startup
health checks
HTTP streaming
database operations
file loading
diagnostics
```

must not freeze the UI.

Do not load multiple models simultaneously.

---

# 25. GENERATION DEFAULTS

Use conservative defaults.

Example:

```text
temperature: 0.3
top_p: 0.8
repeat_penalty: appropriate llama.cpp default
max_tokens: conservative UI default
context: 4096
```

Do not hard-code unsupported llama.cpp flags without validating the installed version.

Expose advanced generation controls behind an Advanced section.

---

# 26. ERROR HANDLING

Errors must be understandable.

Bad:

```text
ConnectionError: HTTPConnectionPool(...)
```

Better:

```text
Sarthika Code could not connect to the local model server.

Possible causes:
• llama-server is not running
• the configured port is unavailable
• the model failed to load
• the configured executable is invalid

Check Diagnostics for more information.
```

Keep technical details in diagnostics/logs.

---

# 27. DIAGNOSTICS SCREEN

Show:

```text
Application version
Python version
Operating system
CPU
RAM
Model path
Model filename
Model size
Quantization if known
llama-server executable
Server URL
Server status
Context size
Generation settings
Response timing
Tokens generated
Approximate tokens/second
Application log path
Database path
```

Provide:

```text
[Copy Diagnostics]
```

Do not expose secrets.

---

# 28. LOGGING

Use structured local logging.

Include:

```text
timestamp
level
component
event
message
```

Do not log:

* full source files
* secrets
* API keys
* credentials
* complete private conversations unless explicitly needed and documented

Log paths and errors safely.

---

# 29. OFFLINE DEMO MODE

Implement:

```text
MockLLMProvider
```

It must allow developers to test:

* UI
* streaming
* cancellation
* workflow selection
* chat persistence
* error states

without requiring a GGUF model.

This mode must never be confused with real AI inference.

---

# 30. TESTING

Use pytest.

Required unit tests:

```text
model path validation
settings persistence
chat persistence
message persistence
prompt construction
workflow registry
sensitive file filtering
file size limits
server status handling
server startup failure
server crash handling
diagnostics generation
```

Add integration tests where practical.

Use mocks for llama-server.

Do not require a real 3B model in CI.

---

# 31. UI TESTABILITY

Design services independently from the UI so most logic can be tested without launching the desktop application.

Do not place business logic inside button click handlers.

Bad:

```python
def on_send_clicked():
    # 300 lines of logic
```

Good:

```python
def on_send_clicked():
    self.chat_controller.send_message(...)
```

The UI should orchestrate, not contain core business logic.

---

# 32. REPOSITORY STRUCTURE

Use:

```text
sarthika-code/
│
├── README.md
├── LICENSE
├── pyproject.toml
├── .gitignore
├── .github/
│   ├── workflows/
│   │   └── tests.yml
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
│
├── docs/
│   ├── architecture.md
│   ├── installation.md
│   ├── privacy.md
│   ├── limitations.md
│   ├── benchmarks.md
│   ├── roadmap.md
│   └── troubleshooting.md
│
├── src/
│   └── sarthika_code/
│       ├── main.py
│       ├── app/
│       ├── domain/
│       ├── services/
│       ├── llm/
│       ├── prompts/
│       ├── storage/
│       ├── security/
│       ├── ui/
│       └── utils/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── scripts/
│   ├── benchmark_local.py
│   ├── start_llama_server.py
│   └── build_release.py
│
├── assets/
│
└── website/
    ├── index.html
    ├── styles.css
    └── script.js
```

---

# 33. PYPROJECT

Use modern Python packaging.

Include:

```text
project metadata
runtime dependencies
optional development dependencies
pytest configuration
ruff configuration
mypy configuration
```

Keep runtime dependencies minimal.

Do not add a package merely because it is convenient.

---

# 34. GITIGNORE

Must exclude:

```text
*.gguf
*.safetensors
.env
*.db
*.sqlite
*.sqlite3
logs/
build/
dist/
__pycache__/
.pytest_cache/
.venv/
```

Also exclude:

```text
local configuration
credentials
private test data
generated binaries
```

---

# 35. PUBLIC WEBSITE

Create a completely static GitHub Pages-compatible website.

It must contain:

```text
Hero
Product explanation
Local-first explanation
Features
How it works
Supported hardware
Model setup
Privacy
Limitations
Benchmark methodology
Screenshots/placeholders
Installation
GitHub link
Roadmap
Contributing
```

The website must NOT provide:

* live AI chat
* cloud inference
* account creation
* file upload
* model upload
* backend API

The website is informational only.

---

# 36. BRAND LANGUAGE

Use:

> Local-first AI coding assistant.

> Designed to run without a GPU.

> No API key required for local inference.

> Your selected code stays on your device.

> Experimental software. Always review and test generated code.

Avoid:

> AGI

> Human-level intelligence

> Fully autonomous developer

> Replaces programmers

> Guaranteed bug-free code

> 100% accurate

---

# 37. BENCHMARKING

Create a reproducible local benchmark script.

Record:

```text
OS
CPU
RAM
model filename
model size
quantization
context size
prompt token count
generated token count
time to first token
tokens/second
approximate RAM usage
success/failure
```

Benchmark dataset:

```text
10 Laravel tasks
10 Python tasks
10 debugging tasks
10 code explanation tasks
10 implementation planning tasks
```

Do not manufacture benchmark results.

The application must report measurements obtained from actual runs.

Do not compare against proprietary systems unless the methodology is documented and genuinely comparable.

---

# 38. DOCUMENTATION

README must include:

```text
Product mission
Features
Non-features
System requirements
Hardware guidance
Installation
Model setup
llama.cpp setup
First launch
Using workflows
Project context
Privacy
Security
Limitations
Troubleshooting
Diagnostics
Benchmark methodology
Development setup
Testing
Building releases
Contributing
Roadmap
Credits
License
Model licensing disclaimer
```

Clearly distinguish:

```text
Application license
Model license
llama.cpp license
Third-party dependency licenses
```

Do not assume the model weights can be redistributed.

---

# 39. LICENSE

Recommend and implement an appropriate open-source license for the application code.

Before finalizing model redistribution or bundling:

* inspect the model license
* inspect llama.cpp licensing requirements
* inspect third-party dependency licenses

Do not bundle model weights unless redistribution rights are verified.

---

# 40. IMPLEMENTATION MILESTONES

Build the project in milestones.

## Milestone 0 — Architecture

Deliver:

* architecture document
* dependency decision
* database design
* service boundaries
* state machine
* UI information architecture

Do not write the entire application yet.

---

## Milestone 1 — Application Foundation

Implement:

* package structure
* PySide6 bootstrap
* configuration
* logging
* error handling
* SQLite
* SQLAlchemy
* migrations/schema initialization
* test infrastructure

Acceptance:

Application launches without llama-server.

---

## Milestone 2 — Model Manager

Implement:

* model selection
* path validation
* llama-server executable selection
* server lifecycle
* state machine
* health checking
* diagnostics

Acceptance:

User can start and stop a real local llama-server.

---

## Milestone 3 — LLM Provider

Implement:

* LLMProvider abstraction
* LlamaCppProvider
* streaming
* cancellation
* health check
* error handling
* MockLLMProvider

Acceptance:

The same UI can work with either the real provider or mock provider.

---

## Milestone 4 — Chat

Implement:

* chat creation
* messages
* streaming UI
* cancellation
* persistence
* rename
* delete
* export
* copy

Acceptance:

User can conduct and reopen a complete local conversation.

---

## Milestone 5 — Developer Workflows

Implement all workflow definitions.

Acceptance:

Every workflow creates deterministic structured prompts and produces reviewable output.

---

## Milestone 6 — Code Context

Implement:

* code editor
* language selection
* selected files
* security filtering
* file preview
* context size calculation

Acceptance:

No file can be sent without explicit user selection.

---

## Milestone 7 — UX Polish

Implement:

* onboarding
* model setup experience
* workflow-first home screen
* diagnostics
* settings
* privacy
* limitations
* empty states
* loading states
* error states

---

## Milestone 8 — Testing

Implement:

* unit tests
* integration tests
* mock server tests
* persistence tests
* security tests
* workflow tests

Target strong coverage of application logic.

---

## Milestone 9 — Packaging

Implement:

* PyInstaller configuration
* Windows build
* Linux build
* application metadata
* icons/placeholders
* release scripts

Do not bundle model weights.

---

## Milestone 10 — Documentation & Website

Complete:

* README
* documentation
* troubleshooting
* benchmarks
* privacy documentation
* static website
* contribution guide

---

# 41. ACCEPTANCE CRITERIA

Version 0.1 is complete only when:

### Installation

A new developer can install the application using documented instructions.

### Model

A user can select a GGUF model without copying it into the repository.

### Server

The application can start, monitor, and stop llama-server.

### Chat

The user can have a streamed conversation.

### Cancellation

The user can stop generation.

### Persistence

Closing/reopening the application preserves chats.

### Workflows

All curated workflows function.

### Context

Users can explicitly select source files.

### Security

Sensitive files are blocked by default.

### Privacy

No hidden telemetry or cloud inference exists.

### Stability

A failed model/server startup does not crash the application.

### Testing

CI passes without requiring a real GGUF model.

### Packaging

A release artifact can be generated reproducibly.

### Documentation

A new user can understand how to install and configure the application.

---

# 42. DEVELOPMENT RULES

Follow these rules throughout implementation:

1. Do not over-engineer.
2. Do not add features outside v0.1.
3. Do not create unnecessary abstractions.
4. Do not put business logic in UI classes.
5. Do not block the GUI thread.
6. Do not execute model output.
7. Do not silently upload files.
8. Do not automatically modify source files.
9. Do not commit model weights.
10. Do not fabricate benchmark results.
11. Do not fabricate test results.
12. Do not claim code was executed if it was not.
13. Do not claim a model response is correct merely because it was generated.
14. Prefer explicit user actions over automation.
15. Prefer understandable errors over raw stack traces.
16. Prefer local/offline behavior.
17. Prefer simple dependencies.
18. Document architectural decisions.
19. Write tests alongside important functionality.
20. Keep the application usable on ordinary laptops.

---

# 43. AI CODING AGENT RULES

If you are implementing this repository inside an existing workspace:

FIRST:

1. Inspect the repository.
2. Identify existing files.
3. Identify existing Python version.
4. Identify installed dependencies.
5. Identify existing tests.
6. Identify existing build configuration.
7. Do not overwrite existing work blindly.

Then:

1. Create/update the architecture.
2. Implement one milestone at a time.
3. Run tests after meaningful changes.
4. Run Ruff.
5. Run type checks where practical.
6. Fix failures before moving forward.
7. Keep changes small and reviewable.

Never generate hundreds of files without validating the architecture.

Never create fake implementations simply to satisfy the requested file tree.

If a feature cannot be implemented correctly yet, document the limitation rather than pretending it works.

---

# 44. REQUIRED OUTPUT FROM THE IMPLEMENTATION AGENT

At the beginning, produce:

1. Architecture rationale.
2. Final repository tree.
3. Component responsibilities.
4. Database schema.
5. LLM abstraction design.
6. llama-server lifecycle design.
7. UI screen map.
8. Workflow architecture.
9. Security model.
10. Milestone implementation plan.
11. Dependency plan.

Then begin implementation.

After every milestone report:

```text
Implemented
Changed files
Tests added
Tests executed
Test results
Known limitations
Next milestone
```

Never report tests as passing unless they were actually executed.

---

# 45. VERSION 0.2 — ROADMAP ONLY

Do NOT implement Version 0.2.

Possible future capabilities:

```text
project indexing
smarter project context
embeddings/RAG
Git read integration
diff-aware workflows
optional tool execution
controlled terminal
code patch generation
workspace-aware assistance
additional local models
model benchmarking UI
plugin architecture
```

Any future tool execution must have a substantially stronger security model and explicit user consent.

---

# 46. FINAL PRODUCT PRINCIPLE

The most important principle is:

> **Sarthika Code should be a reliable local coding tool, not a flashy AI demo.**

Prioritize:

```text
Reliability
Privacy
Clarity
Performance
Safety
Maintainability
Reproducibility
Documentation
```

over:

```text
feature count
autonomy
marketing claims
complexity
visual effects
experimental AI capabilities
```

Build Version 0.1 as a product that a real developer could install on an ordinary laptop and trust with local development work.

Do not implement beyond Version 0.1 unless explicitly instructed.
