"""Extract text from PDF using MinerU API.

Usage:
    python mineru_extract.py <pdf_path> --output ./output_dir [--mode auto|pipeline|vlm] [--language auto|ch|en]

Output:
    <output>/full.md           — complete Markdown (formulas in LaTeX, tables as HTML)
    <output>/content_list.json — structured content blocks
    <output>/images/           — extracted embedded images
    <output>/layout.json       — layout analysis results
"""

import argparse
import gc
import json
import os
import re
import sys
import threading
import time
import zipfile

import psutil
import requests

API_BASE = "https://mineru.net/api/v4"


class DebugLogger:
    """Diagnostic logger for memory and system monitoring."""

    def __init__(self, output_dir, enabled=False):
        self.enabled = enabled
        self.log_path = os.path.join(output_dir, "debug.log") if output_dir else None
        self._lock = threading.Lock()
        self._monitoring = False
        self._monitor_thread = None
        self._start_time = time.time()
        self._last_available_gb = None

        if enabled and output_dir:
            os.makedirs(output_dir, exist_ok=True)
            self._write_log("LOGGER_INIT", "Debug logging enabled")
            self._log_system_info()

    def _write_log(self, tag, message):
        """Write a single log line with timestamp. Flush immediately."""
        if not self.enabled or not self.log_path:
            return
        elapsed = time.time() - self._start_time
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        ms = int((time.time() % 1) * 1000)
        line = f"[{timestamp}.{ms:03d}] [{elapsed:8.2f}s] [{tag:20s}] {message}\n"
        with self._lock:
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(line)
                    f.flush()
                    os.fsync(f.fileno())
            except Exception:
                pass  # Don't let logging errors crash the script

    def _log_system_info(self):
        """Log system-level information at startup."""
        vm = psutil.virtual_memory()
        self._write_log("SYSTEM_INFO", f"Total RAM: {vm.total / 1024**3:.2f} GB")
        self._write_log("SYSTEM_INFO", f"Available RAM: {vm.available / 1024**3:.2f} GB")
        self._write_log("SYSTEM_INFO", f"Used RAM: {vm.used / 1024**3:.2f} GB")
        self._write_log("SYSTEM_INFO", f"RAM percent: {vm.percent}%")
        try:
            disk_root = os.path.splitdrive(os.path.abspath(self.log_path))[0]
            disk_path = disk_root + "\\" if disk_root else "/"
            disk = psutil.disk_usage(disk_path)
            self._write_log("SYSTEM_INFO", f"Disk free: {disk.free / 1024**3:.2f} GB")
        except Exception:
            pass
        proc = psutil.Process(os.getpid())
        mem_info = proc.memory_info()
        self._write_log("SYSTEM_INFO", f"Python process RSS: {mem_info.rss / 1024**2:.1f} MB")
        self._write_log("SYSTEM_INFO", f"Python process VMS: {mem_info.vms / 1024**2:.1f} MB")

    def snapshot(self, tag, extra=""):
        """Take a memory snapshot and log it."""
        if not self.enabled:
            return
        vm = psutil.virtual_memory()
        proc = psutil.Process(os.getpid())
        mem_info = proc.memory_info()
        available_gb = vm.available / 1024**3

        # Detect rapid memory drop
        warning = ""
        if self._last_available_gb is not None:
            delta = self._last_available_gb - available_gb
            if delta > 0.5:
                warning = f" [WARN: dropped {delta:.2f}GB in one step]"
            elif delta > 0.1:
                warning = f" [NOTE: dropped {delta:.2f}GB]"
        self._last_available_gb = available_gb

        if available_gb < 2.0:
            warning += f" [CRITICAL: <2GB free!]"

        self._write_log(tag,
            f"System: {available_gb:.2f}GB free / {vm.total / 1024**3:.2f}GB total "
            f"({vm.percent}% used) | "
            f"Process: RSS={mem_info.rss / 1024**2:.1f}MB, VMS={mem_info.vms / 1024**2:.1f}MB"
            f"{warning}"
            + (f" | {extra}" if extra else "")
        )

    def log_step_start(self, step_name, extra=""):
        """Log the start of a major step."""
        self.snapshot(f"STEP_START:{step_name}", extra)

    def log_step_end(self, step_name, duration=None, extra=""):
        """Log the end of a major step."""
        dur_str = f" ({duration:.2f}s)" if duration is not None else ""
        self.snapshot(f"STEP_END:{step_name}{dur_str}", extra)

    def log_event(self, tag, message):
        """Log a custom event."""
        self._write_log(tag, message)

    def log_directory_contents(self, dir_path, tag="DIR_CONTENTS"):
        """Log the contents of a directory (file count, total size)."""
        if not self.enabled:
            return
        total_size = 0
        file_count = 0
        try:
            for root, dirs, files in os.walk(dir_path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total_size += os.path.getsize(fp)
                        file_count += 1
                    except Exception:
                        pass
        except Exception:
            pass
        self._write_log(tag,
            f"Directory: {dir_path} | {file_count} files, {total_size / 1024**2:.2f} MB total")

    def log_top_processes(self, n=10, tag="TOP_PROCESSES"):
        """Log top N processes by memory usage."""
        if not self.enabled:
            return
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = p.info
                rss = info["memory_info"].rss if info["memory_info"] else 0
                procs.append((info["pid"], info["name"], rss))
            except Exception:
                pass
        procs.sort(key=lambda x: x[2], reverse=True)
        self._write_log(tag, f"Top {n} processes by RSS:")
        for pid, name, rss in procs[:n]:
            self._write_log(tag, f"  PID {pid:6d} | {name:30s} | {rss / 1024**2:.1f} MB")

    def _get_all_processes_rss(self):
        """Get RSS for all running processes. Returns dict: {pid: (name, rss_bytes)}."""
        procs = {}
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = p.info
                rss = info["memory_info"].rss if info["memory_info"] else 0
                procs[info["pid"]] = (info["name"], rss)
            except Exception:
                pass
        return procs

    def _log_memory_growths(self, baseline, current, top_n=10):
        """Compare current process memory with baseline and log top growers."""
        growers = []
        for pid, (name, rss_now) in current.items():
            if pid in baseline:
                _, rss_base = baseline[pid]
                delta = rss_now - rss_base
                if delta > 50 * 1024 * 1024:  # > 50MB growth
                    growers.append((pid, name, rss_base, rss_now, delta))

        growers.sort(key=lambda x: x[4], reverse=True)

        if not growers:
            self._write_log("MEMORY_GROWTH", "No significant process memory growth detected")
            return

        self._write_log("MEMORY_GROWTH",
            f"Top {min(top_n, len(growers))} memory growers since t=0:")
        for pid, name, rss_base, rss_now, delta in growers[:top_n]:
            level = ("CRITICAL" if delta > 200 * 1024 * 1024
                     else "WARN" if delta > 100 * 1024 * 1024 else "")
            tag = f"MEMORY_GROWTH:{level}" if level else "MEMORY_GROWTH"
            self._write_log(tag,
                f"  PID {pid:6d} | {name:30s} | "
                f"{rss_base / 1024**2:.1f}MB -> {rss_now / 1024**2:.1f}MB "
                f"(+{delta / 1024**2:.1f}MB)")

    def start_post_completion_monitoring(self, duration=30, interval=1,
                                         growth_check_interval=5):
        """Start background monitoring after script completion.

        Args:
            duration: total monitoring time in seconds
            interval: base interval for system memory checks (seconds)
            growth_check_interval: interval for per-process memory growth checks (seconds)
        """
        if not self.enabled:
            return

        self._monitoring = True
        self._write_log("POST_COMPLETE",
            f"Monitoring started: {duration}s duration, {interval}s interval, "
            f"growth check every {growth_check_interval}s")

        baseline_procs = self._get_all_processes_rss()
        self._write_log("POST_COMPLETE",
            f"Baseline: {len(baseline_procs)} processes captured")

        def _monitor():
            for i in range(duration):
                if not self._monitoring:
                    break
                time.sleep(interval)
                vm = psutil.virtual_memory()
                available_gb = vm.available / 1024**3
                proc = psutil.Process(os.getpid())
                mem_info = proc.memory_info()

                warning = ""
                if self._last_available_gb is not None:
                    delta = self._last_available_gb - available_gb
                    if delta > 0.5:
                        warning = f" [WARN: dropped {delta:.2f}GB in {interval}s]"
                    elif delta > 0.1:
                        warning = f" [NOTE: dropped {delta:.2f}GB]"
                self._last_available_gb = available_gb

                if available_gb < 4.0:
                    warning += " [CRITICAL: <4GB free!]"
                elif available_gb < 2.0:
                    warning += " [CRITICAL: <2GB free!]"

                self._write_log("POST_COMPLETE",
                    f"t={i + 1:2d}s: {available_gb:.2f}GB free | "
                    f"Process RSS={mem_info.rss / 1024**2:.1f}MB"
                    f"{warning}")

                if (i + 1) % growth_check_interval == 0:
                    current_procs = self._get_all_processes_rss()
                    self._log_memory_growths(baseline_procs, current_procs)
                    top_procs = sorted(
                        [(pid, name, rss)
                         for pid, (name, rss) in current_procs.items()],
                        key=lambda x: x[2],
                        reverse=True
                    )[:10]
                    self._write_log("TOP_PROCESSES_SNAPSHOT",
                        f"t={i + 1:2d}s Top 10 by RSS:")
                    for pid, name, rss in top_procs:
                        self._write_log("TOP_PROCESSES_SNAPSHOT",
                            f"  PID {pid:6d} | {name:30s} | {rss / 1024**2:.1f} MB")

            self._write_log("POST_COMPLETE", "Monitoring ended")
            self._monitoring = False

        self._monitor_thread = threading.Thread(target=_monitor, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        """Stop post-completion monitoring early."""
        self._monitoring = False


def _find_env_file():
    """Find .env by walking up from script directory to project root."""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        env_path = os.path.join(current, ".env")
        if os.path.isfile(env_path):
            return env_path
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def _load_env_file():
    """Load .env from project root (found by walking up from script)."""
    env_path = _find_env_file()
    if env_path:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if value and key not in os.environ:
                    os.environ[key] = value


def get_api_key():
    """Get MinerU API key from .env file or environment variable."""
    _load_env_file()
    key = os.environ.get("MINERU_TOKEN") or os.environ.get("MINERU_API_KEY")
    if not key:
        raise RuntimeError(
            "MINERU_TOKEN not found.\n"
            "Either:\n"
            "  1. Add MINERU_TOKEN=your_key to the project .env file, or\n"
            "  2. Set environment variable: export MINERU_TOKEN=your_key_here\n"
            "Get your API key from https://mineru.net/"
        )
    return key


def upload_local_file(pdf_path, model_version, api_key):
    """Upload a local PDF file to MinerU for batch processing.

    Steps:
      1. POST /api/v4/file-urls/batch to get presigned upload URL + batch_id
      2. PUT file to presigned URL (system auto-submits extraction task)

    Returns:
        batch_id for polling batch results
    """
    filename = os.path.basename(pdf_path)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    resp = requests.post(
        f"{API_BASE}/file-urls/batch",
        headers=headers,
        json={
            "files": [{"name": filename}],
            "model_version": model_version,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"Failed to get upload URL: {data}")

    batch_id = data["data"]["batch_id"]
    file_urls = data["data"]["file_urls"]

    with open(pdf_path, "rb") as f:
        resp = requests.put(file_urls[0], data=f, timeout=300)
        if resp.status_code != 200:
            raise RuntimeError(f"File upload failed: {resp.status_code} {resp.text}")

    print(f"  Upload complete (batch_id: {batch_id})")
    return batch_id


def submit_task(file_url, model_version, language="auto", api_key=None):
    """Submit a PDF parsing task to MinerU API.

    Args:
        file_url: URL of the PDF file (remote or presigned upload URL)
        model_version: "pipeline" or "vlm"
        language: "auto", "ch", or "en"
        api_key: MinerU API key

    Returns:
        task_id string
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "url": file_url,
        "enable_formula": True,
        "enable_table": True,
        "model_version": model_version,
        "language": language,
    }

    resp = requests.post(
        f"{API_BASE}/extract/task", headers=headers, json=body, timeout=30
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0:
        raise RuntimeError(f"Task submission failed: {data}")

    task_id = data["data"]["task_id"]
    return task_id


def poll_task(task_id, api_key, timeout=600, interval=5):
    """Poll task status until completion.

    Args:
        task_id: MinerU task ID
        api_key: MinerU API key
        timeout: max wait time in seconds
        interval: poll interval in seconds

    Returns:
        dict with task result (including download URL)
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")

        resp = requests.get(
            f"{API_BASE}/extract/task/{task_id}", headers=headers, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()

        status = data.get("data", {}).get("state", "unknown")
        if status == "done":
            return data["data"]
        elif status in ("failed", "cancelled"):
            raise RuntimeError(f"Task {task_id} failed: {data}")

        time.sleep(interval)


def poll_batch_results(batch_id, api_key, timeout=600, interval=10):
    """Poll batch extraction results until all tasks complete.

    Args:
        batch_id: batch ID from upload_local_file
        api_key: MinerU API key
        timeout: max wait time in seconds
        interval: poll interval in seconds

    Returns:
        list of task result dicts (each may contain full_zip_url)
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            raise TimeoutError(f"Batch {batch_id} did not complete within {timeout}s")

        resp = requests.get(
            f"{API_BASE}/extract-results/batch/{batch_id}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Batch poll failed: {data}")

        batch_data = data.get("data", {})
        tasks = batch_data.get("extract_result", [])
        if not tasks:
            tasks = batch_data.get("task_results", [])
        if not tasks:
            tasks = batch_data.get("results", [])

        if tasks:
            states = [t.get("state", "unknown") for t in tasks]
            done_count = sum(1 for s in states if s == "done")
            fail_count = sum(1 for s in states if s == "failed")
            print(f"  Progress: {done_count}/{len(tasks)} done, {fail_count} failed "
                  f"({elapsed:.0f}s elapsed)")

            if all(s in ("done", "failed") for s in states):
                failed = [t for t in tasks if t.get("state") == "failed"]
                if failed:
                    for t in failed:
                        print(f"  Warning: task failed: {t.get('err_msg', 'unknown error')}")
                    done_tasks = [t for t in tasks if t.get("state") == "done"]
                    if not done_tasks:
                        raise RuntimeError(f"All tasks failed in batch {batch_id}")
                    return done_tasks
                return tasks
        else:
            print(f"  Waiting for batch results... ({elapsed:.0f}s elapsed)")

        time.sleep(interval)


def download_and_extract(result, output_dir, debug=None):
    """Download and extract the result ZIP file.

    Args:
        result: task result dict from poll_task
        output_dir: directory to extract into
        debug: DebugLogger instance (optional)

    Returns:
        path to full.md
    """
    zip_url = result.get("full_zip_url") or result.get("download_url")
    if not zip_url:
        raise RuntimeError(f"No download URL in result: {result}")

    os.makedirs(output_dir, exist_ok=True)
    zip_path = os.path.join(output_dir, "result.zip")

    # Download ZIP
    debug and debug.log_step_start("download_zip")
    resp = requests.get(zip_url, timeout=120, stream=True)
    resp.raise_for_status()
    downloaded_bytes = 0
    with open(zip_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded_bytes += len(chunk)
    resp.close()
    del resp
    zip_size = os.path.getsize(zip_path)
    debug and debug.log_event("DOWNLOAD_DONE",
        f"ZIP downloaded: {zip_size / 1024**2:.2f} MB ({downloaded_bytes} bytes)")
    debug and debug.log_step_end("download_zip",
        extra=f"ZIP size: {zip_size / 1024**2:.2f} MB")

    # Extract ZIP
    debug and debug.log_step_start("extract_zip")
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            member_path = os.path.join(output_dir, member.filename)
            if not os.path.abspath(member_path).startswith(os.path.abspath(output_dir) + os.sep):
                raise ValueError(f"Unsafe path in ZIP: {member.filename}")
        zf.extractall(output_dir)
    debug and debug.log_step_end("extract_zip")
    debug and debug.log_directory_contents(output_dir, "EXTRACTED_FILES")

    os.remove(zip_path)

    md_path = os.path.join(output_dir, "full.md")
    if not os.path.exists(md_path):
        for root, dirs, files in os.walk(output_dir):
            for f in files:
                if f.endswith(".md"):
                    md_path = os.path.join(root, f)
                    break

    return md_path


def run_mineru(pdf_path, output_dir, mode="auto", language="auto", debug=None):
    """Main MinerU extraction pipeline.

    Args:
        pdf_path: path to local PDF file
        output_dir: output directory
        mode: "auto", "pipeline", or "vlm"
        language: "auto", "ch", or "en"
        debug: DebugLogger instance (optional)

    Returns:
        path to extracted full.md, or None on failure
    """
    debug and debug.log_step_start("run_mineru", f"pdf={pdf_path}, mode={mode}")
    api_key = get_api_key()

    if mode == "auto":
        mode = "vlm"
        print(f"Auto mode: using vlm")
    else:
        print(f"Using specified mode: {mode}")

    is_url = pdf_path.startswith("http://") or pdf_path.startswith("https://")

    if is_url:
        print("Submitting URL extraction task...")
        debug and debug.log_step_start("submit_task")
        task_id = submit_task(pdf_path, mode, language, api_key)
        print(f"Task submitted: {task_id}")
        debug and debug.log_step_end("submit_task", extra=f"task_id={task_id}")

        print("Waiting for results...")
        debug and debug.log_step_start("poll_task")
        result = poll_task(task_id, api_key)
        print("Task completed!")
        debug and debug.log_step_end("poll_task")

        print("Downloading and extracting results...")
        md_path = download_and_extract(result, output_dir, debug)
    else:
        print("Uploading local file to MinerU...")
        debug and debug.log_step_start("upload_file")
        batch_id = upload_local_file(pdf_path, mode, api_key)
        print(f"  Upload complete (batch_id: {batch_id})")
        debug and debug.log_step_end("upload_file", extra=f"batch_id={batch_id}")

        print("Waiting for batch results...")
        debug and debug.log_step_start("poll_batch")
        results = poll_batch_results(batch_id, api_key)
        print("Batch processing completed!")
        debug and debug.log_step_end("poll_batch")

        print("Downloading and extracting results...")
        result = results[0]
        md_path = download_and_extract(result, output_dir, debug)

    print(f"Output: {md_path}")

    try:
        debug and debug.log_step_start("reconstruct")
        from reconstruct_full_md import reconstruct as _reconstruct
        content_list_path = os.path.join(output_dir, "content_list_v2.json")
        full_with_pages_path = os.path.join(output_dir, "full_with_pages.md")
        if os.path.exists(content_list_path):
            json_size = os.path.getsize(content_list_path)
            debug and debug.log_event("RECONSTRUCT_INPUT",
                f"content_list_v2.json: {json_size / 1024**2:.2f} MB")
            print("Reconstructing full.md with page annotations...")
            _reconstruct(content_list_path, full_with_pages_path)
            print(f"  Output: {full_with_pages_path}")
        debug and debug.log_step_end("reconstruct")
    except Exception as e:
        print(f"Warning: Failed to reconstruct full_with_pages.md: {e}")
        debug and debug.log_event("RECONSTRUCT_ERROR", str(e))

    try:
        debug and debug.log_step_start("rename_images")
        print("Renaming images to sequential names...")
        rename_images_in_md(output_dir)
        debug and debug.log_step_end("rename_images")
    except Exception as e:
        print(f"Warning: Failed to rename images: {e}")
        debug and debug.log_event("RENAME_IMAGES_ERROR", str(e))

    debug and debug.log_directory_contents(output_dir, "FINAL_OUTPUT")
    debug and debug.log_top_processes(10, "TOP_PROCESSES_AFTER_RUN")

    gc.collect()
    time.sleep(1)
    debug and debug.log_step_end("run_mineru")
    return md_path


def rename_images_in_md(output_dir):
    """Rename images to sequential names (img_001.jpg, img_002.jpg, ...) in md order.

    Scans full_with_pages.md (falls back to full.md) for image references,
    renames image files on disk, and updates references in both md files.

    Args:
        output_dir: directory containing full.md, full_with_pages.md, and images/
    """
    images_dir = os.path.join(output_dir, "images")
    if not os.path.isdir(images_dir):
        return

    pages_md = os.path.join(output_dir, "full_with_pages.md")
    full_md = os.path.join(output_dir, "full.md")
    source_md = pages_md if os.path.exists(pages_md) else full_md
    if not os.path.exists(source_md):
        return

    with open(source_md, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r'!\[.*?\]\((images/[^)]+)\)'
    seen = []
    seen_set = set()
    for m in re.finditer(pattern, content):
        path = m.group(1)
        if path not in seen_set:
            seen_set.add(path)
            seen.append(path)

    if not seen:
        return

    rename_map = {}
    temp_map = {}
    for idx, old_path in enumerate(seen, 1):
        ext = os.path.splitext(old_path)[1]
        new_name = f"img_{idx:03d}{ext}"
        new_path = f"images/{new_name}"
        rename_map[old_path] = new_path

        old_full = os.path.join(output_dir, old_path)
        new_full = os.path.join(output_dir, new_path)
        if os.path.exists(old_full) and old_full != new_full:
            temp_full = new_full + ".tmp_rename"
            os.rename(old_full, temp_full)
            temp_map[temp_full] = new_full

    for temp_full, final_full in temp_map.items():
        os.rename(temp_full, final_full)

    def replace_refs(md_path):
        if not os.path.exists(md_path):
            return
        with open(md_path, "r", encoding="utf-8") as f:
            text = f.read()
        for old, new in rename_map.items():
            text = text.replace(old, new)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(text)

    replace_refs(full_md)
    replace_refs(pages_md)

    print(f"  Renamed {len(rename_map)} images: img_001{os.path.splitext(seen[0])[1]} ~ img_{len(rename_map):03d}{os.path.splitext(seen[-1])[1]}")


def run_fallback(pdf_path, output_dir):
    """Fallback to extract_pdf.py when MinerU is unavailable.

    Runs extract_pdf.py from the same scripts directory.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fallback_script = os.path.join(script_dir, "extract_pdf.py")

    if not os.path.exists(fallback_script):
        raise FileNotFoundError(
            f"Fallback script not found: {fallback_script}\n"
            "Cannot fall back to local extraction."
        )

    print(f"Running fallback: {fallback_script}")
    import subprocess

    result = subprocess.run(
        [sys.executable, fallback_script, pdf_path, "--output", output_dir, "--dpi", "200"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Warning: extract_pdf.py exited with code {result.returncode}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)

    md_path = os.path.join(output_dir, "text")
    return md_path


def update_status(output_dir, status, pid=None, error=None, output_files=None):
    """Update extraction status file if it exists."""
    status_file = os.path.join(output_dir, "extraction_status.json")
    if not os.path.exists(status_file):
        return  # Only update if status file was created by standalone wrapper

    # Read existing start_time to preserve it
    existing_start_time = None
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            existing_start_time = existing_data.get("start_time")
    except Exception:
        pass

    try:
        status_data = {
            "status": status,
            "pid": pid or os.getpid(),
            "start_time": existing_start_time if existing_start_time is not None else time.time(),
            "end_time": time.time() if status in ("completed", "failed") else None,
            "error": error,
            "output_files": output_files or {}
        }
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass  # Don't let status updates crash the script


def main():
    parser = argparse.ArgumentParser(
        description="Extract PDF content using MinerU API"
    )
    parser.add_argument("pdf_path", help="Path to PDF file (local path or URL)")
    parser.add_argument(
        "--output", default=None, help="Output directory (default: <pdf_name>_mineru)"
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "pipeline", "vlm"],
        default="auto",
        help="Extraction mode (default: auto)",
    )
    parser.add_argument(
        "--language",
        choices=["auto", "ch", "en"],
        default="auto",
        help="Document language (default: auto)",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Do not fall back to extract_pdf.py on MinerU failure",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable detailed diagnostic logging (writes to <output>/debug.log)",
    )
    args = parser.parse_args()

    if args.output is None:
        base = os.path.splitext(os.path.basename(args.pdf_path))[0]
        args.output = base + "_mineru"

    # Initialize debug logger
    debug = DebugLogger(args.output, enabled=args.debug) if args.debug else None
    if debug:
        debug.log_event("SCRIPT_START",
            f"pdf={args.pdf_path}, output={args.output}, mode={args.mode}")

    print(f"Input: {args.pdf_path}")
    print(f"Output: {args.output}")

    try:
        md_path = run_mineru(args.pdf_path, args.output, args.mode, args.language, debug)
        print(f"\nExtraction complete: {md_path}")

        # Update status file if it exists (standalone mode)
        output_files = {
            "full.md": os.path.join(args.output, "full.md"),
            "full_with_pages.md": os.path.join(args.output, "full_with_pages.md"),
            "content_list_v2.json": os.path.join(args.output, "content_list_v2.json"),
        }
        update_status(args.output, "completed", output_files=output_files)

    except Exception as e:
        print(f"\nMinerU extraction failed: {e}", file=sys.stderr)
        debug and debug.log_event("EXTRACTION_FAILED", str(e))

        # Update status file with failure
        update_status(args.output, "failed", error=str(e))

        if args.no_fallback:
            print("Fallback disabled. Exiting.", file=sys.stderr)
            sys.exit(1)
        else:
            print("Warning: Falling back to local extraction (extract_pdf.py)...")
            try:
                run_fallback(args.pdf_path, args.output)
                print(f"\nFallback extraction complete: {args.output}")

                # Update status file with fallback success
                output_files = {
                    "full.md": os.path.join(args.output, "full.md"),
                    "full_with_pages.md": os.path.join(args.output, "full_with_pages.md"),
                    "content_list_v2.json": os.path.join(args.output, "content_list_v2.json"),
                }
                update_status(args.output, "completed", output_files=output_files)

            except Exception as e2:
                print(f"Fallback also failed: {e2}", file=sys.stderr)
                debug and debug.log_event("FALLBACK_FAILED", str(e2))
                update_status(args.output, "failed", error=str(e2))
                sys.exit(1)

    gc.collect()
    time.sleep(1)

    # Start post-completion monitoring (30 seconds, 1-second intervals)
    if debug:
        debug.start_post_completion_monitoring(duration=30, interval=1)
        print(f"\n[DEBUG] Post-completion monitoring started (30s). "
              f"Log: {debug.log_path}")
        # Wait for monitoring to complete
        if debug._monitor_thread:
            debug._monitor_thread.join(timeout=35)


if __name__ == "__main__":
    main()
