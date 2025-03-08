import os
import json
import platform
import time
import sys
from typing import Dict, Any
from pynput import keyboard as pynput_keyboard

from . import state  # Changed from direct imports

CONFIG_FILENAME = ".config"

def load_config() -> Dict[str, Any]:
    config = {}
    if os.path.isfile(CONFIG_FILENAME):
        try:
            with open(CONFIG_FILENAME, "r") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    # Set defaults
    config.setdefault("stop_key", "esc")
    config.setdefault("matching_pattern", [False] * len(state.METHOD_NAMES))
    config.setdefault("mode", "performance")
    config.setdefault("accuracy_thresholds", state.DEFAULT_ACCURACY_THRESHOLDS.copy())
    config.setdefault("scan_duration", 0.5)
    
    # Update global state
    state.MODE = config["mode"]
    state.ACCURACY_THRESHOLDS.update(config["accuracy_thresholds"])
    state.SCAN_DURATION = config["scan_duration"]
    
    save_config(config)
    return config

def save_config(config: Dict[str, Any]) -> None:
    try:
        with open(CONFIG_FILENAME, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")

def import_configuration():
    """Import configuration from another file"""
    file_path = input("Enter file path to import configuration from: ").strip()
    if not os.path.isfile(file_path):
        print("File not found.")
        input("Press Enter to continue...")
        return
    
    try:
        with open(file_path, "r") as f:
            new_config = json.load(f)
        
        if "profiles" not in new_config:
            print("Invalid configuration format.")
            return
        
        # Preserve existing secrets while updating configuration
        current_config = load_config()
        current_config.update(new_config)
        save_config(current_config)
        print("Configuration imported successfully.")
    
    except Exception as e:
        print(f"Error importing configuration: {str(e)}")
    
    input("Press Enter to continue...")

def clear_debug_log():
    """Clear the debug.log file"""
    if os.path.exists("debug.log"):
        try:
            with open("debug.log", "w") as f:
                f.write("")
            print("Debug log cleared.")
        except Exception as e:
            print(f"Error clearing debug log: {e}")
    else:
        print("No debug log file found.")
    input("Press Enter to continue...")

def capture_stop_key() -> str:
    time.sleep(0.3)
    if platform.system() == 'Windows':
        try:
            import keyboard
        except ImportError:
            print("Please install 'keyboard' library for Windows.")
            sys.exit(1)
        print("Press desired stop key combination...")
        key = keyboard.read_hotkey(suppress=True)
        print(f"Pressed: {key}")
        return key
    else:
        print("Press desired stop key...")
        stop_key_code = None
        def on_press(key: Any):
            nonlocal stop_key_code
            try:
                stop_key_code = key.char.lower()
            except AttributeError:
                stop_key_code = str(key).split('.')[-1].lower()
            return False
        with pynput_keyboard.Listener(on_press=on_press) as listener:
            listener.join()
        print(f"Pressed: {stop_key_code}")
        return stop_key_code if stop_key_code else "esc"