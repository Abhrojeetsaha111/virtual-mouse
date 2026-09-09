import os
import cv2
import mediapipe as mp


class HandDetector:
    def __init__(self, mode=False, maxHands=2, detectionCon=0.5, trackCon=0.5):
        self.mode = mode
        self.maxHands = maxHands
        self.detectionCon = detectionCon
        self.trackCon = trackCon

        # ---------------------------------------------------------
        # MediaPipe 1.0.1 - Tasks API
        # ---------------------------------------------------------

        self.BaseOptions = mp.tasks.BaseOptions
        self.HandLandmarker = mp.tasks.vision.HandLandmarker
        self.HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
        self.RunningMode = mp.tasks.vision.RunningMode

        # Find hand_landmarker.task in the same folder as this file
        module_folder = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(
            module_folder,
            "hand_landmarker.task"
        )

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"\nHand model not found!\n"
                f"Expected location:\n{self.model_path}\n\n"
                f"Make sure 'hand_landmarker.task' is in the "
                f"same folder as HandTrackingModule.py."
            )

        # ---------------------------------------------------------
        # Configure MediaPipe Hand Landmarker
        # ---------------------------------------------------------

        self.options = self.HandLandmarkerOptions(
            base_options=self.BaseOptions(
                model_asset_path=self.model_path
            ),
            running_mode=self.RunningMode.IMAGE,
            num_hands=self.maxHands,
            min_hand_detection_confidence=self.detectionCon,
            min_hand_presence_confidence=self.detectionCon,
            min_tracking_confidence=self.trackCon
        )

        # Create detector
        self.hands = self.HandLandmarker.create_from_options(
            self.options
        )

        self.results = None

        # MediaPipe hand connections
        self.connections = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 4),

            (0, 5),
            (5, 6),
            (6, 7),
            (7, 8),

            (5, 9),
            (9, 10),
            (10, 11),
            (11, 12),

            (9, 13),
            (13, 14),
            (14, 15),
            (15, 16),

            (13, 17),
            (17, 18),
            (18, 19),
            (19, 20),

            (0, 17)
        ]

    # -------------------------------------------------------------
    # Detect hands
    # -------------------------------------------------------------

    def find_hands(self, img, draw=True):

        if img is None:
            return img

        # OpenCV uses BGR
        # MediaPipe expects RGB
        imgRGB = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2RGB
        )

        # Create MediaPipe image
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=imgRGB
        )

        # Run hand detection
        self.results = self.hands.detect(mp_image)

        # ---------------------------------------------------------
        # Draw landmarks
        # ---------------------------------------------------------

        if draw and self.results is not None:

            if self.results.hand_landmarks:

                h, w, _ = img.shape

                for hand_landmarks in self.results.hand_landmarks:

                    # Draw connections
                    for start, end in self.connections:

                        x1 = int(
                            hand_landmarks[start].x * w
                        )
                        y1 = int(
                            hand_landmarks[start].y * h
                        )

                        x2 = int(
                            hand_landmarks[end].x * w
                        )
                        y2 = int(
                            hand_landmarks[end].y * h
                        )

                        cv2.line(
                            img,
                            (x1, y1),
                            (x2, y2),
                            (0, 255, 0),
                            2
                        )

                    # Draw landmark points
                    for landmark in hand_landmarks:

                        x = int(
                            landmark.x * w
                        )
                        y = int(
                            landmark.y * h
                        )

                        cv2.circle(
                            img,
                            (x, y),
                            5,
                            (255, 0, 255),
                            cv2.FILLED
                        )

        return img

    # -------------------------------------------------------------
    # Get landmark positions
    # -------------------------------------------------------------

    def find_position(self, img, handNo=0, draw=True):

        lmList = []

        # No detection yet
        if self.results is None:
            return lmList

        # No hands detected
        if not self.results.hand_landmarks:
            return lmList

        # Requested hand doesn't exist
        if handNo < 0 or handNo >= len(
            self.results.hand_landmarks
        ):
            return lmList

        myHand = self.results.hand_landmarks[handNo]

        # ---------------------------------------------------------
        # A complete MediaPipe hand contains 21 landmarks.
        # Do not return incomplete data.
        # ---------------------------------------------------------

        if len(myHand) < 21:
            return lmList

        h, w, _ = img.shape

        for landmark_id, landmark in enumerate(myHand):

            cx = int(
                landmark.x * w
            )

            cy = int(
                landmark.y * h
            )

            lmList.append([
                landmark_id,
                cx,
                cy
            ])

            if draw:

                cv2.circle(
                    img,
                    (cx, cy),
                    5,
                    (255, 0, 255),
                    cv2.FILLED
                )

        # Safety check
        if len(lmList) != 21:
            return []

        return lmList

    # -------------------------------------------------------------
    # Release MediaPipe resources
    # -------------------------------------------------------------

    def close(self):
        try:
            self.hands.close()
        except Exception:
            pass