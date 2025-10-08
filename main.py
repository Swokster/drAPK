from GUI import create_gui
import sys

def main():
    try:
        gui = create_gui()
        gui.run()
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()