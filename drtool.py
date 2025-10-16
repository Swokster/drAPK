import os
import re
import sys
import subprocess
import shutil
import time
import tkinter as tk
from time import sleep
from tkinter import filedialog, messagebox
from abc import ABC, abstractmethod
from config_manager import ConfigManager
import concurrent.futures
import threading


class BaseTool(ABC):
    """Base tool class"""

    version_path = None

    def __init__(self, config_path="config.json"):
        self.cfg = ConfigManager(config_path)
        self.theme = self.cfg.get_theme_data()
        self.log_callback = None
        self.progress_callback = None
        self.event_handlers = {}

        last_version = self.cfg.get("last_version")
        versions_dir = self.cfg.get("versions_dir")
        self._setup_paths()

        if not versions_dir or not last_version:
            pass
        else:
            BaseTool.version_path = os.path.join(versions_dir, last_version)

    def on(self, event_name, callback):
        """Event subscription mechanism"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(callback)

    def emit(self, event_name, data=None):
        """Event generation"""
        if event_name in self.event_handlers:
            for callback in self.event_handlers[event_name]:
                try:
                    callback(data)
                except Exception as e:
                    self.log(f"❌ Event handler error: {e}")

    def _setup_paths(self):
        """Create base folder structure from config"""
        if BaseTool.version_path:
            # Getting folder structure form config
            folder_structure = self.cfg.get("folder_structure")

            # Dynamically generate paths based on configuration
            self.paths = {}
            for key, folder_name in folder_structure.items():
                self.paths[key] = os.path.join(BaseTool.version_path, folder_name)
        else:
            # If version is missing, initialize empty paths for all config keys
            folder_structure = self.cfg.get("folder_structure", {})
            self.paths = {key: '' for key in folder_structure.keys()}

    def set_reload_callback(self, callback):
        self.reload_callback = callback

    def log(self, message):
        """Logging tool"""
        if self.log_callback:
            self.log_callback(message)

    def set_log_callback(self, callback):
        """GUI set callback"""
        self.log_callback = callback

    def progress(self, callback):
        """GUI  set progress bar callback"""
        self.progress_callback = callback

    @classmethod
    def refresh(cls, new_version_path):
        cls.version_path = new_version_path

    def get_config(self, key, default=None):
        """Get Config values"""
        return self.cfg.get(key, default)

    def set_config(self, key, value):
        """Set config values"""
        self.cfg.set(key, value)

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def message(self):
        pass

class DRTool(BaseTool):
    """Base Class for DayR Tools (Corona Archiver, Unluac, Luac)"""
    pass

class APKTool(BaseTool):
    """Base class for APK operations"""
    pass


# APKTool Classes
class UnAPK(APKTool):
    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.result_message = ""
        self.apktool_path = self.cfg.get("apktool")
        self.java_path = self.cfg.get("java")

    def run(self):
        """Launch unpacking in a background thread"""
        if not self.apktool_path:
            raise FileNotFoundError("APKTool path not configured")
        if not self.java_path:
            raise FileNotFoundError("JDK path not configured")
        thread = threading.Thread(target=self._unpack_apk)
        thread.daemon = True
        thread.start()

    def _unpack_apk(self):
        """APK unpacking in a background thread"""
        try:
            if not BaseTool.version_path:
                self.log("❌ No version selected")
                return

            apk_folder = self.paths['apk']
            unpack_folder = self.paths['apk_unpacked']

            if not os.path.isdir(apk_folder):
                self.log("❌ APK folder not found")
                return

            apk_files = [f for f in os.listdir(apk_folder) if f.lower().endswith(".apk")]
            if not apk_files:
                self.log("❌ No APK files found")
                return

            apk_file = os.path.join(apk_folder, apk_files[0])
            self.log(f"🔧 Unpacking: {apk_files[0]}")

            os.makedirs(unpack_folder, exist_ok=True)

            self.log("🔄 Running APKTool...")
            result = subprocess.run(
                [self.java_path, "-jar", self.apktool_path, "d", apk_file, "-o", unpack_folder, "-f"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.result_message = "APK unpacked successfully"
                self.log(f"✅ APK unpacked successfully to {unpack_folder}")
            else:
                self.log(f"❌ APKTool error: {result.stderr}")

        except Exception as e:
            self.log(f"❌ Error: {str(e)}")

    def message(self):
        return self.result_message

class Pack(APKTool):

    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.result_message = ""
        self.start_time = None
        self.stage_times = {}
        self.final_name = self._get_apk_name()
        self.output_dir = self.paths['output']

    def run(self):
        """Launch packaging and signing in a separate thread"""
        thread = threading.Thread(target=self._pack_and_sign)
        thread.daemon = True
        thread.start()

    def _get_apk_name(self):
        """Get exact APK filename without extension from 1_APK folder"""
        apk_folder = self.paths['apk']
        if os.path.exists(apk_folder):
            apk_files = [f for f in os.listdir(apk_folder) if f.lower().endswith(".apk")]
            if apk_files:
                return os.path.splitext(apk_files[0])[0]
        return "app"

    def _pack_and_sign(self):
        """Main method: packaging and signing in background mode"""
        self.start_time = time.time()

        try:
            self.log("📦 Starting APK packaging and signing...")

            # Refresh progressbar
            if self.progress_callback:
                self.progress_callback(10)

            # 1. APK Building
            stage_start = time.time()
            apk_path = self._pack_apk()
            self.stage_times['packaging'] = time.time() - stage_start

            if not apk_path:
                self._reset_progress()
                return

            # Refresh progressbar
            if self.progress_callback:
                self.progress_callback(50)

            # 2. Getting alias
            stage_start = time.time()
            keystore_data = self._get_keystore_data()
            self.stage_times['keystore'] = time.time() - stage_start

            if not keystore_data:
                self._reset_progress()
                return

            # Refresh progressbar
            if self.progress_callback:
                self.progress_callback(60)

            # 3. Signing APK
            stage_start = time.time()
            success = self._sign_apk(apk_path, keystore_data)
            self.stage_times['signing'] = time.time() - stage_start

            if success:
                # Refresh progressbar to 100%
                if self.progress_callback:
                    self.progress_callback(100)

                self._show_time_summary()
                self.result_message = "APK packaged and signed successfully"
                self.log(f"✅ APK packaging and signing completed.")
            else:
                self._reset_progress()
                self.log("❌ APK signing failed")

        except Exception as e:
            self.log(f"❌ Packaging error: {str(e)}")
            self._reset_progress()

    def _show_time_summary(self):
        """Displays execution time summary"""
        total_time = time.time() - self.start_time

        # Time formatting
        def format_time(seconds):
            if seconds < 1:
                return f"{seconds * 1000:.0f}ms"
            elif seconds < 60:
                return f"{seconds:.1f}s"
            else:
                mins = int(seconds // 60)
                secs = seconds % 60
                return f"{mins}m {secs:.1f}s"

        self.log("⏱️  Time summary:")
        self.log(f"   📦 Packaging: {format_time(self.stage_times.get('packaging', 0))}")
        self.log(f"   🔑 Keystore: {format_time(self.stage_times.get('keystore', 0))}")
        self.log(f"   🔏 Signing: {format_time(self.stage_times.get('signing', 0))}")
        self.log(f"   ⏱️  Total: {format_time(total_time)}")

    def _reset_progress(self):
        """Reset progress bar on error"""
        if self.progress_callback:
            self.progress_callback(0)

    def _pack_apk(self):
        """Package APK files"""
        try:
            unpack_dir = self.paths['apk_unpacked']
            self.output_dir = self.paths['output']

            # Use final_name for output file
            unsigned_apk_name = f"unsigned_{self.final_name}.apk"
            apk_path = os.path.join(self.output_dir, unsigned_apk_name)

            if not os.path.exists(unpack_dir):
                self.log(f"❌ Unpacked APK directory not found: {unpack_dir}")
                return None

            # Create output directory
            os.makedirs(self.output_dir, exist_ok=True)

            # Get apktool and java paths
            apktool_path = self.get_config("apktool")
            java_path = self.get_config("java")
            if not apktool_path or not java_path:
                self.log("❌ APKTool or Java path not configured")
                return None

            # Remove old APK if exists
            if os.path.exists(apk_path):
                self.log("🗑️ Removing old APK file...")
                os.remove(apk_path)

            # Build APK without signing
            cmd = [
                java_path, "-jar", apktool_path,
                "b", unpack_dir,
                "-o", apk_path
            ]

            self.log(f"🔄 Building APK: {unsigned_apk_name}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if os.path.exists(apk_path):
                self.log(f"✅ APK packaged (unsigned): {unsigned_apk_name}")
                return apk_path
            else:
                self.log("❌ APK file not created")
                return None

        except subprocess.CalledProcessError as e:
            self.log(f"❌ APKTool packaging error: {e.stderr}")
            return None
        except Exception as e:
            self.log(f"❌ Packaging error: {str(e)}")
            return None

    def _get_keystore_data(self):
        """Retrieve key data from configuration"""
        try:
            #self.log("🔑 Getting keystore data...")

            # IMPORTANT: Force reload configuration before use
            self.cfg = ConfigManager(self.cfg.config_file)

            # Always fetch the latest data from the config
            keystore_path = self.cfg.get("last_keystore")
            keystore_password = self.cfg.get("last_keystore_password")
            alias = self.cfg.get("last_alias")

            #self.log(f"📋 Keystore config: {keystore_path}")
            #self.log(f"📋 Alias config: {alias}")

            if not keystore_path:
                self.log("❌ Keystore path not configured")
                return None

            if not os.path.exists(keystore_path):
                self.log(f"❌ Keystore file not found: {keystore_path}")
                return None

            if not keystore_password:
                self.log("❌ Keystore password not configured")
                return None

            if not alias:
                self.log("❌ Keystore alias not configured")
                return None

            keystore_data = {
                'path': keystore_path,
                'password': keystore_password,
                'alias': alias
            }

            self.log(f"✅ Keystore data loaded: {os.path.basename(keystore_path)}")
            self.log(f" 📍 Alias: {alias}")

            return keystore_data

        except Exception as e:
            self.log(f"❌ Keystore data error: {str(e)}")
            return None

    def _sign_apk(self, apk_path, keystore_data):
        """Sign APK with proper Java environment"""
        try:
            self.log("🔏 Signing APK...")

            if not os.path.exists(apk_path):
                self.log("❌ APK file not found for signing")
                return False

            # Get tool paths
            apksigner_path = self.get_config("apksigner")
            zipalign_path = self.get_config("zipalign")
            java_path = self.get_config("java")

            if not all([apksigner_path, zipalign_path, java_path]):
                self.log("❌ Required tools not configured")
                return False

            # Set JAVA_HOME from java.exe path
            java_home = os.path.dirname(os.path.dirname(java_path))

            # Define output paths
            signed_apk_name = f"{self.final_name}.apk"
            signed_apk_path = os.path.join(self.output_dir, signed_apk_name)
            aligned_apk_path = os.path.join(self.output_dir, f"aligned_{self.final_name}.apk")

            # Clean up old files
            for path in [aligned_apk_path, signed_apk_path]:
                if os.path.exists(path):
                    #self.log(f"🗑️ Removing old file: {os.path.basename(path)}")
                    os.remove(path)

            # 1. Zipalign (65% progress)
            self.log("🔄 Aligning APK...")
            if self.progress_callback:
                self.progress_callback(65)

            align_cmd = [zipalign_path, "-v", "-p", "4", apk_path, aligned_apk_path]
            subprocess.run(align_cmd, capture_output=True, text=True, check=True)
            #self.log("✅ APK aligned")

            # 2. APKSigner signing (80% progress) - ONLY ONCE
            self.log("🔄 Signing APK...")
            if self.progress_callback:
                self.progress_callback(80)

            sign_cmd = [
                apksigner_path, "sign",
                "--ks", keystore_data['path'],
                "--ks-pass", f"pass:{keystore_data['password']}",
                "--key-pass", f"pass:{keystore_data['password']}",
                "--ks-key-alias", keystore_data['alias'],
                "--out", signed_apk_path,
                aligned_apk_path
            ]

            # Set Java environment
            env = os.environ.copy()
            env['JAVA_HOME'] = java_home
            env['PATH'] = f"{os.path.dirname(java_path)};{env['PATH']}"

            # Execute signing ONLY ONCE
            result = subprocess.run(sign_cmd, capture_output=True, text=True, check=True, timeout=120, env=env)

            if result.returncode == 0:
                self.log("✅ APK signed successfully")
            else:
                self.log(f"❌ APK signing failed: {result.stderr}")
                return False

            # 3. Final cleanup (90% progress)
            self.log("🔄 Finalizing...")
            if self.progress_callback:
                self.progress_callback(90)

            # Clean up temporary files
            if os.path.exists(aligned_apk_path):
                os.remove(aligned_apk_path)
                #self.log("🗑️ Temporary aligned file removed")

            if os.path.exists(apk_path):
                os.remove(apk_path)
                #self.log("🗑️ Temporary unsigned file removed")

            # Clean up APKSigner signature file
            signature_file = signed_apk_path + ".idsig"
            if os.path.exists(signature_file):
                os.remove(signature_file)
                #self.log("🗑️ Removed temporary signature file")

            self.log(f"📦 Signed APK: {signed_apk_name}")
            return True

        except subprocess.CalledProcessError as e:
            self.log(f"❌ Signing process error: {e.stderr.strip()}")
            return False

        except Exception as e:
            self.log(f"❌ Signing error: {str(e)}")
            return False

    def message(self):
        return self.result_message

class GenerateKeystore(APKTool):
    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.java_path = self.get_config("java")


    def run(self):
        """Run keystore generation/adding alias form"""
        if not self.java_path:
            raise FileNotFoundError("Java path not configured")
        thread = threading.Thread(target=self._show_mode_selection)
        thread.daemon = True
        thread.start()

    def _show_mode_selection(self):
        form = tk.Toplevel()
        form.title("Keystore Manager")
        form.geometry("300x150")
        form.grab_set()
        form.resizable(False, False)

        # Apply theme
        form.configure(background=self.theme['bg_color'])

        # Create widgets with explicit color settings
        label = tk.Label(form, text="Select operation:", font=("Arial", 12),
                         background=self.theme['bg_color'], foreground=self.theme['text_color'])
        label.pack(pady=20)

        btn_frame = tk.Frame(form, background=self.theme['bg_color'])
        btn_frame.pack(pady=10)

        new_btn = tk.Button(btn_frame, text="New Keystore", width=12,
                            background=self.theme['lighter_bg'], foreground=self.theme['button_text_color'],
                            command=lambda: self._show_generate_form(form))
        new_btn.pack(side="left", padx=10)

        add_btn = tk.Button(btn_frame, text="Add Key", width=12,
                            background=self.theme['lighter_bg'], foreground=self.theme['button_text_color'],
                            command=lambda: self._show_add_key_form(form))
        add_btn.pack(side="left", padx=10)

        cancel_btn = tk.Button(form, text="Cancel",
                               background=self.theme['lighter_bg'], foreground=self.theme['button_text_color'],
                               command=form.destroy)
        cancel_btn.pack(pady=10)

    def _show_generate_form(self, parent_window):
        """New keystore generation form"""
        parent_window.destroy()
        self._show_keystore_form("Generate Keystore", self._generate_keystore, is_add_mode=False)

    def _show_add_key_form(self, parent_window):
        """Alias addition form"""
        parent_window.destroy()
        self._show_keystore_form("Add Key to Keystore", self._add_key_to_keystore, is_add_mode=True)

    def _show_keystore_form(self, title, submit_callback, is_add_mode=False):
        """Universal form for keystore management"""
        form = tk.Toplevel()
        form.title(title)
        form.geometry("500x400" if is_add_mode else "400x500")
        form.grab_set()
        form.resizable(False, False)

        # Apply Theme
        form.configure(background=self.theme['bg_color'])

        # Apply Forms Defaults
        filename_var = tk.StringVar(value="myapp.keystore")
        keystore_path_var = tk.StringVar()
        alias_var = tk.StringVar(value="release-key")
        password_var = tk.StringVar(value="123456")
        cn_var = tk.StringVar(value="My App")
        ou_var = tk.StringVar(value="Android Development")
        o_var = tk.StringVar(value="My Company")
        l_var = tk.StringVar(value="City")
        st_var = tk.StringVar(value="City")
        c_var = tk.StringVar(value="EU")
        show_pass_var = tk.BooleanVar()

        frame = tk.Frame(form, padx=10, pady=10, background=self.theme['bg_color'])
        frame.pack(fill="both", expand=True)

        row = 0

        # Keystore file selection field (add mode only)
        if is_add_mode:
            tk.Label(frame, text="Keystore file:",
                     background=self.theme['bg_color'], foreground=self.theme['text_color']).grid(row=row, column=0,
                                                                                                  sticky="w", pady=5)
            keystore_frame = tk.Frame(frame, background=self.theme['bg_color'])
            keystore_frame.grid(row=row, column=1, sticky="ew", pady=5)
            tk.Entry(keystore_frame, textvariable=keystore_path_var, width=40,
                     background=self.theme['lighter_bg'], foreground=self.theme['text_color']).pack(side="left",
                                                                                                    padx=(0, 5))
            tk.Button(keystore_frame, text="...",
                      background=self.theme['lighter_bg'], foreground=self.theme['button_text_color'],
                      command=lambda: self._browse_keystore_file(keystore_path_var)).pack(side="left")
            row += 1
        else:
            # Filename input field (create mode only)
            tk.Label(frame, text="Filename*:",
                     background=self.theme['bg_color'], foreground=self.theme['text_color']).grid(row=row, column=0,
                                                                                                  sticky="w", pady=2)
            tk.Entry(frame, textvariable=filename_var, width=30,
                     background=self.theme['lighter_bg'], foreground=self.theme['text_color']).grid(row=row, column=1,
                                                                                                    sticky="ew", pady=2)
            row += 1

        # Show Password Checkbox
        password_entry_ref = [None]

        def toggle_pass_visibility():
            if password_entry_ref[0]:
                if show_pass_var.get():
                    password_entry_ref[0].config(show="")
                else:
                    password_entry_ref[0].config(show="*")

        tk.Checkbutton(frame, text="Show password", variable=show_pass_var,
                       background=self.theme['bg_color'], foreground=self.theme['text_color'],
                       command=toggle_pass_visibility).grid(
            row=row, column=0, sticky="w", columnspan=2, pady=5)
        row += 1

        # General fileds
        fields = [
            ("Alias*:", alias_var, False),
            ("Password*:", password_var, True),
            ("Common Name (CN)*:", cn_var, False),
            ("Organization (O)*:", o_var, False),
            ("Organizational Unit (OU):", ou_var, False),
            ("City (L)*:", l_var, False),
            ("State (ST)*:", st_var, False),
            ("Country Code (C)*:", c_var, False)
        ]

        # Create form fields with explicit color specifications
        for label_text, var, is_password in fields:
            tk.Label(frame, text=label_text,
                     background=self.theme['bg_color'], foreground=self.theme['text_color']).grid(row=row, column=0,
                                                                                                  sticky="w", pady=2)
            entry = tk.Entry(frame, textvariable=var, width=30, show="*" if is_password else "",
                             background=self.theme['lighter_bg'], foreground=self.theme['text_color'])
            entry.grid(row=row, column=1, sticky="ew", pady=2)

            if is_password:
                password_entry_ref[0] = entry

            row += 1

        # Buttons
        btn_frame = tk.Frame(frame, background=self.theme['bg_color'])
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)

        submit_text = "Add Key" if is_add_mode else "Generate"
        submit_btn = tk.Button(btn_frame, text=submit_text,
                               background=self.theme['lighter_bg'], foreground=self.theme['button_text_color'],
                               command=lambda: submit_callback(form, filename_var, keystore_path_var, alias_var,
                                                               password_var, cn_var, ou_var, o_var, l_var, st_var,
                                                               c_var,
                                                               is_add_mode))
        submit_btn.pack(side="left", padx=5)

        cancel_btn = tk.Button(btn_frame, text="Cancel",
                               background=self.theme['lighter_bg'], foreground=self.theme['button_text_color'],
                               command=form.destroy)
        cancel_btn.pack(side="left", padx=5)

        frame.columnconfigure(1, weight=1)

    def _browse_keystore_file(self, keystore_path_var):
        """Keystore choose"""
        keystore_path = filedialog.askopenfilename(
            title="Select Keystore file",
            filetypes=[("Keystore files", "*.keystore *.jks"), ("All files", "*.*")]
        )
        if keystore_path:
            keystore_path_var.set(keystore_path)

    def _validate_fields(self, is_add_mode, **fields):
        """Form's fileds validation"""
        for field_name, field_value in fields.items():
            if not field_value.strip():
                messagebox.showerror("Error", f"Please fill all required fields (*)")
                return False

        if is_add_mode and not os.path.exists(fields['keystore_path']):
            messagebox.showerror("Error", "Keystore file not found")
            return False

        return True

    def _prepare_dname(self, cn, ou, o, l, st, c):
        """Prepation Distinguished Name"""
        dn_parts = []
        if cn: dn_parts.append(f"CN={cn}")
        if ou: dn_parts.append(f"OU={ou}")
        if o: dn_parts.append(f"O={o}")
        if l: dn_parts.append(f"L={l}")
        if st: dn_parts.append(f"ST={st}")
        if c: dn_parts.append(f"C={c}")
        return ",".join(dn_parts)

    def _execute_keytool_command(self, cmd, success_message, error_context, form):
        """Execute keytool command"""
        try:
            keytool_path = self._find_keytool()
            if not keytool_path:
                raise FileNotFoundError("keytool not found")

            self.log(f"🔄 Command: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=120)

            if process.returncode == 0:
                self.log(f"✅ {success_message}")
                messagebox.showinfo("Success", success_message)
                form.destroy()
            else:
                error_msg = stderr.strip() if stderr else stdout.strip() or "Unknown error"
                self.log(f"❌ {error_context}: {error_msg}")
                messagebox.showerror("Error", f"{error_context}:\n{error_msg}")

        except subprocess.TimeoutExpired:
            self.log(f"❌ {error_context} timeout")
            messagebox.showerror("Error", f"{error_context} timeout (120 seconds)")
        except Exception as e:
            self.log(f"❌ {error_context} error: {str(e)}")
            messagebox.showerror("Error", f"{error_context} error:\n{str(e)}")

    def _add_key_to_keystore(self, form, filename_var, keystore_path_var, alias_var,
                             password_var, cn_var, ou_var, o_var, l_var, st_var, c_var, is_add_mode):
        """Add alias to existing keystore"""
        keystore_path = keystore_path_var.get().strip()
        alias = alias_var.get().strip()
        password = password_var.get().strip()
        cn = cn_var.get().strip()
        ou = ou_var.get().strip()
        o = o_var.get().strip()
        l = l_var.get().strip()
        st = st_var.get().strip()
        c = c_var.get().strip()

        if not self._validate_fields(is_add_mode,
                                     keystore_path=keystore_path, alias=alias, password=password,
                                     cn=cn, o=o, l=l, st=st, c=c):
            return

        dname = self._prepare_dname(cn, ou, o, l, st, c)

        self.log(f"🔑 Adding key to keystore: {os.path.basename(keystore_path)}")
        self.log(f"📍  Alias: {alias}")

        cmd = [
            self._find_keytool(),
            "-genkeypair",
            "-keystore", keystore_path,
            "-alias", alias,
            "-keyalg", "RSA",
            "-keysize", "2048",
            "-validity", "10000",
            "-storepass", password,
            "-keypass", password,
            "-dname", dname
        ]

        self._execute_keytool_command(
            cmd,
            f"Key '{alias}' added successfully!",
            "Key addition failed",
            form
        )

    def _generate_keystore(self, form, filename_var, keystore_path_var, alias_var,
                           password_var, cn_var, ou_var, o_var, l_var, st_var, c_var, is_add_mode):
        """New keystore generation"""
        filename = filename_var.get().strip()
        alias = alias_var.get().strip()
        password = password_var.get().strip()
        cn = cn_var.get().strip()
        ou = ou_var.get().strip()
        o = o_var.get().strip()
        l = l_var.get().strip()
        st = st_var.get().strip()
        c = c_var.get().strip()

        if not self._validate_fields(is_add_mode,
                                     filename=filename, alias=alias, password=password,
                                     cn=cn, o=o, l=l, st=st, c=c):
            return

        if not filename.lower().endswith('.keystore'):
            filename += '.keystore'
        keystore_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

        # File exist validation
        if os.path.exists(keystore_path):
            if not messagebox.askyesno("File exists",
                                       f"File {os.path.basename(keystore_path)} already exists. Overwrite?"):
                return

        dname = self._prepare_dname(cn, ou, o, l, st, c)

        self.log(f"🔑 Generating keystore: {os.path.basename(keystore_path)}")

        cmd = [
            self._find_keytool(),
            "-genkeypair",
            "-keystore", keystore_path,
            "-alias", alias,
            "-keyalg", "RSA",
            "-keysize", "2048",
            "-validity", "10000",
            "-storepass", password,
            "-keypass", password,
            "-dname", dname
        ]

        self._execute_keytool_command(
            cmd,
            f"Keystore generated successfully!\nFile: {os.path.basename(keystore_path)}",
            "Keystore generation failed",
            form
        )

    def _find_keytool(self):
        """Keytool search"""
        # Attemp to find keytool close to java
        java_dir = os.path.dirname(self.java_path)
        for name in ["keytool.exe", "keytool"]:
            keytool_path = os.path.join(java_dir, name)
            if os.path.exists(keytool_path):
                return keytool_path

        import shutil
        return shutil.which("keytool")

    def message(self):
        return "Keystore generation completed"

class KeystoreManager(APKTool):
    """Keystore manager"""

    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.generator = GenerateKeystore(config_path)
        self.current_keystore_path = None
        self.current_password = None
        self.current_alias = None
        self.gui_combobox = None
        self.gui_combobox_var = None
        self._load_saved_keystore()

    def run(self):
        """Core method - choose and validate keystore"""
        # Choose keystore file
        keystore_path = filedialog.askopenfilename(
            title="Select Keystore file",
            filetypes=[("Keystore files", "*.keystore *.jks"), ("All files", "*.*")]
        )

        if not keystore_path:
            self.log("❌ Keystore selection cancelled")
            return

        keystore_name = os.path.basename(keystore_path)

        # Password entry
        password_result = self._input_password_dialog(keystore_name)
        if not password_result:
            return

        # Password validating
        if not self._verify_keystore_password(keystore_path, password_result["password"]):
            messagebox.showerror("Error", "Invalid keystore password")
            self.log("❌ Invalid keystore password")
            return

        # Data Save
        self.current_keystore_path = keystore_path
        self.current_password = password_result["password"]
        self.cfg.set("last_keystore", keystore_path)
        if password_result["save"]:
            self.cfg.set("last_keystore_password", password_result["password"])
            self.log("✅ Keystore data saved to config")
        else:
            self.cfg.set("last_keystore_password", "")
            self.log("✅ Keystore loaded (password not saved)")

        # Refresh Alias list
        aliases = self.get_aliases_list()
        if aliases:
            # save first alias as default
            first_alias = aliases[0]
            self.cfg.set("last_alias", first_alias)
            self.current_alias = first_alias
            self.log(f"🔑 Auto-selected alias: {first_alias}")
        else:
            self.cfg.set("last_alias", "")
            self.current_alias = None
            self.log("⚠️ No aliases found in keystore")

        self.log(f"✅ Keystore verified: {keystore_name}")

        # Refresh GUI combobox_1
        self._update_gui_combobox()

        # Refresh all tools
        self._refresh_all_tools()

    def _refresh_all_tools(self):
        """Updates configuration across all tools"""
        try:
            # callback GUI to refresh
            if self.log_callback:
                self.log_callback("🔄 Keystore updated - refreshing tools...")
                self.log_callback("KEYSTORE_UPDATED")
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"⚠️ Refresh notification failed: {e}")

    def _load_saved_keystore(self):
        """Load saved keystore data from configuration"""
        self.current_keystore_path = self.cfg.get("last_keystore")
        self.current_password = self.cfg.get("last_keystore_password")
        self.current_alias = self.cfg.get("last_alias")

        self.log(f"📋 Loaded from config - Keystore: {self.current_keystore_path}, Alias: {self.current_alias}")

    def _input_password_dialog(self, keystore_name):
        """Input password dialog"""
        dialog = tk.Toplevel()
        dialog.title("Keystore Password")
        dialog.geometry("300x150")
        dialog.grab_set()
        dialog.resizable(False, False)

        # Apply theme
        dialog.configure(background=self.theme['bg_color'])

        result = {"password": None, "save": False}

        tk.Label(dialog, text=f"Password for {keystore_name}:",
                 background=self.theme['bg_color'], foreground=self.theme['text_color']).pack(pady=10)

        password_var = tk.StringVar()
        password_entry = tk.Entry(dialog, textvariable=password_var, show="*", width=30,
                                  background=self.theme['lighter_bg'], foreground=self.theme['text_color'])
        password_entry.pack(pady=5)

        save_var = tk.BooleanVar(value=True)


        tk.Checkbutton(dialog, text="Save password", variable=save_var,
                       background=self.theme['bg_color'],
                       selectcolor=self.theme['bg_color'],
                       foreground=self.theme['text_color']).pack(pady=5)

        def on_ok():
            password = password_var.get().strip()
            if not password:
                messagebox.showerror("Error", "Password cannot be empty")
                return
            result["password"] = password
            result["save"] = save_var.get()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog, background=self.theme['bg_color'])
        btn_frame.pack(pady=10)

        ok_btn = tk.Button(btn_frame, text="OK", command=on_ok, width=8,
                           background=self.theme['lighter_bg'], foreground=self.theme['button_text_color'])
        ok_btn.pack(side="left", padx=5)

        cancel_btn = tk.Button(btn_frame, text="Cancel", command=on_cancel, width=8,
                               background=self.theme['lighter_bg'], foreground=self.theme['button_text_color'])
        cancel_btn.pack(side="left", padx=5)

        password_entry.focus_set()
        password_entry.bind('<Return>', lambda e: on_ok())
        dialog.wait_window()

        return result if result["password"] else None

    def _verify_keystore_password(self, keystore_path, password):
        """Validate keystore password"""
        try:
            keytool_path = self._find_keytool()
            if not keytool_path:
                return False

            cmd = [
                keytool_path,
                "-list",
                "-keystore", keystore_path,
                "-storepass", password
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0

        except Exception:
            return False

    def _find_keytool(self):
        """Search keytool"""
        # Search keytool close to java
        java_path = self.get_config("java")
        if java_path:
            java_dir = os.path.dirname(java_path)
            for name in ["keytool.exe", "keytool"]:
                keytool_path = os.path.join(java_dir, name)
                if os.path.exists(keytool_path):
                    return keytool_path

        # Fallback: global search
        import shutil
        return shutil.which("keytool")

    def get_aliases_list(self):
        """Retrieve key list from keystore"""
        if not self.current_keystore_path or not self.current_password:
            return []

        try:
            keytool_path = self._find_keytool()
            cmd = [
                keytool_path,
                "-list",
                "-keystore", self.current_keystore_path,
                "-storepass", self.current_password
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                aliases = []
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and ',' in line and not line.startswith(('Keystore', 'Your keystore', 'Certificate')):
                        alias = line.split(',')[0].strip()
                        if alias:
                            aliases.append(alias)
                return aliases

        except Exception:
            pass

        return []

    def _update_gui_combobox(self):
        """Refresh combobox_2 in GUI"""
        if self.gui_combobox and self.gui_combobox_var:
            aliases = self.get_aliases_list()
            self.gui_combobox['values'] = aliases

            current_alias = self.cfg.get("last_alias", "")

            if current_alias and aliases and current_alias in aliases:
                self.gui_combobox_var.set(current_alias)
            elif aliases:
                first_alias = aliases[0]
                self.gui_combobox_var.set(first_alias)
                self.cfg.set("last_alias", first_alias)
                self.current_alias = first_alias
            else:
                self.gui_combobox_var.set("")

            #self.log(f"📋 ComboBox updated with {len(aliases)} aliases")

    def set_gui_combobox(self, combobox, combobox_var):
        """Set references to GUI components"""
        self.gui_combobox = combobox
        self.gui_combobox_var = combobox_var
        self._update_gui_combobox()

    def update_alias_selection(self, selected_alias):
        """Update selected alias"""
        if selected_alias:
            clean_alias = selected_alias.split(',')[0].strip()
            self.current_alias = clean_alias
            self.set_config("last_alias", clean_alias)
            self.log(f"🔑 Selected alias: {clean_alias}")

    def set_log_callback(self, callback):
        """Set call back"""
        super().set_log_callback(callback)
        self.generator.set_log_callback(callback)

    def message(self):
        if self.current_keystore_path:
            return f"Keystore: {os.path.basename(self.current_keystore_path)}"
        return "No keystore selected"


class VersionManager(APKTool):
    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.versions_dir = self.cfg.get("versions_dir")
        self.last_version = self.cfg.get("last_version")
        self.gui_combobox = None
        self.gui_combobox_var = None
        self._update_global_version_path()

        # Get folder structure from config
        folder_structure = self.cfg.get("folder_structure")
        self.subfolders = list(folder_structure.values())

    def run(self):
        """Choose APK and create version folder"""
        # Check
        if not self.cfg.get("versions_dir"):
            self.log("❌ Please configure versions directory first")
            messagebox.showwarning("Configuration Required",
                                   "Please set Versions Folder in Settings → Paths first")
            return

        # Choose APK
        apk_path = self._select_apk_file()

        if not apk_path:
            self.log("ℹ️ File selection cancelled")
            return

        # Run thread
        thread = threading.Thread(target=self._process_apk_addition, args=(apk_path,))
        thread.daemon = True
        thread.start()

    def get_versions_for_combo(self):
        """Get available versions"""
        if not self.versions_dir or not os.path.exists(self.versions_dir):
            return []

        versions = [d for d in os.listdir(self.versions_dir)
                    if os.path.isdir(os.path.join(self.versions_dir, d))]
        return sorted(versions, reverse=True)

    def update_version_on_select(self, selected_version):
        """Refresh choosen version"""
        if selected_version:
            self.last_version = selected_version
            self.cfg.set("last_version", selected_version)
            self._update_global_version_path()
            self.log(f"🔀 Switched to version: {selected_version}")
            self.emit('version_changed', {
                'version': selected_version,
                'version_path': os.path.join(self.versions_dir, selected_version)
            })

    def open_current_folder(self):
        """Open choosen version folder"""
        try:
            # Use version form config
            current_version = self.cfg.get("last_version") or self.last_version
            versions_dir = self.cfg.get("versions_dir")

            if not current_version or not versions_dir:
                self.log("❌ No version selected or versions directory not configured")
                return

            version_path = os.path.join(versions_dir, current_version)

            if not os.path.exists(version_path):
                self.log(f"❌ Version folder not found: {version_path}")
                return

            if os.name == 'nt':
                os.startfile(version_path)
            elif os.name == 'posix':
                subprocess.run(['open', version_path] if os.uname().sysname == 'Darwin'
                               else ['xdg-open', version_path])
            else:
                self.log("❌ Unsupported OS")
                return

        except Exception as e:
            self.log(f"❌ Failed to open folder: {e}")

    def refresh_versions(self):
        """Refresh version's list"""
        self.log("🔄 Refreshing versions list...")
        self._update_gui_combobox()
        self._update_global_version_path()

        # Add event
        self.emit('versions_refreshed', {
            'versions_list': self.get_versions_for_combo(),
            'current_version': self.last_version
        })

    def set_gui_combobox(self, combobox, combobox_var):
        """Set GUI combobox link"""
        self.gui_combobox = combobox
        self.gui_combobox_var = combobox_var
        self._update_gui_combobox()

    def _update_global_version_path(self):
        """Refresh global path for all tools"""
        if self.versions_dir and self.last_version:
            new_path = os.path.join(self.versions_dir, self.last_version)
            BaseTool.refresh(new_path)
            self.log(f"📍 Global path updated: {new_path}")

    def _update_gui_combobox(self):
        """Refresh version's combobox"""
        if self.gui_combobox and self.gui_combobox_var:
            versions = self.get_versions_for_combo()
            self.gui_combobox['values'] = versions

            if self.last_version and versions and self.last_version in versions:
                self.gui_combobox_var.set(self.last_version)
            elif versions:
                # Choose first version folder and save config
                first_version = versions[0]
                self.gui_combobox_var.set(first_version)
                self.last_version = first_version
                self.cfg.set("last_version", first_version)
                self._update_global_version_path()
            else:
                self.gui_combobox_var.set("")

    def _select_apk_file(self):
        """Select APK file"""
        apk_path = filedialog.askopenfilename(
            title="Select APK file",
            filetypes=[("APK files", "*.apk")]
        )
        return apk_path

    def _extract_version_from_filename(self, filename):
        """Get version from filename"""
        patterns = [
            r'[\._-]?v?(\d+\.\d+(?:\.\d+)?)',  # v1.2.3, 1.2, 1.2.3
            r'[\._-]?ver?[\._-]?(\d+(?:\.\d+)*)',  # ver1.2, version1.2.3
            r'[\._-]?(\d{4}[\._-]?\d{2}[\._-]?\d{2})',  # 20231231, 2023-12-31
            r'[\._-]?(\d+)_(\d+)',  # 1_2 -> 1.2
            r'(\d{4})',  # 2025, 2024 - standalone 4-digit years
            r'v(\d{4})',  # v2025, v2024 - version with 4-digit year
        ]

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                # merge groups in case
                version_parts = [g for g in match.groups() if g]
                if version_parts:
                    return '.'.join(version_parts)

        # Choose name if no version found
        base_name = os.path.splitext(filename)[0]
        self.log(f"⚠️ Version not found in filename, using: {base_name}")
        return base_name

    def _create_version_structure(self, version):
        """Create folders structure"""
        if not self.versions_dir:
            self.log("❌ Versions directory not configured")
            return None

        version_dir = os.path.join(self.versions_dir, version)

        if os.path.exists(version_dir):
            if not messagebox.askyesno("Version exists",
                                       f"Version {version} already exists. Overwrite?"):
                return None
            shutil.rmtree(version_dir)

        try:
            # New folder structure
            self.log("🔨 Creating new directory structure...")
            os.makedirs(version_dir, exist_ok=True)

            for folder in self.subfolders:
                folder_path = os.path.join(version_dir, folder)
                os.makedirs(folder_path, exist_ok=True)
                self.log(f"   📁 Created: {folder}")

            self.log(f"✅ New directory structure created: {version_dir}")
            return version_dir

        except Exception as e:
            self.log(f"❌ Failed to create directory structure: {str(e)}")
            return None

    def _copy_apk_file(self, apk_path, version_dir):
        """Copy APK to the folder"""
        try:
            apk_name = os.path.basename(apk_path)
            apk_folder_key = 'apk'
            apk_folder = self.paths.get(apk_folder_key)
            target_path = os.path.join(version_dir, apk_folder, apk_name)

            self.log("🔄 Copying APK file...")
            shutil.copy2(apk_path, target_path)

            self.log(f"✅ APK copied to: 1_APK/{apk_name}")
            return target_path

        except Exception as e:
            self.log(f"❌ Failed to copy APK: {str(e)}")
            return None

    def _process_apk_addition(self, apk_path):
        """Main apk adding logic"""
        try:
            apk_name = os.path.basename(apk_path)
            self.log(f"📁 Processing: {apk_name}")

            # Check versions_dir
            if not self.versions_dir:
                self.log("❌ Please configure versions directory first")
                messagebox.showerror("Error", "Please configure versions directory in Settings → Paths")
                return False

            # Create versions_dir
            if not os.path.exists(self.versions_dir):
                self.log(f"📁 Creating versions directory: {self.versions_dir}")
                os.makedirs(self.versions_dir, exist_ok=True)

            # Get version from name
            version = self._extract_version_from_filename(apk_name)
            if not version:
                self.log("❌ Cannot extract version from filename")
                return False

            # Create folder structure
            version_dir = self._create_version_structure(version)
            if not version_dir:
                return False

            # Copy APK
            if not self._copy_apk_file(apk_path, version_dir):
                return False

            # Refresh config and global path
            self.cfg.set("last_version", version)
            self.last_version = version
            self._update_global_version_path()

            # Refresh combobox
            self._update_gui_combobox()

            self.log("✅ APK imported successfully!")
            self.log(f"📂 Version {version} set as current")
            self.log(f"📍 Working directory: {version_dir}")

            self.emit('versions_updated', {
                'version': version,
                'version_dir': version_dir,
                'versions_list': self.get_versions_for_combo()
            })

            return True

        except Exception as e:
            self.log(f"❌ Error importing APK: {str(e)}")
            return False

    def message(self):
        return f"Version Manager - Current: {self.last_version}" if self.last_version else "Version Manager"


# DRTool Classes
class deCAR(DRTool):
    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.result_message = ""

    def run(self):
        self.log("🔓 Starting CAR unpacking...")

        corona_archiver_path = self.cfg.get("corona-archiver")

        input_file = os.path.join(self.paths['apk_unpacked'], "assets", "resource.car")
        output_dir = self.paths['lu']

        if not os.path.exists(input_file):
            self.result_message = "CAR file not found"
            self.log(f"❌ resource.car not found in: {input_file}")
            return

        try:
            self.log(f"✅ CAR decompilation started to {output_dir}")
            subprocess.Popen([
                "python",
                corona_archiver_path,
                "-u",
                input_file,
                output_dir
            ])

        except Exception as e:
            self.result_message = f"Error: {str(e)}"
            self.log(f"❌ CAR unpacking error: {str(e)}")
        self.log(f"✅ CAR decompiled to {output_dir}")
    def message(self):
        return self.result_message

class ToCAR(DRTool):
    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.result_message = ""

    def run(self):
        self.log("🔧 Starting CAR packaging...")

        corona_archiver_path = self.cfg.get("corona-archiver")
        input_dir = self.paths['lu'] + os.path.sep
        output_file = os.path.join(self.paths['apk_unpacked'], "assets", "resource.car")

        if not os.path.exists(input_dir):
            self.result_message = "Input directory not found"
            self.log(f"❌ Input directory not found: {input_dir}")
            return

        self.log(f"📁 Input: {input_dir}")
        self.log(f"📁 Output: {output_file}")

        try:
            # create output in case
            os.makedirs(self.paths['output'], exist_ok=True)

            self.log("🔄 Packaging CAR file...")
            subprocess.run([
                "python",
                corona_archiver_path,
                "-p",
                input_dir,
                output_file
            ])

            if os.path.exists(output_file):
                self.result_message = "CAR packaging completed successfully"
                self.log("✅ CAR packaging completed")
            else:
                self.result_message = "Error: Output file not created"
                self.log("❌ Output file not found")

        except Exception as e:
            self.result_message = f"Error: {str(e)}"
            self.log(f"❌ CAR packaging error: {str(e)}")

    def message(self):
        return self.result_message

class UnluacBase(DRTool):
    """Base class fo LU decompilation"""

    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.result_message = ""
        self.unluac_path = self.cfg.get("unluac")
        self.java_path = self.cfg.get("java")

    @abstractmethod
    def get_input_output_paths(self):
        """abstract method should be implemented in subclass"""
        raise NotImplementedError("Subclasses must implement get_input_output_paths")

    def get_unluac_flags(self):
        """Override this method to add flags like -l for ASM mode"""
        return []

    def _process_single_file(self, input_path, output_path):
        try:
            filename = os.path.basename(input_path)

            cmd = [self.java_path, "-jar", self.unluac_path]
            cmd.extend(self.get_unluac_flags())
            cmd.append(input_path)

            result = subprocess.run(cmd, encoding='utf-8', capture_output=True, text=True, check=True, timeout=30)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            #Looking for ALL assignment strings and decode ALL sequences in them
            decoded_content = re.sub(
                r'( = ")([^"]+?)(")',
                lambda m: m.group(1) + self._decode_all_sequences_in_string(m.group(2)) + m.group(3),
                result.stdout
            )

            with open(output_path, 'w', encoding='utf-8') as f_out:
                f_out.write(decoded_content)

            return True, filename, None

        except Exception as e:
            return False, os.path.basename(input_path), str(e)

    def _decode_all_sequences_in_string(self, text):
        """Decodes all UTF8 sequences in string"""
        out = bytearray()
        temp_text = text

        while temp_text:
            match = re.match(r'\\(\d{1,3})', temp_text)
            if match:
                char_code = int(match.group(1))
                out.extend(bytes([char_code]))
                temp_text = temp_text[match.end():]
            else:
                out.extend(temp_text[0].encode('utf-8'))
                temp_text = temp_text[1:]

        return out.decode('utf-8')

    def _decode_lu_files(self):
        """Decopmilating logic"""
        try:
            input_dir, output_dir = self.get_input_output_paths()

            self.log(f"🔓 Starting LU decompilation from {os.path.basename(input_dir)}...")

            if not os.path.exists(input_dir):
                self.log(f"❌ Input directory not found: {input_dir}")
                return

            # Recursion .lu files search
            lu_files = []
            for root, dirs, files in os.walk(input_dir):
                for file in files:
                    if file.lower().endswith(".lu"):
                        lu_files.append(os.path.join(root, file))

            if not lu_files:
                self.log("❌ No .lu files found")
                return

            total_files = len(lu_files)
            self.log(f"📁 Files to process: {total_files}")

            # Create output dir
            os.makedirs(output_dir, exist_ok=True)

            # Prepare tasks
            tasks = []
            for lu_file_path in lu_files:
                relative_path = os.path.relpath(lu_file_path, input_dir)
                output_file = relative_path.replace('.lu', '.lua')
                output_path = os.path.join(output_dir, output_file)

                tasks.append((lu_file_path, output_path))

            # file processing
            processed_count = 0
            failed_count = 0
            error_messages = []

            max_workers = min(len(tasks), os.cpu_count() * 2)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self._process_single_file, input_path, output_path): input_path
                    for input_path, output_path in tasks
                }

                for future in concurrent.futures.as_completed(future_to_file):
                    input_path = future_to_file[future]
                    try:
                        success, filename, error = future.result()
                        processed_count += 1

                        if self.progress_callback:
                            progress = int((processed_count / total_files) * 100)
                            self.progress_callback(progress)

                        if not success:
                            failed_count += 1
                            error_messages.append(f"❌ {filename}: {error}")

                    except Exception as e:
                        processed_count += 1
                        failed_count += 1
                        error_messages.append(f"❌ {os.path.basename(input_path)}: {str(e)}")

            self.log(f"✅ Decompilation completed: {processed_count - failed_count}/{total_files} successful")

            if failed_count > 0:
                self.log(f"❌ Failed files: {failed_count}")
                for error_msg in error_messages:
                    self.log(error_msg)

            self.result_message = f"Decompiled {processed_count - failed_count}/{total_files} files"

        except Exception as e:
            self.log(f"❌ Decompilation error: {str(e)}")

    def _decode_line(self, line):
        """Decode line if UTF8 sequence found"""
        if re.search(r' = ".*\\\d{3}\\\d{3}', line):
            return self._decode_utf8_sequence(line)
        return line

    def _decode_utf8_sequence(self, sequence):
        """Decoding UTF-8 sequence"""
        out = bytearray()
        temp_seq = sequence
        while temp_seq:
            match = re.match(r'\\(\d{1,3})', temp_seq)
            if match:
                char_code = int(match.group(1))
                out.extend(bytes([char_code]))
                temp_seq = temp_seq[match.end():]
            else:
                break
        return out.decode('utf-8')

    def run(self):
        """Launch decompilation in a separate thread"""
        if not self.unluac_path:
            raise FileNotFoundError("Unluac path not configured")
        if not self.java_path:
            raise FileNotFoundError("Java path not configured")
        thread = threading.Thread(target=self._decode_lu_files)
        thread.daemon = True
        thread.start()

    def message(self):
        return self.result_message

class Unluac(UnluacBase):
    """Decompile .LU from 6_INPUT to 7_OUTPUT"""

    def get_input_output_paths(self):
        return self.paths['input'], self.paths['output']
class Unluac_All(UnluacBase):
    """Decompile .LU from 3_LU to 4_LUA"""

    def get_input_output_paths(self):
        return self.paths['lu'], self.paths['lua']


class LuacBase(DRTool):
    """Base class for Luac"""

    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.result_message = ""

        # Get LUAC.EXE path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        utils_dir = os.path.join(script_dir, "utils")
        lua_dir = os.path.join(utils_dir, "lua-5.1.5_Win64_bin")
        self.luac_path = os.path.join(lua_dir, "luac5.1.exe")
        # Check
        if not os.path.exists(self.luac_path):
            self.luac_path = "luac"  # change to luac from PATH if not found

    def get_input_output_paths(self):
        """Method to be overridden in child classes"""
        raise NotImplementedError("Subclasses must implement get_input_output_paths")

    def _find_lua_files_recursive(self, directory):
        """Recursive search for all .lua files - ONLY FILES, NOT DIRECTORIES"""
        lua_files = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('!')]
            for file in files:
                if file.lower().endswith(".lua"):
                    full_path = os.path.join(root, file)
                    # Validate isfile
                    if os.path.isfile(full_path):
                        lua_files.append(full_path)
        return lua_files

    def _get_output_filename(self, input_path, input_dir):
        """Generate unique output filename - FLAT STRUCTURE"""
        # Use only file name
        filename = os.path.basename(input_path)

        # Replace .lua with .lu
        output_filename = filename.replace('.lua', '.lu')

        # Add suffices in case file name exists
        output_dir = self.get_input_output_paths()[1]
        base_name = output_filename.replace('.lu', '')
        counter = 1
        final_output_name = output_filename

        while os.path.exists(os.path.join(output_dir, final_output_name)):
            final_output_name = f"{base_name}_{counter}.lu"
            counter += 1

        return final_output_name

    def _process_single_file(self, input_path, output_path):
        """Processing single file"""
        try:
            # additional validation file exists
            if not os.path.isfile(input_path):
                return False, os.path.basename(input_path), "Not a file"

            # Create output directory if necessary
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)

            # Start Luac
            result = subprocess.run([
                self.luac_path, "-o", output_path, input_path
            ], capture_output=True, text=True)

            # Check if file was created
            file_created = os.path.exists(output_path)

            if not file_created:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                return False, os.path.basename(input_path), error_msg

            return True, os.path.basename(input_path), None

        except Exception as e:
            return False, os.path.basename(input_path), str(e)

    def _compile_lua_files(self):
        """Common LUA files compilation logic - FLAT OUTPUT STRUCTURE"""
        try:
            input_dir, output_dir = self.get_input_output_paths()

            self.log(f"🔧 Starting LUA compilation from {os.path.basename(input_dir)}...")

            if not os.path.exists(input_dir):
                self.log(f"❌ Input directory not found: {input_dir}")
                return

            # Recursive search for all .lua files
            lua_files = self._find_lua_files_recursive(input_dir)

            if not lua_files:
                self.log("❌ No .lua files found")
                return

            total_files = len(lua_files)
            self.log(f"📁 Found {total_files} .lua files in all subfolders")

            # Create output directory
            os.makedirs(output_dir, exist_ok=True)

            # Preparing tasks - FLAT STRUCTURE
            tasks = []
            for lua_file_path in lua_files:
                output_filename = self._get_output_filename(lua_file_path, input_dir)
                output_path = os.path.join(output_dir, output_filename)
                tasks.append((lua_file_path, output_path))

            # File processing
            processed_count = 0
            failed_count = 0
            error_messages = []

            max_workers = min(len(tasks), os.cpu_count())

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self._process_single_file, input_path, output_path): input_path
                    for input_path, output_path in tasks
                }

                for future in concurrent.futures.as_completed(future_to_file):
                    input_path = future_to_file[future]
                    try:
                        success, filename, error = future.result()
                        processed_count += 1

                        # Refresh progress bar
                        if hasattr(self, 'progress_callback') and self.progress_callback:
                            progress = int((processed_count / total_files) * 100)
                            self.progress_callback(progress)

                        if success:
                            pass
                        else:
                            failed_count += 1
                            error_messages.append(f"❌ {filename}: {error}")

                    except Exception as e:
                        processed_count += 1
                        failed_count += 1
                        error_messages.append(f"❌ {os.path.basename(input_path)}: {str(e)}")

            # Results
            success_count = processed_count - failed_count
            self.log(f"✅ Compilation completed: {success_count}/{total_files} successful")
            self.log(f"📁 All files compiled to: {output_dir}")

            if failed_count > 0:
                self.log(f"❌ Failed files: {failed_count}")
                for error_msg in error_messages:
                    self.log(error_msg)

            self.result_message = f"Compiled {success_count}/{total_files} files to flat structure"

        except Exception as e:
            self.log(f"❌ Compilation error: {str(e)}")

    def run(self):
        """Run compilation in separate threads"""
        thread = threading.Thread(target=self._compile_lua_files)
        thread.daemon = True
        thread.start()

    def message(self):
        return self.result_message
class Luac(LuacBase):
    """Compiling LUA files from 6_INPUT to 7_OUTPUT"""

    def get_input_output_paths(self):
        return self.paths['input'], self.paths['output']
class Luac_All(LuacBase):
    """Compiling all LUA files from 5_EDITING to 3_LU"""

    def get_input_output_paths(self):
        return self.paths['editing'], self.paths['lu']


class ASM(DRTool):
    """Base class for assemble/disassemble tools"""
    def run(self):
        self.log("Not implemented yet")
    def message(self):
        pass
class AsmLu(ASM):
    """Assembling ASM → LU (ASM to Lua bytecode)"""
class LuAsm(ASM):
    """Disassebling LU → ASM (Lua bytecode to ASM)"""


class UTF8Decoder(BaseTool):
    """Base class for decoding UTF8 sequnces"""

    def __init__(self, config_path="config.json"):
        super().__init__(config_path)
        self.result_message = ""

    @abstractmethod
    def get_input_output_paths(self):
        """Abstract method to be implemented in subclasses"""
        raise NotImplementedError("Subclasses must implement get_input_output_paths")

    def decode_utf8_sequences(self, line):
        """Decoding UTF8 escape-sequences to readlable text"""
        out = bytearray()
        while line:
            match = re.match(r'\\(\d{1,3})', line)
            if match:
                char_code = int(match.group(1))
                out.extend(bytes([char_code]))
                line = line[match.end():]
            else:
                out.extend(line[0].encode('utf-8'))
                line = line[1:]

        return out.decode('utf-8')

    def _process_single_file(self, input_path, output_path):
        """Process the file"""
        try:
            # create output dir if necessary
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f_in, \
                    open(output_path, 'w', encoding='utf-8') as f_out:

                for line in f_in:
                    # Determine if the input contains any UTF-8 escape-encoded characters
                    if re.search(r' = ".*\\\d{3}\\\d{3}', line):
                        line = self.decode_utf8_sequences(line)

                    f_out.write(line)

            return True, os.path.basename(input_path), None

        except Exception as e:
            return False, os.path.basename(input_path), str(e)

    def _decode_files(self):
        """Core logic for file decoding"""
        try:
            input_dir, output_dir = self.get_input_output_paths()

            self.log(f"🔤 Starting UTF8 decoding from {os.path.basename(input_dir)}...")

            if not os.path.exists(input_dir):
                self.log(f"❌ Input directory not found: {input_dir}")
                return

            # Performing a recursive scan for .lua files
            lua_files = []
            for root, dirs, files in os.walk(input_dir):
                for file in files:
                    if file.lower().endswith(".lua"):
                        lua_files.append(os.path.join(root, file))

            if not lua_files:
                self.log("❌ No .lua files found")
                return

            total_files = len(lua_files)
            self.log(f"📁 Files to process: {total_files}")

            # Create output dir
            os.makedirs(output_dir, exist_ok=True)

            # Task preparation
            tasks = []
            for lua_file_path in lua_files:
                relative_path = os.path.relpath(lua_file_path, input_dir)
                output_path = os.path.join(output_dir, relative_path)
                tasks.append((lua_file_path, output_path))

            # File processing with progress tracking
            processed_count = 0
            failed_count = 0
            error_messages = []

            max_workers = min(len(tasks), os.cpu_count() * 2)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self._process_single_file, input_path, output_path): input_path
                    for input_path, output_path in tasks
                }

                for future in concurrent.futures.as_completed(future_to_file):
                    input_path = future_to_file[future]
                    try:
                        success, filename, error = future.result()
                        processed_count += 1

                        # Progress bar updates triggered through callback
                        if self.progress_callback:
                            progress = int((processed_count / total_files) * 100)
                            self.progress_callback(progress)

                        if not success:
                            failed_count += 1
                            error_messages.append(f"❌ {filename}: {error}")

                    except Exception as e:
                        processed_count += 1
                        failed_count += 1
                        error_messages.append(f"❌ {os.path.basename(input_path)}: {str(e)}")

            # Result
            success_count = processed_count - failed_count
            self.log(f"✅ UTF8 decoding completed: {success_count}/{total_files} successful")

            if failed_count > 0:
                self.log(f"❌ Failed files: {failed_count}")
                for error_msg in error_messages:
                    self.log(error_msg)

            self.result_message = f"Decoded {success_count}/{total_files} files"

        except Exception as e:
            self.log(f"❌ UTF8 decoding error: {str(e)}")

    def run(self):
        """Launch decoding in a separate thread"""
        thread = threading.Thread(target=self._decode_files)
        thread.daemon = True
        thread.start()

    def find_file_by_pattern(self, search_pattern, search_dir=None):
        """Search for a file matching the pattern in the specified directory"""
        if search_dir is None:
            search_dir = self.paths['lua']  # default output folder

        if not os.path.exists(search_dir):
            self.log(f"❌ Search directory not found: {search_dir}")
            return None

        # Split the pattern into keywords
        keywords = search_pattern.lower().split()

        best_match = None
        best_score = 0

        for root, dirs, files in os.walk(search_dir):
            for file in files:
                if file.lower().endswith('.lua'):
                    file_lower = file.lower()

                    # Count the number of keyword matches
                    score = sum(1 for keyword in keywords if keyword in file_lower)

                    if score > best_score:
                        best_score = score
                        best_match = os.path.join(root, file)
                    elif score == best_score and best_match:
                        # If scores are equal, select the shorter name
                        if len(file) < len(os.path.basename(best_match)):
                            best_match = os.path.join(root, file)

        return best_match

    def _decode_single_file_cli(self, search_pattern):
        """Decode a single file by pattern via CLI"""
        output_dir = os.path.join(self.paths['editing'], "UTF-8")  # 5_EDITING/UTF-8

        self.log(f"🔍 Searching for file with pattern: '{search_pattern}'")

        # File search
        file_path = self.find_file_by_pattern(search_pattern)

        if not file_path:
            self.log(f"❌ File not found for pattern: '{search_pattern}'")
            return False

        self.log(f"✅ Found file: {os.path.basename(file_path)}")

        # SAve output path
        output_path = os.path.join(output_dir, os.path.basename(file_path))

        # File Decoding
        success, filename, error = self._process_single_file(file_path, output_path)

        if success:
            self.log(f"✅ File decoded successfully: {output_path}")
            return True
        else:
            self.log(f"❌ Failed to decode file: {error}")
            return False

    def cli(self, args):
        """CLI interface for GUI integration"""
        if not args or args.strip() == "":
            # If no arguments are provided, initiate full decoding
            self.run()
        elif args.strip() in ["?", "help"]:
            # Show ARGS help
            self._show_help()
        else:
            # If arguments are provided, search for and decode a single file
            self._decode_single_file_cli(args.strip())

    def _show_help(self):
        """Displays CLI usage help"""
        help_text = """
    UTF8 Decoder - CLI Argument Reference:

    Commands:
      (no arguments)   - Decode all .lua files
      <pattern>        - Search and decode file by pattern
      ? or help        - Show this help message

    Examples:
      utf8             - Decode all files
      utf8 lang        - Find and decode file with 'lang' in its name
      utf8 st rostov   - Search by multiple keywords and decode
      utf8 ?           - Display help
    """
        self.log(help_text.strip())


    def message(self):
        return self.result_message
#region Subclasses to decode from custom paths
class UTF8Decoder_LUA_to_UTF8(UTF8Decoder):
    """Decode from 4_LUA directory to UTF-8 folder"""
    def get_input_output_paths(self):
        return self.paths['lua'], os.path.join(self.paths['editing'], "UTF-8")
class UTF8Decoder_EDITING_to_UTF8(UTF8Decoder):
    """Decode from 5_EDITING directory to UTF-8 folder"""
    def get_input_output_paths(self):
        return self.paths['editing'], os.path.join(self.paths['editing'], "UTF-8")
class UTF8Decoder_INPUT_to_OUTPUT(UTF8Decoder):
    """Decode from 6_INPUT directory to 7_OUTPUT"""
    def get_input_output_paths(self):
        return self.paths['input'], self.paths['output']

#endregion