import threading
from typing import Optional, Tuple, List, Dict, Any
import numpy as np

# Global state variables
global_stop_flag = False
macro_stop_flag = False
last_click_time = 0.0
last_click_coord: Optional[Tuple[int, int]] = None
last_click_lock = threading.Lock()
match_log: List[str] = []
match_log_lock = threading.Lock()
MODE = "performance"
ACCURACY_THRESHOLDS: Dict[str, Any] = {}
SCAN_DURATION = 0.5
template_cache: Dict[str, np.ndarray] = {}
current_screen_gray: Optional[np.ndarray] = None

DEFAULT_ACCURACY_THRESHOLDS = {
    "pyautogui": 0.8,
    "template": 0.95,
    "orb": 60,
    "sift": 80,
    "akaze": 10
}

METHOD_NAMES = [
    "PyAutoGUI Matching",
    "Grayscale Template Matching", 
    "ORB Feature Matching",
    "SIFT Feature Matching",
    "AKAZE Feature Matching"
]