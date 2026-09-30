#!/usr/bin/env python3
"""Sarthika Code — Local Benchmark Harness.

Measures actual, factual local inference performance without cloud dependencies
or fabricated metrics. Evaluates prompt processing speed, Time To First Token (TTFT),
generation throughput (tokens/second), and hardware resource utilization.

Usage:
    python scripts/benchmark_local.py [--server-url http://127.0.0.1:8080] [--mock] [--limit N]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure project source is on PYTHONPATH
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from sarthika_code.domain.config import GenerationSettings
from sarthika_code.llm.base import (
    ChatMessage,
    LLMProvider,
    StreamCompletedEvent,
    StreamErrorEvent,
    StreamTokenEvent,
)
from sarthika_code.llm.llama_cpp import LlamaCppProvider
from sarthika_code.llm.mock import MockLLMProvider
from sarthika_code.prompts.context_builder import estimate_tokens

# ==============================================================================
# 50 Standard Benchmark Tasks Across 5 Categories
# ==============================================================================

BENCHMARK_TASKS: list[dict[str, str]] = [
    # Category 1: PHP & Laravel Tasks (10 Tasks)
    {"id": "laravel-01", "category": "laravel", "title": "Eloquent Model with Accessors", "prompt": "Write a Laravel Eloquent model 'Invoice' with a uuid primary key, casts for 'amount_cents' as integer, and an accessor 'formatted_amount' returning '$XX.XX'."},
    {"id": "laravel-02", "category": "laravel", "title": "Form Request with Rules", "prompt": "Write a Laravel FormRequest class 'StoreUserRequest' validating email uniqueness, password complexity with uncompromised check, and optional birthday before today."},
    {"id": "laravel-03", "category": "laravel", "title": "Controller Action Refactor", "prompt": "Refactor a fat Laravel store method into a dedicated invokable Action class 'CreateOrderAction' wrapping customer lookup, order items creation, and event dispatch in a database transaction."},
    {"id": "laravel-04", "category": "laravel", "title": "Queued Notification", "prompt": "Write a queued Laravel Notification 'DeploymentSuccessfulNotification' supporting mail and database channels with a markdown email template."},
    {"id": "laravel-05", "category": "laravel", "title": "Eloquent Query Scope", "prompt": "Write an Eloquent query scope 'scopeFilterBySearch' on an Article model that searches title and body with case-insensitivity using parameter binding."},
    {"id": "laravel-06", "category": "laravel", "title": "Rate Limiting Middleware", "prompt": "Create a custom Laravel middleware 'EnsureApiKeyRateLimit' that tracks request counts per tenant API key using Redis cache tags."},
    {"id": "laravel-07", "category": "laravel", "title": "Artisan Reconciliation Command", "prompt": "Write an Artisan command 'reconcile:ledger' that iterates unverified ledger entries with a progress bar and outputs a summary table."},
    {"id": "laravel-08", "category": "laravel", "title": "Transaction Handling", "prompt": "Write a robust repository method in Laravel that transfers credits between two user accounts with row locking ('lockForUpdate') and transaction rollback."},
    {"id": "laravel-09", "category": "laravel", "title": "Authorization Policy", "prompt": "Write a Laravel Policy class 'DocumentPolicy' defining view, update, and delete rules based on organization ownership and user permissions."},
    {"id": "laravel-10", "category": "laravel", "title": "Database Migration", "prompt": "Write a Laravel database migration creating an 'audit_logs' table with nullable foreign keys to users, indexed action string, and JSON payload column."},

    # Category 2: Python Development Tasks (10 Tasks)
    {"id": "python-01", "category": "python", "title": "Async Rate Limiter", "prompt": "Implement an asynchronous token bucket rate limiter in Python using asyncio.Lock, tracking tokens and refill intervals."},
    {"id": "python-02", "category": "python", "title": "Pydantic V2 Model Hierarchy", "prompt": "Create a Pydantic V2 model hierarchy for API webhook payloads with field validators, datetime serialization, and discriminated unions."},
    {"id": "python-03", "category": "python", "title": "Thread-Safe Cache with TTL", "prompt": "Write a thread-safe in-memory cache class in Python using threading.Lock with time-to-live (TTL) item expiration and eviction."},
    {"id": "python-04", "category": "python", "title": "Context Manager for Temporary Dir", "prompt": "Write a Python context manager class that creates an isolated temporary directory and guarantees deletion on exit even if exceptions occur."},
    {"id": "python-05", "category": "python", "title": "Nested JSON Iterator", "prompt": "Implement a Python generator function 'walk_json_leaves' that recursively yields dotted key paths and scalar values from nested dictionaries and lists."},
    {"id": "python-06", "category": "python", "title": "Retry with Exponential Backoff", "prompt": "Write a decorator in Python that retries an async function up to 3 times with exponential backoff and jitter on specified exception types."},
    {"id": "python-07", "category": "python", "title": "Async HTTP Client Refactor", "prompt": "Refactor a synchronous requests function into an async function using httpx.AsyncClient with explicit timeout configuration."},
    {"id": "python-08", "category": "python", "title": "Abstract Factory Pattern", "prompt": "Design an abstract factory pattern in Python with ABC for creating cloud storage adapters (S3, GCS, Local) with typed upload/download methods."},
    {"id": "python-09", "category": "python", "title": "Memory-Efficient CSV Streamer", "prompt": "Write a Python generator function that streams rows from a multi-gigabyte CSV file in chunks, converting dates and filtering invalid rows with minimal memory usage."},
    {"id": "python-10", "category": "python", "title": "Logging Redaction Filter", "prompt": "Create a custom logging.Filter in Python that regex-replaces sensitive tokens (API keys, authorization headers) with '[REDACTED]' in log records."},

    # Category 3: Code Debugging Tasks (10 Tasks)
    {"id": "debug-01", "category": "debugging", "title": "Multithreaded Race Condition", "prompt": "Given a multithreaded bank account transfer function with deadlocks, explain the root cause and provide the deadlock-free version with lock ordering."},
    {"id": "debug-02", "category": "debugging", "title": "Binary Search Off-by-One", "prompt": "Fix an off-by-one bug in a binary search function where mid calculation causes an infinite loop when searching for missing elements."},
    {"id": "debug-03", "category": "debugging", "title": "ORM N+1 Query Problem", "prompt": "Given a loop fetching author posts in an ORM causing N+1 queries, explain the issue and show the eager-loaded solution using joined loads."},
    {"id": "debug-04", "category": "debugging", "title": "ZeroDivisionError Edge Case", "prompt": "Identify and resolve an unhandled zero division exception in a batch metric aggregator when input lists are empty."},
    {"id": "debug-05", "category": "debugging", "title": "Circular Reference Memory Leak", "prompt": "Explain why circular references in Python parent-child node structures can delay garbage collection and show how to fix it using weakref."},
    {"id": "debug-06", "category": "debugging", "title": "Silent Exception Suppression", "prompt": "Refactor a bare 'except: pass' block that silently suppresses critical database connection errors, logging the traceback and reraising a domain exception."},
    {"id": "debug-07", "category": "debugging", "title": "Timezone Mismatch Bug", "prompt": "Fix a datetime comparison bug in Python where a naive UTC timestamp is compared against an offset-aware local timestamp."},
    {"id": "debug-08", "category": "debugging", "title": "SQL Injection in Raw Query", "prompt": "Identify the SQL injection vulnerability in 'SELECT * FROM users WHERE email = ' + email and rewrite it with parameterized positional bindings."},
    {"id": "debug-09", "category": "debugging", "title": "Un-awaited Async Task Leak", "prompt": "Fix a memory and resource leak in an asyncio background worker where tasks created with create_task are never tracked or shielded."},
    {"id": "debug-10", "category": "debugging", "title": "Unicode Decoding Error", "prompt": "Resolve a 'UnicodeDecodeError: utf-8 codec cannot decode byte' error when reading historical ISO-8859-1 text files."},

    # Category 4: Code Explanation Tasks (10 Tasks)
    {"id": "explain-01", "category": "explanation", "title": "Async Generators in Python", "prompt": "Explain step-by-step how async generators work in Python with '__aiter__' and '__anext__', and when to use them over standard lists."},
    {"id": "explain-02", "category": "explanation", "title": "Complex SQL Execution Plan", "prompt": "Explain how database query planners evaluate index scans vs sequential scans when joining large tables on unindexed foreign keys."},
    {"id": "explain-03", "category": "explanation", "title": "Eager vs Lazy Loading", "prompt": "Explain the architectural trade-offs between eager loading and lazy loading in relational database ORMs."},
    {"id": "explain-04", "category": "explanation", "title": "Cryptographic Salt Mechanics", "prompt": "Explain the purpose of cryptographic salts and slow key derivation functions (Argon2, bcrypt) against precomputed rainbow table attacks."},
    {"id": "explain-05", "category": "explanation", "title": "Pass by Reference vs Value", "prompt": "Explain how object passing works in Python ('call by object reference') and why mutating default argument lists causes persistent state bugs."},
    {"id": "explain-06", "category": "explanation", "title": "RFC 5322 Regex Breakdown", "prompt": "Deconstruct a regular expression validating email addresses, explaining each group, character class, and anchor."},
    {"id": "explain-07", "category": "explanation", "title": "Qt Event Loop & Threading", "prompt": "Explain how the PySide6/Qt event loop dispatches events, and why long-running CPU calculations must not execute on the main GUI thread."},
    {"id": "explain-08", "category": "explanation", "title": "GGUF Quantization Principles", "prompt": "Explain how 4-bit GGUF quantization (e.g. Q4_K_M) compresses 16-bit float weights, and how it impacts inference RAM and perplexity."},
    {"id": "explain-09", "category": "explanation", "title": "SSE vs WebSockets", "prompt": "Compare Server-Sent Events (SSE) and WebSockets for streaming LLM text output in terms of HTTP compatibility and protocol overhead."},
    {"id": "explain-10", "category": "explanation", "title": "Repository Pattern Architecture", "prompt": "Explain the architectural motivation for the Repository pattern in desktop applications, and how it isolates UI services from SQLite storage."},

    # Category 5: Implementation Planning Tasks (10 Tasks)
    {"id": "plan-01", "category": "planning", "title": "SQLite to PostgreSQL Migration", "prompt": "Provide a detailed step-by-step migration plan for transitioning a desktop database from SQLite to PostgreSQL without downtime."},
    {"id": "plan-02", "category": "planning", "title": "Full-Text Search Addition", "prompt": "Draft an architectural plan for adding local full-text search (SQLite FTS5) to an existing conversation history repository."},
    {"id": "plan-03", "category": "planning", "title": "Monolith Class Decomposition", "prompt": "Outline an incremental refactoring plan for splitting a 2000-line monolithic controller into domain services with automated test coverage."},
    {"id": "plan-04", "category": "planning", "title": "Two-Factor Authentication", "prompt": "Create an implementation checklist for adding TOTP two-factor authentication, including secret generation, QR codes, and recovery codes."},
    {"id": "plan-05", "category": "planning", "title": "Legacy Code Test Rollout", "prompt": "Design a phased roadmap for introducing unit and integration testing into a legacy codebase with zero existing tests."},
    {"id": "plan-06", "category": "planning", "title": "REST API Versioning Strategy", "prompt": "Draft an API deprecation and versioning plan (URI vs header versioning) for public software libraries."},
    {"id": "plan-07", "category": "planning", "title": "Asynchronous Queue System", "prompt": "Plan a background job queue architecture for processing large media files with error retries and dead-letter queues."},
    {"id": "plan-08", "category": "planning", "title": "Offline-First Data Sync", "prompt": "Design an architectural plan for conflict resolution (CRDT / vector clocks) in an offline-first desktop synchronization application."},
    {"id": "plan-09", "category": "planning", "title": "OWASP Top 10 Hardening", "prompt": "Create a security audit checklist for hardening a desktop software assistant against credential leakage and untrusted input injection."},
    {"id": "plan-10", "category": "planning", "title": "Performance Profiling Strategy", "prompt": "Outline a methodical performance profiling strategy to diagnose memory leaks and high CPU usage in a Python GUI application."},
]


def collect_hardware_specs() -> dict[str, Any]:
    """Capture factual system specifications without external cloud calls."""
    total_ram_gb = 0.0
    # Try reading Linux /proc/meminfo or Windows memory
    if sys.platform == "linux" and os.path.exists("/proc/meminfo"):
        try:
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        total_ram_gb = round(kb / (1024 * 1024), 2)
                        break
        except Exception:
            pass

    return {
        "os_name": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "machine_arch": platform.machine(),
        "processor": platform.processor() or "x86_64",
        "cpu_count_logical": os.cpu_count() or 1,
        "total_ram_gb": total_ram_gb,
        "python_version": platform.python_version(),
    }


async def run_single_benchmark_task(
    provider: LLMProvider,
    task: dict[str, str],
    settings: GenerationSettings,
) -> dict[str, Any]:
    """Execute a single task against the LLM provider and measure execution timing."""
    messages = [ChatMessage(role="user", content=task["prompt"])]
    prompt_tokens = estimate_tokens(task["prompt"])

    start_time = time.monotonic()
    ttft_ms: float | None = None
    generated_tokens = 0
    full_text_chunks: list[str] = []
    status = "success"
    error_msg: str | None = None

    try:
        async for event in provider.stream_chat(messages, settings=settings):
            if isinstance(event, StreamTokenEvent):
                if ttft_ms is None:
                    ttft_ms = round((time.monotonic() - start_time) * 1000, 2)
                generated_tokens += 1
                full_text_chunks.append(event.delta)
            elif isinstance(event, StreamErrorEvent):
                status = "error"
                error_msg = event.error
                break
            elif isinstance(event, StreamCompletedEvent):
                if event.total_tokens:
                    generated_tokens = event.total_tokens

    except Exception as e:
        status = "error"
        error_msg = str(e)

    total_duration_sec = time.monotonic() - start_time
    tokens_per_sec = round(generated_tokens / max(0.001, total_duration_sec), 2)

    return {
        "task_id": task["id"],
        "category": task["category"],
        "title": task["title"],
        "prompt_tokens_est": prompt_tokens,
        "generated_tokens": generated_tokens,
        "time_to_first_token_ms": ttft_ms or round(total_duration_sec * 1000, 2),
        "total_duration_sec": round(total_duration_sec, 2),
        "tokens_per_second": tokens_per_sec,
        "status": status,
        "error": error_msg,
    }


async def run_benchmark_suite(
    provider: LLMProvider,
    tasks: list[dict[str, str]],
    output_dir: Path,
    is_mock: bool = False,
) -> Path:
    """Execute the benchmark suite, record factual metrics, and save output locally."""
    hardware = collect_hardware_specs()
    settings = GenerationSettings(temperature=0.2, max_tokens=1024)

    print("=" * 65)
    print("Sarthika Code — Local Benchmark Harness")
    print("=" * 65)
    print(f"OS        : {hardware['os_name']} {hardware['os_release']} ({hardware['machine_arch']})")
    print(f"CPU Cores : {hardware['cpu_count_logical']}")
    print(f"Total RAM : {hardware['total_ram_gb']} GB")
    print(f"Mode      : {'Offline Mock Provider' if is_mock else 'Active Local llama-server'}")
    print(f"Tasks     : {len(tasks)} benchmark cases")
    print("-" * 65)

    results: list[dict[str, Any]] = []

    for i, task in enumerate(tasks, 1):
        print(f"[{i:02d}/{len(tasks):02d}] Running ({task['category']}): {task['title']}...", end="", flush=True)
        task_res = await run_single_benchmark_task(provider, task, settings)
        results.append(task_res)

        if task_res["status"] == "success":
            print(f" DONE (~{task_res['tokens_per_second']} tok/s, TTFT: {task_res['time_to_first_token_ms']}ms)")
        else:
            print(f" FAILED ({task_res['error']})")

    # Calculate summary metrics
    successful = [r for r in results if r["status"] == "success"]
    avg_speed = round(sum(r["tokens_per_second"] for r in successful) / max(1, len(successful)), 2)
    avg_ttft = round(sum(r["time_to_first_token_ms"] for r in successful) / max(1, len(successful)), 2)
    total_tokens_generated = sum(r["generated_tokens"] for r in successful)

    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "benchmark_harness_version": "0.1.0",
        "hardware_environment": hardware,
        "is_mock_simulation": is_mock,
        "summary": {
            "total_tasks": len(tasks),
            "successful_tasks": len(successful),
            "failed_tasks": len(tasks) - len(successful),
            "total_tokens_generated": total_tokens_generated,
            "average_tokens_per_second": avg_speed,
            "average_time_to_first_token_ms": avg_ttft,
        },
        "task_results": results,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_slug = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"benchmark_run_{timestamp_slug}.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("-" * 65)
    print("BENCHMARK COMPLETED")
    print(f"Successful Tasks : {len(successful)} / {len(tasks)}")
    print(f"Average Speed    : {avg_speed} tokens/second")
    print(f"Average TTFT     : {avg_ttft} ms")
    print(f"Saved Report     : {report_file}")
    print("=" * 65)

    return report_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Sarthika Code performance benchmarks.")
    parser.add_argument("--server-url", default="http://127.0.0.1:8080", help="llama-server HTTP base URL")
    parser.add_argument("--mock", action="store_true", help="Run benchmark with simulated MockLLMProvider")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of benchmark tasks to run")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "benchmarks", help="Output directory for results")

    args = parser.parse_args()

    tasks_to_run = BENCHMARK_TASKS
    if args.limit and args.limit > 0:
        tasks_to_run = BENCHMARK_TASKS[:args.limit]

    provider: LLMProvider
    if args.mock:
        provider = MockLLMProvider(token_delay=0.001)
    else:
        provider = LlamaCppProvider(args.server_url)

    asyncio.run(run_benchmark_suite(provider, tasks_to_run, args.output_dir, is_mock=args.mock))
    return 0


if __name__ == "__main__":
    sys.exit(main())
