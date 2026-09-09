"""
Virtual Mouse - Hand Gesture Controller
Version: 1.2.4

Features:
- Real-time hand tracking using MediaPipe Tasks API
- Gesture-based cursor control
- Left click
- Right click
- Scroll control
- Windows master volume control
- Adaptive cursor smoothing
- Cursor dead-zone
- Maximum cursor jump protection
- Gesture confirmation and mode stability
- Click cooldown protection
- Windows volume fallback support
- On-screen diagnostics
- Python 3.14 compatible
- Windows compatible
"""

import cv2
import time
import math
import numpy as np
import pyautogui

from HandTrackingModule import HandDetector


# ============================================================
# WINDOWS VOLUME CONTROL
# ============================================================

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import POINTER, cast

except ImportError:
    AudioUtilities = None
    IAudioEndpointVolume = None
    CLSCTX_ALL = None
    POINTER = None
    cast = None


# ============================================================
# CONFIGURATION
# ============================================================

APP_VERSION = "1.2.4"

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()

FRAME_R_MIN_X = 110
FRAME_R_MAX_X = 620

FRAME_R_MIN_Y = 20
FRAME_R_MAX_Y = 350

CURSOR_DEADZONE = 2.5
MAX_CURSOR_STEP = 100

MIN_SMOOTHING = 0.30
MAX_SMOOTHING = 0.75

CLICK_THRESHOLD = 40
RIGHT_CLICK_THRESHOLD = 50

LEFT_CLICK_COOLDOWN = 0.45
RIGHT_CLICK_COOLDOWN = 0.60

VOLUME_MIN_DISTANCE = 20
VOLUME_MAX_DISTANCE = 200

SCROLL_STEP = 60

# Number of consecutive frames required before
# accepting a new gesture mode.
GESTURE_CONFIRM_FRAMES = 4

SHOW_DEBUG = True


# ============================================================
# GLOBAL STATE
# ============================================================

volume = None

prev_time = 0

last_left_click = 0
last_right_click = 0

last_scroll_time = 0

previous_cursor_x = SCREEN_WIDTH // 2
previous_cursor_y = SCREEN_HEIGHT // 2

smoothed_cursor_x = SCREEN_WIDTH // 2
smoothed_cursor_y = SCREEN_HEIGHT // 2

raw_cursor_x = SCREEN_WIDTH // 2
raw_cursor_y = SCREEN_HEIGHT // 2

current_mode = "NEUTRAL"

# Gesture stability state
candidate_mode = "NEUTRAL"
candidate_mode_count = 0
stable_mode = "NEUTRAL"

fps = 0


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_distance(p1, p2):
    """
    Calculate Euclidean distance between two points.
    """

    return math.hypot(
        p2[0] - p1[0],
        p2[1] - p1[1]
    )


def get_volume_percentage():
    """
    Return current Windows master volume as a percentage.
    """

    if volume is None:
        return None

    try:
        level = volume.GetMasterVolumeLevelScalar()

        return int(
            round(float(level) * 100)
        )

    except Exception:
        return None


def clamp(value, minimum, maximum):
    """
    Clamp a value between minimum and maximum.
    """

    return max(
        minimum,
        min(value, maximum)
    )


def calculate_adaptive_smoothing(distance):
    """
    Calculate adaptive smoothing based on cursor movement.

    Small movements:
        More smoothing

    Large movements:
        Less smoothing
    """

    normalized = np.interp(
        distance,
        [0, 250],
        [MAX_SMOOTHING, MIN_SMOOTHING]
    )

    return float(
        clamp(
            normalized,
            MIN_SMOOTHING,
            MAX_SMOOTHING
        )
    )


def map_cursor_coordinates(x, y):
    """
    Map camera coordinates to screen coordinates.
    """

    x = clamp(
        x,
        FRAME_R_MIN_X,
        FRAME_R_MAX_X
    )

    y = clamp(
        y,
        FRAME_R_MIN_Y,
        FRAME_R_MAX_Y
    )

    mapped_x = np.interp(
        x,
        [
            FRAME_R_MIN_X,
            FRAME_R_MAX_X
        ],
        [
            0,
            SCREEN_WIDTH
        ]
    )

    mapped_y = np.interp(
        y,
        [
            FRAME_R_MIN_Y,
            FRAME_R_MAX_Y
        ],
        [
            0,
            SCREEN_HEIGHT
        ]
    )

    return int(mapped_x), int(mapped_y)


def apply_deadzone(
    target_x,
    target_y,
    current_x,
    current_y
):
    """
    Apply a small dead-zone to prevent cursor jitter.
    """

    dx = target_x - current_x
    dy = target_y - current_y

    if abs(dx) < CURSOR_DEADZONE:
        target_x = current_x

    if abs(dy) < CURSOR_DEADZONE:
        target_y = current_y

    return target_x, target_y


def limit_cursor_jump(
    target_x,
    target_y,
    current_x,
    current_y
):
    """
    Prevent sudden extreme cursor jumps.
    """

    dx = target_x - current_x
    dy = target_y - current_y

    distance = math.hypot(
        dx,
        dy
    )

    if distance <= MAX_CURSOR_STEP:
        return target_x, target_y

    scale = MAX_CURSOR_STEP / distance

    limited_x = (
        current_x
        + dx * scale
    )

    limited_y = (
        current_y
        + dy * scale
    )

    return (
        int(limited_x),
        int(limited_y)
    )


def calculate_cursor_position(
    x,
    y,
    current_x,
    current_y
):
    """
    Calculate stable cursor position using:

    1. Coordinate mapping
    2. Dead-zone
    3. Maximum jump protection
    4. Adaptive smoothing
    """

    target_x, target_y = map_cursor_coordinates(
        x,
        y
    )

    target_x, target_y = apply_deadzone(
        target_x,
        target_y,
        current_x,
        current_y
    )

    target_x, target_y = limit_cursor_jump(
        target_x,
        target_y,
        current_x,
        current_y
    )

    movement_distance = math.hypot(
        target_x - current_x,
        target_y - current_y
    )

    smoothing = calculate_adaptive_smoothing(
        movement_distance
    )

    new_x = (
        current_x
        + (
            target_x - current_x
        ) * (
            1 - smoothing
        )
    )

    new_y = (
        current_y
        + (
            target_y - current_y
        ) * (
            1 - smoothing
        )
    )

    return (
        int(new_x),
        int(new_y)
    )


# ============================================================
# WINDOWS VOLUME INITIALIZATION
# ============================================================

if AudioUtilities is not None:

    try:

        devices = AudioUtilities.GetSpeakers()

        try:

            volume = devices.EndpointVolume

        except Exception:

            interface = devices.Activate(
                IAudioEndpointVolume._iid_,
                CLSCTX_ALL,
                None
            )

            volume = cast(
                interface,
                POINTER(IAudioEndpointVolume)
            )

        print(
            "🔊 Windows volume initialized."
        )

        try:

            min_vol, max_vol, _ = (
                volume.GetVolumeRange()
            )

            print(
                f"Volume range: "
                f"{min_vol:.2f} dB to "
                f"{max_vol:.2f} dB"
            )

        except Exception as e:

            print(
                f"⚠️ Could not read volume range: {e}"
            )

    except Exception as e:

        print(
            f"⚠️ Windows volume initialization failed: {e}"
        )

        volume = None

else:

    print(
        "⚠️ Pycaw not installed. "
        "Windows volume control disabled."
    )


# ============================================================
# CAMERA INITIALIZATION
# ============================================================

cap = cv2.VideoCapture(0)

cap.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    CAMERA_WIDTH
)

cap.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    CAMERA_HEIGHT
)

if not cap.isOpened():

    print(
        "❌ Could not open camera."
    )

    raise SystemExit


# ============================================================
# HAND DETECTOR
# ============================================================

detector = HandDetector(
    maxHands=2,
    detectionCon=0.85,
    trackCon=0.80
)


# ============================================================
# STARTUP INFORMATION
# ============================================================

print()

print("=" * 60)

print(
    "Virtual Mouse - Hand Gesture Controller"
)

print(
    f"Version: {APP_VERSION}"
)

print("=" * 60)

print()

print("Controls:")
print()

print("CURSOR")
print(
    "  Thumb + all four fingers extended"
)
print(
    "  Move index finger to control cursor"
)

print()

print("LEFT CLICK")
print(
    "  Thumb gesture / thumb-index pinch"
)

print()

print("RIGHT CLICK")
print(
    "  Pinky gesture / thumb-pinky pinch"
)

print()

print("VOLUME")
print(
    "  Index finger only"
)
print(
    "  Thumb + index distance controls volume"
)

print()

print("SCROLL")
print(
    "  Index + optional middle finger"
)

print()

print("NEUTRAL")
print(
    "  Any unsupported gesture"
)

print()

print(
    f"Gesture confirmation: "
    f"{GESTURE_CONFIRM_FRAMES} frames"
)

print()

print("Press Q or ESC to exit.")

print()

print("=" * 60)

print()


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, img = cap.read()

    if not success:

        print(
            "⚠️ Failed to read frame."
        )

        continue

    # --------------------------------------------------------
    # MIRROR CAMERA
    # --------------------------------------------------------

    img = cv2.flip(
        img,
        1
    )

    # --------------------------------------------------------
    # HAND DETECTION
    # --------------------------------------------------------

    img = detector.find_hands(
        img,
        draw=True
    )

    lmList = detector.find_position(
        img,
        handNo=0
    )

    # --------------------------------------------------------
    # DEFAULT MODE
    # --------------------------------------------------------

    detected_mode = "NEUTRAL"

    fingers = [
        0,
        0,
        0,
        0,
        0
    ]

    # --------------------------------------------------------
    # PROCESS HAND
    # --------------------------------------------------------

    if len(lmList) != 0:

        # ----------------------------------------------------
        # FINGER DETECTION
        # ----------------------------------------------------

        # Thumb
        if lmList[4][1] > lmList[3][1]:
            fingers[0] = 1
        else:
            fingers[0] = 0

        # Index
        if lmList[8][2] < lmList[6][2]:
            fingers[1] = 1
        else:
            fingers[1] = 0

        # Middle
        if lmList[12][2] < lmList[10][2]:
            fingers[2] = 1
        else:
            fingers[2] = 0

        # Ring
        if lmList[16][2] < lmList[14][2]:
            fingers[3] = 1
        else:
            fingers[3] = 0

        # Pinky
        if lmList[20][2] < lmList[18][2]:
            fingers[4] = 1
        else:
            fingers[4] = 0

        # ----------------------------------------------------
        # FINGER STATES
        # ----------------------------------------------------

        thumb = fingers[0]
        index = fingers[1]
        middle = fingers[2]
        ring = fingers[3]
        pinky = fingers[4]

        # ----------------------------------------------------
        # MODE DETECTION
        # ----------------------------------------------------

        if (
            index == 1
            and middle == 0
            and ring == 0
            and pinky == 0
        ):

            detected_mode = "VOLUME"

        elif (
            index == 1
            and middle in (0, 1)
            and ring == 0
            and pinky == 0
            and thumb == 0
        ):

            detected_mode = "SCROLL"

        elif (
            thumb == 1
            and index == 1
            and middle == 1
            and ring == 1
            and pinky == 1
        ):

            detected_mode = "CURSOR"

        else:

            detected_mode = "NEUTRAL"

        # ----------------------------------------------------
        # GESTURE CONFIRMATION
        # ----------------------------------------------------
        #
        # A new gesture must remain consistent for several
        # consecutive frames before becoming active.
        #
        # This prevents one noisy MediaPipe frame from
        # immediately changing the active mode.
        # ----------------------------------------------------

        if detected_mode == candidate_mode:

            candidate_mode_count += 1

        else:

            candidate_mode = detected_mode
            candidate_mode_count = 1

        if (
            candidate_mode_count
            >= GESTURE_CONFIRM_FRAMES
        ):

            stable_mode = candidate_mode

    else:

        # ----------------------------------------------------
        # NO HAND DETECTED
        # ----------------------------------------------------
        #
        # Immediately stop gesture actions so that an old
        # gesture cannot remain active after the hand leaves
        # the camera frame.
        # ----------------------------------------------------

        detected_mode = "NEUTRAL"

        candidate_mode = "NEUTRAL"

        candidate_mode_count = 0

        stable_mode = "NEUTRAL"

    # --------------------------------------------------------
    # CURRENT TIME
    # --------------------------------------------------------

    current_time = time.time()

    # ========================================================
    # CURSOR MODE
    # ========================================================

    if stable_mode == "CURSOR":

        # ----------------------------------------------------
        # INDEX FINGER TIP
        # ----------------------------------------------------

        index_x = lmList[8][1]
        index_y = lmList[8][2]

        raw_cursor_x, raw_cursor_y = (
            map_cursor_coordinates(
                index_x,
                index_y
            )
        )

        # ----------------------------------------------------
        # CALCULATE STABLE CURSOR
        # ----------------------------------------------------

        (
            smoothed_cursor_x,
            smoothed_cursor_y
        ) = calculate_cursor_position(
            index_x,
            index_y,
            smoothed_cursor_x,
            smoothed_cursor_y
        )

        # ----------------------------------------------------
        # MOVE CURSOR
        # ----------------------------------------------------

        try:

            pyautogui.moveTo(
                smoothed_cursor_x,
                smoothed_cursor_y,
                duration=0
            )

        except Exception as e:

            if SHOW_DEBUG:

                print(
                    f"⚠️ Cursor movement error: {e}"
                )

        # ----------------------------------------------------
        # LEFT CLICK
        # ----------------------------------------------------

        thumb_x = lmList[4][1]
        thumb_y = lmList[4][2]

        wrist_x = lmList[0][1]
        wrist_y = lmList[0][2]

        thumb_palm_distance = get_distance(
            (thumb_x, thumb_y),
            (wrist_x, wrist_y)
        )

        thumb_index_distance = get_distance(
            (lmList[4][1], lmList[4][2]),
            (lmList[8][1], lmList[8][2])
        )

        if (
            thumb_palm_distance
            < CLICK_THRESHOLD
            or
            thumb_index_distance < 35
        ):

            if (
                current_time
                - last_left_click
                >= LEFT_CLICK_COOLDOWN
            ):

                try:

                    pyautogui.click()

                    last_left_click = (
                        current_time
                    )

                except Exception as e:

                    if SHOW_DEBUG:

                        print(
                            f"⚠️ Left click error: {e}"
                        )

        # ----------------------------------------------------
        # RIGHT CLICK
        # ----------------------------------------------------

        pinky_x = lmList[20][1]
        pinky_y = lmList[20][2]

        pinky_palm_distance = get_distance(
            (pinky_x, pinky_y),
            (wrist_x, wrist_y)
        )

        thumb_pinky_distance = get_distance(
            (lmList[4][1], lmList[4][2]),
            (lmList[20][1], lmList[20][2])
        )

        if (
            pinky_palm_distance
            < RIGHT_CLICK_THRESHOLD
            or
            thumb_pinky_distance < 40
        ):

            if (
                current_time
                - last_right_click
                >= RIGHT_CLICK_COOLDOWN
            ):

                try:

                    pyautogui.rightClick()

                    last_right_click = (
                        current_time
                    )

                except Exception as e:

                    if SHOW_DEBUG:

                        print(
                            f"⚠️ Right click error: {e}"
                        )

    # ========================================================
    # SCROLL MODE
    # ========================================================

    elif stable_mode == "SCROLL":

        current_time = time.time()

        if (
            current_time
            - last_scroll_time
            >= 0.08
        ):

            # ------------------------------------------------
            # INDEX FINGER Y POSITION
            # ------------------------------------------------

            index_y = lmList[8][2]

            # ------------------------------------------------
            # MIDDLE FINGER Y POSITION
            # ------------------------------------------------

            middle_y = lmList[12][2]

            # ------------------------------------------------
            # SCROLL CENTER
            # ------------------------------------------------

            center_y = (
                FRAME_R_MIN_Y
                + FRAME_R_MAX_Y
            ) / 2

            # ------------------------------------------------
            # SCROLL UP
            # ------------------------------------------------

            if index_y < center_y - 35:

                try:

                    pyautogui.scroll(
                        1
                    )

                except Exception as e:

                    if SHOW_DEBUG:

                        print(
                            f"⚠️ Scroll error: {e}"
                        )

            # ------------------------------------------------
            # SCROLL DOWN
            # ------------------------------------------------

            elif index_y > center_y + 35:

                try:

                    pyautogui.scroll(
                        -1
                    )

                except Exception as e:

                    if SHOW_DEBUG:

                        print(
                            f"⚠️ Scroll error: {e}"
                        )

            last_scroll_time = (
                current_time
            )

    # ========================================================
    # VOLUME MODE
    # ========================================================

    elif stable_mode == "VOLUME":

        # ----------------------------------------------------
        # THUMB + INDEX DISTANCE
        # ----------------------------------------------------

        thumb_x = lmList[4][1]
        thumb_y = lmList[4][2]

        index_x = lmList[8][1]
        index_y = lmList[8][2]

        distance = get_distance(
            (thumb_x, thumb_y),
            (index_x, index_y)
        )

        # ----------------------------------------------------
        # VOLUME CONTROL
        # ----------------------------------------------------

        if volume is not None:

            try:

                min_vol, max_vol, _ = (
                    volume.GetVolumeRange()
                )

                volume_level = np.interp(
                    distance,
                    [
                        VOLUME_MIN_DISTANCE,
                        VOLUME_MAX_DISTANCE
                    ],
                    [
                        min_vol,
                        max_vol
                    ]
                )

                volume_level = clamp(
                    volume_level,
                    min_vol,
                    max_vol
                )

                volume.SetMasterVolumeLevel(
                    float(volume_level),
                    None
                )

            except Exception as e:

                if SHOW_DEBUG:

                    print(
                        f"⚠️ Volume control error: {e}"
                    )

        # ----------------------------------------------------
        # DISPLAY VOLUME DISTANCE
        # ----------------------------------------------------

        cv2.putText(
            img,
            f"Distance: {int(distance)}",
            (15, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2
        )

    # ========================================================
    # NEUTRAL MODE
    # ========================================================

    elif stable_mode == "NEUTRAL":

        pass

    # ========================================================
    # MODE UPDATE
    # ========================================================

    current_mode = stable_mode

    # ========================================================
    # FPS CALCULATION
    # ========================================================

    current_time = time.time()

    if prev_time != 0:

        time_difference = (
            current_time
            - prev_time
        )

        if time_difference > 0:

            fps = 1 / time_difference

    prev_time = current_time

    # ========================================================
    # HEADER BACKGROUND
    # ========================================================

    cv2.rectangle(
        img,
        (0, 0),
        (CAMERA_WIDTH, 95),
        (0, 0, 0),
        -1
    )

    # ========================================================
    # MODE DISPLAY
    # ========================================================

    cv2.putText(
        img,
        f"MODE: {current_mode}",
        (15, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    # ========================================================
    # FPS DISPLAY
    # ========================================================

    cv2.putText(
        img,
        f"FPS: {int(fps)}",
        (430, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    # ========================================================
    # VOLUME STATUS
    # ========================================================

    if volume is not None:

        current_volume = (
            get_volume_percentage()
        )

        if current_volume is not None:

            volume_status = (
                f"VOL: {current_volume}%"
            )

        else:

            volume_status = "VOL: OK"

    else:

        volume_status = "VOL: OFF"

    cv2.putText(
        img,
        volume_status,
        (500, 78),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    # ========================================================
    # VERSION DISPLAY
    # ========================================================

    cv2.putText(
        img,
        f"v{APP_VERSION}",
        (15, 78),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )

    # ========================================================
    # DEBUG INFORMATION
    # ========================================================

    if SHOW_DEBUG:

        # ----------------------------------------------------
        # SCREEN RESOLUTION
        # ----------------------------------------------------

        cv2.putText(
            img,
            f"Screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT}",
            (15, 155),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1
        )

        # ----------------------------------------------------
        # CURSOR POSITION
        # ----------------------------------------------------

        cv2.putText(
            img,
            (
                f"Cursor: "
                f"{smoothed_cursor_x},"
                f"{smoothed_cursor_y}"
            ),
            (15, 175),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1
        )

        # ----------------------------------------------------
        # FINGER STATES
        # ----------------------------------------------------

        cv2.putText(
            img,
            f"Fingers: {fingers}",
            (15, 195),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1
        )

        # ----------------------------------------------------
        # FRAME RANGE X
        # ----------------------------------------------------

        cv2.putText(
            img,
            (
                f"Frame X: "
                f"{FRAME_R_MIN_X}-"
                f"{FRAME_R_MAX_X}"
            ),
            (15, 215),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1
        )

        # ----------------------------------------------------
        # FRAME RANGE Y
        # ----------------------------------------------------

        cv2.putText(
            img,
            (
                f"Frame Y: "
                f"{FRAME_R_MIN_Y}-"
                f"{FRAME_R_MAX_Y}"
            ),
            (15, 235),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1
        )

        # ----------------------------------------------------
        # GESTURE CONFIRMATION STATUS
        # ----------------------------------------------------

        cv2.putText(
            img,
            (
                f"Gesture: "
                f"{candidate_mode} "
                f"{candidate_mode_count}/"
                f"{GESTURE_CONFIRM_FRAMES}"
            ),
            (15, 255),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1
        )

    # ========================================================
    # CONTROL GUIDE
    # ========================================================

    cv2.putText(
        img,
        "Q / ESC = EXIT",
        (420, 125),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (255, 255, 255),
        1
    )

    # ========================================================
    # SHOW WINDOW
    # ========================================================

    cv2.imshow(
        "Virtual Mouse",
        img
    )

    # ========================================================
    # KEYBOARD CONTROL
    # ========================================================

    key = cv2.waitKey(1) & 0xFF

    if (
        key == ord("q")
        or key == 27
    ):

        break


# ============================================================
# CLEANUP
# ============================================================

print()

print(
    "Shutting down Virtual Mouse..."
)

cap.release()

cv2.destroyAllWindows()

print(
    "Virtual Mouse stopped cleanly."
)