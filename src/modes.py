import curses
import os
import platform
import sys
import time
import threading
from typing import Any, List, Optional, Dict
import logging
from logging.handlers import RotatingFileHandler

from .state import global_stop_flag, match_log, match_log_lock, SCAN_DURATION
from .config import load_config, save_config
from .matchers import process_template
from .utils import clear_terminal


def configure_logging() -> None:
    """Configure logging system with rotation and proper formatting"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                'debug.log',
                maxBytes=2*1024*1024,  # 2MB
                backupCount=5,
                encoding='utf-8'
            ),
            logging.StreamHandler()
        ]
    )
    logging.captureWarnings(True)

def start_global_stop_listener(stop_key: str) -> None:
    global global_stop_flag, macro_stop_flag
    global_stop_flag = False
    macro_stop_flag = False  # Reset flags on listener start
    if platform.system() == 'Windows':
        try:
            import keyboard
        except ImportError:
            print("Please install the 'keyboard' library (pip install keyboard) for global key detection on Windows.")
            sys.exit(1)
        def on_stop() -> None:
            global global_stop_flag, macro_stop_flag
            global_stop_flag = True
            macro_stop_flag = True
        keyboard.add_hotkey(stop_key, on_stop)
    else:
        try:
            from pynput import keyboard as pynput_keyboard
        except ImportError:
            print("Please install the 'pynput' library (pip install pynput) for global key detection.")
            sys.exit(1)
        def on_press(key: Any) -> Optional[bool]:
            global global_stop_flag, macro_stop_flag
            try:
                if stop_key.lower() == key.char.lower():
                    global_stop_flag = True
                    macro_stop_flag = True
                    return False
            except AttributeError:
                if stop_key.lower() in str(key).lower():
                    global_stop_flag = True
                    macro_stop_flag = True
                    return False
        listener = pynput_keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()

def continuous_matching(stdscr: Any, selection_flags: List[bool], valid_image_paths: List[str]) -> None:
    stdscr.nodelay(True)
    while not global_stop_flag:
        stdscr.clear()
        stdscr.addstr(0, 0, "Continuous Matching Mode: Global stop key is active. Press it to exit. ('q' to quit)")
        with match_log_lock:
            for i, line in enumerate(match_log[-15:]):
                stdscr.addstr(2 + i, 0, line[:stdscr.getmaxyx()[1] - 1])
        row: int = 18
        for tpl in valid_image_paths:
            stdscr.addstr(row, 0, f"Processing template: {tpl}")
            stdscr.refresh()
            process_template(selection_flags, tpl)
            if global_stop_flag:
                break
            time.sleep(SCAN_DURATION)
        stdscr.refresh()
        time.sleep(SCAN_DURATION)
        ch: int = stdscr.getch()
        if ch == ord('q'):
            sys.exit(0)
    stdscr.clear()
    stdscr.addstr(0, 0, "Stop key detected. Exiting continuous matching mode...")
    stdscr.refresh()
    time.sleep(1)

def debug_matching_mode(stdscr: Any, selection_flags: List[bool], valid_image_paths: List[str]) -> None:
    """Debug matching mode that follows the same pattern as continuous matching"""
    global global_stop_flag
    
    # Configure logging to capture more detailed information
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.handlers.RotatingFileHandler(
                'debug.log',
                maxBytes=2*1024*1024,
                backupCount=5,
                encoding='utf-8',
                delay=True
            )
        ],
        force=True
    )
    
    # Add handler to capture logs in match_log
    class MatchLogHandler(logging.Handler):
        def emit(self, record):
            msg = self.format(record)
            with match_log_lock:
                match_log.append(msg)
                if len(match_log) > 100:
                    match_log.pop(0)
    
    match_handler = MatchLogHandler()
    match_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(match_handler)
    
    # Use single window approach just like continuous mode
    stdscr.nodelay(True)
    
    # Main loop - identical structure to continuous_matching
    while not global_stop_flag:
        stdscr.clear()
        stdscr.addstr(0, 0, "Debug Matching Mode: Global stop key is active. Press it to exit. ('q' to quit)")
        
        # Show logs in the same way continuous mode does
        with match_log_lock:
            for i, line in enumerate(match_log[-15:]):
                stdscr.addstr(2 + i, 0, line[:stdscr.getmaxyx()[1] - 1])
        
        row = 18
        for tpl in valid_image_paths:
            stdscr.addstr(row, 0, f"Processing template: {tpl}")
            stdscr.refresh()
            process_template(selection_flags, tpl)
            if global_stop_flag:
                break
            time.sleep(SCAN_DURATION)
            
        stdscr.refresh()
        time.sleep(SCAN_DURATION)
        
        ch = stdscr.getch()
        if ch == ord('q'):
            sys.exit(0)
            
    stdscr.clear()
    stdscr.addstr(0, 0, "Stop key detected. Exiting debug matching mode...")
    stdscr.refresh()
    time.sleep(1)

def start_matching_mode(debug: bool = False) -> None:
    from .ui.menus import algorithm_selection_menu

    clear_terminal()
    config: Dict[str, Any] = load_config()
    if not config.get("default_profile") and config.get("profiles"):
        first_profile: str = list(config["profiles"].keys())[0]
        config["default_profile"] = first_profile
        save_config(config)
        print(f"No default profile found. Auto-setting default profile to '{first_profile}'.")
    default_profile: str = config.get("default_profile", "")
    if default_profile not in config.get("profiles", {}):
        print("Default profile not set or not found. Please set a default profile first.")
        input("Press Enter to return to the main menu...")
        return
    profile_data: Dict[str, Any] = config["profiles"][default_profile]
    base_path: str = profile_data.get("path", ".")
    if base_path == ".":
        base_path = os.getcwd()
    image_files: List[str] = profile_data.get("image_files", [])
    image_paths: List[str] = [os.path.join(base_path, img) for img in image_files]
    valid_image_paths: List[str] = [img for img in image_paths if os.path.isfile(img)]
    if not valid_image_paths:
        print("No valid image files found in the default profile.")
        input("Press Enter to return to the main menu...")
        return
    try:
        selection_flags: List[bool] = curses.wrapper(algorithm_selection_menu)
    except curses.error as e:
        print("Error initializing curses menu:", e)
        return
    if not any(selection_flags):
        print("No methods selected. Exiting.")
        input("Press Enter to return to the main menu...")
        return
    stop_key: str = config.get("stop_key", "esc")
    mode_label: str = "debug" if debug else "continuous"
    print(f"Starting {mode_label} matching mode. (Global stop key: {stop_key})")
    start_global_stop_listener(stop_key)
    if debug:
        curses.wrapper(lambda stdscr: debug_matching_mode(stdscr, selection_flags, valid_image_paths))
        print("Debug matching mode stopped.")
    else:
        curses.wrapper(lambda stdscr: continuous_matching(stdscr, selection_flags, valid_image_paths))
        print("Continuous matching stopped.")
    input("Press Enter to return to the main menu...")

def debug_mode() -> None:
    start_matching_mode(debug=True)
    
def start_with_default_profile():
    """Entry point for starting continuous matching with the default profile"""
    from .macros import play_macro  # Import here to avoid circular dependencies
    
    # Start macro playback in background thread
    macro_thread = threading.Thread(target=play_macro, daemon=True)
    macro_thread.start()
    
    # Start main matching functionality
    start_matching_mode(debug=False)