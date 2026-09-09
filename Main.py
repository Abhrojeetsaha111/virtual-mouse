import cv2
import time
import math
import numpy as np
import pyautogui

from pycaw.pycaw import AudioUtilities
from HandTrackingModule import HandDetector


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
# SETTINGS
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

SMOOTHING_FACTOR = 0.5

prev_cursor_x = screenWidth // 2
prev_cursor_y = screenHeight // 2

CLICK_THRESHOLD = 40
RIGHT_CLICK_THRESHOLD = 50

left_click_ready = True
right_click_ready = True

pTime = time.time()


# ============================================================
# TEXT
# ============================================================

def putText(text, loc=(250, 450), color=(0, 255, 255)):

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

    # IMPORTANT:
    # A complete hand must have 21 landmarks.

    if not lmList or len(lmList) < 21:
        return []

    fingers = []

    # --------------------------------------------------------
    # Thumb
    # --------------------------------------------------------

    if lmList[4][1] > lmList[3][1]:

        fingers.append(1)

    else:

        fingers.append(0)

    # --------------------------------------------------------
    # Index, Middle, Ring, Pinky
    # --------------------------------------------------------

    for i in range(1, 5):

        tip = tipIds[i]
        pip = tip - 2

        if lmList[tip][2] < lmList[pip][2]:

            fingers.append(1)

        else:

            fingers.append(0)

    # --------------------------------------------------------
    # Safety
    # --------------------------------------------------------

    if len(fingers) != 5:
        return []

    return fingers


# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        # ----------------------------------------------------
        # CAMERA FRAME
        # ----------------------------------------------------

        success, img = cap.read()

        if not success:

            print("Failed to capture frame.")
            break

        # Mirror camera
        img = cv2.flip(img, 1)

        # ----------------------------------------------------
        # HAND DETECTION
        # ----------------------------------------------------

        img = detector.find_hands(
            img,
            draw=True
        )

        lmList = detector.find_position(
            img,
            draw=False
        )

        # ----------------------------------------------------
        # FINGERS
        # ----------------------------------------------------

        fingers = get_fingers(lmList)

        # ====================================================
        # MODE SELECTION
        # ====================================================

        if len(fingers) == 5:

            # ------------------------------------------------
            # Neutral
            # ------------------------------------------------

            if (
                fingers == [0, 0, 0, 0, 0]
                and active == 0
            ):

                mode = "N"

            # ------------------------------------------------
            # Scroll
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
            # Volume
            # ------------------------------------------------

            elif (
                fingers == [1, 1, 0, 0, 0]
                and active == 0
            ):

                mode = "Volume"
                active = 1

            # ------------------------------------------------
            # Cursor
            # ------------------------------------------------

            elif (
                fingers == [1, 1, 1, 1, 1]
                and active == 0
            ):

                mode = "Cursor"
                active = 1

        # ====================================================
        # SCROLL
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

                    cv2.line(
                        img,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        3
                    )

                    if abs(y2 - y1) > 50:

                        if y2 > y1:

                            putText(
                                "Scroll Up",
                                (250, 450),
                                (0, 255, 0)
                            )

                            pyautogui.scroll(3)

                        else:

                            putText(
                                "Scroll Down",
                                (250, 450),
                                (0, 0, 255)
                            )

                            pyautogui.scroll(-3)

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

                # Hand disappeared
                active = 0
                mode = "N"

        # ====================================================
        # VOLUME
        # ====================================================

        if mode == "Volume":

            putText(
                "Volume",
                (250, 450),
                (0, 255, 255)
            )

            # NEVER access fingers[-1] unless we have 5 fingers
            if len(fingers) == 5:

                # Pinky open = leave volume mode
                if fingers[4] == 1:

                    active = 0
                    mode = "N"

                else:

                    x1 = lmList[4][1]
                    y1 = lmList[4][2]

                    x2 = lmList[8][1]
                    y2 = lmList[8][2]

                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2

                    cv2.circle(
                        img,
                        (x1, y1),
                        10,
                        color,
                        cv2.FILLED
                    )

                    cv2.circle(
                        img,
                        (x2, y2),
                        10,
                        color,
                        cv2.FILLED
                    )

                    cv2.line(
                        img,
                        (x1, y1),
                        (x2, y2),
                        color,
                        3
                    )

                    cv2.circle(
                        img,
                        (cx, cy),
                        8,
                        color,
                        cv2.FILLED
                    )

                    # ----------------------------------------
                    # Distance between thumb and index
                    # ----------------------------------------

                    length = math.hypot(
                        x2 - x1,
                        y2 - y1
                    )

                    vol = np.interp(
                        length,
                        [hmin, hmax],
                        [minVol, maxVol]
                    )

                    volBar = np.interp(
                        vol,
                        [minVol, maxVol],
                        [400, 150]
                    )

                    volPer = np.interp(
                        vol,
                        [minVol, maxVol],
                        [0, 100]
                    )

                    # ----------------------------------------
                    # Set volume
                    # ----------------------------------------

                    if audio_available:

                        try:

                            volume.SetMasterVolumeLevel(
                                float(vol),
                                None
                            )

                        except Exception:
                            pass

                    # ----------------------------------------
                    # Minimum indicator
                    # ----------------------------------------

                    if length < 50:

                        cv2.circle(
                            img,
                            (cx, cy),
                            11,
                            (0, 0, 255),
                            cv2.FILLED
                        )

                    # ----------------------------------------
                    # Volume bar
                    # ----------------------------------------

                    cv2.rectangle(
                        img,
                        (30, 150),
                        (55, 400),
                        (209, 206, 0),
                        3
                    )

                    cv2.rectangle(
                        img,
                        (30, int(volBar)),
                        (55, 400),
                        (215, 255, 127),
                        cv2.FILLED
                    )

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
        # CURSOR
        # ====================================================

        if mode == "Cursor":

            putText(
                "Cursor",
                (250, 450),
                (0, 255, 255)
            )

            cv2.rectangle(
                img,
                (110, 20),
                (620, 350),
                (255, 255, 255),
                3
            )

            if len(fingers) == 5:

                # ------------------------------------------------
                # Release cursor mode
                # ------------------------------------------------

                if fingers[1:] == [0, 0, 0, 0]:

                    active = 0
                    mode = "N"

                    left_click_ready = True
                    right_click_ready = True

                else:

                    # ------------------------------------------------
                    # Index finger
                    # ------------------------------------------------

                    x1 = lmList[8][1]
                    y1 = lmList[8][2]

                    # ------------------------------------------------
                    # Screen coordinates
                    # ------------------------------------------------

                    X = int(
                        np.interp(
                            x1,
                            [110, 620],
                            [0, screenWidth - 1]
                        )
                    )

                    Y = int(
                        np.interp(
                            y1,
                            [20, 350],
                            [0, screenHeight - 1]
                        )
                    )

                    # ------------------------------------------------
                    # Smooth cursor
                    # ------------------------------------------------

                    X = int(
                        SMOOTHING_FACTOR * X
                        +
                        (1 - SMOOTHING_FACTOR)
                        * prev_cursor_x
                    )

                    Y = int(
                        SMOOTHING_FACTOR * Y
                        +
                        (1 - SMOOTHING_FACTOR)
                        * prev_cursor_y
                    )

                    prev_cursor_x = X
                    prev_cursor_y = Y

                    # ------------------------------------------------
                    # Move mouse
                    # ------------------------------------------------

                    pyautogui.moveTo(
                        X,
                        Y
                    )

                    # ------------------------------------------------
                    # Palm
                    # ------------------------------------------------

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

                # Hand disappeared
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

        # Q = quit
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break


except KeyboardInterrupt:

    print("\nProgram stopped by user.")


except Exception as e:

    print("\nUnexpected error:")
    print(type(e).__name__)
    print(e)


finally:

    cap.release()

    cv2.destroyAllWindows()

    try:
        detector.close()
    except Exception:
        pass

    print("Virtual Mouse stopped.")