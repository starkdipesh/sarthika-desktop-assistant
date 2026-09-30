# Sarthika Code — Local Benchmark Output Directory

This directory stores local, user-generated benchmark reports produced by `scripts/benchmark_local.py`.

## Privacy Guarantee
Benchmark results are stored **strictly on your local disk** in JSON format (`benchmark_run_<timestamp>.json`). Sarthika Code **never transmits benchmark data to any external server or telemetry service**.

## Schema of Benchmark Reports
Each JSON report records:
- `timestamp_utc`: ISO 8601 execution timestamp.
- `hardware_environment`: Operating system, CPU architecture, logical core count, total RAM.
- `summary`: Total tasks run, success rate, average throughput (tokens/second), average Time to First Token (TTFT).
- `task_results`: Per-task execution timings, token counts, and completion status.
