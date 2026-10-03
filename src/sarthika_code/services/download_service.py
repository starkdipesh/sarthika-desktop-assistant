"""Model and engine download service for Sarthika Code.

Provides asynchronous/background downloading of recommended local GGUF models
and pre-built llama-server engine binaries with real-time progress, speed, ETA,
and automatic extraction without requiring external tools, git, or terminal commands.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import sys
import tarfile
import threading
import time
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from sarthika_code.app.paths import AppPaths
from sarthika_code.utils.logging import get_logger

logger = get_logger("DownloadService")


@dataclass(frozen=True)
class DownloadableModel:
    """Specification of a recommended downloadable GGUF model."""

    id: str
    name: str
    description: str
    parameters: str
    quantization: str
    size_bytes: int
    size_formatted: str
    recommended_ram: str
    download_url: str
    filename: str


@dataclass
class DownloadProgress:
    """Current state and metrics of an active download task."""

    downloaded_bytes: int = 0
    total_bytes: int = 0
    percent: float = 0.0
    speed_bytes_sec: float = 0.0
    eta_seconds: float = 0.0
    status: str = "idle"  # "connecting", "downloading", "extracting", "completed", "error", "cancelled"
    message: str = ""
    error: str | None = None


# Official verified Hugging Face direct download endpoints for recommended models
RECOMMENDED_MODELS: list[DownloadableModel] = [
    DownloadableModel(
        id="qwen-2.5-coder-1.5b",
        name="Qwen 2.5 Coder 1.5B (Fast / 8 GB RAM)",
        description="Lightweight and very fast. Recommended for 8 GB RAM laptops and low-context use.",
        parameters="1.54B",
        quantization="Q4_K_M",
        size_bytes=986_000_000,
        size_formatted="~986 MB",
        recommended_ram="8 GB RAM",
        download_url="https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        filename="qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
    ),
    DownloadableModel(
        id="qwen-2.5-coder-3b",
        name="Qwen 2.5 Coder 3B (Recommended Standard)",
        description="Excellent balance of coding capability, speed, and accuracy on ordinary CPUs.",
        parameters="3.09B",
        quantization="Q4_K_M",
        size_bytes=1_930_000_000,
        size_formatted="~1.93 GB",
        recommended_ram="16 GB RAM",
        download_url="https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/resolve/main/qwen2.5-coder-3b-instruct-q4_k_m.gguf",
        filename="qwen2.5-coder-3b-instruct-q4_k_m.gguf",
    ),
]

# llama.cpp stable release precompiled binaries
LLAMA_CPP_RELEASE_TAG = "b4776"
ENGINE_DOWNLOAD_URLS: dict[str, str] = {
    "win32": f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_CPP_RELEASE_TAG}/llama-{LLAMA_CPP_RELEASE_TAG}-bin-win-avx2-x64.zip",
    "linux": f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_CPP_RELEASE_TAG}/llama-{LLAMA_CPP_RELEASE_TAG}-bin-ubuntu-x64.zip",
}


class ModelDownloadService:
    """Manages downloading model weights and engine binaries in background threads."""

    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths
        self._cancel_events: dict[str, threading.Event] = {}

    def get_recommended_models(self) -> list[DownloadableModel]:
        """Return the list of curated models available for 1-click download."""
        return RECOMMENDED_MODELS

    def get_model_destination_path(self, model: DownloadableModel) -> Path:
        """Resolve the target disk path for a downloadable model."""
        self.paths.ensure_directories()
        return self.paths.models_dir / model.filename

    def is_model_downloaded(self, model: DownloadableModel) -> bool:
        """Check if the given model file already exists and is non-empty."""
        dest = self.get_model_destination_path(model)
        return dest.exists() and dest.is_file() and dest.stat().st_size > 10_000_000

    def get_engine_destination_path(self) -> Path:
        """Resolve the expected path to the local llama-server executable."""
        self.paths.ensure_directories()
        exec_name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
        standard_path = self.paths.bin_dir / exec_name
        if standard_path.exists() and standard_path.is_file():
            return standard_path

        # Check repository root bin directory
        root_bin = Path(__file__).resolve().parent.parent.parent.parent / "bin" / exec_name
        if root_bin.exists() and root_bin.is_file():
            return root_bin

        return standard_path

    def is_engine_available(self) -> bool:
        """Check if llama-server binary is present in bin_dir, repo bin, or system PATH."""
        dest = self.get_engine_destination_path()
        if dest.exists() and dest.is_file():
            if sys.platform != "win32" and not os.access(dest, os.X_OK):
                with contextlib.suppress(OSError):
                    dest.chmod(dest.stat().st_mode | 0o755)
            return True

        exec_name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
        return shutil.which(exec_name) is not None

    def cancel_download(self, task_id: str) -> None:
        """Signal an active download task to stop."""
        if task_id in self._cancel_events:
            self._cancel_events[task_id].set()
            logger.info("Cancellation requested for task '%s'", task_id)

    def download_model(
        self,
        model: DownloadableModel,
        on_progress: Callable[[DownloadProgress], None] | None = None,
        task_id: str = "model_download",
    ) -> Path:
        """Download a model file synchronously with chunked streaming and progress reporting.

        Usually invoked from a worker thread. Writes to a .part file before atomic rename.
        """
        dest_path = self.get_model_destination_path(model)
        temp_path = dest_path.with_suffix(dest_path.suffix + ".part")

        cancel_event = threading.Event()
        self._cancel_events[task_id] = cancel_event

        progress = DownloadProgress(
            total_bytes=model.size_bytes,
            status="connecting",
            message=f"Connecting to Hugging Face for {model.name}...",
        )
        if on_progress:
            on_progress(progress)

        try:
            with (
                httpx.Client(follow_redirects=True, timeout=httpx.Timeout(connect=30.0, read=60.0, write=60.0, pool=30.0)) as client,
                client.stream("GET", model.download_url) as response,
            ):
                if response.status_code != 200:
                    raise RuntimeError(f"Download failed with HTTP status {response.status_code}")

                total = int(response.headers.get("content-length", model.size_bytes))
                progress.total_bytes = total
                progress.status = "downloading"

                downloaded = 0
                start_time = time.monotonic()
                last_update = start_time

                self.paths.models_dir.mkdir(parents=True, exist_ok=True)
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=128 * 1024):
                        if cancel_event.is_set():
                            progress.status = "cancelled"
                            progress.message = "Download cancelled by user."
                            if on_progress:
                                on_progress(progress)
                            if temp_path.exists():
                                temp_path.unlink()
                            raise RuntimeError("Download cancelled by user.")

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            now = time.monotonic()
                            if now - last_update >= 0.25:  # Update UI every 250ms
                                elapsed = max(0.001, now - start_time)
                                speed = downloaded / elapsed
                                remaining_bytes = max(0, total - downloaded)
                                eta = remaining_bytes / max(1.0, speed)
                                percent = min(100.0, (downloaded / max(1, total)) * 100.0)

                                progress.downloaded_bytes = downloaded
                                progress.percent = percent
                                progress.speed_bytes_sec = speed
                                progress.eta_seconds = eta
                                progress.message = f"Downloading: {downloaded / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB ({percent:.1f}%)"
                                if on_progress:
                                    on_progress(progress)
                                last_update = now


            # Download finished, atomically replace final destination
            if temp_path.exists():
                temp_path.replace(dest_path)

            progress.downloaded_bytes = total
            progress.percent = 100.0
            progress.status = "completed"
            progress.message = f"{model.name} downloaded successfully!"
            if on_progress:
                on_progress(progress)

            logger.info("Successfully downloaded model %s to %s", model.id, dest_path)
            return dest_path

        except Exception as exc:
            if not cancel_event.is_set():
                progress.status = "error"
                progress.error = str(exc)
                progress.message = f"Download error: {exc}"
                if on_progress:
                    on_progress(progress)
            if temp_path.exists():
                with contextlib_suppress():
                    temp_path.unlink()
            raise
        finally:
            self._cancel_events.pop(task_id, None)

    def download_engine(
        self,
        on_progress: Callable[[DownloadProgress], None] | None = None,
        task_id: str = "engine_download",
    ) -> Path:
        """Download and unpack the prebuilt llama-server binary for the current platform."""
        platform_key = "win32" if sys.platform == "win32" else "linux"
        download_url = ENGINE_DOWNLOAD_URLS.get(platform_key)
        if not download_url:
            raise RuntimeError(f"No prebuilt llama-server binary configured for platform: {sys.platform}")

        dest_binary = self.get_engine_destination_path()
        archive_name = "llama_archive.zip"
        archive_path = self.paths.bin_dir / archive_name

        cancel_event = threading.Event()
        self._cancel_events[task_id] = cancel_event

        progress = DownloadProgress(
            status="connecting",
            message="Connecting to download local inference engine...",
        )
        if on_progress:
            on_progress(progress)

        try:
            self.paths.bin_dir.mkdir(parents=True, exist_ok=True)
            with (
                httpx.Client(follow_redirects=True, timeout=httpx.Timeout(connect=30.0, read=60.0, write=60.0, pool=30.0)) as client,
                client.stream("GET", download_url) as response,
            ):
                if response.status_code != 200:
                    raise RuntimeError(f"Engine download failed with HTTP status {response.status_code}")

                total = int(response.headers.get("content-length", 50 * 1024 * 1024))
                progress.total_bytes = total
                progress.status = "downloading"

                downloaded = 0
                start_time = time.monotonic()
                last_update = start_time

                with open(archive_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=128 * 1024):
                        if cancel_event.is_set():
                            progress.status = "cancelled"
                            if on_progress:
                                on_progress(progress)
                            if archive_path.exists():
                                archive_path.unlink()
                            raise RuntimeError("Download cancelled by user.")

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            now = time.monotonic()
                            if now - last_update >= 0.25:
                                elapsed = max(0.001, now - start_time)
                                speed = downloaded / elapsed
                                percent = min(100.0, (downloaded / max(1, total)) * 100.0)
                                progress.downloaded_bytes = downloaded
                                progress.percent = percent
                                progress.speed_bytes_sec = speed
                                progress.message = f"Downloading AI engine: {downloaded / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB"
                                if on_progress:
                                    on_progress(progress)
                                last_update = now

            # Extract archive (deliver complete engine folder including runtime shared libraries)
            progress.status = "extracting"
            progress.message = "Extracting inference engine and runtime shared libraries..."
            if on_progress:
                on_progress(progress)

            target_binary_name = "llama-server.exe" if platform_key == "win32" else "llama-server"
            extracted_count = 0

            if zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    for member in zip_ref.infolist():
                        if member.is_dir():
                            continue
                        fname = os.path.basename(member.filename)
                        if not fname:
                            continue
                        out_target = self.paths.bin_dir / fname
                        with zip_ref.open(member) as source, open(out_target, "wb") as target:
                            shutil.copyfileobj(source, target)
                        extracted_count += 1
            else:
                with tarfile.open(archive_path, "r:*") as tar_ref:
                    for member in tar_ref.getmembers():
                        if not member.isfile():
                            continue
                        fname = os.path.basename(member.name)
                        if not fname:
                            continue
                        extracted_file = tar_ref.extractfile(member)
                        if extracted_file:
                            out_target = self.paths.bin_dir / fname
                            with open(out_target, "wb") as target:
                                shutil.copyfileobj(extracted_file, target)
                            extracted_count += 1

            if archive_path.exists():
                archive_path.unlink()

            if not dest_binary.exists():
                raise RuntimeError("Extracted archive did not contain llama-server binary.")

            if sys.platform != "win32":
                for item in self.paths.bin_dir.iterdir():
                    if item.is_file():
                        with contextlib.suppress(OSError):
                            item.chmod(item.stat().st_mode | 0o755)

            progress.status = "completed"
            progress.message = "AI Engine setup completed!"
            if on_progress:
                on_progress(progress)

            logger.info("Successfully extracted complete engine suite (%d files) to %s", extracted_count, self.paths.bin_dir)
            return dest_binary

        except Exception as exc:
            if archive_path.exists():
                with contextlib_suppress():
                    archive_path.unlink()
            if not cancel_event.is_set():
                progress.status = "error"
                progress.error = str(exc)
                progress.message = f"Engine setup error: {exc}"
                if on_progress:
                    on_progress(progress)
            raise
        finally:
            self._cancel_events.pop(task_id, None)


def contextlib_suppress():
    """Helper context manager to ignore OSError during file cleanup."""
    import contextlib
    return contextlib.suppress(OSError)
