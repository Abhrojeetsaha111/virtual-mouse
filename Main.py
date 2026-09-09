import cv2
import time
import math
import numpy as np
import pyautogui

from pycaw.pycaw import AudioUtilities
from HandTrackingModule import HandDetector


# ============================================================
# VIRTUAL MOUSE v1.2
# ============================================================
#
# Features:
# - Real-time hand tracking
# - Gesture-based cursor control
# - Right click
# - Scrolling
# - Windows volume control
# - FPS display
#
# v1.2 improvements:
# - Adaptive cursor smoothing
# - Cursor dead-zone filtering
# - Maximum cursor jump protection
#
# ============================================================


# ============================================================
# CAMERA
# ============================================================

wCam, hCam = 640, 480

cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, wCam)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, hCam)

if not cap.isOpened():

    print("ERROR: Could not open camera.")
    raise SystemExit


# ============================================================
# HAND DETECTOR
# ============================================================

detector = HandDetector(
    maxHands=2,
    detectionCon=0.85,
    trackCon=0.8
)


# ============================================================
# WINDOWS VOLUME
# ============================================================

try:

    devices = AudioUtilities.GetSpeakers()
    volume = devices.EndpointVolume

    volRange = volume.GetVolumeRange()

    minVol = volRange[0]
    maxVol = volRange[1]

    audio_available = True

except Exception as e:

    print("WARNING: Windows volume control unavailable.")
    print(e)

    volume = None

    minVol = -65
    maxVol = 0

    audio_available = False


# ============================================================
# GENERAL SETTINGS
# ============================================================

hmin = 50
hmax = 200

volBar = 400
volPer = 0
vol = 0

color = (0, 215, 255)

tipIds = [4, 8, 12, 16, 20]

mode = "N"
active = 0

pyautogui.FAILSAFE = False

screenWidth, screenHeight = pyautogui.size()


# ============================================================
# CURSOR SETTINGS - v1.2
# ============================================================

# Camera rectangle used for cursor movement.

FRAME_R_MIN_X = 110
FRAME_R_MAX_X = 620

FRAME_R_MIN_Y = 20
FRAME_R_MAX_Y = 350


# Small movements below this value are ignored.
# This helps reduce hand-tracking jitter.

CURSOR_DEADZONE = 2.5


# Prevents a tracking error from moving the cursor
# an extremely large distance in a single frame.

MAX_CURSOR_STEP = 100


# Adaptive smoothing range.
#
# Slow movement:
# More smoothing = more stable cursor
#
# Fast movement:
# Less smoothing = faster response

MIN_SMOOTHING = 0.30
MAX_SMOOTHING = 0.75


# Current smoothed cursor position.

prev_cursor_x = screenWidth // 2
prev_cursor_y = screenHeight // 2


# Previous raw mapped cursor position.

prev_raw_x = prev_cursor_x
prev_raw_y = prev_cursor_y


# ============================================================
# CLICK SETTINGS
# ============================================================

CLICK_THRESHOLD = 40
RIGHT_CLICK_THRESHOLD = 50

left_click_ready = True
right_click_ready = True


# ============================================================
# FPS
# ============================================================

pTime = time.time()


# ============================================================
# TEXT FUNCTION
# ============================================================

def putText(
    text,
    loc=(250, 450),
    color=(0, 255, 255)
):

    cv2.putText(
        img,
        str(text),
        loc,
        cv2.FONT_HERSHEY_COMPLEX_SMALL,
        3,
        color,
        3
    )


# ============================================================
# FINGER DETECTION
# ============================================================

def get_fingers(lmList):

    # A complete hand must have 21 landmarks.

    if not lmList or len(lmList) < 21:

        return []

    fingers = []

    # --------------------------------------------------------
    # THUMB
    # --------------------------------------------------------

    if lmList[4][1] > lmList[3][1]:

        fingers.append(1)

    else:

        fingers.append(0)

    # --------------------------------------------------------
    # INDEX, MIDDLE, RING, PINKY
    # --------------------------------------------------------

    for i in range(1, 5):

        tip = tipIds[i]
        pip = tip - 2

        if lmList[tip][2] < lmList[pip][2]:

            fingers.append(1)

        else:

            fingers.append(0)

    # --------------------------------------------------------
    # SAFETY
    # --------------------------------------------------------

    if len(fingers) != 5:

        return []

    return fingers


# ============================================================
# ADAPTIVE CURSOR SMOOTHING
# ============================================================

def smooth_cursor(
    target_x,
    target_y,
    previous_x,
    previous_y,
    previous_raw_x,
    previous_raw_y
):
    """
    Adaptive cursor smoothing.

    Slow hand movement:
        More smoothing -> less jitter.

    Fast hand movement:
        Less smoothing -> faster response.
    """

    # --------------------------------------------------------
    # Calculate raw movement
    # --------------------------------------------------------

    raw_dx = target_x - previous_raw_x
    raw_dy = target_y - previous_raw_y

    movement = math.hypot(
        raw_dx,
        raw_dy
    )

    # --------------------------------------------------------
    # Adaptive smoothing
    # --------------------------------------------------------

    smoothing = np.interp(
        movement,
        [0, 80],
        [MAX_SMOOTHING, MIN_SMOOTHING]
    )

    smoothing = float(
        np.clip(
            smoothing,
            MIN_SMOOTHING,
            MAX_SMOOTHING
        )
    )

    # --------------------------------------------------------
    # Smooth cursor position
    # --------------------------------------------------------

    new_x = (
        smoothing * target_x
        +
        (1 - smoothing) * previous_x
    )

    new_y = (
        smoothing * target_y
        +
        (1 - smoothing) * previous_y
    )

    # --------------------------------------------------------
    # Dead-zone filtering
    # --------------------------------------------------------

    if abs(new_x - previous_x) < CURSOR_DEADZONE:

        new_x = previous_x

    if abs(new_y - previous_y) < CURSOR_DEADZONE:

        new_y = previous_y

    # --------------------------------------------------------
    # Maximum cursor movement protection
    # --------------------------------------------------------

    delta_x = new_x - previous_x
    delta_y = new_y - previous_y

    distance = math.hypot(
        delta_x,
        delta_y
    )

    if distance > MAX_CURSOR_STEP:

        scale = MAX_CURSOR_STEP / distance

        new_x = previous_x + delta_x * scale
        new_y = previous_y + delta_y * scale

    # --------------------------------------------------------
    # Screen boundaries
    # --------------------------------------------------------

    new_x = int(
        np.clip(
            new_x,
            0,
            screenWidth - 1
        )
    )

    new_y = int(
        np.clip(
            new_y,
            0,
            screenHeight - 1
        )
    )

    return new_x, new_y


# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        # ====================================================
        # CAMERA FRAME
        # ====================================================

        success, img = cap.read()

        if not success:

            print("Failed to capture frame.")
            break

        # Mirror the webcam.

        img = cv2.flip(
            img,
            1
        )

        # ====================================================
        # HAND DETECTION
        # ====================================================

        img = detector.find_hands(
            img,
            draw=True
        )

        lmList = detector.find_position(
            img,
            draw=False
        )

        # ====================================================
        # FINGER DETECTION
        # ====================================================

        fingers = get_fingers(
            lmList
        )

        # ====================================================
        # MODE SELECTION
        # ====================================================

        if len(fingers) == 5:

            # ------------------------------------------------
            # NEUTRAL
            # ------------------------------------------------

            if (
                fingers == [0, 0, 0, 0, 0]
                and active == 0
            ):

                mode = "N"

            # ------------------------------------------------
            # SCROLL
            # ------------------------------------------------

            elif (
                (
                    fingers == [0, 1, 0, 0, 0]
                    or
                    fingers == [0, 1, 1, 0, 0]
                )
                and active == 0
            ):

                mode = "Scroll"
                active = 1

            # ------------------------------------------------
            # VOLUME
            # ------------------------------------------------

            elif (
                fingers == [1, 1, 0, 0, 0]
                and active == 0
            ):

                mode = "Volume"
                active = 1

            # ------------------------------------------------
            # CURSOR
            # ------------------------------------------------

            elif (
                fingers == [1, 1, 1, 1, 1]
                and active == 0
            ):

                mode = "Cursor"
                active = 1

        # ====================================================
        # SCROLL MODE
        # ====================================================

        if mode == "Scroll":

            putText(
                "Scroll",
                (250, 450),
                (0, 255, 255)
            )

            if len(fingers) == 5:

                if fingers == [0, 1, 1, 0, 0]:

                    x1 = lmList[8][1]
                    y1 = lmList[8][2]

                    x2 = lmList[12][1]
                    y2 = lmList[12][2]

                    # ----------------------------------------
                    # Draw fingertips
                    # ----------------------------------------

                    cv2.circle(
                        img,
                        (x1, y1),
                        10,
                        (0, 255, 0),
                        cv2.FILLED
                    )

                    cv2.circle(
                        img,
                        (x2, y2),
                        10,
                        (0, 255, 0),
                        cv2.FILLED
                    )

                    # ----------------------------------------
                    # Draw line
                    # ----------------------------------------

                    cv2.line(
                        img,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        3
                    )

                    # ----------------------------------------
                    # Scroll direction
                    # ----------------------------------------

                    if abs(y2 - y1) > 50:

                        if y2 > y1:

                            putText(
                                "Scroll Up",
                                (250, 450),
                                (0, 255, 0)
                            )

                            pyautogui.scroll(
                                3
                            )

                        else:

                            putText(
                                "Scroll Down",
                                (250, 450),
                                (0, 0, 255)
                            )

                            pyautogui.scroll(
                                -3
                            )

                    else:

                        putText(
                            "Scroll Ready",
                            (250, 450),
                            (255, 255, 0)
                        )

                elif fingers == [0, 0, 0, 0, 0]:

                    active = 0
                    mode = "N"

            else:

                active = 0
                mode = "N"

        # ====================================================
        # VOLUME MODE
        # ====================================================

        if mode == "Volume":

            putText(
                "Volume",
                (250, 450),
                (0, 255, 255)
            )

            if len(fingers) == 5:

                # ------------------------------------------------
                # Pinky open = leave volume mode
                # ------------------------------------------------

                if fingers[4] == 1:

                    active = 0
                    mode = "N"

                else:

                    # --------------------------------------------
                    # Thumb
                    # --------------------------------------------

                    x1 = lmList[4][1]
                    y1 = lmList[4][2]

                    # --------------------------------------------
                    # Index
                    # --------------------------------------------

                    x2 = lmList[8][1]
                    y2 = lmList[8][2]

                    # --------------------------------------------
                    # Center point
                    # --------------------------------------------

                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2

                    # --------------------------------------------
                    # Draw thumb
                    # --------------------------------------------

                    cv2.circle(
                        img,
                        (x1, y1),
                        10,
                        color,
                        cv2.FILLED
                    )

                    # --------------------------------------------
                    # Draw index
                    # --------------------------------------------

                    cv2.circle(
                        img,
                        (x2, y2),
                        10,
                        color,
                        cv2.FILLED
                    )

                    # --------------------------------------------
                    # Draw connection
                    # --------------------------------------------

                    cv2.line(
                        img,
                        (x1, y1),
                        (x2, y2),
                        color,
                        3
                    )

                    # --------------------------------------------
                    # Center
                    # --------------------------------------------

                    cv2.circle(
                        img,
                        (cx, cy),
                        8,
                        color,
                        cv2.FILLED
                    )

                    # --------------------------------------------
                    # Distance
                    # --------------------------------------------

                    length = math.hypot(
                        x2 - x1,
                        y2 - y1
                    )

                    # --------------------------------------------
                    # Volume mapping
                    # --------------------------------------------

                    vol = np.interp(
                        length,
                        [hmin, hmax],
                        [minVol, maxVol]
                    )

                    # --------------------------------------------
                    # Volume bar
                    # --------------------------------------------

                    volBar = np.interp(
                        vol,
                        [minVol, maxVol],
                        [400, 150]
                    )

                    # --------------------------------------------
                    # Volume percentage
                    # --------------------------------------------

                    volPer = np.interp(
                        vol,
                        [minVol, maxVol],
                        [0, 100]
                    )

                    # --------------------------------------------
                    # Set system volume
                    # --------------------------------------------

                    if audio_available:

                        try:

                            volume.SetMasterVolumeLevel(
                                float(vol),
                                None
                            )

                        except Exception:

                            pass

                    # --------------------------------------------
                    # Minimum indicator
                    # --------------------------------------------

                    if length < 50:

                        cv2.circle(
                            img,
                            (cx, cy),
                            11,
                            (0, 0, 255),
                            cv2.FILLED
                        )

                    # --------------------------------------------
                    # Volume bar outline
                    # --------------------------------------------

                    cv2.rectangle(
                        img,
                        (30, 150),
                        (55, 400),
                        (209, 206, 0),
                        3
                    )

                    # --------------------------------------------
                    # Volume bar fill
                    # --------------------------------------------

                    cv2.rectangle(
                        img,
                        (30, int(volBar)),
                        (55, 400),
                        (215, 255, 127),
                        cv2.FILLED
                    )

                    # --------------------------------------------
                    # Volume percentage
                    # --------------------------------------------

                    cv2.putText(
                        img,
                        f"{int(volPer)}%",
                        (25, 430),
                        cv2.FONT_HERSHEY_COMPLEX,
                        0.9,
                        (209, 206, 0),
                        3
                    )

            else:

                active = 0
                mode = "N"

        # ====================================================
        # CURSOR MODE
        # ====================================================

        if mode == "Cursor":

            putText(
                "Cursor",
                (250, 450),
                (0, 255, 255)
            )

            # ------------------------------------------------
            # Cursor control rectangle
            # ------------------------------------------------

            cv2.rectangle(
                img,
                (
                    FRAME_R_MIN_X,
                    FRAME_R_MIN_Y
                ),
                (
                    FRAME_R_MAX_X,
                    FRAME_R_MAX_Y
                ),
                (255, 255, 255),
                3
            )

            if len(fingers) == 5:

                # ------------------------------------------------
                # Leave cursor mode
                # ------------------------------------------------

                if fingers[1:] == [0, 0, 0, 0]:

                    active = 0
                    mode = "N"

                    left_click_ready = True
                    right_click_ready = True

                else:

                    # =================================================
                    # INDEX FINGER
                    # =================================================

                    x1 = lmList[8][1]
                    y1 = lmList[8][2]

                    # ------------------------------------------------
                    # Draw index fingertip
                    # ------------------------------------------------

                    cv2.circle(
                        img,
                        (x1, y1),
                        10,
                        (0, 255, 0),
                        cv2.FILLED
                    )

                    # =================================================
                    # MAP CAMERA TO SCREEN
                    # =================================================

                    raw_X = int(
                        np.interp(
                            x1,
                            [
                                FRAME_R_MIN_X,
                                FRAME_R_MAX_X
                            ],
                            [
                                0,
                                screenWidth - 1
                            ]
                        )
                    )

                    raw_Y = int(
                        np.interp(
                            y1,
                            [
                                FRAME_R_MIN_Y,
                                FRAME_R_MAX_Y
                            ],
                            [
                                0,
                                screenHeight - 1
                            ]
                        )
                    )

                    # ------------------------------------------------
                    # Clamp raw coordinates
                    # ------------------------------------------------

                    raw_X = int(
                        np.clip(
                            raw_X,
                            0,
                            screenWidth - 1
                        )
                    )

                    raw_Y = int(
                        np.clip(
                            raw_Y,
                            0,
                            screenHeight - 1
                        )
                    )

                    # =================================================
                    # ADAPTIVE SMOOTHING
                    # =================================================

                    X, Y = smooth_cursor(
                        raw_X,
                        raw_Y,
                        prev_cursor_x,
                        prev_cursor_y,
                        prev_raw_x,
                        prev_raw_y
                    )

                    # ------------------------------------------------
                    # Save raw position
                    # ------------------------------------------------

                    prev_raw_x = raw_X
                    prev_raw_y = raw_Y

                    # ------------------------------------------------
                    # Move cursor
                    # ------------------------------------------------

                    pyautogui.moveTo(
                        X,
                        Y
                    )

                    # ------------------------------------------------
                    # Save smoothed position
                    # ------------------------------------------------

                    prev_cursor_x = X
                    prev_cursor_y = Y

                    # =================================================
                    # PALM
                    # =================================================

                    palm_x = lmList[9][1]
                    palm_y = lmList[9][2]

                    # =================================================
                    # LEFT CLICK
                    # =================================================

                    thumb_x = lmList[4][1]
                    thumb_y = lmList[4][2]

                    thumb_palm_distance = math.hypot(
                        thumb_x - palm_x,
                        thumb_y - palm_y
                    )

                    if thumb_palm_distance < CLICK_THRESHOLD:

                        cv2.circle(
                            img,
                            (thumb_x, thumb_y),
                            10,
                            (0, 0, 255),
                            cv2.FILLED
                        )

                        if left_click_ready:

                            pyautogui.click()

                            left_click_ready = False

                    else:

                        left_click_ready = True

                    # =================================================
                    # RIGHT CLICK
                    # =================================================

                    pinky_x = lmList[20][1]
                    pinky_y = lmList[20][2]

                    pinky_palm_distance = math.hypot(
                        pinky_x - palm_x,
                        pinky_y - palm_y
                    )

                    if pinky_palm_distance < RIGHT_CLICK_THRESHOLD:

                        cv2.circle(
                            img,
                            (pinky_x, pinky_y),
                            10,
                            (255, 0, 0),
                            cv2.FILLED
                        )

                        if right_click_ready:

                            pyautogui.rightClick()

                            right_click_ready = False

                    else:

                        right_click_ready = True

            else:

                # ------------------------------------------------
                # Hand disappeared
                # ------------------------------------------------

                active = 0
                mode = "N"

                left_click_ready = True
                right_click_ready = True

        # ====================================================
        # NO HAND
        # ====================================================

        if len(fingers) == 0:

            cv2.putText(
                img,
                "Show your hand",
                (170, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                2
            )

        # ====================================================
        # FPS
        # ====================================================

        cTime = time.time()

        elapsed = cTime - pTime

        if elapsed > 0:

            fps = 1 / elapsed

        else:

            fps = 0

        pTime = cTime

        cv2.putText(
            img,
            f"FPS: {int(fps)}",
            (480, 50),
            cv2.FONT_ITALIC,
            1,
            (255, 0, 0),
            2
        )

        # ====================================================
        # MODE DISPLAY
        # ====================================================

        cv2.putText(
            img,
            f"Mode: {mode}",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        # ====================================================
        # DISPLAY
        # ====================================================

        cv2.imshow(
            "Hand LiveFeed",
            img
        )

        # ====================================================
        # KEYBOARD
        # ====================================================

        key = cv2.waitKey(1) & 0xFF

        # Q = quit

        if key == ord("q"):

            break


# ============================================================
# KEYBOARD INTERRUPT
# ============================================================

except KeyboardInterrupt:

    print("\nProgram stopped by user.")


# ============================================================
# UNEXPECTED ERROR
# ============================================================

except Exception as e:

    print("\nUnexpected error:")
    print(type(e).__name__)
    print(e)


# ============================================================
# CLEANUP
# ============================================================

finally:

    cap.release()

    cv2.destroyAllWindows()

    try:

        detector.close()

    except Exception:

        pass

    print("Virtual Mouse stopped.")