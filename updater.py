import os
import json
import urllib.request
import tempfile
import shutil
import tkinter as tk
from tkinter import messagebox

GITHUB_USER = "Swokster"
GITHUB_REPO = "drAPK"
BRANCH = "master"

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


def download_file_from_github(filepath, dest_folder="."):
    """Download file from GitHub"""
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}/{filepath}"
    dest_path = os.path.join(dest_folder, filepath)

    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with urllib.request.urlopen(url) as response, open(dest_path, "wb") as out_file:
            out_file.write(response.read())
        return True
    except Exception as e:
        print(f"❌ Failed to download {filepath}: {e}")
        return False


def download_folder_from_github(folder_path, dest_folder="."):
    """Downlad folder from GitHub"""
    try:
        # Use GitHub API to get folder content
        api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{folder_path}?ref={BRANCH}"

        with urllib.request.urlopen(api_url) as response:
            contents = json.loads(response.read().decode())

        success = True
        for item in contents:
            # Change \ with /
            item_path = f"{folder_path}/{item['name']}"

            if item['type'] == 'file':
                # Сdownload file
                if not download_file_from_github(item_path, dest_folder):
                    print(f"⚠️ Skipping file: {item_path} (not found)")
                    # Continue downloading

            elif item['type'] == 'dir':
                # download subfolder with recursion
                download_folder_from_github(item_path, dest_folder)

        return True  # return True even if smth not downloaded

    except Exception as e:
        print(f"❌ Failed to download folder {folder_path}: {e}")
        return False

def ask_user_update(current_version, latest_version):
    root = tk.Tk()
    root.withdraw()
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

    # Compare versions as number
    current_parts = list(map(int, current_version.split('.')))
    latest_parts = list(map(int, latest_version.split('.')))

    # fill with 0 if necessary
    max_len = max(len(current_parts), len(latest_parts))
    current_parts.extend([0] * (max_len - len(current_parts)))
    latest_parts.extend([0] * (max_len - len(latest_parts)))

    # Check if updates needed
    needs_update = False
    for i in range(max_len):
        if latest_parts[i] > current_parts[i]:
            needs_update = True
            break
        elif latest_parts[i] < current_parts[i]:
            break

    if not needs_update:
        print(f"✅ Current version {current_version} is up to date.")
        return

    if not ask_user_update(current_version, latest_version):
        print("Update cancelled by user.")
        return

    items = latest_info.get("updated_files", [])
    print(f"Updating {len(items)} items...")

    tmp_dir = tempfile.mkdtemp()
    try:
        for item in items:
            print(f"🔍 Processing: {item}")

            if item.endswith('/'):
                # If folder
                folder_name = item[:-1]  # Remove trailing slash
                if download_folder_from_github(folder_name, tmp_dir):
                    # Copy from temp folder
                    src_path = os.path.join(tmp_dir, folder_name)
                    dest_path = folder_name

                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)
                    shutil.copytree(src_path, dest_path)
                    print(f"✅ {item} folder updated")
                else:
                    print(f"❌ Failed to update folder: {item}")

            else:
                # else - file
                if download_file_from_github(item, tmp_dir):
                    src_path = os.path.join(tmp_dir, item)
                    dest_path = item

                    # Check folder not empty
                    dest_dir = os.path.dirname(dest_path)
                    if dest_dir:  # if subfolders exist
                        os.makedirs(dest_dir, exist_ok=True)

                    # copy file
                    shutil.copy2(src_path, dest_path)
                    print(f"✅ {item} updated")
                else:
                    print(f"❌ Failed to update file: {item}")

        # Refresh version
        config_path = "config.json"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            else:
                cfg = {}

            cfg["version"] = latest_version

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)

            print(f"✅ Config version updated to: {latest_version}")
        except Exception as e:
            print(f"⚠️ Failed to update version in config.json: {e}")

        print(f"✅ Update completed to version {latest_version}.")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)