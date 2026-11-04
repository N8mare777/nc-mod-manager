# NightCoop Manager

> **Unofficial, fan-made project.** Not affiliated with, endorsed by, or supported by the
> NightCoop team. The mod itself lives at [nightcoop.net](https://nightcoop.net/).

A small portable Windows utility to install, update and remove the **NightCoop** mod
for **Cyberpunk 2077** — one EXE, no installer, no settings left behind.

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6)
![Python](https://img.shields.io/badge/python-3.12-3776AB)
![Version](https://img.shields.io/badge/version-0.2.1-FFE500)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- Detects the game folder via Steam (registry + libraries), GOG (registry),
  Epic Games (launcher manifests) and common install paths; every candidate is validated
  by `bin\x64\Cyberpunk2077.exe`
- Manual folder selection as a fallback
- Game version switch (2.5 / 2.31) and mod version selection
- One action button: **Install** when the mod is missing, **Update** when it is installed
- "What's new" viewer with the changelog of the selected build
- Backup of the mod settings (`install-id.txt`, `name.txt`, `servers.txt`)
- Session log in `%TEMP%` with a "Save log" button
- Three UI languages: English, Russian, Swedish
- Fully portable: no registry entries, no config files

## Installation

1. Download `NightCoopManager.exe` from [Releases](../../releases/latest).
2. Run it — no installation required.
3. The game folder is detected automatically; press **Install** or **Update**.

Windows SmartScreen may warn about an unknown publisher because the binary is not
code-signed. The full source is in this repository, and every release lists its
SHA-256 checksum.

## How it works

1. Reads `releases.json` from `nightcoop.net` and picks the build matching the selected
   game version.
2. Downloads the official archive and verifies its SHA-256.
3. Extracts it into the game folder and writes `red4ext\plugins\NightCoop\version.txt`.
4. Records every installed file in `.nightcoop-manifest.json`.

Updates clean the mod's own folder first (keeping `install-id.txt`, `name.txt`,
`servers.txt`, logs and `backup-*`). Uninstall removes only files from the manifest and
restores anything that existed before the installation, so other mods are never damaged.

## Build from source

```bat
pip install pyinstaller PyQt6
build.bat
```

The single-file build appears in `dist\NightCoopManager.exe`.

Project layout:

| File | Purpose |
|---|---|
| `main.py` | PyQt6 UI, theme, workers |
| `updater.py` | detection, download, manifest, install/uninstall |
| `translations.py` | EN / SV / RU strings |
| `readme/` | in-app manuals (packed into the EXE) |
| `assets/flags/` | language flags |

## Documentation

- [Русская документация](readme/README_ru.md)
- [English documentation](readme/README_en.md)
- [Svensk dokumentation](readme/README_sv.md)

## Disclaimer

This is an unofficial community tool. It only downloads the official archive from
`nightcoop.net` and copies the files into the game folder; it does not redistribute the
mod. For any problem with the mod itself (crashes, connection issues, gameplay, bans),
contact the NightCoop authors and the official website — not this project.

## License

[MIT](LICENSE)
