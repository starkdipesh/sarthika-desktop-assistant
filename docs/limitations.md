# Sarthika Code — Product Realities & Limitations

Sarthika Code is an open, private engineering tool designed to be honest about its capabilities, hardware constraints, and the limitations of small-scale local language models.

---

## 1. Product Honesty & Non-AGI Reality

* **Not Artificial General Intelligence (AGI)**: Sarthika Code is a desktop assistant interface paired with a quantized local language model. It does not possess reasoning, understanding, consciousness, or human-level problem-solving ability.
* **Not an Autonomous Software Engineer**: Sarthika Code cannot independently architect applications, write entire enterprise systems from scratch, or verify the correctness of its output.
* **Output Requires Verification**: Local language models are prone to hallucinating non-existent APIs, omitting edge cases, and generating code with syntax, logic, or security bugs. **Always review, test, and validate generated code before executing it or committing it to version control.**
* **Never Claims Tests Passed**: Sarthika Code has no runtime execution environment. Any claim in generated text stating that code was tested or tests passed is simulated model output and must not be taken as factual.

---

## 2. Hardware & Inference Constraints

* **CPU-Bound Performance**: On laptops without a dedicated GPU, inference speed is bounded by CPU clock speed, core count, and memory bandwidth. Token generation speeds typically range between 5 and 15 tokens per second for 3B parameter models.
* **8 GB RAM Best-Effort Mode**:
  * Running an OS, browser, IDE, and a local 3B model concurrently on an 8 GB system places heavy pressure on memory.
  * In 8 GB mode, context size is capped at 2048 tokens to minimize memory footprint. Users should close memory-intensive applications when running inference.
* **Context Window Trade-offs**:
  * Increasing context size (e.g. from 4096 to 8192 or 16384) significantly increases the memory required for the KV-cache and drastically slows down prompt ingestion ("time to first token") on CPU.
* **Single Model Limitation**: Sarthika Code loads exactly one model at a time into memory to prevent system crashes and excessive paging.

---

## 3. Version 0.1 Scope Boundaries

Sarthika Code v0.1 does **not** include:
1. **Web Browsing or Online Retrieval**: Cannot fetch up-to-date documentation or search the web.
2. **Embeddings or RAG**: Cannot automatically search across an entire multi-thousand-file codebase.
3. **Command Execution**: Will never run shell scripts, compilers, or build tools.
4. **File Mutation**: Will never write changes back to your source files.
5. **Git Operations**: Will never inspect Git history, create branches, or make commits.
