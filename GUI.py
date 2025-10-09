import tkinter as tk
from tkinter import ttk, scrolledtext
from config_manager import ConfigManager


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

        # Применяем тему к корневому окну
        self.root.configure(background=self.theme['bg_color'])

        # Создаем виджеты
        self._setup_window()
        self._create_widgets()

        # Инициализируем инструменты
        self._initialize_tools(config_path)
    def _execute_command(self, event):
        """CLI"""
        command = self.command_entry.get().strip().lower()
        if not command:
            return

        self.log_message(f"> {command}")

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

            case "theme":
                self.cfg.open_themes_window(self.root)

            case "reset":
                self.cfg.reset_to_defaults()
                self.log_message("✅ Configuration has been reset to default values")

            case _:
                self.log_message(f"Unknown command: {command}")
                self.log_message("Enter 'help' to get list of available commands")

        self.command_entry.delete(0, tk.END)  # Очищаем поле

    def _setup_window(self):
        """Настройка размеров и положения окна"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = screen_width // 4
        window_height = screen_height // 2
        self.root.geometry(
            f"{window_width}x{window_height}+{(screen_width // 2 - window_width // 2)}+{screen_height // 2 - window_height // 2}")

    def _create_widgets(self):
        """Создание всех виджетов интерфейса"""
        padding = 5

        # Верхняя рамка
        top_frame = tk.Frame(self.root, background=self.theme['bg_color'])
        top_frame.pack(fill='x', padx=padding, pady=padding)

        # Первый ряд - версии
        version_frame = tk.Frame(top_frame, background=self.theme['bg_color'])
        version_frame.pack(fill='x', pady=(0, 5))

        # Комбобокс версий
        self.combo_var = tk.StringVar()
        self.combo = ttk.Combobox(version_frame, textvariable=self.combo_var, state="readonly", width=20)
        self.combo.pack(side='left', padx=(0, padding))

        # Кнопка открытия папки
        self.open_btn = self.create_button(version_frame, "📁", None, width=3)
        self.open_btn.pack(side='left', padx=(0, padding))

        # Кнопка добавления APK
        self.add_btn = self.create_button(version_frame, "➕", None, width=3)
        self.add_btn.pack(side='left', padx=(0, padding))

        # Второй ряд - keystore
        keystore_frame = tk.Frame(top_frame, background=self.theme['bg_color'])
        keystore_frame.pack(fill='x', pady=(5, 0))

        # Комбобокс aliases
        self.keystore_combo_var = tk.StringVar()
        self.keystore_combo = ttk.Combobox(keystore_frame, textvariable=self.keystore_combo_var, state="readonly",
                                           width=20)
        self.keystore_combo.pack(side='left', padx=(0, padding))

        # Кнопка выбора keystore
        self.keystore_browse_btn = self.create_button(keystore_frame, "📁", None, width=3)
        self.keystore_browse_btn.pack(side='left', padx=(0, padding))

        # Кнопка генерации keystore
        self.keystore_gen_btn = self.create_button(keystore_frame, "➕", None, width=3)
        self.keystore_gen_btn.pack(side='left', padx=(0, padding))

        # Кнопка перезагрузки GUI
        self.reload_btn = self.create_button(keystore_frame, "🔄", self._reload_gui, width=3)
        self.reload_btn.pack(side='right', padx=(5, 0))

        # Кнопка конфигурации
        self.config_btn = self.create_button(keystore_frame, "Config", self._open_config)
        self.config_btn.pack(side='right')

        # Кнопки инструментов
        self.btn_frame = tk.Frame(self.root, background=self.theme['bg_color'])
        self.btn_frame.pack(pady=padding)

        # Лог
        log_frame = tk.Frame(self.root, background=self.theme['bg_color'])
        log_frame.pack(fill='both', expand=True, padx=padding, pady=padding)

        # Метка лога
        log_label = tk.Label(log_frame, text="Log:",
                             background=self.theme['bg_color'],
                             foreground=self.theme['text_color'])
        log_label.pack(anchor="w")

        # Текстовое поле лога
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=8,
            background=self.theme['lighter_bg'],
            foreground=self.theme['scroll_text_color'],
            insertbackground=self.theme['scroll_text_color']
        )
        self.log_text.pack(fill='both', expand=True)
        #self.log_text.config(state="disabled")

        # Прогресс бар
        self.progress = ttk.Progressbar(
            self.root,
            orient='horizontal',
            mode='determinate',
            maximum=100
        )
        self.progress.pack(fill='x', padx=padding, pady=(0, padding))

        # Настраиваем стиль прогрессбара
        style = ttk.Style()
        style.configure("TProgressbar",
                        background=self.theme['lighter_bg'],
                        troughcolor=self.theme['bg_color'])
        # Поле ввода команд (после прогрессбара)
        self.command_entry = tk.Entry(
            self.root,
            background=self.theme['lighter_bg'],
            foreground=self.theme['scroll_text_color']
        )
        self.command_entry.pack(fill='x', padx=padding, pady=(0, padding))
        self.command_entry.bind('<Return>', self._execute_command)

    def create_button(self, parent, text, command, width=12, height=2):
        """Создает кнопку с текущей темой"""
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
        """Инициализация инструментов"""
        try:
            from drtool import Vermng, KeystoreManager

            # Create Tools
            self.vermng = Vermng(config_path)
            self.keystore_mng = KeystoreManager(config_path)

            # Set logging callback для логирования
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
        """Инициализация интерфейса с инструментами"""
        # Комбобокс версий
        self.vermng.set_gui_combobox(self.combo, self.combo_var)
        self.combo.bind('<<ComboboxSelected>>', self._on_version_selected)

        # Комбобокс aliases
        self.keystore_mng.set_gui_combobox(self.keystore_combo, self.keystore_combo_var)
        self.keystore_combo.bind('<<ComboboxSelected>>', self._on_alias_selected)

        # Устанавливаем команды для кнопок
        self.open_btn.config(command=self.vermng.open_current_folder)
        self.add_btn.config(command=self.vermng.run)
        self.keystore_browse_btn.config(command=self.keystore_mng.run)
        self.keystore_gen_btn.config(command=self.keystore_mng.generator.run)

        # Создаем кнопки инструментов
        self._create_tool_buttons()

    def _initialize_empty_interface(self):
        """Инициализация пустого интерфейса (без инструментов)"""
        # Делаем кнопки неактивными
        self.open_btn.config(state="disabled")
        self.add_btn.config(state="disabled")
        self.keystore_browse_btn.config(state="disabled")
        self.combo.config(state="disabled")
        self.keystore_combo.config(state="disabled")

        # Создаем пустые кнопки инструментов
        self._create_empty_tool_buttons()

    def _create_tool_buttons(self):
        """Создание кнопок инструментов на основе конфигурации"""
        bindings = self.cfg.get("bindings", [])
        rows, cols = self.cfg.get("buttons_shape", [2, 4])

        # Создаем кнопки
        btn_count = 1
        for row in range(rows):
            row_frame = tk.Frame(self.btn_frame, background=self.theme['bg_color'])
            row_frame.pack()
            for col in range(cols):
                btn_text = ""
                btn_command = None
                tool_instance = None

                # Ищем привязку для текущей кнопки
                binding = next((b for b in bindings if b["button"] == btn_count), None)

                if binding:
                    tool_name = binding.get("tool", "")
                    display_name = binding.get("name", tool_name)

                    if tool_name:
                        try:
                            # Динамически импортируем инструмент
                            tool_module = __import__('drtool')
                            tool_class = getattr(tool_module, tool_name)

                            # Создаем экземпляр инструмента
                            tool_instance = tool_class(self.cfg.config_file)
                            tool_instance.set_log_callback(self.log_message)

                            # Устанавливаем callback для прогресс-бара
                            tool_instance.progress(self._update_progress)

                            btn_text = display_name
                            btn_command = tool_instance.run
                        except AttributeError:
                            # Если инструмент не найден
                            btn_text = display_name
                            self.log_message(f"⚠️ Tool {tool_name} not found")

                # Создаем кнопку с явным указанием цветов
                btn = self.create_button(row_frame, btn_text, btn_command)

                # Делаем кнопку неактивной если для нее нет функционала
                if not binding or not binding.get("tool", ""):
                    btn.config(state="disabled", background=self.theme['darker_bg'])

                btn.pack(side='left', padx=2, pady=2)
                btn_count += 1

    def _create_empty_tool_buttons(self):
        """Создание пустых кнопок (когда инструментов нет)"""
        bindings = self.cfg.get("bindings", [])
        rows, cols = self.cfg.get("buttons_shape", [3, 6])

        btn_count = 1
        for row in range(rows):
            row_frame = tk.Frame(self.btn_frame, background=self.theme['bg_color'])
            row_frame.pack()
            for col in range(cols):
                btn_text = ""

                # Ищем название для кнопки
                binding = next((b for b in bindings if b["button"] == btn_count), None)
                if binding:
                    btn_text = binding.get("name", binding.get("tool", ""))

                # Создаем неактивную кнопку
                btn = self.create_button(row_frame, btn_text, None)
                btn.config(state="disabled", background=self.theme['darker_bg'])
                btn.pack(side='left', padx=2, pady=2)
                btn_count += 1

    def _update_progress(self, value):
        """Callback для обновления прогресс-бара"""
        self.progress['value'] = value
        self.root.update_idletasks()

    def _on_version_selected(self, event):
        """Обработчик выбора версии"""
        selected_version = self.combo_var.get()
        if selected_version and hasattr(self, 'vermng'):
            self.vermng.update_version_on_select(selected_version)

    def _on_versions_updated(self, data):
        """Обработчик события обновления версий"""
        self.log_message("🔄 Versions updated - refreshing UI...")
        self._update_versions_combobox()

    def _on_versions_refreshed(self, data):
        """Обработчик события обновления списка версий"""
        self._update_versions_combobox()

    def _on_version_changed(self, data):
        """Обработчик события смены версии"""
        version = data.get('version', '')
        self.log_message(f"📍 Active version: {version}")

    def _on_config_updated(self, data):
        """Обработчик обновления конфигурации"""
        update_type = data.get("type", "")
        self.log_message(f"🔄 Config updated: {update_type}")

        # Перезагружаем GUI через короткую задержку
        self.root.after(100, self._reload_gui)

    def _update_versions_combobox(self):
        """Обновление комбобокса версий"""
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

    def _on_alias_selected(self, event):
        """Обработчик выбора alias"""
        selected_alias = self.keystore_combo_var.get()
        if selected_alias and hasattr(self, 'keystore_mng'):
            self.keystore_mng.update_alias_selection(selected_alias)

    def _open_config(self):
        """Открытие окна конфигурации"""
        self.cfg.open_config_window()

    def log_message(self, text):
        """Добавление сообщения в лог"""
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
        """Обработчик закрытия окна"""
        self.root.destroy()

    def run(self):
        """Запуск главного цикла"""
        self.root.mainloop()


def create_gui(config_path="config.json"):
    return DemoGUI(config_path)