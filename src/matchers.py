import cv2
import logging
import numpy as np
import pyautogui
import threading
import time
from skimage import exposure
from typing import Optional, Tuple, List, Dict, Any, Callable

from .state import (
    MODE, ACCURACY_THRESHOLDS, SCAN_DURATION,
    template_cache, current_screen_gray,
    match_log, match_log_lock,
    last_click_time, last_click_coord, last_click_lock
)
from .platform_utils import left_click

logger = logging.getLogger(__name__)

class ImageMatcher:
    @staticmethod
    def match_pyautogui(template_path: str, confidence: Optional[float] = None) -> Optional[Tuple[Tuple[int, int], float]]:
        try:
            conf = confidence if confidence is not None else ACCURACY_THRESHOLDS.get("pyautogui", 0.8)
            logging.info("Trying PyAutoGUI matching (confidence=%.2f)...", conf)
            center = pyautogui.locateCenterOnScreen(template_path, confidence=conf)
            if center:
                logging.info("PyAutoGUI found the image at %s", center)
                return (center, 1.0)
            return None
        except pyautogui.ImageNotFoundException:
            logging.info("PyAutoGUI could not find the image on screen.")
            return None
        except Exception as e:
            logging.error("PyAutoGUI error: %s", e)
            return None

    @staticmethod
    def match_template_gray(template_path: str, threshold: Optional[float] = None) -> Optional[Tuple[Tuple[int, int], float]]:
        try:
            logging.info("Trying Template Matching (grayscale)...")
            template = load_template_image(template_path)
            if template is None:
                logging.error("Template image not found: %s", template_path)
                return None
            global current_screen_gray
            if current_screen_gray is None:
                screenshot = pyautogui.screenshot()
                screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            else:
                screen_gray = current_screen_gray
            if MODE == "accuracy":
                try:
                    search_img = exposure.match_histograms(screen_gray, template)
                except Exception as e:
                    logging.error("Histogram matching failed: %s", e)
                    search_img = screen_gray
            else:
                search_img = screen_gray
            thresh = threshold if threshold is not None else ACCURACY_THRESHOLDS.get("template", 0.8)
            result = cv2.matchTemplate(search_img, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val >= thresh:
                h, w = template.shape
                center = (max_loc[0] + w // 2, max_loc[1] + h // 2)
                logging.info("Template match success (confidence=%.2f) at %s", max_val, center)
                return (center, max_val)
            else:
                logging.info("Template match failed (max confidence=%.2f)", max_val)
                return None
        except Exception as e:
            logging.error("Template matching error: %s", e)
            return None

    @staticmethod
    def match_orb(template_path: str) -> Optional[Tuple[Tuple[int, int], float]]:
        try:
            logging.info("Trying ORB feature matching...")
            orb = cv2.ORB_create(nfeatures=2000, scaleFactor=1.2, nlevels=8, edgeThreshold=15, patchSize=31)
            template = load_template_image(template_path)
            if template is None:
                logging.error("Template image not found: %s", template_path)
                return None
            
            global current_screen_gray
            if current_screen_gray is None:
                screenshot = pyautogui.screenshot()
                screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            else:
                screen_gray = current_screen_gray
            
            kp1, des1 = orb.detectAndCompute(template, None)
            kp2, des2 = orb.detectAndCompute(screen_gray, None)
            logging.info("ORB detected %d template keypoints and %d screen keypoints", len(kp1), len(kp2))
            
            if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
                logging.info("ORB: Insufficient features detected to match.")
                return None

            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = bf.knnMatch(des1, des2, k=2)
            good_matches = [m for m, n in matches if m.distance < 0.7 * n.distance]
            min_matches = ACCURACY_THRESHOLDS.get("orb", 15)
            logging.info("ORB initial good matches: %d", len(good_matches))
            
            if len(good_matches) < min_matches:
                logging.info("ORB match failed (only %d good matches).", len(good_matches))
                return None

            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)
            
            if M is None:
                logging.info("ORB: Homography estimation failed.")
                return None

            inlier_count = np.sum(mask)
            logging.info("ORB homography inliers: %d/%d", inlier_count, len(good_matches))
            if inlier_count < max(min_matches, 0.25 * len(good_matches)):
                logging.info("ORB: Insufficient homography inliers.")
                return None

            h, w = template.shape
            corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
            transformed_corners = cv2.perspectiveTransform(corners, M)
            
            if not cv2.isContourConvex(transformed_corners):
                logging.info("ORB: Transformed corners are not convex.")
                return None
                
            original_area = h * w
            transformed_area = cv2.contourArea(transformed_corners)
            area_ratio = transformed_area / original_area
            if not (0.1 < area_ratio < 10):
                logging.info("ORB: Implausible area ratio (%.2f)", area_ratio)
                return None

            x_coords = transformed_corners[:, 0, 0]
            y_coords = transformed_corners[:, 0, 1]
            center = (int(np.mean(x_coords)), int(np.mean(y_coords)))
            
            screen_width, screen_height = pyautogui.size()
            if not (0 <= center[0] <= screen_width and 0 <= center[1] <= screen_height):
                logging.info("ORB: Calculated center outside screen boundaries.")
                return None

            score = inlier_count
            logging.info("ORB match found (inliers=%d) at %s", score, center)
            return (center, score)
            
        except Exception as e:
            logging.error("ORB matching error: %s", e)
            return None

    @staticmethod
    def match_sift(template_path: str, ratio_thresh: float = 0.7, ransac_thresh: float = 5.0) -> Optional[Tuple[Tuple[int, int], float]]:
        logging.info("Starting SIFT feature matching...")
        if not hasattr(cv2, 'SIFT_create'):
            logging.error("SIFT not available in this OpenCV installation.")
            return None
        sift = cv2.SIFT_create()
        template = load_template_image(template_path)
        if template is None:
            logging.error("Template image not found: %s", template_path)
            return None
        
        global current_screen_gray
        if current_screen_gray is None:
            screenshot = pyautogui.screenshot()
            screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        else:
            screen_gray = current_screen_gray
        
        kp1, des1 = sift.detectAndCompute(template, None)
        kp2, des2 = sift.detectAndCompute(screen_gray, None)
        if des1 is None or des2 is None or len(des1) < 2 or len(des2) < 2:
            logging.info("Insufficient features detected for matching.")
            return None

        bf = cv2.BFMatcher(cv2.NORM_L2)
        matches = bf.knnMatch(des1, des2, k=2)
        good_matches = [m for m, n in matches if m.distance < ratio_thresh * n.distance]

        min_matches = ACCURACY_THRESHOLDS.get("sift", 10)
        if len(good_matches) < min_matches:
            logging.info("Not enough good matches: found %d, required %d", len(good_matches), min_matches)
            return None

        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, ransac_thresh)
        if M is None or mask is None:
            logging.info("Homography computation failed.")
            return None
        
        if abs(np.linalg.det(M)) < 1e-5:
            logging.info("Degenerate homography matrix detected.")
            return None
        
        h, w = template.shape[:2]
        original_area = h * w
        corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
        transformed_corners = cv2.perspectiveTransform(corners, M)
        area = cv2.contourArea(transformed_corners)
        if area < 0.01 * original_area or area > 100 * original_area:
            logging.info("Transformed area invalid (original: %d, transformed: %d)", original_area, area)
            return None

        hull = cv2.convexHull(transformed_corners)
        centroid = np.mean(hull.squeeze(), axis=0)
        center = (int(centroid[0]), int(centroid[1]))
        score = float(np.sum(mask))
        logging.info("SIFT match found (inliers=%d) at %s", int(score), center)
        
        return (center, score)

    @staticmethod
    def match_akaze(template_path: str) -> Optional[Tuple[Tuple[int, int], float]]:
        try:
            logging.info("Trying AKAZE feature matching...")
            akaze = cv2.AKAZE_create()
            template = load_template_image(template_path)
            if template is None:
                logging.error("Template image not found: %s", template_path)
                return None
            global current_screen_gray
            if current_screen_gray is None:
                screenshot = pyautogui.screenshot()
                screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            else:
                screen_gray = current_screen_gray
            kp1, des1 = akaze.detectAndCompute(template, None)
            kp2, des2 = akaze.detectAndCompute(screen_gray, None)
            if des1 is None or des2 is None:
                logging.info("AKAZE: insufficient features detected to match.")
                return None
            bf = cv2.BFMatcher(cv2.NORM_HAMMING)
            matches = bf.knnMatch(des1, des2, k=2)
            good_matches = [m for m, n in matches if m.distance < 0.7 * n.distance]
            min_matches = ACCURACY_THRESHOLDS.get("akaze", 10)
            if len(good_matches) >= min_matches:
                src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                M, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                if M is not None:
                    h, w = template.shape
                    corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
                    transformed_corners = cv2.perspectiveTransform(corners, M)
                    x_coords = transformed_corners[:, 0, 0]
                    y_coords = transformed_corners[:, 0, 1]
                    center = (int((x_coords.min() + x_coords.max()) / 2),
                              int((y_coords.min() + y_coords.max()) / 2))
                    score = len(good_matches)
                    logging.info("AKAZE match found (good matches=%d) at %s", score, center)
                    return (center, score)
                else:
                    logging.info("AKAZE found %d good matches, but homography failed.", len(good_matches))
                    return None
            else:
                logging.info("AKAZE match failed (only %d good matches).", len(good_matches))
                return None
        except Exception as e:
            logging.error("AKAZE matching error: %s", e)
            return None

METHODS = [
    ("PyAutoGUI Matching", ImageMatcher.match_pyautogui),
    ("Grayscale Template Matching", ImageMatcher.match_template_gray),
    ("ORB Feature Matching", ImageMatcher.match_orb),
    ("SIFT Feature Matching", ImageMatcher.match_sift),
    ("AKAZE Feature Matching", ImageMatcher.match_akaze)
]

def load_template_image(template_path: str) -> Optional[np.ndarray]:
    if template_path in template_cache:
        return template_cache[template_path]
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is not None:
        template_cache[template_path] = template
    return template

def find_best_match(selection_flags: List[bool], template_path: str) -> Tuple[Optional[Tuple[int, int]], Optional[float], Optional[str]]:
    global current_screen_gray
    results: List[Tuple[Tuple[int, int], float, str]] = []
    needs_screenshot: bool = any(flag and METHODS[i][0] != "PyAutoGUI Matching" for i, flag in enumerate(selection_flags))
    if needs_screenshot:
        screenshot = pyautogui.screenshot()
        current_screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
    threads: List[threading.Thread] = []
    results_lock = threading.Lock()
    def worker(index: int) -> None:
        method_name, method_func = METHODS[index]
        logging.info(f"--- Running {method_name} for template {template_path} ---")
        res = method_func(template_path)
        if res is not None and isinstance(res, tuple):
            center, score = res
            if center is not None:
                with results_lock:
                    results.append((center, score, method_name))
    for idx, flag in enumerate(selection_flags):
        if flag:
            t = threading.Thread(target=worker, args=(idx,))
            t.daemon = True
            t.start()
            threads.append(t)
    for t in threads:
        t.join()
    current_screen_gray = None
    if not results:
        return None, None, None
    best = max(results, key=lambda x: x[1])
    logging.info("Best match using %s with score %.2f at %s", best[2], best[1], best[0])
    return best[0], best[1], best[2]

def process_template(selection_flags: List[bool], template_path: str) -> None:
    global last_click_time, last_click_coord
    center, score, method_used = find_best_match(selection_flags, template_path)
    if center is not None:
        msg: str = f"Best match for {template_path}: {center} (score: {score} using {method_used})"
        logging.info(msg)
        with match_log_lock:
            match_log.append(msg)
            if len(match_log) > 15:
                match_log[:] = match_log[-15:]
        current_time: float = time.time()
        click_threshold: float = 20  # minimum distance (pixels) to consider distinct click
        should_click: bool = True
        with last_click_lock:
            if last_click_coord is not None:
                dx: int = center[0] - last_click_coord[0]
                dy: int = center[1] - last_click_coord[1]
                dist: float = (dx**2 + dy**2) ** 0.5
                if (current_time - last_click_time < 0.5) and (dist < click_threshold):
                    should_click = False
            if should_click:
                last_click_coord = center
                last_click_time = current_time
        if should_click:
            try:
                # Move to the center and perform a left click using left_click helper
                pyautogui.moveTo(center[0], center[1])
                left_click(center[0], center[1])
                logging.info("Moved to and clicked at %s", center)
            except pyautogui.FailSafeException:
                logging.warning("PyAutoGUI FailSafe triggered; click aborted and ignored.")
        else:
            logging.info("Click suppressed for %s to avoid rapid repeat clicks.", center)
    else:
        logging.info("No valid match found for template %s", template_path)
