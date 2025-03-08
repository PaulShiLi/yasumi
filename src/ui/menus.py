# src/ui/menus.py
import curses
import locale
import sys
import time
import os
import json
from typing import Any, List, Dict, Optional

from ..config import (
    load_config,
    save_config,
    capture_stop_key,
    import_configuration,
    clear_debug_log
)
from ..state import (
    MODE,
    ACCURACY_THRESHOLDS,
    SCAN_DURATION,
    METHOD_NAMES,
    DEFAULT_ACCURACY_THRESHOLDS
)
from ..matchers import METHODS
from ..modes import (
    start_with_default_profile,
    debug_mode,
)
from ..macros import modify_key_macro
from ..utils import clear_terminal


def draw_menu(stdscr: Any, current_idx: int, selection_flags: List[bool], use_emoji: bool) -> None:
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    instr_text: str = "Use ↑/↓ or number keys to navigate, Space to toggle, Enter to confirm selection, 'q' to quit"
    stdscr.addnstr(0, 0, instr_text, w - 1)
    for idx, name in enumerate(METHOD_NAMES):
        mark: str = "✅" if (use_emoji and selection_flags[idx]) else ("[x]" if selection_flags[idx] else ("❌" if use_emoji else "[ ]"))
        menu_line: str = f"{idx+1}) {mark} {name}"
        menu_line = menu_line[:w - 1]
        line_num: int = idx + 2
        if line_num >= h:
            break
        if idx == current_idx:
            stdscr.attron(curses.A_REVERSE)
            stdscr.addnstr(line_num, 0, menu_line, w - 1)
            stdscr.attroff(curses.A_REVERSE)
        else:
            stdscr.addnstr(line_num, 0, menu_line, w - 1)
    stdscr.refresh()

def algorithm_selection_menu(stdscr: Any) -> List[bool]:
    curses.curs_set(0)
    stdscr.keypad(True)
    enc: str = sys.stdout.encoding or locale.getpreferredencoding()
    use_emoji: bool = ("UTF" in enc.upper()) if enc else False
    config = load_config()
    
    if "matching_pattern" in config and isinstance(config["matching_pattern"], list):
        selection_flags: List[bool] = config["matching_pattern"]
    else:
        selection_flags = [False] * len(METHOD_NAMES)
    
    current_idx: int = 0
    draw_menu(stdscr, current_idx, selection_flags, use_emoji)
    
    while True:
        key: int = stdscr.getch()
        if key == ord('q'):
            sys.exit(0)
        
        try:
            if chr(key).isdigit():
                num = int(chr(key))
                if 1 <= num <= len(METHOD_NAMES):
                    current_idx = num - 1
        except Exception:
            pass
        
        if key in (curses.KEY_UP, ord('k')):
            current_idx = (current_idx - 1) % len(METHOD_NAMES)
        elif key in (curses.KEY_DOWN, ord('j')):
            current_idx = (current_idx + 1) % len(METHOD_NAMES)
        elif key == ord(' '):
            selection_flags[current_idx] = not selection_flags[current_idx]
        elif key in (curses.KEY_ENTER, 10, 13):
            break
        
        draw_menu(stdscr, current_idx, selection_flags, use_emoji)
    
    config["matching_pattern"] = selection_flags
    save_config(config)
    return selection_flags

def adjust_thresholds_menu(stdscr: Any) -> None:
    curses.curs_set(1)
    stdscr.clear()
    algos = ["pyautogui", "template", "orb", "sift", "akaze"]
    algo_names = {
        "pyautogui": "PyAutoGUI Matching",
        "template": "Grayscale Template Matching",
        "orb": "ORB Feature Matching",
        "sift": "SIFT Feature Matching",
        "akaze": "AKAZE Feature Matching"
    }
    current_idx = 0
    
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Adjust Accuracy Thresholds (↑/↓ to navigate, Enter to modify, q to quit):")
        
        for i, key in enumerate(algos):
            default_val = 0.8 if key in ["pyautogui", "template"] else 10
            value = ACCURACY_THRESHOLDS.get(key, default_val)
            display_str = f"{i+1}) {algo_names[key]}: {value}"
            if i == current_idx:
                stdscr.addstr(i+2, 0, display_str, curses.A_REVERSE)
            else:
                stdscr.addstr(i+2, 0, display_str)
        
        key = stdscr.getch()
        
        if key == ord('q'):
            break
        elif key in (curses.KEY_UP, ord('k')):
            current_idx = (current_idx - 1) % len(algos)
        elif key in (curses.KEY_DOWN, ord('j')):
            current_idx = (current_idx + 1) % len(algos)
        elif key in (curses.KEY_ENTER, 10, 13):
            selected_algo = algos[current_idx]
            default_val = 0.8 if selected_algo in ["pyautogui", "template"] else 10
            current_val = ACCURACY_THRESHOLDS.get(selected_algo, default_val)
            
            stdscr.addstr(len(algos)+3, 0, f"New value for {algo_names[selected_algo]} (current: {current_val}): ")
            curses.echo()
            new_val_str = stdscr.getstr(len(algos)+3, len(f"New value for {algo_names[selected_algo]} (current: {current_val}): ")).decode()
            curses.noecho()
            
            try:
                new_val = float(new_val_str) if selected_algo in ["pyautogui", "template"] else int(new_val_str)
                config = load_config()
                config["accuracy_thresholds"][selected_algo] = new_val
                save_config(config)
                ACCURACY_THRESHOLDS.update(config["accuracy_thresholds"])
            except Exception as e:
                stdscr.addstr(len(algos)+4, 0, f"Invalid input: {str(e)}")
                stdscr.getch()
        
    curses.curs_set(0)

def adjust_scan_duration_menu(stdscr: Any) -> None:
    global SCAN_DURATION  # Move this to the top
    curses.curs_set(1)
    stdscr.clear()
    prompt: str = f"Current Scan Duration (seconds): {SCAN_DURATION}. Enter new scan duration (or 'q' to quit): "
    stdscr.addstr(0, 0, prompt)
    stdscr.clrtoeol()
    curses.echo()
    
    new_val_str: str = stdscr.getstr(1, 0).decode('utf-8').strip()
    curses.noecho()
    
    if new_val_str.lower() == 'q':
        sys.exit(0)
    
    try:
        new_val: float = float(new_val_str)
        config: Dict[str, Any] = load_config()
        config["scan_duration"] = new_val
        save_config(config)
        SCAN_DURATION = new_val  # Now properly modifies the global
        stdscr.addstr(2, 0, "Scan duration updated. Press any key to continue.")
        stdscr.getch()
    except Exception as e:
        stdscr.addstr(2, 0, f"Invalid input: {e}. Press any key to continue.")
        stdscr.getch()
    
    curses.curs_set(0)

def settings_menu() -> None:
    while True:
        clear_terminal()
        config = load_config()
        current_mode = config.get("mode", "performance")
        print("\nSettings Menu:")
        print("1) Set Stop Key")
        print("2) Set Default Profile")
        print("3) Import configuration")
        print("4) Show Debugging Logs")
        print("5) Clear Debug Log")
        print("6) Toggle Mode (current: {})".format(current_mode))
        print("7) Adjust Accuracy Thresholds")
        print("8) Adjust Scan Duration")
        print("9) Return")
        
        choice: str = input("Enter option number (or 'q' to quit): ").strip()
        
        if choice.lower() == 'q':
            sys.exit(0)
        elif choice == "1":
            set_stop_key()
        elif choice == "2":
            set_default_profile_menu()
        elif choice == "3":
            import_configuration()
        elif choice == "4":
            show_debugging_logs()
        elif choice == "5":
            clear_debug_log()
        elif choice == "6":
            toggle_mode()
        elif choice == "7":
            curses.wrapper(adjust_thresholds_menu)
        elif choice == "8":
            curses.wrapper(adjust_scan_duration_menu)  # Now correctly defined
        elif choice == "9":
            break
        else:
            print("Invalid selection, try again.")
            time.sleep(1)

def set_stop_key():
    clear_terminal()
    new_key = capture_stop_key()
    config = load_config()
    config["stop_key"] = new_key
    save_config(config)
    print(f"Stop key updated to: {new_key}")
    input("Press Enter to continue...")

def set_default_profile_menu():
    config = load_config()
    profiles = config.get("profiles", {})
    
    if not profiles:
        print("No profiles available!")
        return
    
    print("Available profiles:")
    for idx, name in enumerate(profiles.keys()):
        print(f"{idx+1}) {name}")
    
    choice = input("Select profile number: ").strip()
    try:
        index = int(choice) - 1
        selected = list(profiles.keys())[index]
        config["default_profile"] = selected
        save_config(config)
        print(f"Default profile set to: {selected}")
    except (ValueError, IndexError):
        print("Invalid selection")
    input("Press Enter to continue...")

def create_new_profile():
    config = load_config()
    name = input("Profile name: ").strip()
    
    if not name:
        print("Name cannot be empty!")
        return
    
    if name in config.get("profiles", {}):
        print("Profile already exists!")
        return
    
    path = input("Base path (default .): ").strip() or "."
    images = input("Image files (comma-separated): ").split(",")
    
    config.setdefault("profiles", {})[name] = {
        "path": path,
        "image_files": [img.strip() for img in images if img.strip()],
        "key_recording": []
    }
    save_config(config)
    print(f"Profile '{name}' created")
    input("Press Enter to continue...")

def import_profile():
    config = load_config()
    path = input("Import file path: ").strip()
    
    if not os.path.exists(path):
        print("File not found!")
        return
    
    try:
        with open(path) as f:
            imported = json.load(f)
        
        for name, data in imported.items():
            config.setdefault("profiles", {})[name] = data
        save_config(config)
        print(f"Imported {len(imported)} profiles")
    except Exception as e:
        print(f"Import failed: {str(e)}")
    input("Press Enter to continue...")

def edit_profile_menu():
    while True:
        clear_terminal()
        print("Profile Management")
        print("1. Create New Profile")
        print("2. Import Profile")
        print("3. Modify Macros")
        print("4. Return")
        
        choice = input("Select option: ").strip()
        
        if choice == "1":
            create_new_profile()
        elif choice == "2":
            import_profile()
        elif choice == "3":
            modify_key_macro()
        elif choice == "4":
            break
        else:
            print("Invalid choice")

def show_debugging_logs():
    clear_terminal()
    if os.path.exists("debug.log"):
        with open("debug.log") as f:
            print(f.read())
    else:
        print("No debug log found")
    input("Press Enter to continue...")

def toggle_mode():
    config = load_config()
    new_mode = "accuracy" if config.get("mode") == "performance" else "performance"
    config["mode"] = new_mode
    save_config(config)
    print(f"Switched to {new_mode} mode")
    input("Press Enter to continue...")

def main_menu():
    while True:
        clear_terminal()
        print("Yasumi AFK Tool")
        print("1. Start with Default Profile")
        print("2. Profile Management")
        print("3. Settings")
        print("4. Debug Mode")
        print("5. Exit")
        
        choice = input("Select option: ").strip()
        
        if choice == "1":
            start_with_default_profile()
        elif choice == "2":
            edit_profile_menu()
        elif choice == "3":
            settings_menu()
        elif choice == "4":
            debug_mode()
        elif choice in ("5", "q"):
            print("Exiting...")
            break
        else:
            print("Invalid choice")