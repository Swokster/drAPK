from GUI import create_gui
import sys
from config_manager import ConfigManager
from updater import update_project

def main():
    try:
        config = ConfigManager()
        # config.auto_discover_tools("drtool", [
        #     'BaseTool', 'APKTool', 'DRTool',
        #     'UnluacBase', 'LuacBase', 'UTF8Decoder',  # Base Classes
        #     'CLScript'
        # ])
        # # config.auto_discover_tools("other_tools", ['Excluded classes'])

        if not config.perform_initial_setup():
            print("❌ Initial setup failed. Please check configuration.")
            sys.exit(1)


        gui = create_gui()
        gui.run()
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_project()
    main()
