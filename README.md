# drAPK
Modular tool for reverse engineering and modifying Android APK files. Initially architected for manipulating APKs built with Corona SDK (Lua 5.1), its extensible core allows for adaptation to other frameworks, including Unity and native binaries.

---
## Use Cases

drAPK is designed for:
modders and reverse-engineering enthusiasts,

technical users who build or test custom APKs,

anyone who wants to automate APK rebuild and signing pipelines.

It’s small, scriptable, and built for experimentation.

---
## Features

- **Unpack / modify / build APKs** using external tools like `apktool`, `zipalign`, `jarsigner`, and `java`.
- **Dynamic version switching** — change working directories on the fly without restarting the interface.
- **Keystore integration** — manage or generate signing keys directly from the GUI.
- **Config-driven interface** — buttons, bindings, and themes are defined in `config.json`.
- **Built-in CLI console** — execute commands (`help`, `cls`, `utf8`, etc.) directly inside the GUI.
- **Live configuration reload** — the interface reacts to changes in real time without restarting the program.

---
## Architecture
core/ → configuration, event system, and base utilities
tools/ → individual tools (VersionManager, KeystoreManager, UTF8Decoder)
gui/ → dynamic Tkinter interface
config.json → configuration and button bindings
The components communicate through an internal **Event Dispatcher**, allowing live UI updates and state synchronization across modules.

---
Of course. Here is the translation of the build composition section for your `README.md` in English.

---

## Build Composition

This project uses the following tools and dependencies:
### Core Development Tools
*   **JDK** - [jdk-17.0.16+8 (Portable)](https://adoptium.net/) - A portable version of OpenJDK from Eclipse Adoptium

### Android Tools
*   **Android SDK** - A set of tools for Android development:
    *   Command-line tools (`cmdline-tools`)
    *   Build Tools
    *   Platform Tools
    *   Android Platforms

### Utilities for Archives and Scripts
*   **Corona Archiver | Solar2D Game Engine pack/unpack** - from [0BuRner](https://github.com/0BuRner/corona-archiver)
*   **LuaC/UnLuaC** - Lua script compiler and decompiler

### APK Analysis Tools
*   **Apktool** - [Official Repository](https://github.com/iBotPeaches/Apktool) - A tool for reverse engineering Android applications (APK files)

---

**Note:** Please ensure all the listed tools are correctly installed and added to your system's PATH before working with the project.
## Installation & Launch
1. Require Python 3.10+ 
2. All dependencies and utilities included
3. Final setting will be performed automatically while initial start or after reset

---
## Run the GUI:
main.py

---
## Roadmap

Plugin system (user-defined tools in /tools)

Task queue and parallel execution

Improved logging and progress tracking

Backup version handling

Optional modern GUI front-end

---

License

This project is distributed under the MIT License — see LICENSE
© Swokster