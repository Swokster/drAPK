import tkinter as tk
from tkinter import ttk, scrolledtext
from config_manager import ConfigManager
from drtool import UTF8Decoder_LUA_to_UTF8 as UTF8

class DemoGUI:
    def __init__(self, config_path="config.json"):
        self.cfg = ConfigManager(config_path)
        self.cfg.main_gui = self
        self.theme = self.cfg.get_theme_data()

        self.root = tk.Tk()
        self.root.title("DEMOTOOL GUI")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.reload_callbacks = []

        # Subscribe to config events
        self.cfg.on("config_updated", self._on_config_updated)

        # Apply theme to main window
        self.root.configure(background=self.theme['bg_color'])

        # Create widgets
        self._setup_window()
        self._create_widgets()

        # Tool initialize
        self._initialize_tools(config_path)
    def _execute_command(self, event):
        """CLI"""
        command = self.command_entry.get().strip().lower()
        if not command:
            return

        self.log_message(f"> {command}")

        parts = command.split()
        command = parts[0].lower()
        args = " ".join(parts[1:]) if len(parts) > 1 else ""

        match command:
            case "clear" | "cls":
                self.log_text.config(state="normal")
                self.log_text.delete(1.0, tk.END)
                self.log_text.config(state="normal")

            case "help" | "?":
                self.log_message("  'help' or '?' - show help")
                self.log_message("  'clear' or 'cls' - clear log")
                self.log_message("  'theme' - open theme config")
                self.log_message("  'reset' - reset config")
                self.log_message("  'utf8' or 'utf8 xx x' - decode UTF-8")

            case "theme":
                self.cfg.open_themes_window(self.root)

            case "reset":
                self.cfg.reset_to_defaults()
                self.log_message("✅ Configuration has been reset to default values")

            case "utf8":
                utf8_tool = UTF8()
                utf8_tool.set_log_callback(self.log_message)
                utf8_tool.cli(args)  # Pass arguments to CLI method

            case _:
                self.log_message(f"Unknown command: {command}")
                self.log_message("Enter 'help' to get list of available commands")

        self.command_entry.delete(0, tk.END)  # Clear CL

    def _setup_window(self):
        """Configure window size and position"""
        #screen_width = self.root.winfo_screenwidth()
        screen_width = 1990
        screen_height = self.root.winfo_screenheight()
        window_width = screen_width // 4
        window_height = screen_height // 2
        self.root.geometry(
            f"{window_width}x{window_height}+{(screen_width // 2 - window_width // 2)}+{screen_height // 2 - window_height // 2}")

    def _create_widgets(self):
        """Create widgets interface"""
        padding = 5

        # Top frame
        top_frame = tk.Frame(self.root, background=self.theme['bg_color'])
        top_frame.pack(fill='x', padx=padding, pady=padding)

        # Firs row - version control
        version_frame = tk.Frame(top_frame, background=self.theme['bg_color'])
        version_frame.pack(fill='x', pady=(0, 5))

        # Combobox_1 - version control
        self.combo_var = tk.StringVar()
        self.combo = ttk.Combobox(version_frame, textvariable=self.combo_var, state="readonly", width=20)
        self.combo.pack(side='left', padx=(0, padding))

        # Open folder button
        self.open_btn = self.create_button(version_frame, "📁", None, width=3)
        self.open_btn.pack(side='left', padx=(0, padding))

        # Add APK Button
        self.add_btn = self.create_button(version_frame, "➕", None, width=3)
        self.add_btn.pack(side='left', padx=(0, padding))

        # Second row - keystore
        keystore_frame = tk.Frame(top_frame, background=self.theme['bg_color'])
        keystore_frame.pack(fill='x', pady=(5, 0))

        # ComboBox aliases
        self.keystore_combo_var = tk.StringVar()
        self.keystore_combo = ttk.Combobox(keystore_frame, textvariable=self.keystore_combo_var, state="readonly",
                                           width=20)
        self.keystore_combo.pack(side='left', padx=(0, padding))

        # Select keystore button
        self.keystore_browse_btn = self.create_button(keystore_frame, "📁", None, width=3)
        self.keystore_browse_btn.pack(side='left', padx=(0, padding))

        # Keystore generation button
        self.keystore_gen_btn = self.create_button(keystore_frame, "➕", None, width=3)
        self.keystore_gen_btn.pack(side='left', padx=(0, padding))



        # Configuration button
        self.config_btn = self.create_button(keystore_frame, "Config", self._open_config)
        self.config_btn.pack(side='right', padx=(5, 0))
        # Reload Gui button
        self.reload_btn = self.create_button(keystore_frame, "🔄", self._reload_gui, width=3)
        self.reload_btn.pack(side='right', padx=(10, 0))

        # Tool buttons
        self.btn_frame = tk.Frame(self.root, background=self.theme['bg_color'])
        self.btn_frame.pack(pady=padding)

        # Log
        log_frame = tk.Frame(self.root, background=self.theme['bg_color'])
        log_frame.pack(fill='both', expand=True, padx=padding, pady=padding)

        # Log Label
        log_label = tk.Label(log_frame, text="Log:",
                             background=self.theme['bg_color'],
                             foreground=self.theme['text_color'])
        log_label.pack(anchor="w")

        # ScrollText filed
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=8,
            background=self.theme['lighter_bg'],
            foreground=self.theme['scroll_text_color'],
            insertbackground=self.theme['scroll_text_color']
        )
        self.log_text.pack(fill='both', expand=True)
        #self.log_text.config(state="disabled")

        # Progress bar
        self.progress = ttk.Progressbar(
            self.root,
            orient='horizontal',
            mode='determinate',
            maximum=100
        )
        self.progress.pack(fill='x', padx=padding, pady=(0, padding))

        # Progress bar Style
        style = ttk.Style()
        style.configure("TProgressbar",
                        background=self.theme['lighter_bg'],
                        troughcolor=self.theme['bg_color'])
        # Command Line
        self.command_entry = tk.Entry(
            self.root,
            background=self.theme['lighter_bg'],
            foreground=self.theme['scroll_text_color']
        )
        self.command_entry.pack(fill='x', padx=padding, pady=(0, padding))
        self.command_entry.bind('<Return>', self._execute_command)

    def create_button(self, parent, text, command, width=12, height=2):
        """Create button with theme applied"""
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            height=height,
            background=self.theme['lighter_bg'],
            foreground=self.theme['button_text_color'],
            activebackground=self.theme['lighter_bg'],
            activeforeground=self.theme['button_text_color']
        )

    def _initialize_tools(self, config_path):
        """Tools initialization function"""
        try:
            from drtool import VersionManager, KeystoreManager

            # Create Tools
            self.vermng = VersionManager(config_path)
            self.keystore_mng = KeystoreManager(config_path)

            # Set logging callback for logging
            self.vermng.set_log_callback(self.log_message)
            self.keystore_mng.set_log_callback(self.log_message)

            # Sign for event
            self.vermng.on('versions_updated', self._on_versions_updated)
            self.vermng.on('versions_refreshed', self._on_versions_refreshed)
            self.vermng.on('version_changed', self._on_version_changed)

            # Initialise interface
            self._initialize_interface()

        except ImportError as e:
            self.log_message(f"⚠️ Tools not available: {e}")
            self._initialize_empty_interface()

    def _initialize_interface(self):
        """Initialize the interface with tools"""
        # Version combobox
        self.vermng.set_gui_combobox(self.combo, self.combo_var)
        self.combo.bind('<<ComboboxSelected>>', self._on_version_selected)

        # Aliases combobox
        self.keystore_mng.set_gui_combobox(self.keystore_combo, self.keystore_combo_var)
        self.keystore_combo.bind('<<ComboboxSelected>>', self._on_alias_selected)

        # Set commands for buttons
        self.open_btn.config(command=self.vermng.open_current_folder)
        self.add_btn.config(command=self.vermng.run)
        self.keystore_browse_btn.config(command=self.keystore_mng.run)
        self.keystore_gen_btn.config(command=self.keystore_mng.generator.run)

        # Create tool buttons
        self._create_tool_buttons()

    def _initialize_empty_interface(self):
        """Initialize empty interface (without tools)"""
        # Disable buttons
        self.open_btn.config(state="disabled")
        self.add_btn.config(state="disabled")
        self.keystore_browse_btn.config(state="disabled")
        self.combo.config(state="disabled")
        self.keystore_combo.config(state="disabled")

        # Create empty tool buttons
        self._create_empty_tool_buttons()

    def _create_tool_buttons(self):
        """Create tool buttons dynamically based on configuration"""
        bindings = self.cfg.get("bindings", [])
        rows, cols = self.cfg.get("buttons_shape", [2, 4])

        # Buttons create from config
        btn_count = 1
        for row in range(rows):
            row_frame = tk.Frame(self.btn_frame, background=self.theme['bg_color'])
            row_frame.pack()
            for col in range(cols):
                btn_text = ""
                btn_command = None

                # check bindings in config
                binding = next((b for b in bindings if b["button"] == btn_count), None)

                if binding:
                    tool_name = binding.get("tool", "")
                    display_name = binding.get("name", tool_name)

                    if tool_name:
                        try:
                            # Create a closure for deferred initialization
                            def create_tool_runner(tool_class_name=tool_name, tool_display_name=display_name):
                                def tool_runner():
                                    try:
                                        # Dynamically import and instantiate the tool on demand (upon click)
                                        tool_module = __import__('drtool')
                                        tool_class = getattr(tool_module, tool_class_name)

                                        # Initialize a NEW instance of the tool
                                        tool_instance = tool_class(self.cfg.config_file)
                                        tool_instance.set_log_callback(self.log_message)
                                        tool_instance.progress(self._update_progress)

                                        #self.log_message(f"🔄 Starting {tool_display_name}...")
                                        tool_instance.run()

                                    except Exception as e:
                                        self.log_message(f"❌ Error initializing {tool_display_name}: {e}")

                                return tool_runner

                            btn_text = display_name
                            btn_command = create_tool_runner()

                        except Exception as e:
                            btn_text = display_name
                            self.log_message(f"⚠️ Tool {tool_name} setup error: {e}")

                # Create a button with explicit color settings
                btn = self.create_button(row_frame, btn_text, btn_command)

                # Disable the button if no functionality is available for it
                if not binding or not binding.get("tool", ""):
                    btn.config(state="disabled", background=self.theme['darker_bg'])

                btn.pack(side='left', padx=2, pady=2)
                btn_count += 1

    def _create_empty_tool_buttons(self):
        """Create placeholder buttons (when no tools are available)"""
        bindings = self.cfg.get("bindings", [])
        rows, cols = self.cfg.get("buttons_shape", [3, 6])

        btn_count = 1
        for row in range(rows):
            row_frame = tk.Frame(self.btn_frame, background=self.theme['bg_color'])
            row_frame.pack()
            for col in range(cols):
                btn_text = ""

                # Find a label for the button
                binding = next((b for b in bindings if b["button"] == btn_count), None)
                if binding:
                    btn_text = binding.get("name", binding.get("tool", ""))

                # Create placeholder button
                btn = self.create_button(row_frame, btn_text, None)
                btn.config(state="disabled", background=self.theme['darker_bg'])
                btn.pack(side='left', padx=2, pady=2)
                btn_count += 1

    def _update_progress(self, value):
        """Progressbar update Callback"""
        self.progress['value'] = value
        self.root.update_idletasks()

    def _on_version_selected(self, event):
        """Version select event handler"""
        selected_version = self.combo_var.get()
        if selected_version and hasattr(self, 'vermng'):
            self.vermng.update_version_on_select(selected_version)

    def _on_versions_updated(self, data):
        """Version update event handler"""
        self.log_message("🔄 Versions updated - refreshing UI...")
        self._update_versions_combobox()

    def _on_versions_refreshed(self, data):
        """Version list update event handler"""
        self._update_versions_combobox()

    def _on_version_changed(self, data):
        """Version change event handler"""
        version = data.get('version', '')
        self.log_message(f"📍 Active version: {version}")

    def _on_config_updated(self, data):
        """Configuration update event handler"""
        update_type = data.get("type", "")
        self.log_message(f"🔄 Config updated: {update_type}")

        # Reload GUI with a short delay
        self.root.after(100, self._reload_gui)
    def _on_alias_selected(self, event):
        """Alias selection event handler"""
        selected_alias = self.keystore_combo_var.get()
        if selected_alias and hasattr(self, 'keystore_mng'):
            self.keystore_mng.update_alias_selection(selected_alias)

    def _update_versions_combobox(self):
        """Reload GUI with a short delay"""
        if hasattr(self, 'vermng') and self.combo:
            versions = self.vermng.get_versions_for_combo()
            self.combo['values'] = versions

            current_version = self.vermng.last_version
            if current_version and current_version in versions:
                self.combo_var.set(current_version)
            elif versions:
                self.combo_var.set(versions[0])
            else:
                self.combo_var.set("")

    def _open_config(self):
        """Open config window"""
        self.cfg.open_config_window()

    def log_message(self, text):
        """Log message"""
        if hasattr(self, 'log_text'):
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, f"{text}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
            self.root.update_idletasks()
        else:
            print(text)

    def _reload_gui(self):
        """Thread-safe GUI reload"""

        def perform_reload():
            self.log_message("🔄 Reloading GUI...")
            self.root.destroy()
            new_gui = DemoGUI(self.cfg.config_file)
            new_gui.run()

        self.root.after(0, perform_reload)

    def _on_close(self):
        """Close window event handler"""
        self.root.destroy()

    def run(self):
        """Start main loop"""
        self.root.mainloop()


def create_gui(config_path="config.json"):
    return DemoGUI(config_path)