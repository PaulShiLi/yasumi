# src/yasumi.py
from src.ui.menus import main_menu
from src.config import load_config

def main():
    load_config()
    main_menu()

if __name__ == "__main__":
    main()