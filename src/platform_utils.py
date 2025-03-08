import platform
import time
import ctypes
import pyautogui
from typing import Tuple

# Platform-specific left click implementation
if platform.system() == "Darwin":
    import Quartz
    def left_click(x: int, y: int):
        screen_height = pyautogui.size().height
        pos = (x, screen_height - y)
        event_down = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseDown, pos, Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)
        time.sleep(0.01)
        event_up = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventLeftMouseUp, pos, Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)
else:
    def left_click(x: int, y: int):
        pyautogui.click(x, y)

# Windows-specific input handling
if platform.system() == "Windows":
    PUL = ctypes.POINTER(ctypes.c_ulong)
    
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", PUL)
        ]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", PUL)
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]
        _anonymous_ = ("_input",)
        _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUT)]

    SendInput = ctypes.windll.user32.SendInput
    KEYEVENTF_KEYUP = 0x0002
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004

    def send_keyboard_event(vk: int, flags: int):
        inp = INPUT()
        inp.type = 1
        inp.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=None)
        SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

    def send_mouse_event(x: int, y: int, flags: int):
        screen_width, screen_height = pyautogui.size()
        abs_x = int(x * 65535 / screen_width)
        abs_y = int(y * 65535 / screen_height)
        inp = INPUT()
        inp.type = 0
        inp.mi = MOUSEINPUT(dx=abs_x, dy=abs_y, mouseData=0, 
                          dwFlags=flags | 0x8000, time=0, dwExtraInfo=None)
        SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
else:
    def send_keyboard_event(vk: int, flags: int):
        pyautogui.press(chr(vk))
    
    def send_mouse_event(x: int, y: int, flags: int):
        pyautogui.moveTo(x, y)

VK_CODE = {
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
    'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
    'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
    'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
    'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59,
    'z': 0x5A, '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33,
    '4': 0x34, '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38,
    '9': 0x39, 'enter': 0x0D, 'esc': 0x1B, 'space': 0x20,
    'tab': 0x09, 'shift': 0x10
}

def send_key_event(key: str, down: bool):
    if platform.system() != "Windows":
        if down:
            pyautogui.keyDown(key)
        else:
            pyautogui.keyUp(key)
        return
    
    use_shift = key.isupper()
    key = key.lower()
    vk = VK_CODE.get(key)
    if not vk:
        return
    
    if use_shift:
        send_keyboard_event(VK_CODE['shift'], 0)
    
    flags = 0 if down else KEYEVENTF_KEYUP
    send_keyboard_event(vk, flags)
    
    if use_shift:
        send_keyboard_event(VK_CODE['shift'], KEYEVENTF_KEYUP)