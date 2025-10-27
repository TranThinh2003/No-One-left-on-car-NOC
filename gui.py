import customtkinter as ctk
from PIL import Image
from state_manager import StateManager
from detection import PersonDetector
from notifier import Notifier
import cv2
import time
import datetime
import threading
import numpy as np
import pygame

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class NOCGui:
    def __init__(self, root):
        # Main GUI initialization and state setup
        self.root = root
        self.root.geometry("900x600")
        self.root.minsize(600, 400)
        self.root.maxsize(900, 600)
        self.root.title("NOC")

        self.notifier = Notifier()
        self.state = StateManager()
        self.detector = PersonDetector(model_path="models/yolo11n_320.onnx")
        
        self.vertical_switch_state = False
        self.engine_running = False
        self.uptime_start = None
        
        self.vehicle_stopped_completely = False
        self.door_fully_open = False
        self.door_fully_closed = True
        self.detection_active = False
        self.alarm_was_turned_off = False
        self.current_image = None
        self.last_detected_count = 0 

        self.detection_thread = None
        self.alert_sound_thread = None
        self.auto_open_thread = None 
        self.sos_thread = None
        self.safety_instruction_thread = None
        self.cqcn_thread = None
        self.stop_event = threading.Event()
        self.stop_alert_sound_event = threading.Event()
        self.stop_auto_open_event = threading.Event()
        self.stop_safety_instruction_event = threading.Event()
        self.stop_cqcn_event = threading.Event()
        self.countdown_timer_id = None

        try:
            self.off_switch_img = self.load_image("ui/off_vertical_switch.png")
            self.on_switch_img = self.load_image("ui/on_vertical_switch.png")
        except Exception as e:
            print(f"Error loading images: {e}")
            self.off_switch_img = None
            self.on_switch_img = None

        # GUI layout setup
        self.main_frame = ctk.CTkFrame(root)
        self.main_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.main_frame.rowconfigure(0, weight=0)
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.rowconfigure(2, weight=0)
        
        self.main_frame.columnconfigure(0, weight=0, minsize=100)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.columnconfigure(2, weight=0, minsize=250)

        self.engine_button = ctk.CTkButton(
            self.main_frame, text="Khởi động\n------\nTắt máy", width=60,
            height=60, corner_radius=40, command=self.toggle_engine
        )
        self.engine_button.grid(row=0, column=0, padx=10, pady=(20,10), sticky="nw")

        status_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        status_frame.grid(row=0, column=1, padx=10, pady=(20,10), sticky="ew")
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(status_frame, text="TRẠNG THÁI", font=("Arial", 15, "bold"))
        self.status_label.grid(row=0, column=0, pady=(0,0), sticky="w")
        
        self.status_entry = ctk.CTkEntry(status_frame, height=30, font=("Arial", 18, "bold"))
        self.status_entry.grid(row=1, column=0, pady=(0,5), sticky="ew")
        self.status_entry.insert(0, "Khởi động xe để kích hoạt hệ thống")

        info_frame = ctk.CTkFrame(self.main_frame, fg_color="#f0f0f0", corner_radius=8, border_width=2)
        info_frame.grid(row=0, column=2, padx=10, pady=(20,10), sticky="ne")
        info_frame.columnconfigure(0, weight=1)
        
        time_icon = ctk.CTkLabel(info_frame, text="🕒", font=("Arial", 14), fg_color="transparent")
        time_icon.grid(row=0, column=0, sticky="w", padx=(5,0), pady=(5,0))
        self.time_label = ctk.CTkLabel(
            info_frame, text=datetime.datetime.now().strftime("%H:%M:%S\n%d/%m/%Y"), 
            font=("Arial", 12, "bold"), fg_color="transparent", justify="left"
        )
        self.time_label.grid(row=0, column=1, sticky="w", padx=(0,5), pady=(5,0))
        
        uptime_icon = ctk.CTkLabel(info_frame, text="⏱", font=("Arial", 14), fg_color="transparent")
        uptime_icon.grid(row=1, column=0, sticky="w", padx=(3,0), pady=(0,5))
        uptime_text = ctk.CTkLabel(info_frame, text="System uptime: ", font=("Arial", 12), fg_color="transparent")
        uptime_text.grid(row=1, column=1, sticky="w", padx=(2,0),pady=(0,5))
        self.uptime_label = ctk.CTkLabel(info_frame, text="00:00:00", font=("Arial", 12, "bold"), fg_color="transparent")
        self.uptime_label.grid(row=1, column=2, sticky="w", padx=(0,5),pady=(0,2))

        self.update_clock()

        self.video_label = ctk.CTkLabel(self.main_frame, text="", fg_color="#a0a0a0", corner_radius=8)
        self.video_label.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        self.initial_gray_image = self.create_gray_image(640, 480)
        self.video_label.configure(image=self.initial_gray_image)

        buttons_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        buttons_frame.grid(row=1, column=2, padx=(0,10), pady=(5,0), sticky="n")
        
        button_params = {"width": 90, "height": 40, "corner_radius": 10, "font": ("Arial", 12)}
        
        self.move_button = ctk.CTkButton(buttons_frame, text="Di chuyển", **button_params, state="disabled", command=self.start_moving)
        self.move_button.grid(row=0, column=0, padx=5, pady=5)
        self.stop_button = ctk.CTkButton(buttons_frame, text="Dừng xe", **button_params, state="disabled", command=self.stop_vehicle)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)
        self.close_button = ctk.CTkButton(buttons_frame, text="Đóng cửa", **button_params, state="disabled", command=self.close_door)
        self.close_button.grid(row=1, column=0, padx=5, pady=5)
        self.open_button = ctk.CTkButton(buttons_frame, text="Mở cửa", **button_params, state="disabled", command=self.open_door)
        self.open_button.grid(row=1, column=1, padx=5, pady=5)
        
        self.vertical_switch_button = ctk.CTkButton(
            buttons_frame, image=self.off_switch_img, text="", width=20, height=40,
            fg_color="transparent", hover=None, command=self.toggle_vertical_switch, state="disabled"
        )
        self.vertical_switch_button.grid(row=1, column=2, padx=(5,0), pady=5, sticky="w")
        
        self.door_lock_label = ctk.CTkLabel(buttons_frame, text="🔓", font=("Arial", 24), text_color="gray")
        self.door_lock_label.grid(row=1, column=3, padx=(0,5), pady=5, sticky="w")

        self.turnoff_alarm_button = ctk.CTkButton(buttons_frame, text="📢 Tắt cảnh báo", **button_params, state="disabled", command=self.turn_off_alarm)
        self.turnoff_alarm_button.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        
        scrollable_settings_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="", corner_radius=8)
        scrollable_settings_frame.grid(row=1, column=2, padx=(0,10), pady=(160,10), sticky="nsew")

        self.setting_label = ctk.CTkLabel(scrollable_settings_frame, text="Cài đặt cảnh báo", font=("Arial", 14, "bold"), anchor="w")
        self.setting_label.pack(pady=5, padx=10, anchor="w")
        
        self.auto_open_attempts_spinbox = self._create_spinbox_row_simple(scrollable_settings_frame, label_text="Thử mở cửa tự động", unit_text="lần", default_value="3")
        self.sos_spinbox = self._create_spinbox_row_simple(scrollable_settings_frame, label_text="Gửi SOS và hướng dẫn sau", unit_text="phút", default_value="1")
        self.cqcn_spinbox = self._create_spinbox_row_simple(scrollable_settings_frame, label_text="Gửi tin đến CQCN sau", unit_text="phút", default_value="2")
        
        self.display_label = ctk.CTkLabel(scrollable_settings_frame, text="Hiển thị", font=("Arial", 14, "bold"), anchor="w")
        self.display_label.pack(pady=(10,5), padx=10, anchor="w")
        
        self.fps_checkbox = ctk.CTkCheckBox(scrollable_settings_frame, text="FPS", state="disabled", command=self.update_display_options)
        self.fps_checkbox.select()
        self.fps_checkbox.pack(pady=2, padx=10, anchor="w")
        
        self.bbox_checkbox = ctk.CTkCheckBox(scrollable_settings_frame, text="Bounding box", state="disabled", command=self.update_display_options)
        self.bbox_checkbox.pack(pady=2, padx=10, anchor="w")
        
        self.class_checkbox = ctk.CTkCheckBox(scrollable_settings_frame, text="Class", state="disabled", command=self.update_display_options)
        self.class_checkbox.pack(pady=2, padx=10, anchor="w")
        
        self.score_checkbox = ctk.CTkCheckBox(scrollable_settings_frame, text="Score", state="disabled", command=self.update_display_options)
        self.score_checkbox.pack(pady=2, padx=10, anchor="w")
        
        self.detection_options_checkboxes = [self.bbox_checkbox, self.class_checkbox, self.score_checkbox]

        log_frame = ctk.CTkFrame(self.main_frame, corner_radius=8, fg_color="#f0f0f0")
        log_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.columnconfigure(1, weight=1)

        system_log_status_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        system_log_status_frame.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.log_label = ctk.CTkLabel(system_log_status_frame, text="System Log", anchor="w", font=("Arial", 12, "bold"))
        self.log_label.pack(side="left")

        self.system_log_status_label = ctk.CTkLabel(system_log_status_frame, text="", anchor="w", font=("Arial", 12, "bold"), text_color="orange")
        self.system_log_status_label.pack(side="left", padx=(5, 0))

        self.person_count_label = ctk.CTkLabel(log_frame, text="", anchor="e", font=("Arial", 12, "bold"))
        self.person_count_label.grid(row=0, column=1, padx=10, pady=5, sticky="e")
    
    def _create_spinbox_row_simple(self, parent, label_text, unit_text, default_value="0"):
        # Create a labeled entry row for settings
        spin_frame = ctk.CTkFrame(parent, fg_color="transparent")
        spin_frame.pack(padx=10, pady=(2,2), fill="x")
        label = ctk.CTkLabel(spin_frame, text=label_text, anchor="w", font=("Arial", 12))
        label.pack(side="left")
        unit_label = ctk.CTkLabel(spin_frame, text=unit_text, font=("Arial", 12))
        unit_label.pack(side="right", padx=(5,0))
        entry = ctk.CTkEntry(spin_frame, width=50, justify="center", state="normal")
        entry.pack(side="right")
        entry.insert(0, default_value)
        return entry

    def _set_status(self, text):
        # Update status entry text
        self.status_entry.delete(0, 'end')
        self.status_entry.insert(0, text)

    def _log_and_display(self, message, color="orange"):
        # Log event and update system log label
        self.notifier.log_event(message)
        self.system_log_status_label.configure(text=f"| {message}", text_color=color)

    def _display_countdown_message(self, message):
        # Show countdown message in system log label
        self.system_log_status_label.configure(text=f"| {message}", text_color="orange")

    def _enable_detection_options(self):
        # Enable detection option checkboxes
        for checkbox in self.detection_options_checkboxes:
            checkbox.configure(state="normal")
            
    def _disable_detection_options(self):
        # Disable detection option checkboxes
        for checkbox in self.detection_options_checkboxes:
            checkbox.configure(state="disabled")

    def start_engine(self):
        # Start engine and system, launch preparation thread
        self._set_status("Đang khởi động hệ thống...")
        self.engine_button.configure(state="disabled") 
        self.notifier.setup_session_logger()
        self._log_and_display("Hệ thống đang được khởi động...")
        prepare_thread = threading.Thread(target=self._prepare_and_finalize, daemon=True)
        prepare_thread.start()

    def _prepare_and_finalize(self):
        # Prepare detector and finalize engine start
        success = self.detector.prepare_detector()
        self.root.after(0, self.engine_prepared, success)

    def engine_prepared(self, success):
        # Callback after engine preparation
        if not success:
            self._set_status("Lỗi! Không thể khởi động hệ thống.")
            self._log_and_display("LỖI: Không thể khởi động camera hoặc model.", color="red")
            self.engine_button.configure(state="normal")
            return
        self.engine_running = True
        self.uptime_start = time.time()
        self.stop_event.clear()
        self._set_status("Đã khởi động xe và hệ thống NOC")
        self._log_and_display("Hệ thống đã khởi động thành công.")
        self.enable_controls()
        self.update_display_options()
        self.detection_thread = threading.Thread(
            target=self.detector.process_video,
            args=(self.update_detection_count,),
            kwargs={"stop_event": self.stop_event},
            daemon=True
        )
        self.detection_thread.start()
        threading.Thread(target=self._engine_start_sequence, daemon=True).start()

    def _engine_start_sequence(self):
        # Play startup and idle sounds
        self.notifier.play_startup_sound()
        if self.engine_running:
            self.notifier.play_idle_sound()

    def stop_engine(self):
        # Begin engine/system shutdown
        self._set_status("Đang tắt hệ thống...")
        self.engine_button.configure(state="disabled")
        self._log_and_display("Tắt máy. Kết thúc phiên làm việc.")
        self.notifier.stop_all_sounds()
        cleanup_thread = threading.Thread(target=self._join_threads_and_finalize_shutdown, args=(True,), daemon=True)
        cleanup_thread.start()

    def _join_threads_and_finalize_shutdown(self, play_shutdown_sound=True):
        # Clean up threads and optionally play shutdown sound
        self.notifier.stop_all_sounds()
        self.stop_alert_sound_event.set()
        self.stop_auto_open_event.set()
        self.stop_safety_instruction_event.set()
        self.stop_cqcn_event.set()
        self.stop_event.set()
        if self.countdown_timer_id:
            try: self.root.after_cancel(self.countdown_timer_id)
            except ValueError: pass
            self.countdown_timer_id = None
        threads_to_join = [
            self.alert_sound_thread, self.auto_open_thread, self.sos_thread,
            self.safety_instruction_thread, self.cqcn_thread, self.detection_thread
        ]
        for t in threads_to_join:
            if t and t.is_alive():
                t.join()
        if play_shutdown_sound:
            self.root.after(0, self._finalize_shutdown)
        else:
            self.root.after(500, self.root.destroy)

    def _finalize_shutdown(self):
        # Finalize shutdown and reset UI
        self.notifier.stop_all_sounds() 
        self.notifier.play_engine_off_sound()
        self.root.after(2000, self.engine_stopped)
        
    def engine_stopped(self):
        # Reset state after engine stopped
        self.engine_running = False
        self.uptime_start = None
        self._set_status("Hệ thống đã tắt")
        self.uptime_label.configure(text="00:00:00")
        self.current_image = None
        width, height = self.video_label.winfo_width(), self.video_label.winfo_height()
        if width <= 1 or height <= 1: width, height = 640, 480
        gray_image = self.create_gray_image(width, height)
        self.video_label.configure(image=gray_image, text="", fg_color="#a0a0a0")
        self.vehicle_stopped_completely = False
        self.door_fully_open = False
        self.door_fully_closed = True
        self.detection_active = False
        self.detector.detection_active = False
        self.person_count_label.configure(text="")
        self.system_log_status_label.configure(text="")
        self.disable_controls()
        self.engine_button.configure(state="normal")
        
    def start_moving(self):
        # Set state and UI for vehicle moving
        self.state.start_vehicle()
        self._set_status("Xe đang di chuyển")
        self._log_and_display("Xe đang di chuyển.")
        self.engine_button.configure(state="disabled")
        self.move_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.open_button.configure(state="disabled")
        self.close_button.configure(state="disabled")
        self.vertical_switch_button.configure(state="disabled")
        self.door_lock_label.configure(text_color="gray")
        self.vehicle_stopped_completely = False
        self.door_fully_open = False
        self.door_fully_closed = True
        self.detection_active = False
        self.detector.detection_active = False
        self.alarm_was_turned_off = False 
        self.person_count_label.configure(text="")
        
    def stop_vehicle(self):
        # Set state and UI for vehicle stopping
        self.state.stop_vehicle()
        self._set_status("Xe đang dừng")
        self._log_and_display("Xe đang dừng lại.")
        self.engine_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.move_button.configure(state="normal")
        self.detection_active = False
        self.detector.detection_active = False
        self.person_count_label.configure(text="")
        self._disable_detection_options()
        self.root.after(2000, self.vehicle_stopped_completely_callback)
        
    def vehicle_stopped_completely_callback(self):
        # Callback after vehicle has fully stopped
        self.vehicle_stopped_completely = True
        self._set_status("Xe đã dừng")
        self._log_and_display("Xe đã dừng hẳn.")
        self.stop_button.configure(state="disabled")
        self.open_button.configure(state="normal")
        self.vertical_switch_button.configure(state="disabled")
        self.door_lock_label.configure(text_color="gray")
        
    def open_door(self):
        # Handle door opening logic
        if not self.vehicle_stopped_completely:
            self._set_status("Xe chưa dừng hẳn, không thể mở cửa")
            return
        if self.auto_open_thread and self.auto_open_thread.is_alive():
            self._log_and_display("Hủy mở cửa tự động do người dùng can thiệp.")
            self.stop_auto_open_event.set()
        self.state.open_door()
        self._set_status("Cửa xe đang mở")
        self._log_and_display("Cửa xe đang mở...")
        self.open_button.configure(state="disabled")
        self.close_button.configure(state="normal")
        self.move_button.configure(state="disabled")
        self.vertical_switch_button.configure(state="disabled")
        self.door_lock_label.configure(text_color="gray")
        self.root.after(2000, self.door_opened_completely)
        
    def door_opened_completely(self):
        # Callback after door fully opened
        self.door_fully_open = True
        self.door_fully_closed = False
        self._set_status("Cửa xe đã mở")
        self._log_and_display("Cửa xe đã mở.")
        self.close_button.configure(state="normal")
        if self.detection_active:
            self.turnoff_alarm_button.configure(state="normal")

    def close_door(self):
        # Handle door closing logic
        self.state.close_door()
        self._set_status("Cửa xe đang đóng")
        self._log_and_display("Cửa xe đang đóng...")
        self.open_button.configure(state="disabled")
        self.close_button.configure(state="disabled")
        self.turnoff_alarm_button.configure(state="disabled")
        self.root.after(2000, self.door_closed_completely)
        
    def door_closed_completely(self):
        # Callback after door fully closed
        self.door_fully_closed = True
        self.door_fully_open = False
        self._set_status("Đã đóng cửa")
        self._log_and_display("Cửa xe đã đóng.")
        self.open_button.configure(state="normal")
        self.vertical_switch_button.configure(state="normal")
        self.door_lock_label.configure(text_color="black")
        self.move_button.configure(state="normal")
        if not self.alarm_was_turned_off and not self.detection_active:
            self.root.after(1000, self.start_detection)
        
    def start_detection(self):
        # Start person detection process
        self.detection_active = True
        self.detector.detection_active = True
        self._set_status("Bắt đầu nhận diện...")
        self._log_and_display("Bắt đầu chu trình nhận diện người trên xe.")
        self.open_button.configure(state="normal")
        self.turnoff_alarm_button.configure(state="disabled")
        self._enable_detection_options()
        self._update_countdown(5)

    def _update_countdown(self, remaining_time):
        # Update countdown for alert or action
        if not self.detection_active:
            self.system_log_status_label.configure(text="")
            return
        if remaining_time > 0:
            self._display_countdown_message(f"Phát âm thanh sau {remaining_time}s")
            self.countdown_timer_id = self.root.after(1000, lambda: self._update_countdown(remaining_time - 1))
        else:
            self.countdown_timer_id = None
            self._log_and_display(f"Phát hiện còn {self.last_detected_count} người trên xe.")
            self.person_count_label.configure(text=f"Số người còn trên xe: {self.last_detected_count}")
            self.initiate_alert_sound()

    def initiate_alert_sound(self):
        # Start alert sound thread if needed
        if not self.detection_active: return
        if self.last_detected_count >= 1:
            if not self.auto_open_thread or not self.auto_open_thread.is_alive():
                self._log_and_display("Kích hoạt cảnh báo âm thanh (có người trên xe).")
                self.auto_open_thread = threading.Thread(target=self._auto_open_door_sequence, daemon=True)
                self.auto_open_thread.start()
        else:
            self._log_and_display("Kích hoạt cảnh báo âm thanh (yêu cầu kiểm tra xe).")
        if not self.alert_sound_thread or not self.alert_sound_thread.is_alive():
            self.stop_alert_sound_event.clear()
            self.alert_sound_thread = threading.Thread(target=self._alert_sound_loop, daemon=True)
            self.alert_sound_thread.start()
        
    def _auto_open_door_sequence(self):
        # Attempt to auto-open door with retries
        self.stop_auto_open_event.clear()
        try:
            attempts = int(self.auto_open_attempts_spinbox.get())
            for i in range(1, attempts + 1):
                if self.stop_auto_open_event.is_set(): return
                for countdown in range(10, 0, -1):
                    if self.stop_auto_open_event.is_set(): return
                    self.root.after(0, self._display_countdown_message, f"Mở cửa tự động lần {i} sau {countdown}s...")
                    time.sleep(1)
                if self.stop_auto_open_event.is_set(): return
                is_door_locked = self.vertical_switch_state
                if not is_door_locked:
                    self.root.after(0, self._log_and_display, "Mở cửa tự động thành công.", "green")
                    self.root.after(0, self._simulate_door_opened_successfully)
                    return 
                else:
                    self.root.after(0, self._log_and_display, f"Mở cửa lần {i} thất bại (cửa bị khoá).", "red")
                    time.sleep(2)
            self._log_and_display("Tất cả các lần thử mở cửa đều thất bại.", "red")
            self.sos_thread = threading.Thread(target=self._sos_and_instruction_sequence, daemon=True)
            self.sos_thread.start()
        except (ValueError, ctk.TclError):
             self._log_and_display("Lỗi: giá trị số lần thử không hợp lệ.", "red")
        finally:
            print("Auto-open sequence finished.")

    def _sos_and_instruction_sequence(self):
        # Wait and send SOS, then start safety instructions
        self.stop_safety_instruction_event.clear()
        try:
            wait_minutes = float(self.sos_spinbox.get())
            wait_seconds = int(wait_minutes * 60)
            for remaining in range(wait_seconds, 0, -1):
                if self.stop_safety_instruction_event.is_set(): return
                minutes, seconds = divmod(remaining, 60)
                self.root.after(0, self._display_countdown_message, f"Gửi SOS sau {minutes:02d}:{seconds:02d}...")
                time.sleep(1)
            if self.stop_safety_instruction_event.is_set(): return
            self.root.after(0, self._log_and_display, "Đang gửi tin nhắn SOS...")
            success = self.notifier.send_sos_message()
            if self.stop_safety_instruction_event.is_set(): return
            self.root.after(0, self._log_and_display, "Đã gửi tin nhắn SOS.")
            if success:
                self.root.after(0, self._log_and_display, "Gửi SOS thành công.", "green")
            else:
                self.root.after(0, self._log_and_display, "Gửi SOS thất bại.", "red")
            time.sleep(1)
            self.stop_alert_sound_event.set()
            if self.alert_sound_thread and self.alert_sound_thread.is_alive():
                self.alert_sound_thread.join()
            self.cqcn_thread = threading.Thread(target=self._cqcn_notification_sequence, daemon=True)
            self.cqcn_thread.start()
            self.safety_instruction_thread = threading.Thread(target=self._safety_instruction_loop, daemon=True)
            self.safety_instruction_thread.start()
        finally:
            print("SOS sequence finished initiating other threads.")

    def _safety_instruction_loop(self):
        # Loop to play safety instructions repeatedly
        while not self.stop_safety_instruction_event.is_set():
            self.notifier.play_safety_instructions()
            sound_length = self.notifier.get_sound_length("safety_instructions")
            total_wait_time = sound_length + 2.0
            for _ in range(int(total_wait_time * 10)):
                if self.stop_safety_instruction_event.is_set():
                    self.notifier.stop_alert_sounds()
                    print("Safety instruction loop interrupted.")
                    return
                time.sleep(0.1)
        print("Safety instruction loop stopped.")

    def _cqcn_notification_sequence(self):
        # Wait and notify authorities
        self.stop_cqcn_event.clear()
        try:
            wait_minutes = float(self.cqcn_spinbox.get())
            wait_seconds = int(wait_minutes * 60)
            for remaining in range(wait_seconds, 0, -1):
                if self.stop_cqcn_event.is_set(): return
                minutes, seconds = divmod(remaining, 60)
                self.root.after(0, self._display_countdown_message, f"Gửi tín hiệu đến CQCN sau {minutes:02d}:{seconds:02d}...")
                time.sleep(1)
            if self.stop_cqcn_event.is_set(): return
            self.root.after(0, self._log_and_display, "Hệ thống đã gửi tín hiệu đến Cơ Quan Chức Năng.", "red")
        except (ValueError, ctk.TclError):
            self._log_and_display("Lỗi: giá trị phút CQCN không hợp lệ.", "red")
        finally:
            print("CQCN sequence finished.")

    def _simulate_door_opened_successfully(self):
        # Simulate successful auto door open
        if not self.detection_active: return
        self.state.open_door()
        self._set_status("Cửa xe đã được mở tự động")
        self.door_fully_open = True
        self.door_fully_closed = False
        self.open_button.configure(state="disabled")
        self.close_button.configure(state="normal")
        self.turnoff_alarm_button.configure(state="normal")
        self.vertical_switch_button.configure(state="disabled")
        self.door_lock_label.configure(text_color="gray")

    def _alert_sound_loop(self):
        # Loop to play alert or speaker sound
        while not self.stop_alert_sound_event.is_set():
            if not self.notifier.is_alert_sound_playing():
                if self.last_detected_count >= 1:
                    self.notifier.play_alarm()
                else:
                    self.notifier.play_speaker()
                time.sleep(2.0)
            time.sleep(0.1)
        print("Alert sound loop stopped.")
        
    def _update_person_count_label(self, count):
        # Update label showing number of people detected
        if self.detection_active and not self.countdown_timer_id:
            self.person_count_label.configure(text=f"Số người còn trên xe: {count}")
    
    def update_detection_count(self, detected_count, annotated_frame):
        # Callback to update detection count and video
        if self.detection_active:
            self.last_detected_count = detected_count
            self.root.after(0, self._update_person_count_label, detected_count)
        if not self.stop_event.is_set() and annotated_frame is not None:
            label_width, label_height = self.video_label.winfo_width(), self.video_label.winfo_height()
            if label_width > 1 and label_height > 1:
                annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                resized_frame = cv2.resize(annotated_frame, (label_width, label_height))
                img = Image.fromarray(resized_frame)
                self.current_image = ctk.CTkImage(light_image=img, dark_image=img, size=(label_width, label_height))
                self.root.after(0, self.update_video_label)

    def update_video_label(self):
        # Update video label with current image
        if not self.stop_event.is_set() and self.current_image:
            self.video_label.configure(image=self.current_image, text="")

    def update_display_options(self):
        # Update detection display options (FPS, bbox, etc.)
        if self.engine_running:
            self.detector.show_fps = bool(self.fps_checkbox.get())
            self.detector.show_bbox = bool(self.bbox_checkbox.get())
            self.detector.show_class = bool(self.class_checkbox.get())
            self.detector.show_score = bool(self.score_checkbox.get())

    def turn_off_alarm(self):
        # Stop all alarms and reset detection state
        self.stop_alert_sound_event.set()
        self.stop_safety_instruction_event.set()
        self.notifier.stop_alert_sounds()
        self._log_and_display("Tài xế đã nhấn nút Tắt cảnh báo.")
        self.notifier.log_event("Kết thúc nhận diện. Tài xế đã xác nhận xe trống.")
        self._set_status("Cảnh báo đã tắt. Đã kiểm tra không còn người trên xe. Có thể tắt máy xe.")
        self._log_and_display("Cảnh báo đã được tắt.")
        if self.countdown_timer_id:
            try: self.root.after_cancel(self.countdown_timer_id)
            except ValueError: pass
            self.countdown_timer_id = None
        self.stop_auto_open_event.set()
        self.stop_cqcn_event.set()
        self.detection_active = False
        self.detector.detection_active = False
        self.alarm_was_turned_off = True
        self.person_count_label.configure(text="")
        self.turnoff_alarm_button.configure(state="disabled")
        self._disable_detection_options()
        self.move_button.configure(state="disabled")
        self.close_button.configure(state="normal")
        self.open_button.configure(state="disabled")

    def create_gray_image(self, width, height):
        # Create a gray placeholder image
        if width <= 0 or height <= 0: width, height = 1, 1
        gray_array = np.full((height, width, 3), 160, dtype=np.uint8)
        gray_image = Image.fromarray(gray_array)
        return ctk.CTkImage(light_image=gray_image, dark_image=gray_image, size=(width, height))

    def load_image(self, path):
        # Load and resize an image for UI
        try:
            image = Image.open(path).resize((20, 40), Image.LANCZOS)
            return ctk.CTkImage(light_image=image, dark_image=image, size=(20, 40))
        except FileNotFoundError:
            print(f"CẢNH BÁO: Không tìm thấy file UI: {path}")
            return None

    def update_clock(self):
        # Update time and uptime labels
        current_time = datetime.datetime.now().strftime("%H:%M:%S\n%d/%m/%Y")
        self.time_label.configure(text=current_time)
        if self.engine_running and self.uptime_start:
            uptime_seconds = int(time.time() - self.uptime_start)
            uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))
            self.uptime_label.configure(text=f"{uptime_str}")
        self.root.after(1000, self.update_clock)
        
    def toggle_display(self):
        # (Reserved for toggling display options)
        pass
            
    def toggle_vertical_switch(self):
        # Toggle door lock switch state
        if self.vertical_switch_button.cget("state") == "disabled": return
        self.vertical_switch_state = not self.vertical_switch_state
        if self.vertical_switch_state:
            if self.on_switch_img: self.vertical_switch_button.configure(image=self.on_switch_img)
            self.open_button.configure(state="disabled")
            self.door_lock_label.configure(text="🔒")
        else:
            if self.off_switch_img: self.vertical_switch_button.configure(image=self.off_switch_img)
            if self.vehicle_stopped_completely and self.door_fully_closed:
                self.open_button.configure(state="normal")
            self.door_lock_label.configure(text="🔓")
                
    def toggle_engine(self):
        # Toggle engine on/off
        if not self.engine_running: self.start_engine()
        else: self.stop_engine()
        
    def enable_controls(self):
        # Enable main control buttons
        self.engine_button.configure(state="normal")
        self.move_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.close_button.configure(state="disabled")
        self.vertical_switch_button.configure(state="disabled")
        self.turnoff_alarm_button.configure(state="disabled")
        self.door_lock_label.configure(text_color="gray")
        self.fps_checkbox.configure(state="normal")
        self._disable_detection_options()
            
    def disable_controls(self):
        # Disable main control buttons
        operational_controls = [
            self.move_button, self.stop_button, self.open_button, self.close_button, 
            self.vertical_switch_button, self.turnoff_alarm_button,
            self.fps_checkbox,
        ]
        for control in operational_controls: 
            control.configure(state="disabled")
        self._disable_detection_options()
        self.door_lock_label.configure(text_color="gray")


if __name__ == "__main__":
    # Main application entry point
    root = ctk.CTk()
    app = NOCGui(root)
    def on_closing():
        print("Closing application...")
        if app.engine_running:
            app._log_and_display("Ứng dụng bị đóng đột ngột. Tắt máy.")
        app.notifier.stop_all_sounds()
        app._join_threads_and_finalize_shutdown(play_shutdown_sound=False)
        pygame.quit()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()