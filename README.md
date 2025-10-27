# AI-Powered Child Presence Detection System (NOC)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An embedded computer vision system designed to prevent child heatstroke deaths in vehicles. This project was developed as a graduation thesis at Van Lang University, focusing on creating a practical, low-cost, and real-time solution for a critical safety issue.

The system utilizes a lightweight deep learning model deployed on a single-board computer (Orange Pi 5) to monitor the interior of a vehicle. If a child is detected after the vehicle has been parked and locked, the system activates a multi-stage alert mechanism to notify the driver, parents, or authorities.

## Key Features

*   **Real-Time Child Detection:** Employs the optimized YOLOv11n model to accurately detect human presence from a live video stream.
*   **Embedded System Deployment:** Specifically engineered to run efficiently on the **Orange Pi 5**, ensuring low power consumption and a small form factor suitable for in-vehicle installation.
*   **High-Performance Inference:** Achieves real-time processing speeds, making the alert system responsive and reliable in critical situations.
*   **Automated Alert System:** Features a simulated multi-stage alert logic, including audio warnings and SOS notifications, managed through a central state controller.
*   **User-Friendly Interface:** A simple GUI built to display the live detection feed and system status.

## Demo

## Performance Highlights

After a comprehensive benchmark of SSDLite, NanoDet-plus, and YOLOv11, the **YOLOv11n** model was selected for its superior balance of speed and accuracy on edge hardware.

| Metric                  | Performance                |
| ----------------------- | -------------------------- |
| **Model**               | YOLOv11n (320x320 input)   |
| **Accuracy (mAP@50:95)**| **40.73%**                 |
| **Inference Speed**     | **18.84 FPS** (on Orange Pi 5) |

This performance exceeds the project's real-time requirements (≥ 15 FPS) while maintaining reliable detection accuracy.

## Technology Stack

*   **AI / Deep Learning:** PyTorch, ONNX Runtime
*   **Computer Vision:** OpenCV
*   **Hardware:** Orange Pi 5
*   **Language:** Python
*   **GUI:** Tkinter (or similar Python GUI library)

## Getting Started

Follow these instructions to set up and run the project on your local machine.

#### **1. Prerequisites**

Make sure you have Python 3.8+ and Git installed.

#### **2. Installation & Setup**

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/TranThinh2003/No-One-left-on-car-NOC.git
    cd No-One-left-on-car-NOC
    ```

2.  **Create and activate a virtual environment (Recommended):**
    ```bash
    # Create environment
    python -m venv venv

    # Activate on Windows
    .\venv\Scripts\activate

    # Activate on macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    

#### **3. Running the Application**

To start the system, run the main GUI script:
```bash
python gui.py
