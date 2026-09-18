#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 SnapMemories Master Organizer & Hardware-Accelerated Media Merger Engine
 Done by: KBJ911
================================================================================
Description:
    An enterprise-grade, fully automated, cross-platform media organization
    and restoration suite for Snapchat data exports.
    
    Universal Dual-Ecosystem Mobile GPS & Native QuickTime Audio Engine:
    - Direct Native JPEG Binary Synthesis (Dynamic Heap Serialization):
        Strips conflicting legacy markers (APP0/JFIF, APP2, XMP) down to clean
        image tables, then constructs an exact native APP1 segment adhering to
        strict 12-byte TIFF IFD entry specifications:
        - 0th IFD: ImageWidth (256), ImageLength (257), Orientation (274),
                   Software (305 = EXIF_SOFTWARE), DateTime (306),
                   Artist (315 = EXIF_ARTIST), Exif/GPS IFDs.
        - Exif IFD: ExifVersion (36864 = "0230"), DateTimeOriginal (36867),
                    DateTimeDigitized (36868), LightSource (37384),
                    CameraOwnerName (42032 = EXIF_OWNER).
        - GPS IFD: Strict Samsung Gallery hardware ordering:
                   Tag 2 (GPSLatitude): High-precision 10,000,000 rational DMS
                   Tag 1 (GPSLatitudeRef): Single-byte ASCII hemisphere ('N' / 'S')
                   Tag 3 (GPSLongitudeRef): Single-byte ASCII hemisphere ('E' / 'W')
                   Tag 4 (GPSLongitude): High-precision 10,000,000 rational DMS
        Immediately triggers Samsung Gallery Google Maps cards & street addresses.
    - Native QuickTime Muxing & Sibling Meta Architecture:
        Utilizes FFmpeg's native QuickTime container engine ('-f mov' with '+faststart')
        to place moov at the front, guaranteeing pristine audio track interleaving,
        edit-list timing (`elst`), and instant Apple Photos map pin indexing.
        Injdects a unified dual-format metadata payload:
        1. Android / Samsung: Direct 'moov -> udta -> ©xyz' (30-byte canonical atom).
        2. Apple iOS / iPhone: Direct 'moov -> meta' container atom housing (152 bytes)
           placed as a direct sibling to udta under moov:
           - 'hdlr' (34 bytes: mdir/appl media handler)
           - 'keys' (60 bytes: 'com.apple.quicktime.location.ISO6709')
           - 'ilst -> data' (50 bytes: 'SA\\x15\\xc7' localized ISO 6709 string)
        3. Robust Multi-Track FastStart Relocation & Offset Shifting Engine:
           Accurately updates all stco and co64 chunk offset tables across audio and
           video tracks when moov expands, using flawless front-end byte slicing
           (`data[:moov_start] + moov_data + data[moov_start + moov_len:]`) to preserve
           every single byte of mdat without corruption.
    - Two-Tier Precision Resolution Architecture:
        Tier 1 (Server Timestamp Priority): Directly pairs raw ZIP server timestamps
        and mtime against memories_history.json / HTML records with ±2s window.
        ZIP-priority shadowing: authentic ZIP timestamps unconditionally override
        loose file modification dates to prevent Windows mtime corruption.
        Tier 2 (File Attribute Fallback): Robust fallback for unregistered media.
    - Intel Arc 140V GPU Acceleration: Hardware QuickSync encoding (-bf 0 -g 60).
    - Cross-Platform CPU Limiter: Enforces Core 0 and idle priority (Windows/Linux/NAS).
    - Smart Mosaic Duplication Cleaner & Video Thumbnail Purging.
    - Zero External .EXE Dependencies: 100% self-contained Python + FFmpeg suite.
================================================================================
"""

import os
import sys
import re
import io
import json
import shutil
import ctypes
import struct
import tarfile
import zipfile
import pathlib
import hashlib
import logging
import tempfile
import datetime
import threading
import traceback
import subprocess
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Tuple, Optional, List, Any, Union

# ==============================================================================
# CONFIGURATION & USER VARIABLES (CENTRALLY DEFINED AT TOP)
# ==============================================================================
# Purpose: Root directory containing raw Snapchat data exports, ZIPs, or folders.
# Accepted Formats: Raw string path r'...', sanitized against accidental quotes and slashes.
# Examples: r"C:\Users\KBJ\Desktop\dd" or r"/volume1/Media_KBJ/snapchat"
# Default: r"" (Prompts interactively at runtime if left empty)
SOURCE_DIR: str = r""

# Purpose: Snapchat account username used to construct the root destination folder.
# Accepted Formats: Alphanumeric string with dashes/underscores (e.g., 'kkkk').
# Examples: "kbj911" -> Outputs to 'Snapchat-kbj911'
# Default: "" (Prompts interactively at runtime if left empty)
SNAPCHAT_USERNAME: str = ""

# Purpose: Base output directory where 'Snapchat-[username]' will be created.
# Accepted Formats: Raw string path r'...'. Defaults to the parent folder of SOURCE_DIR if empty.
# Examples: r"C:\Users\KBJ\Desktop" or r"/volume1/Media_KBJ/Organized"
# Default: r""
BASE_OUTPUT_DIR: str = r""

# ------------------------------------------------------------------------------
# EXIF & METADATA BRANDING SETTINGS (EDITABLE FOR ALL FUTURE RUNS)
# ------------------------------------------------------------------------------
# Purpose: Branding signature written to photo EXIF Software tag (Tag 305) and video Software atom (©swr/©too).
# Accepted Formats: String literal.
# Default: "Done by: KBJ911"
EXIF_SOFTWARE: str = "Done by: KBJ911"

# Purpose: Owner signature written to photo EXIF CameraOwnerName (Tag 42032) and video Author atom (©aut).
# Accepted Formats: String literal.
# Default: "KBJ911"
EXIF_OWNER: str = "KBJ911"

# Purpose: Artist signature written to photo EXIF Artist (Tag 315) and video Artist atom (©art).
# Accepted Formats: String literal.
# Default: "KBJ911"
EXIF_ARTIST: str = "KBJ911"

# Purpose: Copyright statement embedded in photos and video container headers.
# Accepted Formats: String literal.
# Default: "Done by: KBJ911"
EXIF_COPYRIGHT: str = "Done by: KBJ911"

# Purpose: Title metadata embedded in video container headers.
# Accepted Formats: String literal.
# Default: "Snapchat Memory"
VIDEO_METADATA_TITLE: str = "Snapchat Memory"

# ------------------------------------------------------------------------------
# PIPELINE & ENCODING SETTINGS
# ------------------------------------------------------------------------------
# Purpose: Number of parallel GPU video rendering streams to run simultaneously.
# Accepted Formats: Integer between 1 and 4.
# Default: 4
GPU_CONCURRENT_WORKERS: int = 4

# Purpose: Baseline timeout in seconds for encoding individual videos before scaling by duration.
# Accepted Formats: Integer (seconds). Prevents infinite hangs on corrupt video frames.
# Default: 75
VIDEO_PROCESS_TIMEOUT_SECONDS: int = 75

# Purpose: Directory prefix for annual media organization.
# Accepted Formats: String ending with a middle dash (e.g., 'Snapchat-').
# Default: "Snapchat-" (Produces 'Snapchat-2020', 'Snapchat-2021', etc.)
YEAR_FOLDER_PREFIX: str = "Snapchat-"

# Purpose: File operation mode to manage disk space.
# Accepted Formats: 'copy' (Safe: preserves source archives intact) or 'move' (Frees disk space).
# Default: "copy"
OPERATION_MODE: str = "copy"

# Purpose: Hardware acceleration selection policy for video encoding.
# Accepted Formats: 'auto' (Auto-detects Intel Arc QSV -> MediaFoundation -> NVENC -> AMF -> CPU),
#                   'qsv' (Intel QuickSync for Arc), 'mf' (Windows MediaFoundation),
#                   'nvenc' (NVIDIA), 'amf' (AMD), or 'cpu' (Force CPU libx264).
# Default: "auto"
PREFERRED_HARDWARE_ACCEL: str = "auto"

# Purpose: Automatically blend transparent overlay PNG stickers/text onto main photos.
# Accepted Formats: True (Merges overlays into JPEG) or False (Leaves raw photo unmerged).
# Default: True (Checked by default)
MERGE_IMAGE_OVERLAYS: bool = True

# Purpose: Automatically burn transparent overlay PNG stickers/text onto video frames.
# Accepted Formats: True (Hardware GPU overlay compositing) or False (Copies raw video).
# Default: True (Checked by default)
MERGE_VIDEO_OVERLAYS: bool = True

# Purpose: Strictly prevent black/transparent overlay PNGs from entering the albums.
# Accepted Formats: True (Excludes unmerged overlays from output) or False (Copies raw PNGs).
# Default: True (Checked by default)
DISCARD_ORPHAN_OVERLAYS: bool = True

# Purpose: Discard raw unmerged duplicates for both videos and photos when a clean merged version exists.
# Accepted Formats: True (Eliminates raw media showing exposed mosaic/blur patches) or False.
# Default: True (Checked by default)
DISCARD_UNMERGED_DUPLICATES: bool = True

# Purpose: Ignore and purge video preview stills ('thumbnail~*.jpg' and '...IBFAEYAE.jpg') generated by Snapchat.
# Accepted Formats: True (Prevents screenshot JPGs next to videos) or False.
# Default: True (Checked by default)
PURGE_VIDEO_THUMBNAILS: bool = True

# Purpose: Subdivide yearly folders into monthly subfolders (e.g., Snapchat-2024/01).
# Accepted Formats: True (Enables YYYY/MM subfolders) or False (Strictly Yearly folders).
# Default: False (Unchecked by default)
CLASSIFY_MONTHLY_FOLDERS: bool = False

# Purpose: Permanently delete all standalone overlay PNG files found in output or source.
# Accepted Formats: True (Deletes all overlay files) or False (Only keeps clean gallery).
# Default: False (Unchecked by default)
PURGE_ALL_OVERLAYS_COMPLETELY: bool = False

# Purpose: Target timezone offset in hours relative to UTC for local time conversion.
# Accepted Formats: Float or Integer between -12.0 and +14.0 (e.g., 3.0 for Saudi Arabia / Asia/Riyadh).
# Default: 3.0
TIMEZONE_OFFSET_HOURS: float = 3.0

# Purpose: Inject EXIF DateTimeOriginal, DateTimeDigitized tags into JPEG photos.
# Accepted Formats: True (Writes EXIF date metadata) or False (Skips EXIF date manipulation).
# Default: True (Checked by default)
UPDATE_EXIF_TAGS: bool = True

# Purpose: Inject geographical GPS latitude/longitude coordinates into photos and videos.
# Accepted Formats: True (Writes GPS tags & QuickTime location atoms) or False (Skips GPS injection).
# Default: True (Checked by default)
UPDATE_GPS_TAGS: bool = True

# Purpose: Patch QuickTime / MP4 header atoms ('mvhd', 'tkhd', 'mdhd') for chronological sorting.
# Accepted Formats: True (Patches video creation timestamps) or False (Skips binary patching).
# Default: True (Checked by default)
PATCH_MP4_METADATA: bool = True

# Purpose: Synchronize OS filesystem modification and access timestamps to capture date.
# Accepted Formats: True (Updates os.utime) or False (Keeps system copy timestamps).
# Default: True (Checked by default)
SET_FS_TIMESTAMPS: bool = True

# Purpose: Detect and eliminate duplicate media items using SHA-256 fingerprinting.
# Accepted Formats: True (Deduplicates identical files) or False (Allows duplicates).
# Default: True (Checked by default)
ENABLE_DEDUPLICATION: bool = True

# Purpose: Maximum allowable second deviation to match timestamps between files and JSON records.
# Accepted Formats: Integer between 0 and 5.
# Default: 2
FUZZY_TIME_WINDOW_SECONDS: int = 2

# Purpose: Base cache directory for NAS downloads and offline binaries.
# Accepted Formats: Absolute Posix path string.
# Default: "/volume1/docker/scripts/scripts-cache" (Falls back to "/app/scripts-cache" inside Docker)
NAS_CACHE_BASE_DIR: str = "/volume1/docker/scripts/scripts-cache"

# ==============================================================================
# ANSI COLOR SCHEME & INTERFACE CONSTANTS (MOBILE SCREEN SAFE: MAX 40 CHARS)
# ==============================================================================
DIVIDER: str = "=" * 40
MINI_DIVIDER: str = "-" * 40

CLR_RESET: str = "\033[0m"
CLR_RED: str = "\033[31m"
CLR_GREEN: str = "\033[32m"
CLR_YELLOW: str = "\033[33m"
CLR_CYAN: str = "\033[36m"
CLR_PINK: str = "\033[35m"
CLR_WHITE: str = "\033[37m"
CLR_BOLD: str = "\033[1m"

# ==============================================================================
# LOGGING SYSTEM (SINGLE LOG FILE SAVED IN SCRIPT DIR, RESET PER RUN)
# ==============================================================================
SCRIPT_PATH = pathlib.Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
LOG_FILE = SCRIPT_DIR / f"{SCRIPT_PATH.stem}.log"

try:
    with open(LOG_FILE, "w", encoding="utf-8") as _lf:
        _lf.write(f"=== SnapMemories Organizer Execution Log: {datetime.datetime.now()} ===\n")
except Exception:
    pass

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

logging.getLogger("PIL").setLevel(logging.WARNING)

LOG_LOCK = threading.Lock()

def log_console(msg: str, level: str = "info", color: str = CLR_WHITE) -> None:
    """Outputs colorized branded log messages to console and mirrors them to disk log."""
    with LOG_LOCK:
        print(f"{color}{msg}{CLR_RESET}")
        if level == "error":
            logging.error(msg)
        elif level == "warning":
            logging.warning(msg)
        else:
            logging.info(msg)

# ==============================================================================
# RUNTIME ENVIRONMENT & OFFLINE CACHE RESOLVER
# ==============================================================================
def is_termux() -> bool:
    """Detects if the script is executing inside an Android Termux environment."""
    return os.path.exists("/data/data/com.termux")

def is_nas_or_docker() -> bool:
    """Detects if the script is executing inside Synology/Ugreen NAS or Docker."""
    return os.path.exists("/.dockerenv") or os.path.exists("/volume1")

def get_offline_cache_dir() -> pathlib.Path:
    """Dynamically resolves the offline cache directory structure."""
    stem = re.sub(r'[-_]offline$', '', SCRIPT_PATH.stem, flags=re.IGNORECASE)
    folder_name = f"{stem}-offline"
    
    if is_nas_or_docker():
        nas_base = pathlib.Path(NAS_CACHE_BASE_DIR)
        if nas_base.exists():
            target_cache = nas_base / folder_name
        else:
            fallback_base = pathlib.Path("/app/scripts-cache")
            fallback_base.mkdir(parents=True, exist_ok=True)
            target_cache = fallback_base / folder_name
    else:
        target_cache = SCRIPT_DIR / folder_name

    target_cache.mkdir(parents=True, exist_ok=True)
    return target_cache

# ==============================================================================
# CROSS-PLATFORM HARDWARE KERNEL CPU LIMITER
# ==============================================================================
def enforce_low_cpu_kernel_governor() -> None:
    """Locks process to Core 0 and IDLE/lowest priority across Windows and Linux/Docker/NAS."""
    if sys.platform.startswith("win"):
        try:
            current_proc = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.kernel32.SetPriorityClass(current_proc, 0x00000040)  # IDLE_PRIORITY_CLASS
            ctypes.windll.kernel32.SetProcessAffinityMask(current_proc, 1)      # Core 0 only
        except Exception as e:
            logging.debug(f"Governor setup note (Win): {e}")
    elif sys.platform.startswith("linux") or is_nas_or_docker():
        try:
            os.nice(19)  # Minimum scheduling priority
        except Exception:
            pass
        try:
            if hasattr(os, "sched_setaffinity"):
                os.sched_setaffinity(0, {0})  # Pin process to CPU Core 0
        except Exception as e:
            logging.debug(f"Governor setup note (Linux): {e}")

enforce_low_cpu_kernel_governor()

# ==============================================================================
# DEPENDENCY MANAGER (STRICT 3-TIER HIERARCHY)
# ==============================================================================
def install_package_tier(pkg_name: str) -> bool:
    """Strict 3-Tier package installation hierarchy."""
    log_console(f"📦 Checking Python dependency: {pkg_name}...", "info", CLR_CYAN)
    
    break_pkg = ["--break-system-packages"] if (is_nas_or_docker() or is_termux()) else []
    cmd_t1 = [sys.executable, "-m", "pip", "install", pkg_name, "--only-binary", ":all:"] + break_pkg
    try:
        res = subprocess.run(cmd_t1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            log_console(f"✅ Tier 1: {pkg_name} binary wheel verified.", "info", CLR_GREEN)
            return True
    except Exception as e:
        logging.debug(f"Tier 1 check note for {pkg_name}: {e}")

    if is_termux():
        log_console(f"🔄 Tier 2: Attempting pkg install python-{pkg_name}...", "warning", CLR_YELLOW)
        try:
            res = subprocess.run(["pkg", "install", "-y", f"python-{pkg_name}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                log_console(f"✅ Tier 2: {pkg_name} installed via Termux pkg.", "info", CLR_GREEN)
                return True
        except Exception as e:
            logging.debug(f"Tier 2 failed for {pkg_name}: {e}")

    log_console(f"⚠️ Tier 3: Compiling '{pkg_name}' via source fallback...", "warning", CLR_YELLOW)
    if is_termux():
        log_console("🔧 Installing Termux build dependencies...", "info", CLR_CYAN)
        subprocess.run(["pkg", "install", "-y", "clang", "make", "libjpeg-turbo", "libpng", "libtiff"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    cmd_t3 = [sys.executable, "-m", "pip", "install", pkg_name] + break_pkg
    try:
        res = subprocess.run(cmd_t3, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            log_console(f"✅ Tier 3: {pkg_name} compiled successfully.", "info", CLR_GREEN)
            return True
    except Exception as e:
        log_console(f"❌ Failed to build dependency '{pkg_name}': {e}", "error", CLR_RED)
        
    return False

HAS_PILLOW = False
try:
    from PIL import Image, ImageOps
    HAS_PILLOW = True
except ImportError:
    if install_package_tier("Pillow"):
        try:
            from PIL import Image, ImageOps
            HAS_PILLOW = True
        except ImportError:
            HAS_PILLOW = False

# ==============================================================================
# FFMPEG AUTO-RESOLVER
# ==============================================================================
def download_with_progress(url: str, dest_path: pathlib.Path) -> bool:
    """Downloads external binaries while reporting scannable progress percentages."""
    log_console(f"⬇️ Downloading external binary: {url}", "info", CLR_CYAN)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out_file:
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            block_size = 1024 * 1024
            while True:
                buffer = resp.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                out_file.write(buffer)
                if total_size > 0:
                    pct = (downloaded / total_size) * 100
                    mb_down = downloaded / (1024 * 1024)
                    mb_tot = total_size / (1024 * 1024)
                    print(f"\r{CLR_CYAN}⏳ Download progress: {mb_down:.1f}MB / {mb_tot:.1f}MB ({pct:.1f}%){CLR_RESET}", end="", flush=True)
            print()
        return True
    except Exception as e:
        print()
        log_console(f"❌ Binary download failed: {e}", "error", CLR_RED)
        return False

def ensure_ffmpeg() -> Optional[str]:
    """Guarantees FFmpeg presence across Windows, Linux, NAS, and Termux environments."""
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        log_console(f"✅ FFmpeg detected in system PATH: {sys_ffmpeg}", "info", CLR_GREEN)
        return sys_ffmpeg

    cache_dir = get_offline_cache_dir()
    if sys.platform.startswith("win"):
        bin_dir = cache_dir / "bin" / "windows"
        ffmpeg_bin = bin_dir / "ffmpeg.exe"
    elif is_termux():
        bin_dir = cache_dir / "bin" / "termux"
        ffmpeg_bin = bin_dir / "ffmpeg"
    elif is_nas_or_docker():
        bin_dir = cache_dir / "bin" / "nas"
        ffmpeg_bin = bin_dir / "ffmpeg"
    else:
        bin_dir = cache_dir / "bin" / "linux"
        ffmpeg_bin = bin_dir / "ffmpeg"

    if ffmpeg_bin.exists():
        try:
            os.chmod(str(ffmpeg_bin), 0o755)
            log_console(f"✅ FFmpeg loaded from offline cache: {ffmpeg_bin}", "info", CLR_GREEN)
            return str(ffmpeg_bin)
        except Exception:
            pass

    log_console("⚠️ FFmpeg binary not found. Initiating automated deployment...", "warning", CLR_YELLOW)
    bin_dir.mkdir(parents=True, exist_ok=True)

    if sys.platform.startswith("win"):
        winget = shutil.which("winget")
        if winget:
            try:
                log_console("🔄 Attempting deployment via Windows winget...", "info", CLR_CYAN)
                subprocess.run([
                    winget, "install", "--id", "Gyan.FFmpeg", "-e",
                    "--accept-source-agreements", "--accept-package-agreements", "--silent"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
                w_ff = shutil.which("ffmpeg")
                if w_ff:
                    return w_ff
            except Exception:
                pass

        win_zip_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        tmp_zip = pathlib.Path(tempfile.gettempdir()) / "ffmpeg_portable.zip"
        if download_with_progress(win_zip_url, tmp_zip):
            try:
                with zipfile.ZipFile(tmp_zip, "r") as z:
                    for name in z.namelist():
                        if name.lower().endswith("bin/ffmpeg.exe") or name.lower().endswith("ffmpeg.exe"):
                            with z.open(name) as src, open(ffmpeg_bin, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                            break
                tmp_zip.unlink(missing_ok=True)
                if ffmpeg_bin.exists():
                    log_console(f"✅ FFmpeg deployed to offline cache: {ffmpeg_bin}", "info", CLR_GREEN)
                    return str(ffmpeg_bin)
            except Exception as e:
                log_console(f"❌ Failed to extract portable FFmpeg: {e}", "error", CLR_RED)

    elif is_termux():
        subprocess.run(["pkg", "install", "-y", "ffmpeg"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return shutil.which("ffmpeg")

    elif is_nas_or_docker() or sys.platform.startswith("linux"):
        try:
            subprocess.run(["apt-get", "update", "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["apt-get", "install", "-y", "ffmpeg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            l_ff = shutil.which("ffmpeg")
            if l_ff:
                return l_ff
        except Exception:
            pass

        static_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        tmp_tar = pathlib.Path(tempfile.gettempdir()) / "ffmpeg_static.tar.xz"
        if download_with_progress(static_url, tmp_tar):
            try:
                with tarfile.open(tmp_tar, "r:xz") as tar:
                    for member in tar.getmembers():
                        if member.name.endswith("/ffmpeg") and not member.name.endswith("qt-faststart"):
                            mf = tar.extractfile(member)
                            if mf:
                                with open(ffmpeg_bin, "wb") as f_out:
                                    shutil.copyfileobj(mf, f_out)
                                break
                os.chmod(str(ffmpeg_bin), 0o755)
                if is_nas_or_docker():
                    try:
                        shutil.chown(str(ffmpeg_bin), user=1000, group=10)
                    except Exception:
                        pass
                tmp_tar.unlink(missing_ok=True)
                return str(ffmpeg_bin)
            except Exception as e:
                log_console(f"❌ Static binary extraction failed: {e}", "error", CLR_RED)

    return None

FFMPEG_BIN: Optional[str] = ensure_ffmpeg()

# ==============================================================================
# HARDWARE ACCELERATION ENGINE (INTEL ARC 140V DEDICATED SETUP)
# ==============================================================================
def detect_system_gpus() -> str:
    """Inspects installed graphics adapters via system management interfaces."""
    if sys.platform.startswith("win"):
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"]
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=5)
            lines = [line.strip() for line in out.splitlines() if line.strip()]
            if lines:
                return " / ".join(lines)
        except Exception:
            pass
    elif is_nas_or_docker() or sys.platform.startswith("linux"):
        for render_node in ["/dev/dri/renderD128", "/dev/dri/renderD129"]:
            if os.path.exists(render_node):
                return f"Intel QSV DRM Node ({render_node})"
        try:
            out = subprocess.check_output(["lspci"], text=True, stderr=subprocess.DEVNULL, timeout=3)
            for line in out.splitlines():
                if "VGA" in line or "3D" in line:
                    return line.split(":")[-1].strip()
        except Exception:
            pass
    return "Standard GPU Controller"

DETECTED_GPU_NAME = detect_system_gpus()

def get_qsv_device_global_args() -> List[str]:
    """Returns hardware device arguments for QSV on Linux/Docker if DRI render node exists."""
    if not sys.platform.startswith("win"):
        for dev in ["/dev/dri/renderD128", "/dev/dri/renderD129"]:
            if os.path.exists(dev):
                return ["-qsv_device", dev]
    return []

def probe_hardware_acceleration() -> Tuple[str, List[str], str]:
    """Tests and benchmarks available video encoders with a real frame render."""
    if not FFMPEG_BIN:
        return "libx264", ["-preset", "ultrafast", "-crf", "20"], "CPU (libx264 - Ultrafast)"

    candidates = []
    gpu_lower = DETECTED_GPU_NAME.lower()
    qsv_dev_args = get_qsv_device_global_args()

    if "arc" in gpu_lower or "intel" in gpu_lower or "qsv" in gpu_lower or PREFERRED_HARDWARE_ACCEL.lower() in ["auto", "qsv", "mf"]:
        candidates.append((
            "h264_qsv",
            ["-preset", "veryfast", "-global_quality", "21", "-async_depth", "4", "-bf", "0", "-g", "60"],
            f"Intel Arc 140V QuickSync GPU ({DETECTED_GPU_NAME})"
        ))
        if sys.platform.startswith("win"):
            candidates.append((
                "h264_mf",
                ["-b:v", "6M", "-rate_control", "cbr"],
                f"Intel Arc 140V MediaFoundation GPU ({DETECTED_GPU_NAME})"
            ))
    elif "nvidia" in gpu_lower or "geforce" in gpu_lower or "rtx" in gpu_lower:
        candidates.append((
            "h264_nvenc",
            ["-preset", "p4", "-cq", "20", "-bf", "0"],
            f"NVIDIA NVENC Dedicated GPU ({DETECTED_GPU_NAME})"
        ))
    elif "amd" in gpu_lower or "radeon" in gpu_lower:
        candidates.append((
            "h264_amf",
            ["-quality", "speed", "-rc", "cqp", "-qp_p", "20"],
            f"AMD AMF Dedicated GPU ({DETECTED_GPU_NAME})"
        ))

    test_file = pathlib.Path(tempfile.gettempdir()) / f"gpu_probe_{os.getpid()}.mp4"
    for enc, args, label in candidates:
        try:
            device_prefix = qsv_dev_args if enc == "h264_qsv" else []
            test_cmd = [
                FFMPEG_BIN, "-y",
                *device_prefix,
                "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.2",
                "-c:v", enc, *args,
                "-pix_fmt", "nv12" if "qsv" in enc else "yuv420p",
                str(test_file)
            ]
            res = subprocess.run(test_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            if res.returncode == 0 and test_file.exists() and test_file.stat().st_size > 500:
                test_file.unlink(missing_ok=True)
                return enc, args, label
        except Exception:
            pass
        finally:
            test_file.unlink(missing_ok=True)

    return "libx264", ["-preset", "ultrafast", "-crf", "20"], "CPU (libx264 - Ultrafast Fallback)"

ACTIVE_ENCODER, ACTIVE_ENCODER_ARGS, ACTIVE_ENCODER_LABEL = probe_hardware_acceleration()

# ==============================================================================
# UI BRANDING & BANNERS
# ==============================================================================
def display_header() -> None:
    print(f"{CLR_CYAN}{DIVIDER}{CLR_RESET}")
    print(f"{CLR_BOLD}{CLR_WHITE} 👻 SNAPCHAT MASTER ORGANIZER{CLR_RESET}")
    print(f"{CLR_PINK}       Done by: KBJ911{CLR_RESET}")
    print(f"{CLR_CYAN}{DIVIDER}{CLR_RESET}")

def display_footer() -> None:
    print(f"{CLR_CYAN}{DIVIDER}{CLR_RESET}")
    print(f"{CLR_GREEN} ✨ Process Complete! Log saved to:{CLR_RESET}")
    print(f"{CLR_WHITE}    {LOG_FILE}{CLR_RESET}")
    print(f"{CLR_PINK}       Done by: KBJ911{CLR_RESET}")
    print(f"{CLR_CYAN}{DIVIDER}{CLR_RESET}")

# ==============================================================================
# METADATA & PARSING HELPERS
# ==============================================================================
UUID_REGEX = re.compile(r"([A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12})", re.IGNORECASE)
DATE_PREFIX_REGEX = re.compile(r"^(\d{4})[-_](\d{2})[-_](\d{2})")
COORD_REGEX = re.compile(r"(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)")

FULL_TIMESTAMP_REGEX = re.compile(
    r"(?P<year>20\d\d|19\d\d)[-_]?(?P<month>0[1-9]|1[0-2])[-_]?(?P<day>0[1-9]|[12]\d|3[01])"
    r"[-_ ](?P<hour>[01]\d|2[0-3])[-_:.]?(?P<min>[0-5]\d)[-_:.]?(?P<sec>[0-5]\d)"
)

FIXED_EPOCH = datetime.datetime(1970, 1, 1)

def to_fixed_seconds(dt: datetime.datetime) -> int:
    """Converts a naive datetime directly into total seconds from a fixed reference point."""
    return int((dt - FIXED_EPOCH).total_seconds())

ZIP_CACHE: Dict[pathlib.Path, zipfile.ZipFile] = {}
ZIP_CACHE_LOCK = threading.Lock()

def get_cached_zip(zip_path: pathlib.Path) -> zipfile.ZipFile:
    """Thread-safe retrieval of cached ZipFile instances."""
    with ZIP_CACHE_LOCK:
        if zip_path not in ZIP_CACHE:
            ZIP_CACHE[zip_path] = zipfile.ZipFile(zip_path, "r")
        return ZIP_CACHE[zip_path]

def close_all_cached_zips() -> None:
    """Closes all cached ZipFile handles at pipeline completion."""
    with ZIP_CACHE_LOCK:
        for z in ZIP_CACHE.values():
            try:
                z.close()
            except Exception:
                pass
        ZIP_CACHE.clear()

class MemoryMetadata:
    def __init__(self, dt_local: datetime.datetime, dt_utc: datetime.datetime, location: Optional[Tuple[float, float]] = None):
        self.dt_local = dt_local
        self.dt_utc = dt_utc
        self.location = location

class MetadataRegistry:
    """High-Performance Memory Registry with multi-directional ±2s fuzzy matching."""
    def __init__(self):
        self.token_map: Dict[str, MemoryMetadata] = {}
        self.utc_sec_map: Dict[int, MemoryMetadata] = {}
        self.loc_sec_map: Dict[int, MemoryMetadata] = {}

    def register(self, dt_utc: datetime.datetime, dt_local: datetime.datetime, loc: Optional[Tuple[float, float]], tokens: List[str]):
        meta = MemoryMetadata(dt_local, dt_utc, loc)
        u_sec = to_fixed_seconds(dt_utc)
        l_sec = to_fixed_seconds(dt_local)
        self.utc_sec_map[u_sec] = meta
        self.loc_sec_map[l_sec] = meta
        for t in tokens:
            if t:
                self.token_map[t.upper()] = meta

    def query(self, token: Optional[str] = None, dt_candidate: Optional[datetime.datetime] = None) -> Tuple[Optional[MemoryMetadata], str]:
        if token and token.upper() in self.token_map:
            return self.token_map[token.upper()], "TOKEN_EXACT"

        if dt_candidate:
            cand_sec = to_fixed_seconds(dt_candidate)
            search_deltas = [0]
            for step in range(1, FUZZY_TIME_WINDOW_SECONDS + 1):
                search_deltas.extend([step, -step])

            offset_sec = int(TIMEZONE_OFFSET_HOURS * 3600)

            for delta in search_deltas:
                target = cand_sec + delta
                if target in self.utc_sec_map:
                    return self.utc_sec_map[target], f"UTC_MATCH(Δ{delta}s)"

            for delta in search_deltas:
                target = cand_sec + delta
                if target in self.loc_sec_map:
                    return self.loc_sec_map[target], f"LOCAL_MATCH(Δ{delta}s)"

            for delta in search_deltas:
                target = (cand_sec - offset_sec) + delta
                if target in self.utc_sec_map:
                    return self.utc_sec_map[target], f"OFFSET_UTC_MATCH(Δ{delta}s)"

            for delta in search_deltas:
                target = (cand_sec + offset_sec) + delta
                if target in self.loc_sec_map:
                    return self.loc_sec_map[target], f"OFFSET_LOCAL_MATCH(Δ{delta}s)"

        return None, "NO_MATCH"

    def __len__(self) -> int:
        return len(self.utc_sec_map)

def build_metadata_index(source_path: pathlib.Path) -> MetadataRegistry:
    """Pre-scans folders and ZIP archives in-memory for memories_history JSON/HTML."""
    registry = MetadataRegistry()
    log_console("🔍 Deep Pre-Scan: Searching for JSON / HTML / Index metadata...", "info", CLR_CYAN)

    json_files: List[pathlib.Path] = []
    html_files: List[pathlib.Path] = []
    zip_files: List[pathlib.Path] = []

    if source_path.is_dir():
        for root, _, files in os.walk(source_path):
            for file in files:
                p = pathlib.Path(root) / file
                fl = file.lower()
                if fl.endswith(".zip"):
                    zip_files.append(p)
                elif fl.endswith(".json") and ("memories" in fl or "history" in fl):
                    json_files.append(p)
                elif fl.endswith(".html") and ("memories" in fl or "index" in fl):
                    html_files.append(p)
    elif source_path.is_file():
        fl = source_path.name.lower()
        if fl.endswith(".zip"):
            zip_files.append(source_path)
        elif fl.endswith(".json"):
            json_files.append(source_path)
        elif fl.endswith(".html"):
            html_files.append(source_path)

    def register_metadata_entry(date_str: str, loc_str: str, download_link: str = "", media_url: str = ""):
        if not date_str:
            return

        cleaned_date = date_str.replace(" UTC", "").strip()
        dt_utc = None
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S UTC", "%Y/%m/%d %H:%M:%S"]:
            try:
                dt_utc = datetime.datetime.strptime(cleaned_date, fmt)
                break
            except ValueError:
                continue

        if not dt_utc:
            return

        dt_local = dt_utc + datetime.timedelta(hours=TIMEZONE_OFFSET_HOURS)

        loc_tuple = None
        if loc_str:
            m_coords = COORD_REGEX.search(loc_str)
            if m_coords:
                try:
                    lat = float(m_coords.group(1))
                    lon = float(m_coords.group(2))
                    if not (abs(lat) < 0.0001 and abs(lon) < 0.0001):
                        loc_tuple = (lat, lon)
                except ValueError:
                    pass

        tokens: List[str] = []
        for link_field in [download_link, media_url]:
            if link_field:
                decoded_link = urllib.parse.unquote(link_field)
                for u in UUID_REGEX.findall(decoded_link):
                    tokens.append(u.upper())
                for bt in re.findall(r'b~([A-Za-z0-9_\-]{26,36})', decoded_link):
                    tokens.append(bt.upper())
                for token in re.findall(r'[A-Za-z0-9_\-]{28,36}', decoded_link):
                    tokens.append(token.upper())

        registry.register(dt_utc, dt_local, loc_tuple, tokens)

    def parse_json_content(content_str: str):
        try:
            data = json.loads(content_str)
            def find_media_entries(data_obj):
                if isinstance(data_obj, list):
                    for el in data_obj:
                        if isinstance(el, dict) and any(k.lower() == "date" for k in el):
                            yield el
                        else:
                            yield from find_media_entries(el)
                elif isinstance(data_obj, dict):
                    for k, v in data_obj.items():
                        yield from find_media_entries(v)

            for item in find_media_entries(data):
                d_str, loc_s, dl_link, m_url = "", "", "", ""
                for k, v in item.items():
                    kl = k.lower()
                    if kl == "date": d_str = str(v)
                    elif kl in ["download link", "download_link"]: dl_link = str(v)
                    elif kl in ["media download url", "media_download_url"]: m_url = str(v)
                    elif kl == "location": loc_s = str(v)
                register_metadata_entry(d_str, loc_s, dl_link, m_url)
        except Exception as err:
            logging.debug(f"JSON parsing error: {err}")

    def parse_html_content(html_str: str):
        try:
            row_blocks = re.findall(r'<tr[^>]*>(.*?)</tr>', html_str, re.DOTALL | re.IGNORECASE)
            for row in row_blocks:
                cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                if len(cols) >= 2:
                    d_match = re.search(r'(\d{4}[-_/]\d{2}[-_/]\d{2}\s+\d{2}:\d{2}:\d{2})', cols[0])
                    if not d_match:
                        continue
                    d_str = d_match.group(1)
                    loc_s = cols[2] if len(cols) >= 3 else ""
                    link_match = re.search(r'href=[\'"]([^\'"]+)[\'"]', row)
                    dl_link = link_match.group(1) if link_match else ""
                    register_metadata_entry(d_str, loc_s, dl_link, "")
        except Exception as err:
            logging.debug(f"HTML parsing error: {err}")

    for jf in set(json_files):
        try:
            with open(jf, "r", encoding="utf-8", errors="replace") as f:
                parse_json_content(f.read())
        except Exception:
            pass

    for hf in set(html_files):
        try:
            with open(hf, "r", encoding="utf-8", errors="replace") as f:
                parse_html_content(f.read())
        except Exception:
            pass

    for zf in set(zip_files):
        try:
            cached_z = get_cached_zip(zf)
            with ZIP_CACHE_LOCK:
                for name in cached_z.namelist():
                    nl = name.lower()
                    if nl.endswith(".json") and ("memories" in nl or "history" in nl):
                        with cached_z.open(name) as f:
                            parse_json_content(f.read().decode("utf-8", errors="replace"))
                    elif nl.endswith(".html") and ("memories" in nl or "history" in nl):
                        with cached_z.open(name) as f:
                            parse_html_content(f.read().decode("utf-8", errors="replace"))
        except Exception as e:
            logging.debug(f"Failed to inspect zip {zf.name} for metadata: {e}")

    log_console(f"📑 Pre-Scan Complete: Indexed {len(registry)} memory records from JSON/HTML.", "info", CLR_GREEN)
    return registry

def to_mobile_dms_rationals(val: float) -> Tuple[int, int, int]:
    """Exact rational DMS calculation matching Samsung Galaxy hardware precision."""
    val = abs(val)
    deg = int(val)
    rem_min = (val - deg) * 60.0
    minute = int(rem_min)
    sec = (rem_min - minute) * 60.0
    sec_num = int(round(sec * 10000000))
    if sec_num >= 600000000:
        sec_num = 0
        minute += 1
    if minute >= 60:
        minute = 0
        deg += 1
    return deg, minute, sec_num

# ==============================================================================
# PURE-PYTHON DETERMINISTIC NATIVE EXIF SYNTHESIS (DYNAMIC HEAP ALIGNMENT)
# ==============================================================================
def write_clean_mobile_jpeg(file_path: pathlib.Path, dt_local: datetime.datetime, loc: Optional[Tuple[float, float]]) -> bool:
    """
    Constructs the exact native Samsung/iOS binary APP1 segment adhering to strict
    TIFF 6.0 standards (12-byte IFD entries) and mobile hardware ordering:
    Tag 2 -> Tag 1 -> Tag 3 -> Tag 4 with 10,000,000 DMS precision.
    Dynamically computes heap offsets to support customizable Owner and Software strings.
    """
    if file_path.suffix.lower() not in [".jpg", ".jpeg"]:
        return False
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        if not raw_bytes.startswith(b"\xFF\xD8"):
            return False

        has_location = loc is not None and not (abs(loc[0]) < 0.0001 and abs(loc[1]) < 0.0001)

        dt_bytes = dt_local.strftime("%Y:%m:%d %H:%M:%S").encode("ascii") + b"\x00"
        sw_bytes = EXIF_SOFTWARE.encode("utf-8", "replace") + b"\x00"
        owner_bytes = EXIF_OWNER.encode("utf-8", "replace") + b"\x00"
        artist_bytes = EXIF_ARTIST.encode("utf-8", "replace") + b"\x00"

        # TIFF Header (Big-Endian MM)
        tiff_header = b"MM\x00*\x00\x00\x00\x08"

        # Calculate exact IFD block sizes (Strict 12-byte per IFD Entry)
        num_0th_entries = 8 if has_location else 7
        size_0th = 2 + (num_0th_entries * 12) + 4
        exif_ifd_offset = 8 + size_0th

        num_exif_entries = 5
        size_exif = 2 + (num_exif_entries * 12) + 4
        gps_ifd_offset = exif_ifd_offset + size_exif

        num_gps_entries = 4
        size_gps = (2 + (num_gps_entries * 12) + 4) if has_location else 0

        base_heap_offset = gps_ifd_offset + size_gps if has_location else gps_ifd_offset
        heap = bytearray()

        def add_to_heap(data: bytes) -> int:
            nonlocal heap
            offset = base_heap_offset + len(heap)
            heap.extend(data)
            if len(heap) % 2 != 0:
                heap.extend(b"\x00")  # Maintain strict 2-byte word boundary
            return offset

        # Allocate variable-length heap data dynamically
        offset_sw = add_to_heap(sw_bytes)
        offset_dt = add_to_heap(dt_bytes)
        offset_artist = add_to_heap(artist_bytes)
        offset_owner = add_to_heap(owner_bytes)

        if has_location:
            lat = loc[0]
            lon = loc[1]
            lat_ref = b'N' if lat >= 0 else b'S'
            lon_ref = b'E' if lon >= 0 else b'W'

            lat_d, lat_m, lat_s = to_mobile_dms_rationals(lat)
            lon_d, lon_m, lon_s = to_mobile_dms_rationals(lon)

            lat_rationals = struct.pack(">IIIIII", lat_d, 1, lat_m, 1, lat_s, 10000000)
            lon_rationals = struct.pack(">IIIIII", lon_d, 1, lon_m, 1, lon_s, 10000000)

            offset_lat = add_to_heap(lat_rationals)
            offset_lon = add_to_heap(lon_rationals)

        # ----------------------------------------------------------------------
        # 0th IFD Block
        # ----------------------------------------------------------------------
        ifd0 = bytearray()
        ifd0.extend(struct.pack(">H", num_0th_entries))
        ifd0.extend(struct.pack(">HHI", 256, 3, 1) + struct.pack(">HH", 0, 0))
        ifd0.extend(struct.pack(">HHI", 257, 3, 1) + struct.pack(">HH", 0, 0))
        ifd0.extend(struct.pack(">HHI", 274, 3, 1) + struct.pack(">HH", 1, 0))
        ifd0.extend(struct.pack(">HHI", 305, 2, len(sw_bytes)) + struct.pack(">I", offset_sw))
        ifd0.extend(struct.pack(">HHI", 306, 2, len(dt_bytes)) + struct.pack(">I", offset_dt))
        ifd0.extend(struct.pack(">HHI", 315, 2, len(artist_bytes)) + struct.pack(">I", offset_artist))
        ifd0.extend(struct.pack(">HHI", 34665, 4, 1) + struct.pack(">I", exif_ifd_offset))
        if has_location:
            ifd0.extend(struct.pack(">HHI", 34853, 4, 1) + struct.pack(">I", gps_ifd_offset))
        ifd0.extend(struct.pack(">I", 0))  # Next IFD = 0

        # ----------------------------------------------------------------------
        # Exif IFD Block
        # ----------------------------------------------------------------------
        ifd_exif = bytearray()
        ifd_exif.extend(struct.pack(">H", num_exif_entries))
        ifd_exif.extend(struct.pack(">HHI", 36864, 7, 4) + b"0230")
        ifd_exif.extend(struct.pack(">HHI", 36867, 2, len(dt_bytes)) + struct.pack(">I", offset_dt))
        ifd_exif.extend(struct.pack(">HHI", 36868, 2, len(dt_bytes)) + struct.pack(">I", offset_dt))
        ifd_exif.extend(struct.pack(">HHI", 37384, 3, 1) + struct.pack(">HH", 0, 0))
        ifd_exif.extend(struct.pack(">HHI", 42032, 2, len(owner_bytes)) + struct.pack(">I", offset_owner))
        ifd_exif.extend(struct.pack(">I", 0))  # Next IFD = 0

        # ----------------------------------------------------------------------
        # GPS IFD Block (Strict Samsung One UI Order: Tag 2, Tag 1, Tag 3, Tag 4)
        # ----------------------------------------------------------------------
        ifd_gps = bytearray()
        if has_location:
            ifd_gps.extend(struct.pack(">H", num_gps_entries))
            ifd_gps.extend(struct.pack(">HHI", 2, 5, 3) + struct.pack(">I", offset_lat))
            ifd_gps.extend(struct.pack(">HHI", 1, 2, 2) + lat_ref + b"\x00\x00\x00")
            ifd_gps.extend(struct.pack(">HHI", 3, 2, 2) + lon_ref + b"\x00\x00\x00")
            ifd_gps.extend(struct.pack(">HHI", 4, 5, 3) + struct.pack(">I", offset_lon))
            ifd_gps.extend(struct.pack(">I", 0))  # Next IFD = 0

        # Assemble TIFF stream
        tiff_payload = tiff_header + bytes(ifd0) + bytes(ifd_exif) + bytes(ifd_gps) + bytes(heap)
        app1_payload = b"Exif\x00\x00" + tiff_payload
        app1_segment = b"\xFF\xE1" + struct.pack(">H", len(app1_payload) + 2) + app1_payload

        # Strip all legacy APP markers until raw image tables
        pos = 2
        while pos < len(raw_bytes) - 4 and raw_bytes[pos] == 0xFF and raw_bytes[pos+1] in [
            0xE0, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xEB, 0xEC, 0xED, 0xEE, 0xEF, 0xFE
        ]:
            seg_len = int.from_bytes(raw_bytes[pos+2:pos+4], "big")
            pos += 2 + seg_len

        clean_jpeg = b"\xFF\xD8" + app1_segment + raw_bytes[pos:]
        with open(file_path, "wb") as f_out:
            f_out.write(clean_jpeg)
        return True
    except Exception as e:
        logging.debug(f"Error in pure mobile JPEG injection for {file_path.name}: {e}")
        return False

# ==============================================================================
# NATIVE QUICKTIME SIBLING-META & DUAL-ECOSYSTEM ATOM INJECTION ENGINE
# ==============================================================================
def build_quicktime_text_atom(tag: bytes, text: str) -> bytes:
    """Builds a canonical QuickTime user data text atom (e.g., ©swr, ©too, ©art, ©aut)."""
    encoded = text.encode("utf-8", "replace")
    payload = struct.pack(">HH", len(encoded), 0x15C7) + encoded
    return struct.pack(">I4s", len(payload) + 8, tag) + payload

def build_apple_location_meta_box(loc: Tuple[float, float]) -> bytes:
    """
    Constructs the exact native Apple iOS QuickTime 'meta -> keys -> ilst -> data' box
    (152 bytes) matching native iPhone camera output:
    - hdlr: 34 bytes (mdir / appl)
    - keys: 60 bytes ('com.apple.quicktime.location.ISO6709')
    - ilst -> data: 50 bytes with localized 'SA\\x15\\xc7' + ISO 6709 coordinates.
    """
    lat, lon = loc
    lat_str = f"{lat:+08.4f}"
    lon_str = f"{lon:+09.4f}"
    coord_str = f"{lat_str}{lon_str}/".encode("ascii")

    data_payload = struct.pack(">I", 1) + b"SA\x15\xc7" + coord_str
    data_box = struct.pack(">I4s", len(data_payload) + 8, b"data") + data_payload

    item1_payload = struct.pack(">I", 1) + data_box
    item1_box = struct.pack(">I", len(item1_payload) + 4) + item1_payload

    ilst_box = struct.pack(">I4s", len(item1_box) + 8, b"ilst") + item1_box

    key_name = b"mdtacom.apple.quicktime.location.ISO6709"
    key_entry = struct.pack(">I", len(key_name) + 4) + key_name
    keys_payload = struct.pack(">II", 0, 1) + key_entry
    keys_box = struct.pack(">I4s", len(keys_payload) + 8, b"keys") + keys_payload

    hdlr_payload = struct.pack(">II4s4sIIH", 0, 0, b"mdir", b"appl", 0, 0, 0)
    hdlr_box = struct.pack(">I4s", len(hdlr_payload) + 8, b"hdlr") + hdlr_payload

    meta_payload = hdlr_box + keys_box + ilst_box
    meta_box = struct.pack(">I4s", len(meta_payload) + 8, b"meta") + meta_payload
    return meta_box

def inject_dual_gps_and_faststart(file_path: pathlib.Path, loc: Optional[Tuple[float, float]]) -> bool:
    """
    Unified dual-ecosystem injection engine matching native iPhone camera output:
    1. Injects ©xyz (30 bytes) inside udta for Android/Samsung.
    2. Injects Apple iOS meta (152 bytes) directly under moov as a sibling to udta.
    3. Safely shifts all stco and co64 chunk offset tables across audio and video tracks.
    4. Implements clean front-end byte slicing preserving 100% of mdat bytes.
    """
    if not file_path.exists() or file_path.suffix.lower() not in [".mp4", ".mov"]:
        return False

    has_location = loc is not None and not (abs(loc[0]) < 0.0001 and abs(loc[1]) < 0.0001)

    try:
        with open(file_path, "rb") as f:
            data = bytearray(f.read())

        file_len = len(data)
        if file_len < 64:
            return False

        if len(data) >= 12 and data[4:8] == b"ftyp":
            data[8:12] = b"qt  "

        pos = 0
        atoms = []
        while pos < file_len - 8:
            sz = struct.unpack(">I", data[pos:pos+4])[0]
            tag = data[pos+4:pos+8]
            if sz == 1:
                if pos + 16 > file_len: break
                sz = struct.unpack(">Q", data[pos+8:pos+16])[0]
            elif sz == 0:
                sz = file_len - pos

            if sz < 8 or pos + sz > file_len:
                break

            atoms.append((tag, pos, sz))
            pos += sz

        moov_entry = next((a for a in atoms if a[0] == b"moov"), None)
        mdat_entry = next((a for a in atoms if a[0] == b"mdat"), None)

        if not moov_entry or not mdat_entry:
            return False

        _, moov_start, moov_len = moov_entry
        _, mdat_start, mdat_len = mdat_entry

        moov_data = bytearray(data[moov_start : moov_start + moov_len])

        # 1. Android / Samsung: Inject ©xyz inside udta
        udta_boxes = bytearray()
        if has_location:
            lat, lon = loc
            lat_str = f"{lat:+08.4f}"
            lon_str = f"{lon:+09.4f}"
            coord_str = f"{lat_str}{lon_str}/".encode("ascii")
            xyz_payload = b"\x00\x12\x15\xc7" + coord_str
            udta_boxes.extend(struct.pack(">I4s", len(xyz_payload) + 8, b"\xa9xyz") + xyz_payload)

        if EXIF_SOFTWARE:
            udta_boxes.extend(build_quicktime_text_atom(b"\xa9swr", EXIF_SOFTWARE))
            udta_boxes.extend(build_quicktime_text_atom(b"\xa9too", EXIF_SOFTWARE))

        if EXIF_OWNER:
            udta_boxes.extend(build_quicktime_text_atom(b"\xa9art", EXIF_OWNER))
            udta_boxes.extend(build_quicktime_text_atom(b"\xa9aut", EXIF_OWNER))

        u_idx = moov_data.find(b"udta")
        if u_idx != -1 and u_idx >= 4:
            u_sz = struct.unpack(">I", moov_data[u_idx - 4 : u_idx])[0]
            new_udta = moov_data[u_idx - 4 : u_idx - 4 + u_sz] + bytes(udta_boxes)
            struct.pack_into(">I", new_udta, 0, len(new_udta))
            moov_data = moov_data[:u_idx - 4] + new_udta + moov_data[u_idx - 4 + u_sz:]
        else:
            new_udta = struct.pack(">I4s", 8 + len(udta_boxes), b"udta") + bytes(udta_boxes)
            moov_data.extend(new_udta)

        # 2. Apple iOS / iPhone: Inject meta directly under moov as a sibling to udta
        if has_location:
            apple_meta_box = build_apple_location_meta_box(loc)
            existing_meta_offset = -1
            pos = 8
            while pos < len(moov_data) - 8:
                b_sz = struct.unpack(">I", moov_data[pos:pos+4])[0]
                b_tag = moov_data[pos+4:pos+8]
                if b_tag == b"meta":
                    existing_meta_offset = pos
                    break
                if b_sz <= 1: break
                pos += b_sz

            if existing_meta_offset != -1:
                old_m_sz = struct.unpack(">I", moov_data[existing_meta_offset:existing_meta_offset+4])[0]
                moov_data = moov_data[:existing_meta_offset] + apple_meta_box + moov_data[existing_meta_offset + old_m_sz:]
            else:
                moov_data.extend(apple_meta_box)

        new_moov_len = len(moov_data)
        struct.pack_into(">I", moov_data, 0, new_moov_len)

        shift_amount = new_moov_len - moov_len
        if shift_amount <= 0:
            data[moov_start : moov_start + moov_len] = moov_data
            with open(file_path, "wb") as f_out: f_out.write(data)
            return True

        min_offset_to_shift = moov_start + moov_len

        # Update stco chunk offsets
        p = 0
        while True:
            idx = moov_data.find(b"stco", p)
            if idx == -1: break
            atom_start = idx - 4
            if atom_start >= 0 and idx + 12 <= len(moov_data):
                box_sz = struct.unpack(">I", moov_data[atom_start : atom_start + 4])[0]
                if box_sz == 0: box_sz = len(moov_data) - atom_start
                entry_count = struct.unpack(">I", moov_data[idx + 8 : idx + 12])[0]
                if box_sz >= 16 and (12 + entry_count * 4) <= box_sz:
                    for i in range(entry_count):
                        off_pos = idx + 12 + (i * 4)
                        if off_pos + 4 <= len(moov_data):
                            cur_off = struct.unpack(">I", moov_data[off_pos : off_pos + 4])[0]
                            if cur_off >= min_offset_to_shift:
                                struct.pack_into(">I", moov_data, off_pos, cur_off + shift_amount)
            p = idx + 4

        # Update co64 chunk offsets
        p = 0
        while True:
            idx = moov_data.find(b"co64", p)
            if idx == -1: break
            atom_start = idx - 4
            if atom_start >= 0 and idx + 12 <= len(moov_data):
                box_sz = struct.unpack(">I", moov_data[atom_start : atom_start + 4])[0]
                if box_sz == 0: box_sz = len(moov_data) - atom_start
                entry_count = struct.unpack(">I", moov_data[idx + 8 : idx + 12])[0]
                if box_sz >= 16 and (12 + entry_count * 8) <= box_sz:
                    for i in range(entry_count):
                        off_pos = idx + 12 + (i * 8)
                        if off_pos + 8 <= len(moov_data):
                            cur_off = struct.unpack(">Q", moov_data[off_pos : off_pos + 8])[0]
                            if cur_off >= min_offset_to_shift:
                                struct.pack_into(">Q", moov_data, off_pos, cur_off + shift_amount)
            p = idx + 4

        # Clean front-end byte slicing preserving 100% of mdat and trailing bytes
        final = data[:moov_start] + moov_data + data[moov_start + moov_len:]

        with open(file_path, "wb") as f_out:
            f_out.write(final)
        return True
    except Exception as err:
        logging.debug(f"Dual-GPS FastStart engine error for {file_path.name}: {err}")
        return False

def patch_mp4_creation_atom(file_path: pathlib.Path, dt_utc: datetime.datetime) -> bool:
    """Directly patches QuickTime MP4 creation time atoms ('mvhd', 'mdhd', 'tkhd')."""
    if not PATCH_MP4_METADATA or file_path.suffix.lower() not in [".mp4", ".mov"]:
        return False
    MAC_EPOCH_OFFSET = 2082844800
    target_ts = int(dt_utc.timestamp()) + MAC_EPOCH_OFFSET
    if target_ts < 0:
        return False

    try:
        file_size = file_path.stat().st_size
        if file_size < 16:
            return False

        CHUNK_SIZE = 1024 * 1024 * 8
        scan_regions: List[Tuple[int, int]] = [(0, min(file_size, CHUNK_SIZE))]
        
        if file_size > CHUNK_SIZE:
            tail_offset = max(0, file_size - CHUNK_SIZE)
            if tail_offset > scan_regions[0][1]:
                scan_regions.append((tail_offset, file_size))

        patched_any = False
        with open(file_path, "r+b") as f:
            for offset_start, offset_end in scan_regions:
                f.seek(offset_start)
                chunk = f.read(offset_end - offset_start)
                for atom in [b"mvhd", b"mdhd", b"tkhd"]:
                    start = 0
                    while True:
                        idx = chunk.find(atom, start)
                        if idx == -1:
                            break
                        if idx + 8 < len(chunk):
                            v = chunk[idx + 4]
                            actual_write_pos = offset_start + idx + 8
                            f.seek(actual_write_pos)
                            if v == 0:
                                f.write(target_ts.to_bytes(4, "big") * 2)
                                patched_any = True
                            elif v == 1:
                                f.write(target_ts.to_bytes(8, "big") * 2)
                                patched_any = True
                        start = idx + 4
        return patched_any
    except Exception as e:
        logging.debug(f"Failed to patch MP4 creation atom for {file_path.name}: {e}")
        return False

def tag_mp4_container_fast(src_file: pathlib.Path, dest_file: pathlib.Path, dt_utc: datetime.datetime, loc: Optional[Tuple[float, float]]) -> bool:
    """
    Remuxes via FFmpeg (-f mov -movflags +faststart) for pristine audio sync, followed by precise dual-ecosystem
    atom injection (`moov -> meta` sibling to udta for iOS and `moov -> udta -> ©xyz` for Android).
    """
    if not FFMPEG_BIN:
        return False
    try:
        creation_time_str = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_dest = dest_file.parent / f"tmp_tag_{os.getpid()}_{dest_file.name}"

        cmd = [
            FFMPEG_BIN, "-y", "-nostdin",
            "-i", str(src_file),
            "-c", "copy",
            "-f", "mov",  # Native QuickTime container structure for flawless iOS audio sync
            "-movflags", "+faststart",  # Places moov at front for clean atom insertion
            "-metadata", f"creation_time={creation_time_str}",
            "-metadata", f"title={VIDEO_METADATA_TITLE}",
            "-metadata", f"artist={EXIF_ARTIST}",
            "-metadata", f"author={EXIF_OWNER}",
            "-metadata", f"software={EXIF_SOFTWARE}",
            "-metadata", f"encoder={EXIF_SOFTWARE}",
            "-metadata", f"comment={EXIF_SOFTWARE}",
            "-metadata", f"description={EXIF_SOFTWARE}",
            "-metadata", f"copyright={EXIF_COPYRIGHT}",
            str(tmp_dest)
        ]

        extra_kwargs = {}
        if sys.platform.startswith("win"):
            extra_kwargs["creationflags"] = subprocess.IDLE_PRIORITY_CLASS

        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25, **extra_kwargs)
        if res.returncode == 0 and tmp_dest.exists() and tmp_dest.stat().st_size > 1000:
            if dest_file.exists():
                dest_file.unlink()
            tmp_dest.rename(dest_file)
            patch_mp4_creation_atom(dest_file, dt_utc)
            inject_dual_gps_and_faststart(dest_file, loc)
            return True
        else:
            if tmp_dest.exists():
                tmp_dest.unlink()
            return False
    except Exception as e:
        logging.debug(f"Fast MP4 container tagging note: {e}")
        return False

def update_file_timestamps(target_file: pathlib.Path, dt_local: datetime.datetime) -> None:
    """Sets filesystem modification and access timestamps to capture time."""
    if not SET_FS_TIMESTAMPS:
        return
    try:
        ts = dt_local.timestamp()
        os.utime(str(target_file), (ts, ts))
    except Exception:
        pass

def compute_fast_hash(data_bytes: bytes) -> str:
    """Computes a quick SHA-256 fingerprint for deduplication."""
    h = hashlib.sha256()
    h.update(data_bytes[:524288])
    h.update(len(data_bytes).to_bytes(8, "big"))
    return h.hexdigest()

def get_normalized_stem(filename: str) -> str:
    """Strips -main, _main, -overlay, _overlay, copy indicators from stems."""
    stem = pathlib.Path(filename).stem
    clean = re.sub(r'[-_](main|overlay)$', '', stem, flags=re.IGNORECASE)
    clean = re.sub(r'\s*\(\d+\)$', '', clean)
    return clean.strip().upper()

# ==============================================================================
# MEDIA ITEM REPRESENTATION (FULL NATIVE ZIP & IN-MEMORY CACHE SUPPORT)
# ==============================================================================
class MediaItem:
    def __init__(self, filename: str, is_zip: bool, zip_path: Optional[pathlib.Path] = None, disk_path: Optional[pathlib.Path] = None, zip_member_path: Optional[str] = None, zip_datetime: Optional[datetime.datetime] = None):
        self.filename = filename
        self.is_zip = is_zip
        self.zip_path = zip_path
        self.disk_path = disk_path
        self.zip_member_path = zip_member_path or filename
        self.zip_datetime = zip_datetime
        self.ext = pathlib.Path(filename).suffix.lower()
        self.is_overlay = self.ext == ".png" or "-overlay" in filename.lower() or "_overlay" in filename.lower()
        
        fl = filename.lower()
        self.is_thumbnail = ("thumbnail" in fl) or ("thumb~" in fl) or ("_thumb" in fl)
        self.clean_stem = get_normalized_stem(filename)
        
        m_uuid = UUID_REGEX.search(filename)
        self.uuid = m_uuid.group(1).upper() if m_uuid else None

        self.filename_datetime = None
        m_time = FULL_TIMESTAMP_REGEX.search(filename)
        if m_time:
            try:
                self.filename_datetime = datetime.datetime(
                    year=int(m_time.group("year")),
                    month=int(m_time.group("month")),
                    day=int(m_time.group("day")),
                    hour=int(m_time.group("hour")),
                    minute=int(m_time.group("min")),
                    second=int(m_time.group("sec"))
                )
            except ValueError:
                self.filename_datetime = None

    def read_bytes(self) -> bytes:
        if self.is_zip and self.zip_path:
            try:
                zf = get_cached_zip(self.zip_path)
                with ZIP_CACHE_LOCK:
                    return zf.read(self.zip_member_path)
            except Exception as e:
                logging.debug(f"Zip read failed for {self.zip_member_path} in {self.zip_path.name}: {e}")
                return b""
        elif self.disk_path:
            try:
                with open(self.disk_path, "rb") as f:
                    return f.read()
            except Exception as e:
                logging.debug(f"Disk read failed for {self.disk_path}: {e}")
                return b""
        return b""

    def write_to_temp(self) -> pathlib.Path:
        temp_dir = pathlib.Path(tempfile.gettempdir())
        suffix = self.ext if self.ext else ".bin"
        temp_file = temp_dir / f"snap_tmp_{os.getpid()}_{threading.get_ident()}_{hashlib.md5(self.filename.encode()).hexdigest()[:8]}{suffix}"
        if self.is_zip and self.zip_path:
            zf = get_cached_zip(self.zip_path)
            with ZIP_CACHE_LOCK:
                with zf.open(self.zip_member_path) as src, open(temp_file, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        elif self.disk_path:
            shutil.copy2(self.disk_path, temp_file)
        return temp_file

    def get_fallback_datetime(self) -> datetime.datetime:
        if self.filename_datetime:
            return self.filename_datetime
        
        m = DATE_PREFIX_REGEX.match(self.filename)
        if m:
            try:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if self.zip_datetime:
                    return datetime.datetime(y, mo, d, self.zip_datetime.hour, self.zip_datetime.minute, self.zip_datetime.second)
                if self.disk_path:
                    mtime = datetime.datetime.fromtimestamp(self.disk_path.stat().st_mtime)
                    return datetime.datetime(y, mo, d, mtime.hour, mtime.minute, mtime.second)
                return datetime.datetime(y, mo, d, 12, 0, 0)
            except Exception:
                pass

        if self.zip_datetime:
            return self.zip_datetime
        if self.disk_path:
            return datetime.datetime.fromtimestamp(self.disk_path.stat().st_mtime)
        return datetime.datetime.now()

# ==============================================================================
# COMPOSITING ENGINES (PILLOW + HARDWARE GPU ACCELERATED FFMPEG)
# ==============================================================================
def get_video_dimensions(video_path: pathlib.Path) -> Tuple[int, int]:
    """Probes exact video frame dimensions and enforces even integer boundaries."""
    if not FFMPEG_BIN:
        return 1080, 1920
    try:
        cmd = [FFMPEG_BIN, "-i", str(video_path)]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, encoding="utf-8", errors="ignore")
        is_rotated = "rotation of -90" in res.stderr or "rotation of 90" in res.stderr or "rotation of 270" in res.stderr
        m = re.search(r'Video:.*? ([0-9]{2,5})x([0-9]{2,5})', res.stderr)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
            if is_rotated and w > h:
                w, h = h, w
            return (w // 2) * 2, (h // 2) * 2
    except Exception:
        pass
    return 1080, 1920

def probe_file_duration(file_path: pathlib.Path) -> float:
    """Verifies output video duration in seconds to prevent 0-second file corruption."""
    if not FFMPEG_BIN or not file_path.exists():
        return 0.0
    try:
        cmd = [FFMPEG_BIN, "-i", str(file_path)]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, encoding="utf-8", errors="ignore")
        m = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', res.stderr)
        if m:
            return float(m.group(1)) * 3600 + float(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return 0.0

def merge_overlay_image(main_bytes: bytes, overlay_bytes: bytes) -> Optional[bytes]:
    """Blends transparent overlay PNG onto photo with EXIF rotation transposition."""
    if not HAS_PILLOW:
        return None
    try:
        base_img = ImageOps.exif_transpose(Image.open(io.BytesIO(main_bytes))).convert("RGBA")
        over_img = ImageOps.exif_transpose(Image.open(io.BytesIO(overlay_bytes))).convert("RGBA")
        if base_img.size != over_img.size:
            over_img = over_img.resize(base_img.size, getattr(Image, "Resampling", Image).LANCZOS)
        combined = Image.alpha_composite(base_img, over_img).convert("RGB")
        out_buf = io.BytesIO()
        combined.save(out_buf, format="JPEG", quality=96, optimize=True)
        return out_buf.getvalue()
    except Exception as e:
        logging.debug(f"Image overlay merge failed: {e}")
        return None

def merge_overlay_video(main_item: MediaItem, overlay_item: MediaItem, dest_file: pathlib.Path, dt_utc: datetime.datetime, loc: Optional[Tuple[float, float]]) -> bool:
    """Merges video and overlay via GPU with native QuickTime muxing and dual GPS injection."""
    if not FFMPEG_BIN:
        return False

    temp_video = None
    temp_overlay = None
    try:
        temp_video = main_item.write_to_temp()
        orig_dur = probe_file_duration(temp_video)
        w, h = get_video_dimensions(temp_video)

        over_bytes = overlay_item.read_bytes()
        temp_overlay = pathlib.Path(tempfile.gettempdir()) / f"snap_ov_{os.getpid()}_{threading.get_ident()}_{hashlib.md5(overlay_item.filename.encode()).hexdigest()[:8]}.png"

        if HAS_PILLOW:
            with Image.open(io.BytesIO(over_bytes)) as im:
                im_trans = ImageOps.exif_transpose(im).convert("RGBA")
                if im_trans.size != (w, h):
                    im_trans = im_trans.resize((w, h), getattr(Image, "Resampling", Image).BILINEAR)
                im_trans.save(temp_overlay, "PNG")
        else:
            with open(temp_overlay, "wb") as f_ov:
                f_ov.write(over_bytes)

        creation_time_str = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        filter_complex = f"[0:v]setpts=PTS-STARTPTS[base];[base][1:v]overlay=0:0:shortest=1,format=nv12[v_out]"
        device_prefix = get_qsv_device_global_args() if ACTIVE_ENCODER == "h264_qsv" else []

        cmd = [
            FFMPEG_BIN,
            "-y",
            "-nostdin",
            *device_prefix,
            "-fflags", "+genpts+discardcorrupt",
            "-threads", "1",
            "-filter_threads", "1",
            "-i", str(temp_video),
            "-loop", "1",
            "-i", str(temp_overlay),
            "-filter_complex", filter_complex,
            "-map", "[v_out]",
            "-map", "0:a?",
            "-c:v", ACTIVE_ENCODER,
            *ACTIVE_ENCODER_ARGS,
            "-pix_fmt", "nv12" if "qsv" in ACTIVE_ENCODER else "yuv420p",
            "-c:a", "copy",
            "-f", "mov",
            "-movflags", "+faststart",
            "-metadata", f"creation_time={creation_time_str}",
            "-metadata", f"title={VIDEO_METADATA_TITLE}",
            "-metadata", f"artist={EXIF_ARTIST}",
            "-metadata", f"author={EXIF_OWNER}",
            "-metadata", f"software={EXIF_SOFTWARE}",
            "-metadata", f"encoder={EXIF_SOFTWARE}",
            "-metadata", f"comment={EXIF_SOFTWARE}",
            "-metadata", f"description={EXIF_SOFTWARE}",
            "-metadata", f"copyright={EXIF_COPYRIGHT}",
            "-shortest",
            str(dest_file)
        ]

        extra_kwargs = {}
        if sys.platform.startswith("win"):
            extra_kwargs["creationflags"] = subprocess.IDLE_PRIORITY_CLASS

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            **extra_kwargs
        )

        dynamic_timeout = max(VIDEO_PROCESS_TIMEOUT_SECONDS, int(orig_dur * 4)) if orig_dur > 0 else VIDEO_PROCESS_TIMEOUT_SECONDS

        try:
            stdout, stderr = proc.communicate(timeout=dynamic_timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            logging.warning(f"Video {main_item.filename} exceeded dynamic timeout ({dynamic_timeout}s). Terminated safely.")
            return False

        if proc.returncode == 0 and dest_file.exists() and dest_file.stat().st_size > 15000:
            dur = probe_file_duration(dest_file)
            if dur > 0.5:
                patch_mp4_creation_atom(dest_file, dt_utc)
                inject_dual_gps_and_faststart(dest_file, loc)
                return True
            else:
                dest_file.unlink(missing_ok=True)
                return False
        else:
            if dest_file.exists():
                dest_file.unlink(missing_ok=True)
            return False
    except Exception as err:
        logging.debug(f"Video overlay merge exception: {err}")
        return False
    finally:
        for tmp in [temp_video, temp_overlay]:
            if tmp and tmp.exists():
                try: tmp.unlink()
                except Exception: pass

# ==============================================================================
# PIPELINE EXECUTION ENGINE (ORGANIZER)
# ==============================================================================
def extract_snap_memory_id(filename: str) -> str:
    """Extracts the immutable core memory token ensuring paired files share the exact key."""
    m = UUID_REGEX.search(filename)
    if m:
        return f"UUID-{m.group(1).upper()}"
    
    m_b = re.search(r'b~([A-Za-z0-9_\-]{26,34})', filename)
    if m_b:
        return f"BTOKEN-{m_b.group(1).upper()}"

    m_time = FULL_TIMESTAMP_REGEX.search(filename)
    if m_time:
        dt_key = f"{m_time.group('year')}-{m_time.group('month')}-{m_time.group('day')}-{m_time.group('hour')}-{m_time.group('min')}-{m_time.group('sec')}"
        return f"TIME-{dt_key}"

    clean = pathlib.Path(filename).stem
    clean = re.sub(r'[-_](main|overlay|thumb|thumbnail)$', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^\d{4}[-_]\d{2}[-_]\d{2}[-_]?', '', clean)
    clean = re.sub(r'^(media|overlay|thumbnail|thumb)[~_-]?', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^zip[-_~]?', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^b~', '', clean)
    clean = re.sub(r'\s*\(\d+\)$', '', clean)
    clean = clean.strip().upper()
    if len(clean) >= 26:
        clean = clean[:30]
    if clean:
        return f"TOKEN-{clean}"

    return f"FILE-{pathlib.Path(filename).stem.upper()}"

def process_snapchat_memories(source_dir: pathlib.Path, output_dir: pathlib.Path, dry_run: bool = False) -> None:
    """Executes media organization, pairing, compositing, mosaic duplicate removal, and detailed audit logging."""
    registry = build_metadata_index(source_dir)
    valid_exts = {".jpg", ".jpeg", ".mp4", ".mov", ".png"}

    log_console("📂 Discovering media files across folders, subdirectories, and ZIPs...", "info", CLR_CYAN)
    items: List[MediaItem] = []
    zip_items_map: Dict[str, MediaItem] = {}

    if source_dir.is_file() and source_dir.suffix.lower() == ".zip":
        zip_files = [source_dir]
    else:
        zip_files = list(source_dir.glob("*.zip")) + list(source_dir.glob("**/*.zip"))

    # 1. Discover items from ZIP archives first (preserves authentic server timestamps)
    for zf in set(zip_files):
        try:
            cached_z = get_cached_zip(zf)
            with ZIP_CACHE_LOCK:
                for zinfo in cached_z.infolist():
                    zname = zinfo.filename
                    ext = pathlib.Path(zname).suffix.lower()
                    if ext in valid_exts and not zname.endswith("/"):
                        zip_dt = None
                        if zinfo.date_time and zinfo.date_time[0] >= 1980:
                            y = zinfo.date_time[0]
                            # Sanitize MS-DOS epoch wrap-around for pre-1980 dates incorrectly wrapped as future years (e.g. 2098)
                            if y <= datetime.datetime.now().year + 1:
                                try:
                                    zip_dt = datetime.datetime(*zinfo.date_time)
                                except Exception:
                                    zip_dt = None
                        m_item = MediaItem(
                            filename=pathlib.Path(zname).name,
                            is_zip=True,
                            zip_path=zf,
                            zip_member_path=zname,
                            zip_datetime=zip_dt
                        )
                        zip_items_map[m_item.filename.lower()] = m_item
                        items.append(m_item)
        except Exception as e:
            logging.debug(f"Failed to inspect zip {zf.name}: {e}")

    # 2. Discover items from disk (shadow-ignore loose unzipped duplicates to block mtime corruption)
    if source_dir.is_dir():
        for root, _, files in os.walk(source_dir):
            for file in files:
                p = pathlib.Path(root) / file
                fl_lower = file.lower()
                if p.suffix.lower() in valid_exts:
                    if fl_lower in zip_items_map:
                        continue
                    items.append(MediaItem(p.name, is_zip=False, disk_path=p))

    if not items:
        log_console("❌ No media files found in the specified source directory.", "warning", CLR_YELLOW)
        close_all_cached_zips()
        return

    log_console(f"🎯 Total media files discovered: {len(items)}", "info", CLR_GREEN)

    grouped_items: Dict[str, Dict[str, List[MediaItem]]] = {}
    purged_thumbnails_count = 0

    for item in items:
        if item.is_thumbnail and PURGE_VIDEO_THUMBNAILS:
            purged_thumbnails_count += 1
            continue

        group_key = extract_snap_memory_id(item.filename)
        if group_key not in grouped_items:
            grouped_items[group_key] = {"videos": [], "photos": [], "overlays": []}
        
        if item.is_overlay:
            grouped_items[group_key]["overlays"].append(item)
        elif item.ext in [".mp4", ".mov"]:
            grouped_items[group_key]["videos"].append(item)
        elif item.ext in [".jpg", ".jpeg"]:
            grouped_items[group_key]["photos"].append(item)

    # 3. Synchronize authentic server timestamps across companion files in the same memory group
    for g_key, group in grouped_items.items():
        best_server_dt = None
        for sub_list in group.values():
            for m in sub_list:
                if m.zip_datetime:
                    best_server_dt = m.zip_datetime
                    break
            if best_server_dt:
                break
        if best_server_dt:
            for sub_list in group.values():
                for m in sub_list:
                    if not m.zip_datetime:
                        m.zip_datetime = best_server_dt

        group["videos"].sort(key=lambda x: (x.zip_datetime is not None, x.is_zip), reverse=True)
        group["photos"].sort(key=lambda x: (x.zip_datetime is not None, x.is_zip), reverse=True)

    if purged_thumbnails_count > 0:
        log_console(f"🧹 Ignored {purged_thumbnails_count} video thumbnail stills to prevent duplicate photos.", "info", CLR_CYAN)

    print(f"{CLR_CYAN}{MINI_DIVIDER}{CLR_RESET}")
    log_console(f"🧩 Parallel GPU Pipelines: {GPU_CONCURRENT_WORKERS} Concurrent Streams", "info", CLR_GREEN)
    log_console(f"⚡ Hardware Encode      : {ACTIVE_ENCODER_LABEL}", "info", CLR_GREEN)
    log_console(f"🛡️ Smart Cleaner       : Burst-safe deduplication & mosaic purge", "info", CLR_CYAN)
    log_console(f"🚀 Processing {len(grouped_items)} consolidated memory units...", "info", CLR_CYAN)

    success_count = 0
    skipped_count = 0
    duplicate_count = 0
    discarded_overlay_count = 0
    seen_hashes = set()
    name_registry: Dict[str, int] = {}
    
    audit_json_matches = 0
    audit_fallback_matches = 0
    audit_gps_tagged = 0
    audit_gps_dummy_skipped = 0
    audit_gps_missing = 0

    MERGED_MEMORY_KEYS = set()
    MERGED_VIDEO_TIMESTAMPS = set()
    MERGED_PHOTO_TIMESTAMPS = set()
    COMMITTED_VIDEO_TIMESTAMPS = set()

    REGISTRY_LOCK = threading.Lock()
    PROGRESS_LOCK = threading.Lock()

    def resolve_item_metadata(item: MediaItem) -> Tuple[datetime.datetime, datetime.datetime, Optional[Tuple[float, float]], str]:
        """Queries JSON Registry with candidate timestamps, mtime, and ZipInfo."""
        nonlocal audit_json_matches, audit_fallback_matches
        meta = None
        match_reason = "NO_MATCH"

        token_candidates: List[str] = []
        if item.uuid: token_candidates.append(item.uuid)
        if item.clean_stem: token_candidates.append(item.clean_stem)

        for tok in token_candidates:
            meta, match_reason = registry.query(token=tok)
            if meta: break

        if not meta:
            date_candidates: List[Tuple[str, datetime.datetime]] = []
            if item.zip_datetime: date_candidates.append(("zip_dt", item.zip_datetime))
            if item.filename_datetime: date_candidates.append(("filename_dt", item.filename_datetime))

            fallback_dt = item.get_fallback_datetime()
            if fallback_dt: date_candidates.append(("fallback_mtime", fallback_dt))

            for label, dt_c in date_candidates:
                meta, reason = registry.query(dt_candidate=dt_c)
                if meta:
                    match_reason = f"{label}->{reason}"
                    break

        if meta:
            with REGISTRY_LOCK: audit_json_matches += 1
            return meta.dt_local, meta.dt_utc, meta.location, f"Tier1({match_reason})"

        with REGISTRY_LOCK: audit_fallback_matches += 1

        if item.zip_datetime:
            dt_u = item.zip_datetime
            dt_loc = dt_u + datetime.timedelta(hours=TIMEZONE_OFFSET_HOURS)
            return dt_loc, dt_u, None, "Tier2(ZipFallback)"

        if item.filename_datetime:
            dt_loc = item.filename_datetime
            dt_u = dt_loc - datetime.timedelta(hours=TIMEZONE_OFFSET_HOURS)
            return dt_loc, dt_u, None, "Tier2(FilenameFallback)"

        dt_fb = item.get_fallback_datetime()
        return dt_fb, dt_fb - datetime.timedelta(hours=TIMEZONE_OFFSET_HOURS), None, "Tier2(TimestampFallback)"

    def get_destination_path(dt_local: datetime.datetime, ext: str) -> pathlib.Path:
        year = dt_local.year
        month_str = f"{dt_local.month:02d}"
        
        if CLASSIFY_MONTHLY_FOLDERS:
            target_folder = output_dir / f"{YEAR_FOLDER_PREFIX}{year}" / month_str
        else:
            target_folder = output_dir / f"{YEAR_FOLDER_PREFIX}{year}"
            
        base_name = dt_local.strftime("%Y-%m-%d-%H-%M-%S")
        combo_key = f"{year}-{month_str if CLASSIFY_MONTHLY_FOLDERS else 'root'}-{base_name}{ext}"
        
        with REGISTRY_LOCK:
            if combo_key in name_registry:
                name_registry[combo_key] += 1
                filename = f"{base_name}-{name_registry[combo_key]:02d}{ext}"
            else:
                name_registry[combo_key] = 0
                filename = f"{base_name}{ext}"
        return target_folder / filename

    def commit_media(data_bytes: bytes, dt_local: datetime.datetime, dt_utc: datetime.datetime,
                     loc: Optional[Tuple[float, float]], ext: str, match_method: str,
                     original_disk_path: Optional[pathlib.Path] = None, raw_media_item: Optional[MediaItem] = None):
        nonlocal success_count, duplicate_count, audit_gps_tagged, audit_gps_dummy_skipped, audit_gps_missing

        if not data_bytes and not original_disk_path:
            return

        item_name = raw_media_item.filename if raw_media_item else (original_disk_path.name if original_disk_path else "memory")

        if ENABLE_DEDUPLICATION:
            sample_bytes = data_bytes if data_bytes else (raw_media_item.read_bytes() if raw_media_item else b"")
            h = compute_fast_hash(sample_bytes) if sample_bytes else None
            with REGISTRY_LOCK:
                if h and h in seen_hashes:
                    duplicate_count += 1
                    return
                if h: seen_hashes.add(h)

        dest_file = get_destination_path(dt_local, ext)
        if dry_run:
            with PROGRESS_LOCK: success_count += 1
            return

        dest_file.parent.mkdir(parents=True, exist_ok=True)
        gps_status_msg = ""
        tag_status_msg = ""

        if loc:
            lat, lon = loc
            if not (abs(lat) < 0.0001 and abs(lon) < 0.0001):
                gps_status_msg = f"GPS({lat:.4f},{lon:.4f})"
            else:
                gps_status_msg = "GPS(Skipped 0,0 Dummy)"
                with REGISTRY_LOCK: audit_gps_dummy_skipped += 1
                loc = None
        else:
            gps_status_msg = "GPS(None in Record)"
            with REGISTRY_LOCK: audit_gps_missing += 1

        # ----------------------------------------------------------------------
        # Process MP4 / MOV Video Files (Native QuickTime Sibling Meta + Dual GPS)
        # ----------------------------------------------------------------------
        if ext in [".mp4", ".mov"]:
            tagged_ok = False
            temp_in = None
            try:
                if original_disk_path and original_disk_path.exists():
                    source_for_ffmpeg = original_disk_path
                else:
                    temp_in = raw_media_item.write_to_temp() if raw_media_item else None
                    source_for_ffmpeg = temp_in

                if source_for_ffmpeg:
                    tagged_ok = tag_mp4_container_fast(source_for_ffmpeg, dest_file, dt_utc, loc)
            finally:
                if temp_in and temp_in.exists():
                    try: temp_in.unlink()
                    except Exception: pass

            if not tagged_ok:
                if original_disk_path and OPERATION_MODE.lower() == "move":
                    shutil.move(str(original_disk_path), str(dest_file))
                else:
                    b_write = data_bytes if data_bytes else (raw_media_item.read_bytes() if raw_media_item else b"")
                    with open(dest_file, "wb") as f_out: f_out.write(b_write)
                tag_status_msg = "MP4(Raw Copy Fallback)"
            else:
                tag_status_msg = "MP4(QuickTime Remux + Perfect iOS Audio & GPS)"
                if original_disk_path and OPERATION_MODE.lower() == "move" and original_disk_path.exists():
                    try: original_disk_path.unlink()
                    except Exception: pass

            if loc:
                with REGISTRY_LOCK: audit_gps_tagged += 1

        # ----------------------------------------------------------------------
        # Process JPEG Photos (Strict 12-byte TIFF IFD Dynamic Synthesis)
        # ----------------------------------------------------------------------
        else:
            if original_disk_path and OPERATION_MODE.lower() == "move" and not data_bytes:
                shutil.move(str(original_disk_path), str(dest_file))
            else:
                b_write = data_bytes if data_bytes else (raw_media_item.read_bytes() if raw_media_item else b"")
                with open(dest_file, "wb") as f_out:
                    f_out.write(b_write)

            exif_written = False
            if ext in [".jpg", ".jpeg"] and (UPDATE_EXIF_TAGS or UPDATE_GPS_TAGS):
                exif_written = write_clean_mobile_jpeg(dest_file, dt_local, loc)

            tag_status_msg = "JPEG(Strict Mobile EXIF)" if (exif_written and loc) else ("JPEG(Tagged)" if exif_written else "JPEG(Raw)")

            if loc:
                with REGISTRY_LOCK: audit_gps_tagged += 1

        if SET_FS_TIMESTAMPS:
            update_file_timestamps(dest_file, dt_local)

        logging.info(f"AUDIT | {item_name} -> {dest_file.name} | {match_method} | {gps_status_msg} | {tag_status_msg}")
            
        with PROGRESS_LOCK:
            success_count += 1

    total_tasks = len(grouped_items)
    curr_task = 0

    def report_progress():
        nonlocal curr_task
        with PROGRESS_LOCK:
            curr_task += 1
            is_final_stretch = curr_task > (total_tasks - 35)
            if (curr_task % 25 == 0) or is_final_stretch or (curr_task == total_tasks):
                pct = (curr_task / total_tasks) * 100
                log_console(f"⏳ Processed: {curr_task}/{total_tasks} ({pct:.1f}%)", "info", CLR_WHITE)

    phase1_groups = []
    phase2_groups = []

    for group_key, group in grouped_items.items():
        if group.get("overlays") and (group.get("videos") or group.get("photos")):
            phase1_groups.append((group_key, group))
        else:
            phase2_groups.append((group_key, group))

    def process_phase1(group_tuple: Tuple[str, Dict[str, List[MediaItem]]]):
        nonlocal success_count, skipped_count, duplicate_count, discarded_overlay_count, audit_gps_tagged
        group_key, group = group_tuple
        videos = group.get("videos", [])
        photos = group.get("photos", [])
        overlays = group.get("overlays", [])

        if videos and photos:
            with REGISTRY_LOCK: duplicate_count += len(photos)
            photos = []

        try:
            if videos and overlays and MERGE_VIDEO_OVERLAYS and FFMPEG_BIN:
                primary_video = videos[0]
                primary_overlay = overlays[0]
                dt_loc, dt_u, loc, match_method = resolve_item_metadata(primary_video)
                dest_file = get_destination_path(dt_loc, primary_video.ext)
                time_key = dt_loc.strftime("%Y-%m-%d-%H-%M-%S")

                raw_video_bytes = primary_video.read_bytes()
                raw_hash = compute_fast_hash(raw_video_bytes) if raw_video_bytes else None

                if not dry_run:
                    merged_ok = merge_overlay_video(primary_video, primary_overlay, dest_file, dt_u, loc)
                    if merged_ok:
                        if SET_FS_TIMESTAMPS:
                            update_file_timestamps(dest_file, dt_loc)
                        with PROGRESS_LOCK: success_count += 1
                        if loc:
                            with REGISTRY_LOCK: audit_gps_tagged += 1

                        gps_msg = f"GPS({loc[0]:.4f},{loc[1]:.4f})" if loc else "GPS(None)"
                        logging.info(f"AUDIT | MERGED_VIDEO: {primary_video.filename} -> {dest_file.name} | {match_method} | {gps_msg} | Hardware GPU Merge")

                        with REGISTRY_LOCK:
                            if raw_hash: seen_hashes.add(raw_hash)
                            MERGED_MEMORY_KEYS.add(group_key)
                            MERGED_VIDEO_TIMESTAMPS.add(time_key)
                            COMMITTED_VIDEO_TIMESTAMPS.add(time_key)

                        if DISCARD_UNMERGED_DUPLICATES and len(videos) > 1:
                            with REGISTRY_LOCK: duplicate_count += (len(videos) - 1)
                        if DISCARD_ORPHAN_OVERLAYS or PURGE_ALL_OVERLAYS_COMPLETELY:
                            with PROGRESS_LOCK: discarded_overlay_count += len(overlays)
                    else:
                        commit_media(raw_video_bytes, dt_loc, dt_u, loc, primary_video.ext, match_method, original_disk_path=primary_video.disk_path, raw_media_item=primary_video)
                        with PROGRESS_LOCK: discarded_overlay_count += len(overlays)
                else:
                    with PROGRESS_LOCK: success_count += 1

            elif photos and overlays and MERGE_IMAGE_OVERLAYS and HAS_PILLOW:
                primary_photo = photos[0]
                primary_overlay = overlays[0]
                dt_loc, dt_u, loc, match_method = resolve_item_metadata(primary_photo)
                time_key = dt_loc.strftime("%Y-%m-%d-%H-%M-%S")

                raw_photo_bytes = primary_photo.read_bytes()
                raw_hash = compute_fast_hash(raw_photo_bytes) if raw_photo_bytes else None
                merged_bytes = merge_overlay_image(raw_photo_bytes, primary_overlay.read_bytes())
                
                if merged_bytes:
                    commit_media(merged_bytes, dt_loc, dt_u, loc, ".jpg", match_method, original_disk_path=primary_photo.disk_path, raw_media_item=primary_photo)
                    with REGISTRY_LOCK:
                        if raw_hash: seen_hashes.add(raw_hash)
                        MERGED_MEMORY_KEYS.add(group_key)
                        MERGED_PHOTO_TIMESTAMPS.add(time_key)

                    if DISCARD_UNMERGED_DUPLICATES and len(photos) > 1:
                        with REGISTRY_LOCK: duplicate_count += (len(photos) - 1)
                    if DISCARD_ORPHAN_OVERLAYS or PURGE_ALL_OVERLAYS_COMPLETELY:
                        with PROGRESS_LOCK: discarded_overlay_count += len(overlays)
                else:
                    commit_media(raw_photo_bytes, dt_loc, dt_u, loc, primary_photo.ext, match_method, original_disk_path=primary_photo.disk_path, raw_media_item=primary_photo)

        except Exception as err:
            with PROGRESS_LOCK: skipped_count += 1
            logging.error(f"Error processing phase 1 group {group_key}: {err}\n{traceback.format_exc()}")
        finally:
            report_progress()

    def process_phase2(group_tuple: Tuple[str, Dict[str, List[MediaItem]]]):
        nonlocal success_count, skipped_count, duplicate_count, discarded_overlay_count
        group_key, group = group_tuple
        videos = group.get("videos", [])
        photos = group.get("photos", [])
        overlays = group.get("overlays", [])

        try:
            if videos:
                for v_idx, current_video in enumerate(videos):
                    dt_loc, dt_u, loc, match_method = resolve_item_metadata(current_video)
                    time_key = dt_loc.strftime("%Y-%m-%d-%H-%M-%S")
                    raw_bytes = current_video.read_bytes()
                    raw_hash = compute_fast_hash(raw_bytes) if raw_bytes else None

                    with REGISTRY_LOCK:
                        is_mosaic_dup = (
                            (raw_hash and raw_hash in seen_hashes)
                            or (group_key in MERGED_MEMORY_KEYS)
                            or (time_key in MERGED_VIDEO_TIMESTAMPS and v_idx > 0)
                        )

                    if is_mosaic_dup and DISCARD_UNMERGED_DUPLICATES:
                        with REGISTRY_LOCK: duplicate_count += 1
                    else:
                        commit_media(raw_bytes, dt_loc, dt_u, loc, current_video.ext, match_method, original_disk_path=current_video.disk_path, raw_media_item=current_video)
                        with REGISTRY_LOCK: COMMITTED_VIDEO_TIMESTAMPS.add(time_key)

            elif photos:
                for p_idx, current_photo in enumerate(photos):
                    dt_loc, dt_u, loc, match_method = resolve_item_metadata(current_photo)
                    time_key = dt_loc.strftime("%Y-%m-%d-%H-%M-%S")
                    raw_bytes = current_photo.read_bytes()
                    raw_hash = compute_fast_hash(raw_bytes) if raw_bytes else None

                    with REGISTRY_LOCK:
                        is_thumb_of_video = (time_key in COMMITTED_VIDEO_TIMESTAMPS) or (time_key in MERGED_VIDEO_TIMESTAMPS)
                        is_photo_dup = (
                            (raw_hash and raw_hash in seen_hashes)
                            or (group_key in MERGED_MEMORY_KEYS)
                            or is_thumb_of_video
                        )

                    if is_photo_dup and (DISCARD_UNMERGED_DUPLICATES or PURGE_VIDEO_THUMBNAILS):
                        with REGISTRY_LOCK: duplicate_count += 1
                    else:
                        commit_media(raw_bytes, dt_loc, dt_u, loc, current_photo.ext, match_method, original_disk_path=current_photo.disk_path, raw_media_item=current_photo)
                        with REGISTRY_LOCK: MERGED_PHOTO_TIMESTAMPS.add(time_key)

            elif overlays:
                if DISCARD_ORPHAN_OVERLAYS or PURGE_ALL_OVERLAYS_COMPLETELY:
                    with PROGRESS_LOCK: discarded_overlay_count += len(overlays)
                else:
                    for ov in overlays:
                        dt_loc, dt_u, loc, match_method = resolve_item_metadata(ov)
                        commit_media(ov.read_bytes(), dt_loc, dt_u, loc, ov.ext, match_method, original_disk_path=ov.disk_path, raw_media_item=ov)

        except Exception as err:
            with PROGRESS_LOCK: skipped_count += 1
            logging.error(f"Error processing phase 2 group {group_key}: {err}\n{traceback.format_exc()}")
        finally:
            report_progress()

    worker_threads = max(1, GPU_CONCURRENT_WORKERS)
    try:
        if phase1_groups:
            with ThreadPoolExecutor(max_workers=worker_threads) as executor:
                for item in phase1_groups: executor.submit(process_phase1, item)

        if phase2_groups:
            with ThreadPoolExecutor(max_workers=worker_threads) as executor:
                for item in phase2_groups: executor.submit(process_phase2, item)
    finally:
        close_all_cached_zips()

    print(f"{CLR_CYAN}{MINI_DIVIDER}{CLR_RESET}")
    log_console(f"✅ Success: {success_count} media files organized & merged.", "info", CLR_GREEN)
    if discarded_overlay_count > 0:
        log_console(f"🧹 Cleaned up: {discarded_overlay_count} black/orphan overlay PNGs removed.", "info", CLR_CYAN)
    if duplicate_count > 0:
        log_console(f"🧹 Duplicates Purged: {duplicate_count} unmerged/mosaic duplicates eliminated.", "info", CLR_CYAN)
    if skipped_count > 0:
        log_console(f"⚠️ Skipped / Errors: {skipped_count} items.", "warning", CLR_YELLOW)

    print(f"\n{CLR_CYAN}{DIVIDER}{CLR_RESET}")
    print(f"{CLR_BOLD}{CLR_WHITE} 📊 GPS & METADATA AUDIT REPORT (تقرير التدقيق){CLR_RESET}")
    print(f"{CLR_CYAN}{DIVIDER}{CLR_RESET}")
    print(f"  • JSON/HTML Registry Matches : {CLR_GREEN}{audit_json_matches}{CLR_RESET}")
    print(f"  • Fallback Name/File Matches : {CLR_YELLOW}{audit_fallback_matches}{CLR_RESET}")
    print(f"  • Files Successfully GPS Tagged : {CLR_GREEN}{audit_gps_tagged}{CLR_RESET}")
    print(f"  • Dummy (0,0) GPS Skipped    : {CLR_YELLOW}{audit_gps_dummy_skipped}{CLR_RESET}")
    print(f"  • Records With No GPS in JSON: {CLR_RED}{audit_gps_missing}{CLR_RESET}")
    print(f"{CLR_CYAN}{MINI_DIVIDER}{CLR_RESET}")
    log_console(f"📝 Full itemized audit trail saved in: {LOG_FILE}", "info", CLR_CYAN)

# ==============================================================================
# INTERACTIVE SETTINGS & FEATURE TOGGLES MENU (CHECKBOX UI)
# ==============================================================================
def settings_toggle_menu() -> None:
    """Provides an interactive CLI interface with live checkboxes for all variables."""
    global MERGE_IMAGE_OVERLAYS, MERGE_VIDEO_OVERLAYS, DISCARD_ORPHAN_OVERLAYS
    global DISCARD_UNMERGED_DUPLICATES, PURGE_VIDEO_THUMBNAILS, CLASSIFY_MONTHLY_FOLDERS, PURGE_ALL_OVERLAYS_COMPLETELY
    global UPDATE_EXIF_TAGS, UPDATE_GPS_TAGS, PATCH_MP4_METADATA, SET_FS_TIMESTAMPS
    global ENABLE_DEDUPLICATION, OPERATION_MODE, GPU_CONCURRENT_WORKERS, FUZZY_TIME_WINDOW_SECONDS

    def fmt_state(val: bool) -> str:
        return f"{CLR_GREEN}[✔ ON]{CLR_RESET}" if val else f"{CLR_RED}[✖ OFF]{CLR_RESET}"

    while True:
        print(f"\n{CLR_CYAN}{DIVIDER}{CLR_RESET}")
        print(f"{CLR_BOLD}{CLR_WHITE} ⚙️ SETTINGS & FEATURE TOGGLES (تعديل الخيارات){CLR_RESET}")
        print(f"{CLR_PINK}       Done by: KBJ911{CLR_RESET}")
        print(f"{CLR_CYAN}{DIVIDER}{CLR_RESET}")
        print(f" {CLR_YELLOW}[1]{CLR_RESET}  🎨 Merge Photo Overlays (دمج ملصقات الصور)        : {fmt_state(MERGE_IMAGE_OVERLAYS)}")
        print(f" {CLR_YELLOW}[2]{CLR_RESET}  🎬 Merge Video Overlays (دمج ملصقات الفيديو)       : {fmt_state(MERGE_VIDEO_OVERLAYS)}")
        print(f" {CLR_YELLOW}[3]{CLR_RESET}  🧹 Discard Black Orphan PNGs (استبعاد الملصقات)    : {fmt_state(DISCARD_ORPHAN_OVERLAYS)}")
        print(f" {CLR_YELLOW}[4]{CLR_RESET}  🛡️ Purge Mosaic Duplicates (حذف المكرر المشوه)     : {fmt_state(DISCARD_UNMERGED_DUPLICATES)}")
        print(f" {CLR_YELLOW}[5]{CLR_RESET}  🚫 Purge Video Preview JPGs (حذف لقطات المعاينة)  : {fmt_state(PURGE_VIDEO_THUMBNAILS)}")
        print(f" {CLR_YELLOW}[6]{CLR_RESET}  📅 Update Photo EXIF Date (حقن تاريخ الالتقاط)     : {fmt_state(UPDATE_EXIF_TAGS)}")
        print(f" {CLR_YELLOW}[7]{CLR_RESET}  📍 Inject GPS Location Tags (حقن الموقع الجغرافي)  : {fmt_state(UPDATE_GPS_TAGS)}")
        print(f" {CLR_YELLOW}[8]{CLR_RESET}  🎥 Patch MP4 Creation Time (تصحيح وقت الفيديو)     : {fmt_state(PATCH_MP4_METADATA)}")
        print(f" {CLR_YELLOW}[9]{CLR_RESET}  🕒 Match File System Time (مطابقة وقت الويندوز)   : {fmt_state(SET_FS_TIMESTAMPS)}")
        print(f" {CLR_YELLOW}[10]{CLR_RESET} 🔒 SHA-256 Deduplication (منع الملفات المتطابقة)   : {fmt_state(ENABLE_DEDUPLICATION)}")
        print(f" {CLR_YELLOW}[11]{CLR_RESET} 📁 Monthly Folders YYYY/MM (تصنيف المجلد الشهري) : {fmt_state(CLASSIFY_MONTHLY_FOLDERS)}")
        print(f" {CLR_YELLOW}[12]{CLR_RESET} 🗑️ Purge All Overlays Completely (حذف كل الملصقات) : {fmt_state(PURGE_ALL_OVERLAYS_COMPLETELY)}")
        print(f" {CLR_YELLOW}[13]{CLR_RESET} 📦 Operation Mode (طريقة النقل)                 : {CLR_CYAN}[{OPERATION_MODE.upper()}]{CLR_RESET}")
        print(f" {CLR_YELLOW}[14]{CLR_RESET} 🚀 GPU Parallel Streams (مسارات كرت الشاشة)       : {CLR_CYAN}[{GPU_CONCURRENT_WORKERS} Streams]{CLR_RESET}")
        print(f" {CLR_YELLOW}[15]{CLR_RESET} ⏱️ Fuzzy Time Match Window (نطاق مطابقة الثواني)  : {CLR_CYAN}[±{FUZZY_TIME_WINDOW_SECONDS}s]{CLR_RESET}")
        print(f"{CLR_CYAN}{MINI_DIVIDER}{CLR_RESET}")
        print(f" {CLR_GREEN}[0]{CLR_RESET}  💾 Save Settings & Back to Main Menu (حفظ ورجوع)")
        print(f"{CLR_CYAN}{DIVIDER}{CLR_RESET}")

        opt = input(f"{CLR_CYAN}👉 Enter option number to toggle [0-15]: {CLR_RESET}").strip()

        if opt == "1": MERGE_IMAGE_OVERLAYS = not MERGE_IMAGE_OVERLAYS
        elif opt == "2": MERGE_VIDEO_OVERLAYS = not MERGE_VIDEO_OVERLAYS
        elif opt == "3": DISCARD_ORPHAN_OVERLAYS = not DISCARD_ORPHAN_OVERLAYS
        elif opt == "4": DISCARD_UNMERGED_DUPLICATES = not DISCARD_UNMERGED_DUPLICATES
        elif opt == "5": PURGE_VIDEO_THUMBNAILS = not PURGE_VIDEO_THUMBNAILS
        elif opt == "6": UPDATE_EXIF_TAGS = not UPDATE_EXIF_TAGS
        elif opt == "7": UPDATE_GPS_TAGS = not UPDATE_GPS_TAGS
        elif opt == "8": PATCH_MP4_METADATA = not PATCH_MP4_METADATA
        elif opt == "9": SET_FS_TIMESTAMPS = not SET_FS_TIMESTAMPS
        elif opt == "10": ENABLE_DEDUPLICATION = not ENABLE_DEDUPLICATION
        elif opt == "11": CLASSIFY_MONTHLY_FOLDERS = not CLASSIFY_MONTHLY_FOLDERS
        elif opt == "12": PURGE_ALL_OVERLAYS_COMPLETELY = not PURGE_ALL_OVERLAYS_COMPLETELY
        elif opt == "13": OPERATION_MODE = "move" if OPERATION_MODE.lower() == "copy" else "copy"
        elif opt == "14": GPU_CONCURRENT_WORKERS = (GPU_CONCURRENT_WORKERS % 4) + 1
        elif opt == "15": FUZZY_TIME_WINDOW_SECONDS = (FUZZY_TIME_WINDOW_SECONDS % 4) + 1
        elif opt == "0":
            log_console("💾 Settings saved successfully.", "info", CLR_GREEN)
            break
        else:
            print(f"{CLR_RED}⚠️ Invalid choice, please enter 0 to 15.{CLR_RESET}")

# ==============================================================================
# INTERACTIVE CLI INTERFACE & MAIN EXECUTION
# ==============================================================================
def sanitize_path(path_str: str) -> pathlib.Path:
    clean = path_str.strip().strip("'\"").strip()
    return pathlib.Path(clean).expanduser().resolve()

def sanitize_username(user_str: str) -> str:
    clean = user_str.strip().strip("'\"").strip()
    clean = clean.replace(" ", "-").replace("_", "-")
    return clean if clean else "User"

def run_menu() -> None:
    display_header()
    src_input = SOURCE_DIR
    if not src_input:
        while True:
            raw_in = input(f"{CLR_YELLOW}📁 Drag and drop source folder or ZIP (Raw Snapchat, ZIPs, or Legacy): {CLR_RESET}")
            if raw_in.strip():
                src_path = sanitize_path(raw_in)
                if src_path.exists():
                    break
                log_console(f"❌ Path does not exist: {src_path}", "error", CLR_RED)
    else:
        src_path = sanitize_path(src_input)

    username_input = SNAPCHAT_USERNAME
    if not username_input:
        while True:
            raw_user = input(f"{CLR_YELLOW}👤 Enter your Snapchat username to match it with new folder name (e.g., KBJ911): {CLR_RESET}")
            clean_user = sanitize_username(raw_user)
            if clean_user and clean_user != "User":
                username = clean_user
                break
    else:
        username = sanitize_username(username_input)

    root_folder_name = f"Snapchat-{username}"
    out_path = sanitize_path(BASE_OUTPUT_DIR) / root_folder_name if BASE_OUTPUT_DIR else (src_path.parent / root_folder_name if src_path.is_file() else src_path.parent / root_folder_name)

    while True:
        print(f"\n{CLR_CYAN}{DIVIDER}{CLR_RESET}")
        log_console(f"📍 Source Directory: {src_path}", "info", CLR_WHITE)
        log_console(f"👤 Account Name    : {username}", "info", CLR_WHITE)
        log_console(f"🎯 Output Directory: {out_path}", "info", CLR_GREEN)
        log_console(f"🖥️ Detected GPU    : {DETECTED_GPU_NAME}", "info", CLR_CYAN)
        log_console(f"⚡ Hardware Engine : {ACTIVE_ENCODER_LABEL}", "info", CLR_GREEN)
        log_console(f"🚀 GPU Multi-Stream: {GPU_CONCURRENT_WORKERS} Concurrent Pipelines", "info", CLR_GREEN)
        log_console(f"🛡️ Smart Cleaner   : Burst-Safe Clean & Mosaic Purge", "info", CLR_GREEN)
        log_console(f"📂 Folder Strategy : {'Yearly & Monthly (YYYY/MM)' if CLASSIFY_MONTHLY_FOLDERS else 'Yearly Only (Snapchat-YYYY)'}", "info", CLR_CYAN)
        log_console(f"🎨 Photo Overlays  : {'Enabled' if MERGE_IMAGE_OVERLAYS else 'Disabled'}", "info", CLR_CYAN)
        log_console(f"🎬 Video Overlays  : {'Enabled (GPU Direct)' if MERGE_VIDEO_OVERLAYS else 'Disabled'}", "info", CLR_CYAN)
        log_console(f"📍 GPS Tagging     : {'ON (Native QuickTime Sibling Meta & Dual Ecosystem)' if UPDATE_GPS_TAGS else 'OFF'}", "info", CLR_CYAN)
        log_console(f"⏱️ Fuzzy Time Match: Window ±{FUZZY_TIME_WINDOW_SECONDS}s (UTC & Local Multi-Epoch)", "info", CLR_CYAN)
        log_console(f"🔧 Tool Mode       : 100% Pure Python & Native FFmpeg (Zero .EXE Dependency)", "info", CLR_GREEN)
        print(f"{CLR_CYAN}{MINI_DIVIDER}{CLR_RESET}")

        print(f"{CLR_WHITE}Select Operation:{CLR_RESET}")
        print(f" {CLR_GREEN}1){CLR_RESET} Start Organizing & Updating ({OPERATION_MODE.upper()} to folders)")
        print(f" {CLR_YELLOW}2){CLR_RESET} ⚙️ Settings & Feature Toggles (قائمة الخيارات والتفعيل)")
        print(f" {CLR_CYAN}3){CLR_RESET} Dry-Run Preview (Simulate without writing files)")
        print(f" {CLR_RED}4){CLR_RESET} Exit")
        print(f"{CLR_CYAN}{MINI_DIVIDER}{CLR_RESET}")

        choice = input(f"{CLR_CYAN}👉 Enter choice [1-4]: {CLR_RESET}").strip()
        if choice == "1":
            process_snapchat_memories(src_path, out_path, dry_run=False)
            break
        elif choice == "2":
            settings_toggle_menu()
        elif choice == "3":
            process_snapchat_memories(src_path, out_path, dry_run=True)
            break
        else:
            close_all_cached_zips()
            sys.exit(0)

    display_footer()

if __name__ == "__main__":
    try:
        run_menu()
    except KeyboardInterrupt:
        log_console("\n⚠️ Process interrupted by user.", "warning", CLR_YELLOW)
        close_all_cached_zips()
        sys.exit(0)
    except Exception as fatal_err:
        log_console(f"💥 Fatal execution error: {fatal_err}", "error", CLR_RED)
        logging.error(traceback.format_exc())
        close_all_cached_zips()
        sys.exit(1)
