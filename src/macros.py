import time
import threading
import json
import os
import platform
import logging
import pyautogui
import pydirectinput
from pynput import keyboard, mouse
from typing import List, Dict, Any

from .state import macro_stop_flag
from .config import load_config, save_config
from .platform_utils import left_click

is_macro_recording = False
macro_events = []
record_start_time = 0.0
key_listener = None
mouse_listener = None

def on_key_press(key):
    global macro_events, record_start_time
    timestamp = time.perf_counter() - record_start_time
    try:
        key_str = key.char
    except AttributeError:
        key_str = key.name if hasattr(key, 'name') else str(key)
    macro_events.append({"type": "key_press", "key": key_str, "time": timestamp})

def on_key_release(key):
    global macro_events, record_start_time
    timestamp = time.perf_counter() - record_start_time
    try:
        key_str = key.char
    except AttributeError:
        key_str = key.name if hasattr(key, 'name') else str(key)
    macro_events.append({"type": "key_release", "key": key_str, "time": timestamp})

def on_mouse_move(x, y):
    global macro_events, record_start_time
    timestamp = time.perf_counter() - record_start_time
    macro_events.append({"type": "mouse_move", "x": x, "y": y, "time": timestamp})

def on_mouse_click(x, y, button, pressed):
    global macro_events, record_start_time
    timestamp = time.perf_counter() - record_start_time
    macro_events.append({"type": "mouse_click", "x": x, "y": y, "button": str(button), "pressed": pressed, "time": timestamp})

def on_mouse_scroll(x, y, dx, dy):
    global macro_events, record_start_time
    timestamp = time.perf_counter() - record_start_time
    macro_events.append({"type": "mouse_scroll", "x": x, "y": y, "dx": dx, "dy": dy, "time": timestamp})

def start_macro_recording():
    global is_macro_recording, macro_events, record_start_time, key_macro_keyboard_listener, key_macro_mouse_listener
    if is_macro_recording:
        return
    print("Key Recorder: Recording started.")
    macro_events = []
    record_start_time = time.perf_counter()
    key_macro_keyboard_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
    key_macro_mouse_listener = mouse.Listener(on_move=on_mouse_move, on_click=on_mouse_click, on_scroll=on_mouse_scroll)
    key_macro_keyboard_listener.start()
    key_macro_mouse_listener.start()
    is_macro_recording = True

def stop_macro_recording():
    global is_macro_recording, key_macro_keyboard_listener, key_macro_mouse_listener
    if not is_macro_recording:
        return
    key_macro_keyboard_listener.stop()
    key_macro_mouse_listener.stop()
    key_macro_keyboard_listener.join()
    key_macro_mouse_listener.join()
    is_macro_recording = False
    print("Key Recorder: Recording stopped.")

def toggle_macro_recording():
    if not is_macro_recording:
        start_macro_recording()
    else:
        stop_macro_recording()

# New functions for macro profile selection and clearing:
def select_macro_profile():
    config = load_config()
    profiles = config.get("profiles", {})
    if not profiles:
        print("No profiles available.")
        return
    print("Available profiles:")
    profile_list = list(profiles.keys())
    for idx, profile in enumerate(profile_list):
        print(f"{idx+1}) {profile}")
    choice = input("Select profile number for macro: ").strip()
    try:
        index = int(choice) - 1
        selected = profile_list[index]
        config["macro_profile"] = selected
        save_config(config)
        print(f"Macro will be saved to profile: {selected}")
    except Exception as e:
        print("Invalid input:", e)

def clear_macro_for_profile():
    config = load_config()
    profiles = config.get("profiles", {})
    if not profiles:
        print("No profiles available.")
        return
    print("Available profiles:")
    profile_list = list(profiles.keys())
    for idx, profile in enumerate(profile_list):
        print(f"{idx+1}) {profile}")
    choice = input("Select profile number to clear macro from: ").strip()
    try:
        index = int(choice) - 1
        selected = profile_list[index]
        config["profiles"][selected]["key_recording"] = []
        save_config(config)
        print(f"Macro cleared for profile: {selected}")
    except Exception as e:
        print("Invalid input:", e)

def modify_key_macro():
    print("Modify Key Macro mode:")
    print("Options:")
    print("1) Record Macro (Press F8 to toggle recording, F9 to exit)")
    print("2) Select profile to save macro to")
    print("3) Clear macro from profile")
    print("4) Exit")
    choice = input("Enter option number: ").strip()
    if choice == "1":
        # Start global hotkeys to record macro.
        from pynput import keyboard as pynput_keyboard
        print("Press F8 to toggle recording, F9 to exit this mode.")
        def exit_listener():
            h.stop()
        with pynput_keyboard.GlobalHotKeys({
            '<f8>': toggle_macro_recording,
            '<f9>': exit_listener
        }) as h:
            h.join()
    elif choice == "2":
        select_macro_profile()
    elif choice == "3":
        clear_macro_for_profile()
    elif choice == "4":
        return
    else:
        print("Invalid selection.")

def play_macro():
    global macro_stop_flag
    config = load_config()
    # Use macro_profile if set, else default_profile
    default_profile = config.get("macro_profile", config.get("default_profile", ""))
    if not default_profile or default_profile not in config.get("profiles", {}):
        print("No valid profile available for macro playback.")
        return
    macro = config["profiles"][default_profile].get("key_recording", [])
    if not macro:
        return
    print("Replaying macro continuously in the background...")
    macro_stop_flag = False
    while not macro_stop_flag:
        start_time = time.perf_counter()
        for event in macro:
            if macro_stop_flag:
                break
            event_time = event.get("time", 0)
            while time.perf_counter() - start_time < event_time:
                if macro_stop_flag:
                    break
                time.sleep(0.001)
            if macro_stop_flag:
                break
            if platform.system() == "Windows":
                if event["type"] == "key_press":
                    pydirectinput.keyDown(event["key"].lower())
                elif event["type"] == "key_release":
                    pydirectinput.keyUp(event["key"].lower())
                elif event["type"] == "mouse_move":
                    pydirectinput.moveTo(event["x"], event["y"])
                elif event["type"] == "mouse_click":
                    if event["pressed"]:
                        pydirectinput.click(x=event["x"], y=event["y"], button="left")
                    else:
                        pydirectinput.mouseUp(x=event["x"], y=event["y"], button="left")
                elif event["type"] == "mouse_scroll":
                    try:
                        pydirectinput.scroll(event["dy"], x=event["x"], y=event["y"])
                    except Exception as e:
                        logging.error("Error in mouse_scroll: %s", e)
            else:
                if event["type"] == "key_press":
                    pyautogui.keyDown(event["key"])
                elif event["type"] == "key_release":
                    pyautogui.keyUp(event["key"])
                elif event["type"] == "mouse_move":
                    pyautogui.moveTo(event["x"], event["y"])
                elif event["type"] == "mouse_click":
                    left_click(event["x"], event["y"])
                elif event["type"] == "mouse_scroll":
                    try:
                        pyautogui.scroll(event["dy"], x=event["x"], y=event["y"])
                    except Exception as e:
                        logging.error("Error in mouse_scroll: %s", e)
        time.sleep(0.5)
