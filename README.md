# 🖱️ Virtual Mouse

A real-time hand-gesture virtual mouse built with **Python, OpenCV, MediaPipe and PyAutoGUI**.

The application uses a webcam to detect hand landmarks and converts specific hand gestures into mouse movement, left/right clicks, scrolling, and Windows master-volume control.

---

## ✨ Features

- 🎥 Real-time hand tracking using MediaPipe
- 🖱️ Cursor control using the index finger
- 👆 Left-click gesture
- 👉 Right-click gesture
- ↕️ Gesture-based scrolling
- 🔊 Windows master-volume control
- 📊 Live FPS display
- 🎯 Cursor smoothing for stable movement
- 🔄 Automatic handling when the hand leaves the camera frame
- ⚡ Real-time webcam processing

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| OpenCV | Webcam and image processing |
| MediaPipe | Hand landmark detection |
| NumPy | Mathematical calculations |
| PyAutoGUI | Mouse and scroll control |
| Pycaw | Windows volume control |

---

## 📁 Project Structure

```text
virtual-mouse/
│
├── Main.py
├── HandTrackingModule.py
├── hand_landmarker.task
├── requirements.txt
├── README.md
└── .gitignore

![Virtual Mouse Demo](screenshots/virtual-mouse-demo.png)

## ✨ Features

| Feature | Description |
|---|---|
| 🖱️ Virtual Cursor | Control the mouse cursor using hand movements |
| 👆 Left Click | Perform a left click using a hand gesture |
| 🤚 Right Click | Perform a right click using a hand gesture |
| ↕️ Scrolling | Scroll through pages using hand gestures |
| 🔊 Volume Control | Adjust system volume using thumb and index finger |
| ✋ Hand Tracking | Detect and track 21 hand landmarks in real time |
| 📷 Webcam Control | Uses the webcam for real-time gesture recognition |
| 📊 FPS Display | Shows the current processing frame rate |

## 🖐️ Gesture Controls

| Gesture | Action |
|---|---|
| ☝️ Index + Middle + Ring + Pinky | Cursor mode |
| ☝️ Index + Middle | Scroll mode |
| 👍☝️ Thumb + Index | Volume control |
| 👍 Thumb gesture | Left click |
| 🤙 Pinky gesture | Right click |
| ⌨️ Press `Q` | Exit the application |

## 🛠️ Technology Stack

- **Python** — Core programming language
- **OpenCV** — Webcam and image processing
- **MediaPipe** — Real-time hand landmark detection
- **NumPy** — Numerical processing
- **PyAutoGUI** — Mouse and scrolling control
- **Pycaw** — Windows system volume control