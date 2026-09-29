# Sarthika Code — Local Benchmark Methodology & Dataset

To guarantee product honesty and prevent fabricated claims, Sarthika Code defines a reproducible, transparent benchmarking harness (`scripts/benchmark_local.py`).

---

## 1. Benchmark Principles

1. **No Fabricated Benchmarks**: All reported benchmark results must reflect actual execution data measured on real hardware.
2. **Standardized Quantization**: Standard benchmarks evaluate **Qwen2.5-Coder 3B Instruct** at `Q4_K_M` precision.
3. **Reproducibility**: Anyone can execute `python scripts/benchmark_local.py` to test their local CPU and record actual performance metrics.

---

## 2. Metrics Captured

Every benchmark run records:
* **Operating System**: OS distribution, kernel version, architecture.
* **CPU Specifications**: CPU brand, model, physical core count, logical thread count.
* **Total & Available RAM**: Measured at start and peak memory during generation.
* **Model Parameters**: Filename, size in bytes, quantization format (`Q4_K_M`).
* **Context Size**: Evaluated at 2048, 4096, and 8192 tokens.
* **Prompt Processing Speed**: Prompt ingestion rate (tokens/second) and Time to First Token (TTFT) in milliseconds.
* **Generation Throughput**: Generation speed (tokens/second) and total generated tokens.
* **Memory Pressure**: Peak resident memory usage (RSS) of `llama-server`.

---

## 3. Standard 50-Task Benchmark Dataset

The evaluation suite consists of 50 deterministic software engineering tasks across 5 categories:

### Category 1: PHP & Laravel Tasks (10 Tasks)
1. Generate a Laravel Eloquent relationship model with custom accessor and casts.
2. Draft a Form Request validation class with complex conditional rules.
3. Refactor a fat controller method into a dedicated action service class.
4. Implement a queued Laravel notification with database and email channels.
5. Create an Eloquent query scope for multi-column search filtering.
6. Design a custom middleware for rate-limiting specific route patterns.
7. Write an Artisan CLI command for data reconciliation with progress bars.
8. Refactor nested database transactions using `DB::transaction()` closures.
9. Implement a Laravel policy class for role-based authorization.
10. Draft a database migration for an audit log table with foreign key constraints.

### Category 2: Python Development Tasks (10 Tasks)
11. Implement an asynchronous rate-limiter using `asyncio.Semaphore` and token bucket.
12. Write a Pydantic V2 model hierarchy with custom field validators and serializers.
13. Implement a thread-safe singleton cache manager with TTL expiration.
14. Create a context manager for temporary directory isolation and cleanup.
15. Write a custom iterator class traversing a nested JSON structure.
16. Implement retry logic with exponential backoff and jitter.
17. Refactor a synchronous HTTP client function to use `httpx.AsyncClient`.
18. Design a typed abstract factory pattern for data source connectors.
19. Implement a memory-efficient generator for parsing multi-gigabyte CSV logs.
20. Create a custom logging filter that redacts email addresses and API keys.

### Category 3: Code Debugging Tasks (10 Tasks)
21. Identify and fix a race condition in a multithreaded bank account transfer simulation.
22. Debug an off-by-one error causing index exceptions in a binary search function.
23. Resolve an N+1 query problem in a simulated ORM data loader.
24. Fix an unhandled edge case causing zero-division error in average calculation.
25. Identify a memory leak caused by circular references in a custom graph data structure.
26. Debug a silent exception suppression issue in a nested try/except block.
27. Resolve a timezone mismatch bug when comparing UTC and localized timestamps.
28. Fix a SQL injection vulnerability in a dynamic raw query string.
29. Debug an async task cancellation leak where background tasks were not awaited.
30. Resolve a Unicode encoding error when parsing foreign language text streams.

### Category 4: Code Explanation Tasks (10 Tasks)
31. Explain the operational mechanics of an async generator in Python.
32. Explain the execution plan and bottleneck of a complex SQL query with multiple JOINs.
33. Explain the difference between eager loading and lazy loading in Eloquent/SQLAlchemy.
34. Walk through the step-by-step logic of a custom cryptographic hashing routine.
35. Explain memory implications of passing large data by reference vs. value.
36. Break down a complex regular expression validating RFC 5322 email addresses.
37. Explain the concurrency model of the Qt event loop and signals/slots across threads.
38. Explain how GGUF quantization reduces memory footprint while preserving perplexity.
39. Explain how HTTP Server-Sent Events (SSE) differ from WebSockets.
40. Explain the architectural advantages of the repository pattern in enterprise applications.

### Category 5: Implementation Planning Tasks (10 Tasks)
41. Outline a step-by-step plan for migrating an existing SQLite database to PostgreSQL.
42. Draft an implementation plan for adding full-text search to a legacy codebase.
43. Create a step-by-step refactoring strategy for decomposing a 2000-line monolith class.
44. Design an implementation plan for adding two-factor authentication (TOTP).
45. Outline a rollout plan for introducing automated unit tests to untested code.
46. Create an API versioning strategy and deprecation plan for REST endpoints.
47. Plan an asynchronous queue processing system for heavy file conversions.
48. Design an architecture plan for offline-first data caching and sync.
49. Draft an implementation checklist for hardening an application against OWASP Top 10.
50. Outline a performance profiling and query optimization plan for slow endpoints.
