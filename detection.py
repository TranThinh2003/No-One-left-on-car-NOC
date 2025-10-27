import cv2
import supervision as sv
from ultralytics import YOLO
import time

class PersonDetector:
    def __init__(self, model_path):
        # Path to the YOLO model file
        self.model_path = model_path
        self.model = None
        
        # Initialize tracking and annotation utilities from supervision
        self.tracker = sv.ByteTrack(frame_rate=30)
        self.smoother = sv.DetectionsSmoother()
        self.bbox_annotator = sv.BoxAnnotator(thickness=2)
        self.label_annotator = sv.LabelAnnotator()
        self.cap = None  # OpenCV VideoCapture object
        
        # Detection and display state flags
        self.detection_active = False
        self.video_running = False
        self.show_fps = False
        self.show_bbox = False
        self.show_class = False
        self.show_score = False

    def prepare_detector(self):
        """Loads the model, initializes the webcam, and runs a warm-up prediction."""
        print("Preparing detector...")
        if self.model is None:
            # Load YOLO model for detection
            self.model = YOLO(self.model_path, task="detect")
        
        if self.cap is None:
            # Open webcam (device 0)
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("Error: Cannot open webcam")
                self.cap = None
                return False
            
        print("Warming up the model...")
        ret, frame = self.cap.read()
        if ret:
            # Run a dummy prediction to warm up the model
            self.model.predict(frame)
            print("Model warm-up complete.")
        else:
            print("Warning: Could not grab a frame for warm-up.")
        print("Detector prepared.")
        return True

    def release_detector(self):
        """Releases the webcam and model resources."""
        self.video_running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        print("Detector released.")
        time.sleep(0.1)

    def process_video(self, callback_update_count, *, stop_event=None):
        """
        Processes the video feed, runs detection, and calls the callback with the count and frame.
        Assumes prepare_detector has been called.
        """
        if self.cap is None or not self.cap.isOpened():
            print("Error: Webcam not prepared. Call prepare_detector() first.")
            callback_update_count(0, None)
            return

        self.video_running = True
        detected_count = 0
        fps_start_time = time.time()
        fps_frame_count = 0
        display_fps = 0.0

        if stop_event is None:
            print("Error: stop_event is required for process_video.")
            self.release_detector()
            return
            
        while self.video_running and not stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                print("Warning: Failed to grab frame")
                time.sleep(0.1) 
                continue

            if self.detection_active:
                # Run detection and tracking
                result = self.model.predict(frame, conf=0.35)[0]
                detections = sv.Detections.from_ultralytics(result).with_nms(threshold=0.3, class_agnostic=False)
                detections = self.tracker.update_with_detections(detections)
                detections = self.smoother.update_with_detections(detections)
                # Count only class_id == 0 (usually 'person' in COCO)
                detected_count = len(detections[detections.class_id == 0])
            else:
                detected_count = 0
                detections = sv.Detections.empty()

            annotated_frame = frame.copy()
            
            # Draw bounding boxes if enabled
            if self.show_bbox and self.detection_active:
                annotated_frame = self.bbox_annotator.annotate(annotated_frame, detections)
            
            # Draw class/score labels if enabled
            if (self.show_class or self.show_score) and self.detection_active:
                labels = [
                    f"{self.model.names[class_id]}{' ' + f'{confidence:0.2f}' if self.show_score else ''}"
                    for class_id, confidence in zip(detections.class_id, detections.confidence)
                ]
                annotated_frame = self.label_annotator.annotate(annotated_frame, detections, labels)
            
            # FPS calculation
            fps_frame_count += 1
            elapsed_time = time.time() - fps_start_time
            if elapsed_time > 1.0:
                display_fps = fps_frame_count / elapsed_time
                fps_frame_count = 0
                fps_start_time = time.time()

            # Draw FPS on frame if enabled
            if self.show_fps:
                fps_text = f"FPS: {display_fps:.1f}"
                font_face = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.8
                font_thickness = 2
                text_color = (255, 255, 255)  
                bg_color = (0, 0, 0)          
                margin = 70
                padding = 10

                (text_w, text_h), baseline = cv2.getTextSize(fps_text, font_face, font_scale, font_thickness)

                text_x = margin
                text_y = text_h + 60 

                rect_x1 = text_x - padding
                rect_y1 = text_y - text_h - baseline - padding
                rect_x2 = text_x + text_w + padding
                rect_y2 = text_y + padding

                cv2.rectangle(annotated_frame, (rect_x1, rect_y1), (rect_x2, rect_y2), bg_color, -1)
                cv2.putText(annotated_frame, fps_text, (text_x, text_y), 
                            font_face, font_scale, text_color, font_thickness, cv2.LINE_AA)

            # Call the callback with the current count and frame
            callback_update_count(detected_count, annotated_frame)
        
        self.release_detector()