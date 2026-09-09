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