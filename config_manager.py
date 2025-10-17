import os
import json
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class ConfigManager:
    TOOLS_CONFIG = {
        "versions_dir": {
            "name": "Versions Folder",
            "description": "Folder for storing versions",
            "file_types": [],
            "required": True
        },
        "java": {
            "name": "Java Runtime",
            "location": "JDK/jdk-17.0.16+8/bin/java.exe",
            "description": "Java executable (java.exe)",
            "file_types": [("Java executable", "java.exe"), ("All files", "*.*")],
            "required": True
        },
        "apktool": {
            "name": "APKTool",
            "location": "APKTool/apktool.jar",
            "description": "APKTool JAR file",
            "file_types": [("JAR files", "*.jar"), ("All files", "*.*")],
            "required": True
        },
        "apksigner": {
            "name": "APKSigner",
            "location": "AndroidSDK/build-tools/34.0.0/apksigner.bat",
            "description": "APKSigner tool",
            "file_types": [("APKSigner", "apksigner.bat"), ("All files", "*.*")],
            "required": True
        },
        "zipalign": {
            "name": "Zipalign",
            "location": "AndroidSDK/build-tools/34.0.0/zipalign.exe",
            "description": "Zipalign tool",
            "file_types": [("Zipalign", "zipalign.exe"), ("All files", "*.*")],
            "required": True
        },
        "unluac": {
            "name": "Unluac",
            "location": "Unluac/unluac.jar",
            "description": "Unluac decompiler JAR",
            "file_types": [("JAR files", "*.jar"), ("All files", "*.*")],
            "required": True
        },
        "corona-archiver": {
            "name": "Corona Archiver",
            "location": "Corona_Archiver/corona-archiver-master/corona-archiver.py",
            "description": "Corona Archiver Python script",
            "file_types": [("Python files", "*.py"), ("All files", "*.*")],
            "required": True
        },
        "luac": {
            "name": "luac",
            "location": "Luac/luac.exe",
            "description": "Luac compiler",
            "file_types": [("exe files", "*.exe"), ("All files", "*.*")],
            "required": True
        }
    }

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.data = self._load()
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.utils_dir = os.path.join(self.project_root, "utils")
        self.initial_dir = self.utils_dir

        # Create root window if it doesn't exist
        self._root = None
        # Event system for GUI updates
        self._event_listeners = {}

    # === Event System ===
    def on(self, event_name, callback):
        """Register event listener"""
        if event_name not in self._event_listeners:
            self._event_listeners[event_name] = []
        self._event_listeners[event_name].append(callback)

    # def off(self, event_name, callback):
    #     """Unregister event listener"""
    #     if event_name in self._event_listeners:
    #         if callback in self._event_listeners[event_name]:
    #             self._event_listeners[event_name].remove(callback)

    def emit(self, event_name, data=None):
        """Emit event to all listeners"""
        if event_name in self._event_listeners:
            for callback in self._event_listeners[event_name]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in event listener: {e}")

    def _get_root(self):
        """Get or create root Tkinter window"""
        try:
            # Try to get existing root
            root = tk._default_root
            if root and root.winfo_exists():
                return root
        except:
            pass

        # Create new root
        self._root = tk.Tk()
        self._root.withdraw()  # Hide the root window
        return self._root

    def _load(self):
        """Load config from file or return default dict."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self._show_error(f"Failed to load config: {e}")
                return {}
        return {}

    def save(self):
        """Save current config to file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            self._show_error(f"Failed to save config: {e}")

    def get(self, key, default=None):
        """Get value from config."""
        return self.data.get(key, default)

    def set(self, key, value):
        """Set value and auto-save."""
        self.data[key] = value
        self.save()

    def get_theme_data(self):
        """Returns ALL theme data: base colors + automatic derivatives"""
        themes = self.get("themes", {})
        current_theme = self.get("current_theme", "light")
        theme = themes.get(current_theme, {})

        bg_color = theme.get("background", "#FFFFFF")
        text_color = theme.get("text_color", "#000000")
        button_text_color = theme.get("button_text", "#000000")
        scroll_text_color = theme.get("scroll_text", "#000000")

        # Automatic derivative colors
        lighter_bg = self.lighten_color(bg_color, 0.2)
        darker_bg = self.darken_color(bg_color, 0.1)

        return {
            'bg_color': bg_color,
            'lighter_bg': lighter_bg,
            'darker_bg': darker_bg,
            'text_color': text_color,
            'button_text_color': button_text_color,
            'scroll_text_color': scroll_text_color
        }

    @staticmethod
    def lighten_color(hex_color, factor = 0.2):
        """Lighten color"""

        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)

            r = min(255, int(r + (255 - r) * factor))
            g = min(255, int(g + (255 - g) * factor))
            b = min(255, int(b + (255 - b) * factor))

            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color

    @staticmethod
    def darken_color(hex_color, factor=0.1):
        """Darken color"""
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)

            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))

            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color

    # === GUI part ===
    def open_config_window(self):
        """Open configuration window with tabs/buttons."""
        root = self._get_root()
        window = tk.Toplevel(root)
        window.title("Configuration")

        window_width = 150
        window_height = 220

        # Center window on screen
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        window.grab_set()

        # Get colors from config
        bg_color, lighter_color, text_color, button_text_color, scroll_text_color = self.get_theme_colors()
        window.configure(background=bg_color)

        frame = tk.Frame(window, background=bg_color)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create Buttons
        btn_width = 12

        btn_themes = tk.Button(frame, text="Themes", width=btn_width,
                               background=lighter_color, foreground=button_text_color,
                               command=lambda: [window.destroy(), self.open_themes_window()])
        btn_themes.pack(pady=5)

        btn_paths = tk.Button(frame, text="Paths", width=btn_width,
                              background=lighter_color, foreground=button_text_color,
                              command=lambda: [window.destroy(), self._open_paths_window()])
        btn_paths.pack(pady=5)

        btn_open_config = tk.Button(frame, text="Reset to Defaults", width=btn_width,
                              background=lighter_color, foreground=button_text_color,
                              command=lambda: [window.destroy(), self.reset_to_defaults()])
        btn_open_config.pack(pady=5)

        btn_reset = tk.Button(frame, text="Open Config", width=btn_width,
                              background=lighter_color, foreground=button_text_color,
                              command=lambda: [window.destroy(), self._open_config_in_editor()])
        btn_reset.pack(pady=5)

        btn_advanced = tk.Button(frame, text="Advanced", width=btn_width,
                                 background=lighter_color, foreground=button_text_color,
                                 command=lambda: [window.destroy(), self.open_advanced_config_editor()])
        btn_advanced.pack(pady=5)

    def open_advanced_config_editor(self):
        """Open advanced configuration editor"""
        editor = ConfigEditor(self)
        editor.open_editor()

    def _open_paths_window(self):
        """Sub-window for selecting paths."""
        root = self._get_root()
        window = tk.Toplevel(root)
        window.title("Tools paths")
        window.geometry("500x400")
        window.grab_set()

        # Center window on screen
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - window.winfo_width()) // 2
        y = (screen_height - window.winfo_height()) // 2
        window.geometry(f"+{x}+{y}")

        # Get colors directly from config
        bg_color, lighter_color, text_color, button_text_color, scroll_text_color = self.get_theme_colors()
        window.configure(background=bg_color)

        frame = tk.Frame(window, background=bg_color)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.entries = {}

        for tool, config in self.TOOLS_CONFIG.items():
            row = tk.Frame(frame, background=bg_color)
            row.pack(fill="x", pady=5)

            label = tk.Label(row, text=config["name"], width=15, background=bg_color, foreground=text_color)
            label.pack(side="left")

            entry_var = tk.StringVar(value=self.get(tool, "Not assigned"))
            entry = tk.Entry(row, textvariable=entry_var, width=40, background=lighter_color, foreground=text_color)
            entry.pack(side="left", padx=5)
            self.entries[tool] = entry_var

            if tool == "versions_dir":
                browse = tk.Button(row, text="Browse", background=lighter_color, foreground=button_text_color,
                                   command=lambda var=entry_var: self._browse_folder(var))
            else:
                browse = tk.Button(row, text="Browse", background=lighter_color, foreground=button_text_color,
                                   command=lambda t=tool, var=entry_var: self._browse_path(t, var))
            browse.pack(side="left")

        button_frame = tk.Frame(frame, background=bg_color)
        button_frame.pack(fill="x", pady=10)

        # Auto-detect button
        auto_detect_btn = tk.Button(button_frame, text="Auto\nDetect", width=8, height=2,
                                    background=lighter_color, foreground=button_text_color,
                                    command=lambda: self.check_and_fix_paths(window))
        auto_detect_btn.pack(side="left", padx=5)

        # Fix JDK button
        fix_jdk_btn = tk.Button(button_frame, text="Fix\nJDK", width=8, height=2,
                                background=lighter_color, foreground=button_text_color,
                                command=self._setup_jdk_environment)
        fix_jdk_btn.pack(side="left", padx=5)

        # Save button
        save_btn = tk.Button(button_frame, text="Save", background=lighter_color, foreground=button_text_color,
                             command=lambda: self._save_paths(window))
        save_btn.pack(side="right", padx=5)

    def open_themes_window(self):
        """Theme management window"""
        root = self._get_root()
        window = tk.Toplevel(root)
        window.title("Themes Configuration")
        window.geometry("250x200")
        window.grab_set()

        # Center window on screen
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - window.winfo_width()) // 2
        y = (screen_height - window.winfo_height()) // 2
        window.geometry(f"+{x}+{y}")

        themes = self.get("themes", {})
        current_theme = self.get("current_theme", "light")
        font_settings = self.get("font", {"family": "Arial", "size": 10})

        theme_manager = ThemeManager(window, themes, current_theme, font_settings, self)
        theme_manager.pack(fill="both", expand=True, padx=10, pady=10)

    def _open_config_in_editor(self):
        """Open config.json in Notepad (Windows) without blocking GUI"""

        def _open():
            try:
                if not os.path.exists(self.config_file):
                    self._show_info("Config file not found")
                    return

                subprocess.Popen(
                    ['cmd', '/c', 'start', '', 'notepad', self.config_file],
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            except Exception as e:
                self._show_error(f"Failed to open config: {e}")

        threading.Thread(target=_open, daemon=True).start()

    def _browse_path(self, tool, var):
        """Select path for tool."""
        config = self.TOOLS_CONFIG.get(tool, {})
        file_types = config.get("file_types", [("All files", "*.*")])
        description = config.get("description", f"Select {tool} file")

        path = filedialog.askopenfilename(
            title=description,
            filetypes=file_types,
            initialdir=self.initial_dir
        )
        if path:
            var.set(path)

    def _browse_folder(self, var):
        """Select folder for versions_dir"""
        config = self.TOOLS_CONFIG["versions_dir"]
        description = config.get("description", "Select versions folder")

        path = filedialog.askdirectory(
            title=description,
            initialdir=self.initial_dir
        )
        if path:
            var.set(path)

    def _save_paths(self, window):
        """Save chosen paths to config."""
        for tool, var in self.entries.items():
            self.set(tool, var.get())
        self._show_info("Paths updated successfully")

        # Emit event for GUI update
        self.emit("config_updated", {"type": "paths"})

        window.destroy()

    def get_theme_colors(self):
        """Get current theme colors (legacy method for backward compatibility)"""
        theme_data = self.get_theme_data()
        return (theme_data['bg_color'], theme_data['lighter_bg'], theme_data['text_color'],
                theme_data['button_text_color'], theme_data['scroll_text_color'])

    def reset_to_defaults(self):
        """Reset selected config fields to default (without overwriting the entire config)."""
        if not self._show_reset_warning():
            return False
        reset_keys = [
            "initial_start", "versions_dir", "java", "apktool", "apksigner", "zipalign",
            "corona-archiver", "unluac", "last_version", "last_keystore",
            "last_keystore_password", "last_alias", "luac"
        ]

        for key in reset_keys:
            if key == "initial_start":
                self.data[key] = True
            else:
                self.data[key] = ""

        self.save()

        # Emit event after reset
        self.emit("config_updated", {"type": "partial_reset"})

        self._show_info("Selected configuration fields have been reset.")
        return True

    def _show_reset_warning(self):
        """Show warning dialog before resetting config"""
        result = messagebox.askyesno(
            "Reset Configuration",
            "All current configuration will be lost and reset to default values.\n\n"
            "This action cannot be undone!\n\n"
            "Do you want to continue?",
            icon="warning"
        )
        return result

    def set_default_utils(self, location=None):
        """Set default paths based on hardcoded location with file existence check"""
        if location is None:
            location = self.utils_dir

        found_paths = {}

        for tool, config in self.TOOLS_CONFIG.items():
            # Skip tools without location field and versions_dir
            if tool == "versions_dir" or "location" not in config:
                continue

            expected_path = os.path.join(location, config["location"])
            # Check if file exists at expected path
            if os.path.exists(expected_path):
                found_paths[tool] = expected_path
            else:
                # Try to find file by base name in specified directory
                base_dir = os.path.dirname(expected_path)
                base_name = os.path.basename(expected_path)

                if os.path.exists(base_dir):
                    for file in os.listdir(base_dir):
                        file_path = os.path.join(base_dir, file)
                        if os.path.isfile(file_path):
                            # Check by extension and keywords
                            if self._is_matching_file(tool, file, base_name):
                                found_paths[tool] = file_path
                                break

        # Save found paths to config
        for tool, path in found_paths.items():
            self.set(tool, path)

        return found_paths

    def _is_matching_file(self, tool, filename, expected_base):
        """Check if file matches the specified tool"""
        expected_ext = os.path.splitext(expected_base)[1].lower()
        actual_ext = os.path.splitext(filename)[1].lower()

        # First check by extension
        if expected_ext and actual_ext != expected_ext:
            return False

        # Then by keywords in filename
        tool_keywords = {
            "java": ["java"],
            "apktool": ["apktool"],
            "apksigner": ["apksigner"],
            "zipalign": ["zipalign"],
            "unluac": ["unluac"],
            "corona-archiver": ["corona", "archiver"]
        }

        if tool in tool_keywords:
            filename_lower = filename.lower()
            return any(keyword in filename_lower for keyword in tool_keywords[tool])

        return True

    def set_hardcoded_defaults(self, location=None):
        """Set hardcoded paths without checking file existence"""
        if location is None:
            location = self.utils_dir

        for tool, config in self.TOOLS_CONFIG.items():
            # Skip tools without location field and versions_dir
            if tool != "versions_dir" and "location" in config:
                expected_path = os.path.join(location, config["location"])
                self.set(tool, expected_path)

        return True

    def check_and_fix_paths(self, parent_window=None):
        """Check config paths and offer automatic fixing options"""
        missing_tools = []
        invalid_paths = []

        # Check each tool from TOOLS_CONFIG
        for tool, config in self.TOOLS_CONFIG.items():
            # Skip tools without location field
            if "location" not in config and tool != "versions_dir":
                continue

            path = self.get(tool, "")

            if not path:
                missing_tools.append(config["name"])
            elif not os.path.exists(path):
                invalid_paths.append(f"{config['name']}: {path}")

        # If there are path problems
        if missing_tools or invalid_paths:
            problems = []
            if missing_tools:
                problems.append("Not configured: " + ", ".join(missing_tools))
            if invalid_paths:
                problems.append("Invalid paths:\n- " + "\n- ".join(invalid_paths))

            problem_text = "\n".join(problems)

            # Ask user about automatic fixing options
            choice = messagebox.askyesnocancel(
                "Path Problems",
                f"Found problems with tool paths:\n\n{problem_text}\n\n"
                "Choose automatic setup option:\n\n"
                "• YES - Auto-search (intelligent tool search)\n"
                "• NO - Default paths (hardcoded paths)\n"
                "• Cancel - Manual setup",
                icon="warning"
            )

            if choice is True:  # YES - Auto-search
                found = self.set_default_utils()
                self._show_auto_detect_result(found, "Auto-search")

            elif choice is False:  # NO - Hardcoded paths
                self.set_hardcoded_defaults()
                found = {tool: self.get(tool, "") for tool in self.TOOLS_CONFIG.keys()
                         if tool != "versions_dir" and "location" in self.TOOLS_CONFIG[tool]}
                self._show_auto_detect_result(found, "Default Paths")

            # Reload paths window if not Cancel
            if choice is not None and parent_window and hasattr(parent_window, 'destroy'):
                parent_window.destroy()
                self._open_paths_window()

            return choice is not None

        else:
            self._show_info("All paths are configured correctly!")
            return True

    def _show_auto_detect_result(self, found_paths, method_name):
        """Show result of automatic setup"""
        report = []
        for tool, config in self.TOOLS_CONFIG.items():
            # Skip tools without location field
            if "location" not in config and tool != "versions_dir":
                continue

            path = self.get(tool, "")
            if path and os.path.exists(path):
                report.append(f"✓ {config['name']}")
            else:
                report.append(f"✗ {config['name']} (not found)")

        self._show_info(
            f"{method_name} - Result\n\nAutomatic setup result:\n\n" + "\n".join(report)
        )

    def _show_error(self, message):
        """Show error message"""
        root = self._get_root()
        messagebox.showerror("Config error", message, parent=root)

    def _show_info(self, message):
        """Show info message"""
        root = self._get_root()
        messagebox.showinfo("Config", message, parent=root)

    # Initial setup
    def is_initial_start_required(self):
        """Check if initial setup is required"""
        return self.get("initial_start", True)

    def mark_initial_start_completed(self):
        """Mark initial setup as completed"""
        self.set("initial_start", False)
        self.log_message("✅ Initial setup completed")

    def perform_initial_setup(self):
        """Perform initial setup on first launch"""
        if not self.is_initial_start_required():
            return True

        self.log_message("🚀 Performing initial setup...")

        # Verify and configure JDK
        if not self._setup_jdk_environment():
            return False

        # Mark setup as completed
        self.mark_initial_start_completed()
        return True

    # Setup JDK
    def _setup_jdk_environment(self):
        """JDK environment setup - locate and extract modules"""
        java_path = self.get("java")

        # Ofer automatic setup in case Java path is not configured
        if not java_path or not os.path.exists(java_path):
            self.log_message("⚠️ Java path not configured. Starting auto-configuration...")
            if not self.check_and_fix_paths():
                self.log_message("❌ Auto-configuration failed")
                return False
            # Reload path after auto-setup
            java_path = self.get("java")

        if not java_path or not os.path.exists(java_path):
            self.log_message("❌ Java path still not configured after auto-setup")
            return False

        return self._check_and_fix_jdk_environment(java_path)

    def _check_and_fix_jdk_environment(self, java_path):
        """JDK environment verification and repair"""
        try:
            # Locate lib directory (one level up from bin)
            bin_dir = os.path.dirname(java_path)
            jdk_dir = os.path.dirname(bin_dir)
            lib_dir = os.path.join(jdk_dir, "lib")

            self.log_message(f"🔍 Checking JDK environment: {jdk_dir}")

            if not os.path.exists(lib_dir):
                self.log_message(f"❌ JDK lib directory not found: {lib_dir}")
                return False

            # Looking for modules file (without extension)
            modules_path = os.path.join(lib_dir, "modules")
            modules_fix_archive = os.path.join(lib_dir, "modules_fix.rar")

            # Checking for main modules file
            if os.path.exists(modules_path):
                file_size = os.path.getsize(modules_path)
                self.log_message(f"✅ JDK modules file found: {modules_path} ({file_size} bytes)")
                return True
            else:
                self.log_message(f"⚠️ JDK modules file not found: {modules_path}")

                # Looking for fix archive
                if os.path.exists(modules_fix_archive):
                    self.log_message("📦 Found modules_fix.rar, extracting...")
                    return self._extract_modules_fix(modules_fix_archive, lib_dir)
                else:
                    self.log_message("❌ Neither modules file nor modules_fix.rar found")
                    self.log_message("💡 Please ensure JDK installation is complete")
                    return False

        except Exception as e:
            self.log_message(f"❌ JDK environment check failed: {str(e)}")
            return False

    # extractions
    def _extract_modules_fix(self, archive_path, target_dir):
        """Extracting modules_fix.rar archive"""
        try:
            # Checking for WinRAR or built-in RAR support in Python
            if self._extract_with_winrar(archive_path, target_dir):
                self.log_message("✅ modules_fix.rar extracted successfully with WinRAR")
                return True
            elif self._extract_with_python(archive_path, target_dir):
                self.log_message("✅ modules_fix.rar extracted successfully with Python")
                return True
            else:
                self.log_message("❌ Failed to extract modules_fix.rar")
                self.log_message("💡 Please install WinRAR or ensure archive is not corrupted")
                return False

        except Exception as e:
            self.log_message(f"❌ Extraction error: {str(e)}")
            return False


    def _extract_with_winrar(self, archive_path, target_dir):
        """Extraction using WinRAR"""
        try:
            # Trying to find WinRAR in standard paths
            winrar_paths = [
                r"C:\Program Files\WinRAR\WinRAR.exe",
                r"C:\Program Files (x86)\WinRAR\WinRAR.exe",
                r"C:\Program Files\WinRAR\Rar.exe",
                r"C:\Program Files (x86)\WinRAR\Rar.exe"
            ]

            winrar_exe = None
            for path in winrar_paths:
                if os.path.exists(path):
                    winrar_exe = path
                    break

            if not winrar_exe:
                # Trying to find in PATH
                import shutil
                winrar_exe = shutil.which("WinRAR.exe") or shutil.which("Rar.exe")

            if winrar_exe:
                cmd = [winrar_exe, "x", "-y", archive_path, target_dir]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    return True
                else:
                    self.log_message(f"⚠️ WinRAR extraction failed: {result.stderr}")

            return False

        except Exception as e:
            self.log_message(f"⚠️ WinRAR extraction attempt failed: {str(e)}")
            return False

    def _extract_with_python(self, archive_path, target_dir):
        """Extraction using Python libraries"""
        try:
            # Attempt to use patoolib if available
            try:
                import patoolib
                patoolib.extract_archive(archive_path, outdir=target_dir)
                return True
            except ImportError:
                self.log_message("ℹ️ patoolib not available, trying rarfile...")

            # Trying to use rarfile
            try:
                import rarfile
                with rarfile.RarFile(archive_path) as rf:
                    rf.extractall(target_dir)
                return True
            except ImportError:
                self.log_message("ℹ️ rarfile not available")

            # Last attempt - use 7-zip if installed
            return self._extract_with_7zip(archive_path, target_dir)

        except Exception as e:
            self.log_message(f"⚠️ Python extraction failed: {str(e)}")
            return False

    def _extract_with_7zip(self, archive_path, target_dir):
        """Extraction using 7-zip"""
        try:
            seven_zip_paths = [
                r"C:\Program Files\7-Zip\7z.exe",
                r"C:\Program Files (x86)\7-Zip\7z.exe"
            ]

            seven_zip_exe = None
            for path in seven_zip_paths:
                if os.path.exists(path):
                    seven_zip_exe = path
                    break

            if not seven_zip_exe:
                import shutil
                seven_zip_exe = shutil.which("7z.exe")

            if seven_zip_exe:
                cmd = [seven_zip_exe, "x", "-y", archive_path, f"-o{target_dir}"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                return result.returncode == 0

            return False

        except Exception as e:
            self.log_message(f"⚠️ 7-zip extraction failed: {str(e)}")
            return False


    # Stand-Alone run
    def run_standalone(self):
        """Running configurator as standalone application"""
        root = self._get_root()
        root.deiconify()
        root.title("Config Manager - Standalone")

        self._create_standalone_gui(root)

        root.mainloop()

    def _create_standalone_gui(self, root):
        """Creating GUI for standalone mode"""
        # Getting colors
        bg_color, lighter_color, text_color, button_text_color, scroll_text_color = self.get_theme_colors()

        # Main window setting
        root.configure(background=bg_color)
        root.geometry("300x200")

        # Center window on screen
        root.update_idletasks()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - root.winfo_width()) // 2
        y = (screen_height - root.winfo_height()) // 2
        root.geometry(f"+{x}+{y}")

        # Create frame
        frame = tk.Frame(root, background=bg_color)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = tk.Label(
            frame,
            text="Configuration Manager",
            font=("Arial", 14, "bold"),
            background=bg_color,
            foreground=text_color
        )
        title_label.pack(pady=(0, 20))

        # Config Button
        config_btn = tk.Button(
            frame,
            text="Config",
            command=self.open_config_window,
            width=15,
            height=2,
            background=lighter_color,
            foreground=button_text_color,
            activebackground=lighter_color,
            activeforeground=button_text_color
        )
        config_btn.pack(pady=10)

        # Exit Button
        exit_btn = tk.Button(
            frame,
            text="Exit",
            command=root.destroy,
            width=15,
            height=2,
            background=lighter_color,
            foreground=button_text_color,
            activebackground=lighter_color,
            activeforeground=button_text_color
        )
        exit_btn.pack(pady=10)

        # Status bar
        status_label = tk.Label(
            frame,
            text="Standalone mode",
            font=("Arial", 8),
            background=bg_color,
            foreground=text_color
        )
        status_label.pack(side="bottom", pady=(10, 0))

    #abstarct methods
    def log_message(self, message):
        """Unified logging method"""

        print(f"[ConfigManager] {message}")

class ThemeManager(tk.Frame):
    def __init__(self, parent, themes, current_theme, font_settings, config_manager):
        super().__init__(parent)
        self.themes = themes
        self.current_theme = current_theme
        self.font_settings = font_settings
        self.cfg = config_manager
        self.parent_window = parent

        self._create_widgets()
        self._apply_theme_to_window()

    def _create_widgets(self):
        # Top section - theme selection
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", pady=(0, 10))

        tk.Label(top_frame, text="Select Theme", font=("Arial", 12, "bold")).pack(anchor="w")

        # Frame for theme buttons
        theme_buttons_frame = tk.Frame(top_frame)
        theme_buttons_frame.pack(fill="x", pady=10)

        # Light/Dark buttons
        light_dark_frame = tk.Frame(theme_buttons_frame)
        light_dark_frame.pack(side="left", padx=(0, 10))

        self.light_btn = tk.Button(light_dark_frame, text="L", width=3, height=2,
                                   command=lambda: self._select_theme("light"))
        self.light_btn.pack(pady=1)

        self.dark_btn = tk.Button(light_dark_frame, text="D", width=3, height=2,
                                  command=lambda: self._select_theme("dark"))
        self.dark_btn.pack(pady=1)

        # Custom button
        self.custom_btn = tk.Button(theme_buttons_frame, text="CUSTOM", width=8, height=5,
                                    command=self._customize_theme)
        self.custom_btn.pack(side="left")

        # Font button
        self.font_btn = tk.Button(theme_buttons_frame, text="Font", width=8, height=5,
                                  command=self._change_font)
        self.font_btn.pack(side="right", padx=(10, 0))

        # Customization area
        self.customize_frame = tk.LabelFrame(self, text="Customize Colors")

        # Control buttons
        button_frame = tk.Frame(self)
        button_frame.pack(fill="x", pady=10)

        self.save_btn = tk.Button(button_frame, text="Save & Close",
                                  command=self._save_and_close)
        self.save_btn.pack(side="right", padx=5)

        tk.Button(button_frame, text="Cancel", command=self.parent_window.destroy).pack(side="left")

    def _create_customize_widgets(self):
        """Create widgets for theme customization"""
        for widget in self.customize_frame.winfo_children():
            widget.destroy()

        theme = self.themes["custom"]

        color_fields = [
            ("Background", "background", "Main window background"),
            ("Button Text", "button_text", "Button text color"),
            ("Scroll Text", "scroll_text", "Log text color")
        ]

        self.color_vars = {}

        for label, key, description in color_fields:
            color_frame = tk.Frame(self.customize_frame)
            color_frame.pack(fill="x", pady=3, padx=5)

            tk.Label(color_frame, text=label, width=15, anchor="w").pack(side="left")
            tk.Label(color_frame, text=description, fg="gray", font=("Arial", 8)).pack(side="left", padx=(5, 0))

            var = tk.StringVar(value=theme.get(key, "#000000"))
            entry = tk.Entry(color_frame, textvariable=var, width=8)
            entry.pack(side="left", padx=5)

            color_btn = tk.Button(color_frame, text="🎨", width=3,
                                  command=lambda v=var, k=key: self._pick_color(v, k))
            color_btn.pack(side="left")

            self.color_vars[key] = var
            var.trace('w', lambda *args: self._apply_theme_to_window())

    def _pick_color(self, color_var, color_key):
        """Color picker dialog"""
        from tkinter import colorchooser
        color = colorchooser.askcolor(initialcolor=color_var.get(), title=f"Choose {color_key}")
        if color[1]:
            color_var.set(color[1])

    def _select_theme(self, theme_name):
        """Select preset theme"""
        self.current_theme = theme_name
        self._apply_theme_to_window()

    def _customize_theme(self):
        """Enter customization mode"""
        self.current_theme = "custom"
        self._create_customize_widgets()
        self.customize_frame.pack(fill="x", pady=5)
        self._apply_theme_to_window()

    def _change_font(self):
        """Font selection dialog"""
        # Create font selection window
        font_window = tk.Toplevel(self.parent_window)
        font_window.title("Font Selection")
        font_window.geometry("300x200")
        font_window.grab_set()

        # Apply theme to font selection window
        self._apply_theme_to_specific_window(font_window)

        frame = tk.Frame(font_window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Current font settings
        current_family = self.font_settings.get("family", "Arial")
        current_size = self.font_settings.get("size", 10)

        # Font family selection
        tk.Label(frame, text="Font Family:").pack(anchor="w")
        font_family_var = tk.StringVar(value=current_family)
        font_family_combo = ttk.Combobox(frame, textvariable=font_family_var, state="readonly")
        font_family_combo['values'] = ['Arial', 'Helvetica', 'Times New Roman', 'Courier New', 'Verdana', 'Tahoma']
        font_family_combo.pack(fill="x", pady=5)

        # Font size selection
        tk.Label(frame, text="Font Size:").pack(anchor="w")
        font_size_var = tk.StringVar(value=str(current_size))
        font_size_combo = ttk.Combobox(frame, textvariable=font_size_var, state="readonly")
        font_size_combo['values'] = ['8', '9', '10', '11', '12', '14', '16', '18']
        font_size_combo.pack(fill="x", pady=5)

        # Buttons
        button_frame = tk.Frame(frame)
        button_frame.pack(fill="x", pady=10)

        def apply_font():
            try:
                new_family = font_family_var.get()
                new_size = int(font_size_var.get())

                self.font_settings = {
                    "family": new_family,
                    "size": new_size
                }

                # SAVE TO CONFIG:
                self.cfg.set("font", self.font_settings)

                font_window.destroy()

            except ValueError:
                pass

        tk.Button(button_frame, text="Apply", command=apply_font).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=font_window.destroy).pack(side="right", padx=5)

        # Apply theme to all widgets in font selection window
        self._apply_theme_to_specific_window(font_window)

    def _apply_theme_to_window(self):
        """Apply theme to theme settings window"""
        theme = self.themes[self.current_theme]

        bg_color = theme.get("background", "#FFFFFF")
        text_color = theme.get("text_color", "#000000")
        button_text_color = theme.get("button_text", "#000000")
        scroll_text_color = theme.get("scroll_text", "#000000")
        lighter_color = self.cfg.lighten_color(bg_color, 0.2)

        # Apply to all widgets in settings window
        all_widgets = self._get_all_widgets(self.parent_window)

        for widget in all_widgets:
            try:
                if isinstance(widget, (tk.Frame, tk.LabelFrame)):
                    widget.configure(background=bg_color)
                else:
                    widget.configure(background=lighter_color)

                if isinstance(widget, tk.Button):
                    widget.configure(foreground=button_text_color, background=lighter_color)
                elif isinstance(widget, (tk.Label, tk.Entry)):
                    widget.configure(foreground=text_color)
            except:
                pass

        self.parent_window.configure(background=bg_color)
        self.configure(background=bg_color)

    def _apply_theme_to_specific_window(self, window):
        """Apply theme to specific window"""
        theme = self.themes[self.current_theme]

        bg_color = theme.get("background", "#FFFFFF")
        text_color = theme.get("text_color", "#000000")
        button_text_color = theme.get("button_text", "#000000")
        lighter_color = self.cfg.lighten_color(bg_color, 0.2)

        # Apply to all widgets in window
        all_widgets = self._get_all_widgets(window)

        for widget in all_widgets:
            try:
                if isinstance(widget, (tk.Frame, tk.LabelFrame)):
                    widget.configure(background=bg_color)
                else:
                    widget.configure(background=lighter_color)

                if isinstance(widget, tk.Button):
                    widget.configure(foreground=button_text_color, background=lighter_color)
                elif isinstance(widget, (tk.Label, tk.Entry)):
                    widget.configure(foreground=text_color)
            except:
                pass


        window.configure(background=bg_color)

    def _get_all_widgets(self, parent):
        """Recursively get all window widgets"""
        widgets = [parent]
        for child in parent.winfo_children():
            widgets.extend(self._get_all_widgets(child))
        return widgets

    def _save_and_close(self):
        """Save configuration and close window"""
        # Update custom theme if edited
        if self.current_theme == "custom" and hasattr(self, 'color_vars'):
            for key, var in self.color_vars.items():
                self.themes["custom"][key] = var.get()

        # Save to config
        self.cfg.set("themes", self.themes)
        self.cfg.set("current_theme", self.current_theme)
        self.cfg.set("font", self.font_settings)

        # Emit event for GUI reload
        self.cfg.emit("config_updated", {
            "type": "theme",
            "theme": self.current_theme,
            "font": self.font_settings
        })

        # Close theme settings window
        self.parent_window.destroy()

class ConfigEditor:
    def __init__(self, config_manager):
        self.cfg = config_manager
        self.parent_window = None
        self.bg_color, self.lighter_color, self.text_color, self.button_text_color, self.scroll_text_color = self.cfg.get_theme_colors()

    def open_editor(self):
        """Open the advanced configuration editor"""
        root = self.cfg._get_root()
        self.parent_window = tk.Toplevel(root)
        self.parent_window.title("Advanced Configuration Editor")
        self.parent_window.geometry("550x700")
        self.parent_window.grab_set()

        # Applying theme to main window
        self.parent_window.configure(background=self.bg_color)

        # Center window
        self.parent_window.update_idletasks()
        screen_width = self.parent_window.winfo_screenwidth()
        screen_height = self.parent_window.winfo_screenheight()
        x = (screen_width - self.parent_window.winfo_width()) // 2
        y = (screen_height - self.parent_window.winfo_height()) // 2
        self.parent_window.geometry(f"+{x}+{y}")

        # Configuring style for tabs
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=self.lighter_color,
                        foreground=self.text_color,
                        focuscolor=self.bg_color,
                        padding=[10, 5])
        style.map("TNotebook.Tab",
                  background=[("selected", self.bg_color),
                              ("active", self.lighter_color)],
                  foreground=[("selected", self.text_color),
                              ("active", self.text_color)])

        # Create notebook for tabs
        notebook = ttk.Notebook(self.parent_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Button Layout Tab
        buttons_frame = tk.Frame(notebook, bg=self.bg_color)
        self._create_buttons_editor(buttons_frame)
        notebook.add(buttons_frame, text="Button Layout")

        # Folders Tab
        folders_frame = tk.Frame(notebook, bg=self.bg_color)
        self._create_folders_editor(folders_frame)
        notebook.add(folders_frame, text="Folders")

        # Bindings Tab
        bindings_frame = tk.Frame(notebook, bg=self.bg_color)
        self._create_bindings_editor(bindings_frame)
        notebook.add(bindings_frame, text="Button Bindings")

        # Control buttons
        btn_frame = tk.Frame(self.parent_window, background=self.bg_color)
        btn_frame.pack(fill="x", pady=10)

        save_btn = tk.Button(btn_frame, text="Save All",
                             command=lambda: self._save_all(self.parent_window),
                             background=self.lighter_color, foreground=self.button_text_color)
        save_btn.pack(side="right", padx=5)

        cancel_btn = tk.Button(btn_frame, text="Cancel",
                               command=self.parent_window.destroy,
                               background=self.lighter_color, foreground=self.button_text_color)
        cancel_btn.pack(side="right", padx=5)

    def _enable_hotkeys(self, text_widget):
        """Enable Ctrl+V paste functionality for Text widgets (physical key binding)"""

        def paste(event=None):
            try:
                text_widget.insert(tk.INSERT, text_widget.clipboard_get())
                return "break"  # Prevent default behavior
            except tk.TclError:
                pass

        def copy(event=None):
            """Копирование в буфер обмена"""
            try:
                if text_widget.tag_ranges(tk.SEL):
                    # Copy text if selected
                    selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                    text_widget.clipboard_clear()
                    text_widget.clipboard_append(selected_text)
                return "break"
            except tk.TclError:
                pass

        def undo(event=None):
            """Отмена последнего действия"""
            try:
                text_widget.edit_undo()
                return "break"
            except tk.TclError:
                # Ignore in case undo not supported
                pass

        text_widget.configure(undo=True)

        # Bind by keycode - works regardless of keyboard layout
        # Paste(Ctrl+V)
        text_widget.bind("<Control-KeyPress>", lambda e: paste() if e.keycode == 86 else None)
        # Copy (Ctrl+C)
        text_widget.bind("<Control-KeyPress>", lambda e: copy() if e.keycode == 67 else None)
        # Undo (Ctrl+Z)
        text_widget.bind("<Control-KeyPress>", lambda e: undo() if e.keycode == 90 else None)

    def _create_buttons_editor(self, parent):
        """Editor for buttons_shape [rows, columns]"""
        frame = tk.LabelFrame(parent, text="Button Grid Layout",
                             bg=self.bg_color, fg=self.text_color)
        frame.pack(fill="x", padx=10, pady=5)

        current = self.cfg.get("buttons_shape", [])

        # Use existing values or empty
        rows_val = str(current[0]) if len(current) > 0 else ""
        cols_val = str(current[1]) if len(current) > 1 else ""

        # Rows
        rows_label = tk.Label(frame, text="Rows:", bg=self.bg_color, fg=self.text_color)
        rows_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.rows_var = tk.StringVar(value=rows_val)
        rows_entry = tk.Entry(frame, textvariable=self.rows_var, width=10,
                             bg=self.lighter_color, fg=self.text_color, insertbackground=self.text_color)
        rows_entry.grid(row=0, column=1, padx=5, pady=5)

        # Columns
        cols_label = tk.Label(frame, text="Columns:", bg=self.bg_color, fg=self.text_color)
        cols_label.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.cols_var = tk.StringVar(value=cols_val)
        cols_entry = tk.Entry(frame, textvariable=self.cols_var, width=10,
                             bg=self.lighter_color, fg=self.text_color, insertbackground=self.text_color)
        cols_entry.grid(row=0, column=3, padx=5, pady=5)

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

    def _create_folders_editor(self, parent):
        """folder_structure Editor"""
        frame = tk.LabelFrame(parent, text="Folders",
                              bg=self.bg_color, fg=self.text_color)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        folders = self.cfg.get("folder_structure", {})
        self.folder_vars = {}

        folder_keys = list(folders.keys())

        if not folder_keys:
            no_folders_label = tk.Label(frame, text="No folders configured",
                                        bg=self.bg_color, fg="gray")
            no_folders_label.pack(pady=20)
            return

        # create scrolling frame
        canvas = tk.Canvas(frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Button Titles
        key_label = tk.Label(scrollable_frame, text="Key", font=("Arial", 9, "bold"),
                             bg=self.bg_color, fg=self.text_color)
        key_label.grid(row=0, column=0, padx=5, pady=5)

        name_label = tk.Label(scrollable_frame, text="Name", font=("Arial", 9, "bold"),
                              bg=self.bg_color, fg=self.text_color)
        name_label.grid(row=0, column=1, padx=5, pady=5)

        for i, key in enumerate(folder_keys, 1):
            # Key label - fixed frame
            key_label = tk.Label(scrollable_frame, text=f"{key}:", bg=self.bg_color, fg=self.text_color)
            key_label.grid(row=i, column=0, sticky="w", padx=5, pady=2)

            # Name entry - editable frame (заменяем Entry на Text для поддержки Ctrl+V)
            value = folders[key]
            name_text = tk.Text(scrollable_frame, width=25, height=1, wrap=tk.NONE,
                                bg=self.lighter_color, fg=self.text_color,
                                insertbackground=self.text_color)
            name_text.insert("1.0", value)
            name_text.grid(row=i, column=1, sticky="ew", padx=5, pady=2)

            # Включаем поддержку Ctrl+V
            self._enable_hotkeys(name_text)

            # Сохраняем ссылку на виджет
            self.folder_vars[key] = name_text

        scrollable_frame.columnconfigure(1, weight=1)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _create_bindings_editor(self, parent):
        """Bindings Editor"""
        frame = tk.LabelFrame(parent, text="Button Bindings",
                              bg=self.bg_color, fg=self.text_color)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        bindings = self.cfg.get("bindings", [])
        self.binding_data = bindings.copy()  # Save original data
        self.binding_vars = []  # Edited bindings list
        self.binding_texts = []  # Edited text list for Display Name
        self.desc_texts = []  # Edited text list for Description

        if not bindings:
            no_bindings_label = tk.Label(frame, text="No button bindings configured",
                                         bg=self.bg_color, fg="gray")
            no_bindings_label.pack(pady=20)
            return

        # create scrolling frame
        canvas = tk.Canvas(frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Button Titles
        button_label = tk.Label(scrollable_frame, text="Button #", font=("Arial", 9, "bold"),
                                bg=self.bg_color, fg=self.text_color)
        button_label.grid(row=0, column=0, padx=5, pady=5)

        desc_label = tk.Label(scrollable_frame, text="Description", font=("Arial", 9, "bold"),
                              bg=self.bg_color, fg=self.text_color)
        desc_label.grid(row=0, column=1, padx=5, pady=5)

        name_label = tk.Label(scrollable_frame, text="Display Name", font=("Arial", 9, "bold"),
                              bg=self.bg_color, fg=self.text_color)
        name_label.grid(row=0, column=2, padx=5, pady=5)

        # Create frame for each binding
        for i, binding in enumerate(bindings, 1):
            # Button Number (Editable frame)
            button_num = str(binding.get("button", ""))
            button_var = tk.StringVar(value=button_num)
            button_entry = tk.Entry(scrollable_frame, textvariable=button_var, width=3,
                                    bg=self.lighter_color, fg=self.text_color,
                                    insertbackground=self.text_color)
            button_entry.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            self.binding_vars.append(button_var)

            # Description (Text widget with 2 lines and word wrap)
            description = binding.get("description", binding.get("tool", ""))
            desc_text = tk.Text(scrollable_frame, width=30, height=2, wrap=tk.WORD,
                                bg=self.lighter_color, fg=self.text_color,
                                insertbackground=self.text_color)
            desc_text.insert("1.0", description)
            desc_text.grid(row=i, column=1, padx=5, pady=2, sticky="nsew")
            self._enable_hotkeys(desc_text)  # Enable Ctrl+V
            self.desc_texts.append(desc_text)

            # Display Name (Text widget with 2 lines and word wrap)
            name_content = binding.get("name", "")
            name_text = tk.Text(scrollable_frame, width=15, height=2, wrap=tk.WORD,
                                bg=self.lighter_color, fg=self.text_color,
                                insertbackground=self.text_color)
            name_text.insert("1.0", name_content)
            name_text.grid(row=i, column=2, padx=5, pady=2, sticky="nsew")
            self._enable_hotkeys(name_text)  # Enable Ctrl+V
            self.binding_texts.append(name_text)

        scrollable_frame.columnconfigure(1, weight=1)
        scrollable_frame.columnconfigure(2, weight=1)
        scrollable_frame.rowconfigure(tk.ALL, weight=1)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _save_all(self, window):
        """Save all changes"""
        # Save buttons_shape
        rows = self.rows_var.get().strip()
        cols = self.cols_var.get().strip()

        if rows and cols:
            try:
                self.cfg.set("buttons_shape", [int(rows), int(cols)])
            except ValueError:
                messagebox.showerror("Error", "Rows and Columns must be numbers")
                return
        else:
            if "buttons_shape" in self.cfg.data:
                del self.cfg.data["buttons_shape"]

        # Save folder_structure
        if hasattr(self, 'folder_vars') and self.folder_vars:
            folders = {}
            for key, var in self.folder_vars.items():
                value = var.get().strip()
                if value:
                    folders[key] = value

            if folders:
                self.cfg.set("folder_structure", folders)
            else:
                if "folder_structure" in self.cfg.data:
                    del self.cfg.data["folder_structure"]

        # Save bindings
        if hasattr(self, 'binding_vars') and self.binding_vars and hasattr(self, 'binding_data'):
            updated_bindings = []
            button_numbers = set()
            duplicate_found = False

            # Check for duplicates
            for i, binding in enumerate(self.binding_data):
                if i < len(self.binding_vars):
                    button_var = self.binding_vars[i]
                    button_num = button_var.get().strip()

                    if button_num:
                        try:
                            button_num_int = int(button_num)
                            if button_num_int in button_numbers:
                                messagebox.showerror("Error",
                                                     f"Duplicate button number found: {button_num}\n"
                                                     "Button numbers must be unique.")
                                duplicate_found = True
                                break
                            button_numbers.add(button_num_int)
                        except ValueError:
                            messagebox.showerror("Error",
                                                 f"Invalid button number: '{button_num}'\n"
                                                 "Button number must be a valid integer.")
                            duplicate_found = True
                            break

            # If duplicates or invalid numbers are found, abort saving
            if duplicate_found:
                return

            # Save data if validation passes
            for i, binding in enumerate(self.binding_data):
                if i < len(self.binding_vars) and i < len(self.binding_texts):
                    button_var = self.binding_vars[i]
                    name_text = self.binding_texts[i]

                    # Retrieve updated values
                    button_num = button_var.get().strip()
                    name_content = name_text.get("1.0", "end-1c").strip()

                    # Create updated binding
                    updated_binding = binding.copy()

                    # Update button number only if valid
                    if button_num:
                        try:
                            updated_binding["button"] = int(button_num)
                        except ValueError:
                            pass

                    # Update name
                    updated_binding["name"] = name_content

                    updated_bindings.append(updated_binding)

            if updated_bindings:
                self.cfg.set("bindings", updated_bindings)
            else:
                if "bindings" in self.cfg.data:
                    del self.cfg.data["bindings"]

        self.cfg.save()
        self.cfg.emit("config_updated", {"type": "advanced"})
        window.destroy()

if __name__ == "__main__":
    print("Starting ConfigManager as standalone application...")
    config = ConfigManager()
    config.run_standalone()