import os
import json
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
            "description": "Java executable (java.exe)",
            "file_types": [("Java executable", "java.exe"), ("All files", "*.*")],
            "required": True
        },
        "apktool": {
            "name": "APKTool",
            "description": "APKTool JAR file",
            "file_types": [("JAR files", "*.jar"), ("All files", "*.*")],
            "required": True
        },
        "apksigner": {
            "name": "APKSigner",
            "description": "APKSigner tool",
            "file_types": [("APKSigner", "apksigner.bat"), ("All files", "*.*")],
            "required": True
        },
        "zipalign": {
            "name": "Zipalign",
            "description": "Zipalign tool",
            "file_types": [("Zipalign", "zipalign.exe"), ("All files", "*.*")],
            "required": True
        },
        "unluac": {
            "name": "Unluac",
            "description": "Unluac decompiler JAR",
            "file_types": [("JAR files", "*.jar"), ("All files", "*.*")],
            "required": True
        },
        "corona-archiver": {
            "name": "Corona Archiver",
            "description": "Corona Archiver Python script",
            "file_types": [("Python files", "*.py"), ("All files", "*.*")],
            "required": True
        }
    }

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.data = self._load()
        self.main_gui = None
        # Get project root path (where config_manager.py is located)
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.utils_dir = os.path.join(self.project_root, "utils")
        self.initial_dir = self.utils_dir

    def _load(self):
        """Load config from file or return default dict."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                messagebox.showerror("Config error", f"Failed to load config: {e}")
                return {}
        return {}

    def save(self):
        """Save current config to file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Config error", f"Failed to save config: {e}")

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
    def lighten_color(hex_color, factor=0.2):
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
    def open_config_window(self, parent):
        """Open configuration window with tabs/buttons."""
        window = tk.Toplevel(parent)
        window.title("Configuration")

        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        window_width = 150
        window_height = 130

        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2

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
                               command=lambda: [window.destroy(), self.open_themes_window(parent)])
        btn_themes.pack(pady=5)

        btn_paths = tk.Button(frame, text="Paths", width=btn_width,
                              background=lighter_color, foreground=button_text_color,
                              command=lambda: [window.destroy(), self._open_paths_window(parent)])
        btn_paths.pack(pady=5)

        btn_reset = tk.Button(frame, text="Reset to Defaults", width=btn_width,
                              background=lighter_color, foreground=button_text_color,
                              command=lambda: [window.destroy(),self.reset_to_defaults()])
        btn_reset.pack(pady=5)

    def _open_paths_window(self, parent):
        """Sub-window for selecting paths."""
        window = tk.Toplevel(parent)  # parent - original main window
        window.title("Tools paths")
        window.geometry("500x400")
        window.grab_set()

        # Get colors directly from config
        bg_color, lighter_color, text_color, button_text_color, scroll_text_color = self.get_theme_colors()
        window.configure(background=bg_color)

        # Remove padding from Frame, use padx/pady in pack
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

        save_btn = tk.Button(frame, text="Save", background=lighter_color, foreground=button_text_color,
                             command=lambda: self._save_paths(window))
        save_btn.pack(pady=10)

    def open_themes_window(self, parent):
        """Theme management window"""
        window = tk.Toplevel(parent)
        window.title("Themes Configuration")
        window.geometry("250x200")
        window.grab_set()

        themes = self.get("themes", {})
        current_theme = self.get("current_theme", "light")
        font_settings = self.get("font", {"family": "Arial", "size": 10})

        theme_manager = ThemeManager(window, themes, current_theme, font_settings, self, self.main_gui)
        theme_manager.pack(fill="both", expand=True, padx=10, pady=10)

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
        messagebox.showinfo("Saved", "Paths updated successfully")
        window.destroy()

    def get_theme_colors(self):
        """Get current theme colors (legacy method for backward compatibility)"""
        theme_data = self.get_theme_data()
        return (theme_data['bg_color'], theme_data['lighter_bg'], theme_data['text_color'],
                theme_data['button_text_color'], theme_data['scroll_text_color'])

    def reset_to_defaults(self):
        """Reset config to default values"""
        if not self._show_reset_warning():
            return False
        default_config = {
            "versions_dir": "",
            "java": "",
            "apktool": "",
            "apksigner": "",
            "zipalign": "",
            "corona-archiver": "",
            "unluac": "",
            "last_version": "",
            "last_keystore": "",
            "last_keystore_password": "",
            "last_alias": "",

            "buttons_shape": [2, 4],
            "bindings": [
                {"button": 1, "tool": "UnAPK", "name": "Unpack\nAPK"},
                {"button": 2, "tool": "deCAR", "name": "Decompile\nresource.car"},
                {"button": 3, "tool": "Unluac_All", "name": "Unluac\nLU"},
                {"button": 4, "tool": "Unluac", "name": "Unluac\nINPUT"},
                {"button": 5, "tool": "Pack", "name": "Pack\nSign"},
                {"button": 6, "tool": "ToCAR", "name": "Compile\nresource.car"},
                {"button": 7, "tool": "Luac_All", "name": "Luac\nEDITING"},
                {"button": 8, "tool": "Luac", "name": "Luac\nINPUT"}
            ],

            "themes": {
                "light": {
                    "name": "Light",
                    "background": "#FFFFFF",
                    "text_color": "#000000",
                    "button_text": "#000000",
                    "scroll_text": "#000000"
                },
                "dark": {
                    "name": "Dark",
                    "background": "#2B2B2B",
                    "text_color": "#FFFFFF",
                    "button_text": "#FFFFFF",
                    "scroll_text": "#CCCCCC"
                },
                "custom": {
                    "name": "Custom",
                    "background": "#1E3A5F",
                    "text_color": "#FFFFFF",
                    "button_text": "#FFFFFF",
                    "scroll_text": "#E0E0E0"
                }
            },
            "current_theme": "dark",
            "font": {
                "family": "Arial",
                "size": 10
            }
        }

        self.data = default_config
        self.save()
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

class ThemeManager(tk.Frame):
    def __init__(self, parent, themes, current_theme, font_settings, config_manager, main_gui):
        super().__init__(parent)
        self.themes = themes
        self.current_theme = current_theme
        self.font_settings = font_settings
        self.cfg = config_manager
        self.main_gui = main_gui
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

        # Close theme settings window
        self.parent_window.destroy()

        # Reload main GUI
        if self.main_gui and hasattr(self.main_gui, '_reload_gui'):
            self.main_gui._reload_gui()