from GUI import create_gui
import sys
from config_manager import ConfigManager
from updater import update_project


def main():
    try:
        config = ConfigManager()
        if not config.perform_initial_setup():
            print("❌ Initial setup failed. Please check configuration.")
            sys.exit(1)

        gui = create_gui()

        # Проверяем обновления ПОСЛЕ создания основного GUI
        try:
            update_project()
        except Exception as e:
            print(f"Update check failed: {e}")

        gui.run()
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
