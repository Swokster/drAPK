import os
import json
import urllib.request
import tempfile
import shutil
import tkinter as tk
from tkinter import messagebox

GITHUB_USER = "Swokster"
GITHUB_REPO = "drAPK"
BRANCH = "master"  # или "master"

LATEST_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}/latest.json"

def get_current_version(config_path="config.json"):
    if not os.path.exists(config_path):
        return "0.0.0"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("version", "0.0.0")
    except Exception:
        return "0.0.0"

def get_latest_info():
    try:
        with urllib.request.urlopen(LATEST_URL) as r:
            return json.load(r)
    except Exception as e:
        print(f"⚠️ Unable to check updates: {e}")
        return None

def download_file_from_github(filename, dest_folder="."):
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}/{filename}"
    dest_path = os.path.join(dest_folder, filename)

    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with urllib.request.urlopen(url) as response, open(dest_path, "wb") as out_file:
            out_file.write(response.read())
        return True
    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")
        return False
def ask_user_update(current_version, latest_version):
    root = tk.Tk()
    root.withdraw()  # скрываем главное окно
    message = f"New version available: {latest_version}\nCurrent version: {current_version}\n\nUpdate now?"
    result = messagebox.askyesno("Update Available", message)
    root.destroy()
    return result

def update_project():
    current_version = get_current_version()
    latest_info = get_latest_info()

    if not latest_info:
        return

    latest_version = latest_info.get("version", current_version)
    if latest_version == current_version:
        print(f"✅ Current version {current_version} is up to date.")
        return

    if not ask_user_update(current_version, latest_version):
        print("Update cancelled by user.")
        return

    files = latest_info.get("updated_files", [])
    print(f"Updating {len(files)} files...")

    tmp_dir = tempfile.mkdtemp()
    try:
        for filename in files:
            if download_file_from_github(filename, tmp_dir):
                shutil.move(os.path.join(tmp_dir, filename), filename)
                print(f"✔ {filename} updated")
        # update config version
        config_path = "config.json"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            else:
                cfg = {}

            cfg["version"] = latest_version  # обновляем только версию

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)

            print(f"✅ Config updated: version = {latest_version}")
        except Exception as e:
            print(f"⚠️ Failed to update version in config.json: {e}")
        print(f"✅ Update completed to version {latest_version}.")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
