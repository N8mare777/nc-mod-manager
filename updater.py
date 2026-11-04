# -*- coding: utf-8 -*-
"""
NightCoop Manager - core logic.

- Detect Cyberpunk 2077 (Steam / GOG / Epic / common folders)
- Fetch releases.json, download + verify + extract a build
- Install with an install manifest, clean update, safe uninstall
- Backup mod settings
"""

import os
import json
import time
import shutil
import zipfile
import tempfile
import hashlib
import urllib.request

try:
    import winreg
except ImportError:          # pragma: no cover - non Windows
    winreg = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://nightcoop.net"

MOD_RELATIVE_PATH = os.path.join("red4ext", "plugins", "NightCoop")
VERSION_FILENAME = "version.txt"

# Cyberpunk 2077 executable lives in <game>\bin\x64\Cyberpunk2077.exe
GAME_EXE_RELATIVE = os.path.join("bin", "x64", "Cyberpunk2077.exe")
GAME_EXE_RELATIVE_FALLBACK = "Cyberpunk2077.exe"

MANIFEST_NAME = ".nightcoop-manifest.json"
BACKUP_DIRNAME = ".backup-manager"

# Files inside the mod folder that must survive update and uninstall
PRESERVED_NAMES = {"install-id.txt", "name.txt", "servers.txt"}

MAX_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024   # 4 GB safety limit (zip bomb)

COMMON_PATHS = [
    os.path.join("C:\\", "Program Files (x86)", "Steam", "steamapps", "common", "Cyberpunk 2077"),
    os.path.join("C:\\", "Program Files", "Steam", "steamapps", "common", "Cyberpunk 2077"),
    os.path.join("C:\\", "Program Files (x86)", "GOG Galaxy", "Games", "Cyberpunk 2077"),
    os.path.join("C:\\", "Program Files", "GOG Galaxy", "Games", "Cyberpunk 2077"),
    os.path.join("C:\\", "GOG Games", "Cyberpunk 2077"),
    os.path.join("C:\\", "Program Files", "Epic Games", "Cyberpunk2077"),
]


class OperationCancelled(RuntimeError):
    """Raised when the user cancels a running operation."""


# ---------------------------------------------------------------------------
# Path detection
# ---------------------------------------------------------------------------

def _steam_install_path():
    """Try to get Steam install path from the Windows registry."""
    if winreg is None:
        return None
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
    ]
    for hkey, subkey in roots:
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                for value_name in ("InstallPath", "SteamPath"):
                    try:
                        val, _ = winreg.QueryValueEx(key, value_name)
                        if val:
                            return val
                    except FileNotFoundError:
                        continue
        except (FileNotFoundError, OSError):
            continue
    return None


def _steam_libraries(steam_path):
    """Yield Steam library folders from libraryfolders.vdf."""
    if not steam_path or not os.path.isdir(steam_path):
        return
    vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    if not os.path.isfile(vdf_path):
        return
    try:
        with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return
    import re
    for match in re.finditer(r'"path"\s+"([^"]+)"', content):
        yield match.group(1).replace("\\\\", "\\")


def _steam_game_paths():
    steam_path = _steam_install_path()
    if not steam_path:
        return []
    libraries = [steam_path] + list(_steam_libraries(steam_path))
    seen = set()
    out = []
    for lib in libraries:
        if lib in seen:
            continue
        seen.add(lib)
        out.append(os.path.join(lib, "steamapps", "common", "Cyberpunk 2077"))
    return out


def _gog_game_paths():
    """Read GOG game entries from the registry (gameName == Cyberpunk 2077)."""
    if winreg is None:
        return []
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\GOG.com\Games"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\GOG.com\Games"),
        (winreg.HKEY_CURRENT_USER, r"Software\GOG.com\Games"),
    ]
    found = []
    for hive, subkey in roots:
        try:
            base = winreg.OpenKey(hive, subkey)
        except OSError:
            continue
        with base:
            index = 0
            while True:
                try:
                    entry = winreg.EnumKey(base, index)
                except OSError:
                    break
                index += 1
                try:
                    with winreg.OpenKey(base, entry) as game_key:
                        try:
                            game_name, _ = winreg.QueryValueEx(game_key, "gameName")
                        except OSError:
                            game_name = ""
                        try:
                            path, _ = winreg.QueryValueEx(game_key, "path")
                        except OSError:
                            path = ""
                except OSError:
                    continue
                if path and "cyberpunk 2077" in str(game_name).lower():
                    found.append(path)
    return found


EPIC_MANIFEST_DIRS = [
    os.path.join("C:\\", "ProgramData", "Epic", "EpicGamesLauncher", "Data", "Manifests"),
]
EPIC_LAUNCHER_DAT = os.path.join(
    "C:\\", "ProgramData", "Epic", "UnrealEngineLauncher", "LauncherInstalled.dat"
)


def _epic_game_paths():
    """Read Epic Games manifests and LauncherInstalled.dat."""
    found = []

    for manifest_dir in EPIC_MANIFEST_DIRS:
        if not os.path.isdir(manifest_dir):
            continue
        try:
            names = os.listdir(manifest_dir)
        except OSError:
            continue
        for name in names:
            if not name.lower().endswith(".item"):
                continue
            path = os.path.join(manifest_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            display = str(data.get("DisplayName", "")).lower()
            location = str(data.get("InstallLocation", ""))
            if location and ("cyberpunk 2077" in display or "cyberpunk 2077" in location.lower()):
                found.append(location)

    if os.path.isfile(EPIC_LAUNCHER_DAT):
        try:
            with open(EPIC_LAUNCHER_DAT, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("InstallationList", []):
                location = str(item.get("InstallLocation", ""))
                if location and "cyberpunk 2077" in location.lower():
                    found.append(location)
        except (OSError, ValueError):
            pass

    return found


def is_valid_game_path(game_path):
    """True if the folder contains Cyberpunk2077.exe (bin\\x64 or root)."""
    if not game_path or not os.path.isdir(game_path):
        return False
    if os.path.isfile(os.path.join(game_path, GAME_EXE_RELATIVE)):
        return True
    return os.path.isfile(os.path.join(game_path, GAME_EXE_RELATIVE_FALLBACK))


def detect_game_path():
    """Auto-detect the game folder. Returns a validated path or None."""
    candidates = []
    candidates.extend(_steam_game_paths())
    candidates.extend(_gog_game_paths())
    candidates.extend(_epic_game_paths())
    candidates.extend(COMMON_PATHS)

    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        key = os.path.normcase(os.path.abspath(candidate))
        if key in seen:
            continue
        seen.add(key)
        if is_valid_game_path(candidate):
            return candidate
    return None


def get_mod_path(game_path):
    """Return absolute path to the NightCoop mod folder inside the game."""
    return os.path.join(game_path, MOD_RELATIVE_PATH)


def get_version_file(game_path):
    """Return absolute path to version.txt inside the mod folder."""
    return os.path.join(get_mod_path(game_path), VERSION_FILENAME)


def get_installed_version(game_path):
    """Read installed mod version from version.txt, or None."""
    if not is_valid_game_path(game_path):
        return None
    vf = get_version_file(game_path)
    if os.path.isfile(vf):
        try:
            with open(vf, "r", encoding="utf-8") as f:
                return f.read().strip() or None
        except OSError:
            return None
    return None


def is_mod_installed(game_path):
    """True if NightCoop.dll or version.txt exists in the mod folder."""
    if not game_path or not os.path.isdir(game_path):
        return False
    mod_dir = get_mod_path(game_path)
    return (
        os.path.isfile(os.path.join(mod_dir, "NightCoop.dll"))
        or os.path.isfile(os.path.join(mod_dir, VERSION_FILENAME))
    )


def is_game_running():
    """Check if Cyberpunk2077.exe process is running."""
    import subprocess
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Cyberpunk2077.exe", "/FO", "CSV"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        # Cannot check (tasklist missing / blocked) - do not block the user
        return False

    output = (proc.stdout or b"").lower()
    if b"no tasks" in output:
        return False
    return b"cyberpunk2077.exe" in output


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def _manifest_path(game_path):
    return os.path.join(get_mod_path(game_path), MANIFEST_NAME)


def load_manifest(game_path):
    """Return manifest dict or None."""
    path = _manifest_path(game_path)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("files"), list):
            return data
    except (OSError, ValueError):
        pass
    return None


def _save_manifest(game_path, data):
    path = _manifest_path(game_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Releases / versions
# ---------------------------------------------------------------------------

USER_AGENT = "NightCoopManager/0.2.1"


def fetch_releases(base_url=BASE_URL):
    """Fetch and parse releases.json."""
    url = base_url.rstrip("/") + "/releases.json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    return json.loads(data.decode("utf-8"))


def find_release_for_game(releases, game_version):
    """Latest release + file matching the game version."""
    latest_version = releases.get("latest")
    if not latest_version:
        return None, None

    for release in releases.get("releases", []):
        if release.get("version") != latest_version:
            continue
        files = release.get("files", [])
        for file_info in files:
            if game_version in (file_info.get("game") or []):
                return release, file_info
        for file_info in files:
            if not file_info.get("game"):
                return release, file_info
        if len(files) == 1:
            return release, files[0]
    return None, None


def find_release_by_version(releases, target_version, game_version):
    """Specific release version + file matching the game version."""
    for release in releases.get("releases", []):
        if release.get("version") != target_version:
            continue
        files = release.get("files", [])
        for file_info in files:
            if game_version in (file_info.get("game") or []):
                return release, file_info
        for file_info in files:
            if not file_info.get("game"):
                return release, file_info
        if len(files) == 1:
            return release, files[0]
    return None, None


def list_versions_for_game(releases, game_version):
    """[(label, release, file_or_None)] for all releases matching the game version."""
    results = []
    latest_version = releases.get("latest")

    if latest_version:
        for release in releases.get("releases", []):
            if release.get("version") == latest_version:
                for file_info in release.get("files", []):
                    file_game = file_info.get("game", [])
                    if not file_game or game_version in file_game:
                        results.append(("latest", release, None))
                        break
                break

    seen = set()
    if latest_version:
        seen.add(latest_version)
    for release in releases.get("releases", []):
        version = release.get("version")
        if version in seen:
            continue
        for file_info in release.get("files", []):
            file_game = file_info.get("game", [])
            if not file_game or game_version in file_game:
                results.append((version, release, file_info))
                seen.add(version)
                break
    return results


def resolve_file_url(base_url, file_info):
    """Resolve a possibly relative file URL to an absolute one."""
    url = file_info.get("url", "")
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return base_url.rstrip("/") + "/" + url.lstrip("/")


# ---------------------------------------------------------------------------
# Download / extract
# ---------------------------------------------------------------------------

def download_file(url, destination, progress_callback=None, cancel_event=None,
                  timeout=30):
    """Download a URL with progress reporting and cancellation support."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    resp = urllib.request.urlopen(req, timeout=timeout)
    try:
        raw_total = resp.headers.get("Content-Length")
        total = int(raw_total) if raw_total else 0
        downloaded = 0
        block_size = 65536

        with open(destination, "wb") as f:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise OperationCancelled("Operation cancelled by user.")
                chunk = resp.read(block_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)
    finally:
        resp.close()


def verify_sha256(filepath, expected_hash):
    """Verify SHA-256 of a file. Returns True if match (or no hash given)."""
    if not expected_hash:
        return True
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected_hash.lower()


def extract_zip(zip_path, dest_dir):
    """Extract a ZIP archive, rejecting entries that escape dest_dir."""
    dest_abs = os.path.abspath(dest_dir)
    total_size = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            total_size += info.file_size
            if total_size > MAX_ARCHIVE_BYTES:
                raise RuntimeError("Archive is too large to extract.")

            name = info.filename.replace("\\", "/")
            parts = [p for p in name.split("/") if p not in ("", ".")]
            if name.startswith("/") or ".." in parts or ":" in parts[0]:
                raise RuntimeError(f"Archive contains an unsafe path: {info.filename}")

            target = os.path.abspath(os.path.join(dest_abs, *parts))
            if target != dest_abs and not target.startswith(dest_abs + os.sep):
                raise RuntimeError(f"Archive entry escapes target folder: {info.filename}")

        zf.extractall(dest_dir)


# ---------------------------------------------------------------------------
# Install / update
# ---------------------------------------------------------------------------

def _clean_mod_dir(game_path, log):
    """Remove everything in the mod folder except preserved files/folders."""
    mod_dir = get_mod_path(game_path)
    if not os.path.isdir(mod_dir):
        return

    for entry in os.listdir(mod_dir):
        if entry in PRESERVED_NAMES:
            log(f"Preserved: {entry}")
            continue
        if entry.lower().endswith(".log"):
            log(f"Preserved: {entry}")
            continue
        if entry.startswith("backup"):
            log(f"Preserved: {entry}")
            continue
        if entry in (MANIFEST_NAME, BACKUP_DIRNAME):
            continue

        path = os.path.join(mod_dir, entry)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                log(f"Removed old folder: {entry}")
            else:
                os.remove(path)
                log(f"Removed old file: {entry}")
        except OSError as exc:
            log(f"Cannot remove {entry}: {exc}")


def _backup_existing_file(game_path, rel_path, backup_root, log):
    """Copy an existing file into the backup root. Returns relative backup path."""
    src = os.path.join(game_path, rel_path)
    dst = os.path.join(backup_root, rel_path)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    log(f"Backed up existing file: {rel_path}")
    return os.path.relpath(dst, get_mod_path(game_path)).replace("\\", "/")


def _drop_manifest_entry(game_path, entry, log):
    """Restore a pre-existing file or delete a file we installed.

    Restoration only happens if the file is still the copy we wrote, so a file
    that was replaced by another tool in the meantime is never downgraded.
    """
    rel_path = entry.get("path", "")
    if not rel_path:
        return
    target = os.path.join(game_path, rel_path)
    if not os.path.isfile(target):
        return

    try:
        current_hash = _sha256_file(target)
    except OSError:
        return
    expected = (entry.get("sha256") or "").lower()
    untouched = bool(expected) and current_hash == expected

    backup_rel = entry.get("backup")
    if entry.get("pre_existing") and backup_rel:
        backup_abs = os.path.join(get_mod_path(game_path), backup_rel.replace("/", os.sep))
        if os.path.isfile(backup_abs):
            if not untouched:
                log(f"Skipped restore (file changed by someone else): {rel_path}")
                return
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(backup_abs, target)
                log(f"Restored original file: {rel_path}")
                return
            except OSError as exc:
                log(f"Cannot restore {rel_path}: {exc}")
                return

    if expected and current_hash != expected:
        log(f"Skipped (modified by someone else): {rel_path}")
        return

    try:
        os.remove(target)
        log(f"Removed: {rel_path}")
    except OSError as exc:
        log(f"Cannot remove {rel_path}: {exc}")


def _make_work_dir(prefix="nightcoop_"):
    """Create a unique working directory inside the system temp folder."""
    import time

    base = tempfile.gettempdir()
    name = f"{prefix}{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    path = os.path.join(base, name)
    os.makedirs(path, exist_ok=True)
    return path


def install_mod(game_path, game_version, target_version=None, base_url=BASE_URL,
                progress_callback=None, log_callback=None, cancel_event=None):
    """Install or update the mod and record what was written in a manifest."""

    def log(msg):
        if log_callback:
            log_callback(msg)

    if not is_valid_game_path(game_path):
        raise RuntimeError(
            "Cyberpunk2077.exe was not found in the selected folder "
            "(expected bin\\x64\\Cyberpunk2077.exe)."
        )
    if is_game_running():
        raise RuntimeError("Game is running. Please close Cyberpunk 2077 first.")

    log("Fetching releases.json...")
    releases = fetch_releases(base_url)

    if target_version and target_version != "latest":
        release, file_info = find_release_by_version(releases, target_version, game_version)
    else:
        release, file_info = find_release_for_game(releases, game_version)

    if not release or not file_info:
        raise RuntimeError(f"No mod file found for game version {game_version}")

    mod_version = release.get("version", "unknown")
    file_url = resolve_file_url(base_url, file_info)
    expected_sha = file_info.get("sha256")

    log(f"Selected build {mod_version} for game {game_version}")
    log(f"Downloading {file_url}")

    temp_root = _make_work_dir()
    try:
        zip_path = os.path.join(temp_root, "mod.zip")

        def prog(downloaded, total):
            if progress_callback:
                progress_callback(downloaded, total)

        download_file(file_url, zip_path, progress_callback=prog,
                      cancel_event=cancel_event)

        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled("Operation cancelled by user.")

        if expected_sha:
            log("Verifying SHA-256...")
            if not verify_sha256(zip_path, expected_sha):
                raise RuntimeError("SHA-256 checksum mismatch. Download may be corrupted.")
        else:
            log("Warning: no SHA-256 in release data, skipping verification.")

        log("Extracting archive...")
        extract_path = os.path.join(temp_root, "extract")
        os.makedirs(extract_path, exist_ok=True)
        extract_zip(zip_path, extract_path)

        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled("Operation cancelled by user.")

        # Collect archive files (relative paths)
        archive_files = []
        for root, _dirs, files in os.walk(extract_path):
            for fname in files:
                src = os.path.join(root, fname)
                rel = os.path.relpath(src, extract_path)
                archive_files.append((rel, src))

        if not archive_files:
            raise RuntimeError("The archive is empty.")

        # Old manifest: keep track of files we installed last time
        old_manifest = load_manifest(game_path) or {}
        old_entries = {
            e.get("path"): e for e in old_manifest.get("files", []) if e.get("path")
        }

        # Remove stale files we installed previously but that are gone from the new build
        new_rel_set = {rel.replace("\\", "/") for rel, _ in archive_files}
        for rel_path, entry in old_entries.items():
            if rel_path not in new_rel_set:
                log(f"Removing stale file from previous version: {rel_path}")
                _drop_manifest_entry(game_path, entry, log)

        # Idempotent part: clean the mod folder before copying
        log("Cleaning mod folder before install...")
        _clean_mod_dir(game_path, log)

        backup_root = os.path.join(
            get_mod_path(game_path),
            BACKUP_DIRNAME,
            f"{mod_version}-{time.strftime('%Y%m%d-%H%M%S')}".replace("/", "_").replace("\\", "_"),
        )
        os.makedirs(backup_root, exist_ok=True)

        entries = []
        for rel, src in archive_files:
            rel_path = rel.replace("\\", "/")
            dst = os.path.join(game_path, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)

            previous = old_entries.get(rel_path)
            pre_existing = bool(previous.get("pre_existing")) if previous else False
            backup_rel = previous.get("backup") if previous else None

            if previous is None and os.path.isfile(dst):
                # File exists but was not installed by us - keep a copy
                try:
                    backup_rel = _backup_existing_file(
                        game_path, rel_path, backup_root, log
                    )
                    pre_existing = True
                except OSError as exc:
                    raise RuntimeError(f"Cannot back up {rel_path}: {exc}")

            shutil.copy2(src, dst)
            entries.append({
                "path": rel_path,
                "sha256": _sha256_file(dst),
                "size": os.path.getsize(dst),
                "pre_existing": pre_existing,
                "backup": backup_rel,
            })

        # Version marker
        vf = get_version_file(game_path)
        os.makedirs(os.path.dirname(vf), exist_ok=True)
        with open(vf, "w", encoding="utf-8") as f:
            f.write(mod_version)
        entries.append({
            "path": os.path.relpath(vf, game_path).replace("\\", "/"),
            "sha256": _sha256_file(vf),
            "size": os.path.getsize(vf),
            "pre_existing": False,
            "backup": None,
        })

        _save_manifest(game_path, {
            "manager_version": "0.2.1",
            "mod_version": mod_version,
            "game_version": game_version,
            "files": entries,
        })

        log(f"Installed {len(entries)} files. Version: {mod_version}")
        return mod_version
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------

def uninstall_mod(game_path, log_callback=None):
    """Remove the mod using the install manifest; keep user data intact."""

    def log(msg):
        if log_callback:
            log_callback(msg)

    if not is_valid_game_path(game_path):
        raise RuntimeError("Game folder is not valid (Cyberpunk2077.exe not found).")

    manifest = load_manifest(game_path)

    if not manifest:
        log("Install manifest not found - using safe fallback cleanup.")
        if not os.path.isdir(get_mod_path(game_path)):
            log("NightCoop folder not found. Nothing to uninstall.")
            return
        _clean_mod_dir(game_path, log)
        log("Cleanup finished (manifest was missing).")
        return

    log(f"Uninstalling NightCoop {manifest.get('mod_version', '?')}...")
    for entry in manifest.get("files", []):
        _drop_manifest_entry(game_path, entry, log)

    # Remove leftovers in the mod folder (except preserved data)
    _clean_mod_dir(game_path, log)

    # Remove manifest and the manager backup folder
    try:
        os.remove(_manifest_path(game_path))
    except OSError:
        pass
    shutil.rmtree(os.path.join(get_mod_path(game_path), BACKUP_DIRNAME),
                  ignore_errors=True)

    log("Uninstall complete.")


# ---------------------------------------------------------------------------
# Backup of user settings
# ---------------------------------------------------------------------------

def backup_mod_settings(game_path, log_callback=None):
    """Copy install-id.txt, name.txt, servers.txt into a timestamped folder."""
    from datetime import datetime

    def log(msg):
        if log_callback:
            log_callback(msg)

    nightcoop_dir = get_mod_path(game_path)

    if not os.path.isdir(nightcoop_dir):
        log("NightCoop folder not found.")
        return None

    files_to_backup = ["install-id.txt", "name.txt", "servers.txt"]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = os.path.join(nightcoop_dir, f"backup-{timestamp}")

    try:
        os.makedirs(backup_dir, exist_ok=True)
    except OSError as exc:
        log(f"Cannot create backup folder: {exc}")
        return None

    copied = 0
    for fname in files_to_backup:
        src = os.path.join(nightcoop_dir, fname)
        if os.path.isfile(src):
            try:
                shutil.copy2(src, os.path.join(backup_dir, fname))
                copied += 1
                log(f"Backed up: {fname}")
            except OSError as exc:
                log(f"Cannot back up {fname}: {exc}")
        else:
            log(f"Not found (skipped): {fname}")

    log(f"Backup complete: {copied} files -> {backup_dir}")
    return backup_dir
