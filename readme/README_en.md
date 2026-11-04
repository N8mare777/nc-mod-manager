# NightCoop Manager 0.2.1

## What is it

A small utility to install, update and remove the **NightCoop** mod for **Cyberpunk 2077**.
It ships as a single EXE — nothing else has to be installed.

The program is fully portable: it stores **no settings** — neither in the registry nor in
its own files. Download it, install the mod, delete the program. Nothing is left behind.

## Features

- Automatic game folder detection: Steam (registry and library folders), GOG (registry),
  Epic Games (launcher manifests) and common install paths. Every candidate is validated
  by the presence of `bin\x64\Cyberpunk2077.exe`
- Manual folder selection when the game is installed somewhere unusual
- Game version selection (2.5 / 2.31) and mod version selection
- Install / update / uninstall the mod
- Online check of the available version
- Backup of the mod settings (`install-id.txt`, `name.txt`, `servers.txt`)
- "What's new" viewer for the selected build
- Saving the session log to a file (button)
- Three interface languages: English, Russian, Swedish

## How it works

1. The program reads `releases.json` from `nightcoop.net` and picks the build matching the
   selected game version (2.5 or 2.31). Files without a game-version restriction are
   treated as compatible with any version.
2. It downloads the archive of the selected build and verifies its SHA-256.
3. It extracts the archive and copies the files into the game folder.
4. It writes the installed version into `red4ext\plugins\NightCoop\version.txt` and creates
   an install manifest `.nightcoop-manifest.json` listing every installed file with hashes.

On update the program first cleans the mod folder `red4ext\plugins\NightCoop\` from files of
the previous version so no stale DLLs remain. `install-id.txt`, `name.txt`, `servers.txt`,
log files and `backup-*` folders are never touched.

**Uninstall** uses the manifest: only files installed by the program are removed, and only if
they were not modified by something else. Files that existed before installation are restored
from a backup copy. Game files, other mods and your saves are never touched.

## Important: back up before updating

The folder `red4ext\plugins\NightCoop\` holds important data: `install-id.txt`, `name.txt`,
`servers.txt` and log files. They contain the installation ID and the server list — that is
your progress and account binding.

Before updating or removing the mod, press **Backup settings**. The program creates a
`backup-DATE-TIME` folder and copies those files there, so nothing is lost.

Update and uninstall do not delete these files, but a backup is still recommended as a
safety net.

## Log

The program keeps a session log in the temporary folder `%TEMP%\NightCoopManager\`.
The **Save log** button lets you save it anywhere — for example to attach to a bug report.

## Recommendations

- Close the game before installing or updating.
- Use the same mod build as your friends — co-op requires the same version on every machine.
- If the mod does not start, make sure Red4ext is present (the NightCoop archive already includes it).

## Disclaimer

The author of this program is **not affiliated** with the authors of the NightCoop mod.
The program was written to make installing and updating the mod more convenient; it only
downloads the official archive from `nightcoop.net` and copies the files into the game folder.

For any problems with the mod itself — it does not start, crashes, cannot connect to
servers, gameplay questions or bans — contact the **mod authors and the website
nightcoop.net**, not the author of this program.

## Version

0.2.1
