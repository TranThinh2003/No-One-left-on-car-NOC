import logging
import pygame
import datetime
import os
import requests
import threading
import time

# --- SLACK configuration ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
if not SLACK_BOT_TOKEN:
    print("WARNING: SLACK_BOT_TOKEN is not set in .env. SOS feature will not work.")

# List of SLACK user IDs to send messages to
SLACK_USER_IDS_LIST = ["YOUR_USER_ID_HERE"]  # Replace with actual user IDs
MESSAGE_TEXT_TEMPLATE = "Emergency alert from NOC system! Someone is trapped inside. Please check immediately!"

SPAM_COUNT = 5
DELAY_SECONDS = 3

class Notifier:
    def __init__(self):
        self.logger = None

        # Ensure log and sound directories exist
        if not os.path.exists('noc_logs'):
            os.makedirs('noc_logs')
        
        if not os.path.exists('sounds'):
            os.makedirs('sounds')
            print("WARNING: 'sounds' directory did not exist, created. Please add sound files.")

        try:
            # Initialize pygame mixer for sound
            pygame.mixer.init(frequency=44100, size=-16, channels=4, buffer=2048)
            print("Pygame mixer initialized successfully.")
        except Exception as e:
            print(f"ERROR: Could not initialize pygame mixer: {e}")
            pygame.mixer = None

        # Load sounds in background thread
        self.sounds = {}
        self.sounds_loaded_event = threading.Event() 
        self.safety_channel = pygame.mixer.Channel(1) if pygame.mixer else None
        self.loading_thread = threading.Thread(target=self._load_sounds_in_background, daemon=True)
        self.loading_thread.start()

    def _load_sounds_in_background(self):
        """Load sounds in background to avoid blocking GUI."""
        print("Starting background sound loading...")
        if not pygame.mixer:
            self.sounds_loaded_event.set()
            return

        sound_files = {
            "check_again": "sounds/check_again.mp3",
            "alert": "sounds/alert.mp3",
            "start_engine": "sounds/start_engine.wav",
            "car_idle": "sounds/car_idle.wav",
            "turnoff_engine": "sounds/turnoff_engine.wav",
            "safety_instructions": "sounds/safety_instructions.mp3"
        }
        loaded_sounds = {}
        for name, path in sound_files.items():
            if os.path.exists(path):
                try:
                    loaded_sounds[name] = pygame.mixer.Sound(path)
                except pygame.error as e:
                    print(f"ERROR loading sound {path}: {e}")
            else:
                print(f"WARNING: Sound file not found: {path}")
        
        self.sounds = loaded_sounds
        self.sounds_loaded_event.set()
        print("All sounds loaded.")

    def _play_sound(self, sound_name, loop=False):
        self.sounds_loaded_event.wait()
        if not pygame.mixer: return
        
        if sound_name in self.sounds:
            loops = -1 if loop else 0
            try:
                channel = pygame.mixer.find_channel()
                if channel:
                    channel.play(self.sounds[sound_name], loops=loops)
            except pygame.error as e:
                print(f"ERROR playing sound {sound_name}: {e}")
        else:
            print(f"ERROR: Sound '{sound_name}' not loaded.")
            
    def _play_music(self, sound_name, loop=False):
        self.sounds_loaded_event.wait()
        if not pygame.mixer: return
        
        if sound_name in self.sounds:
            loops = -1 if loop else 0
            try:
                pygame.mixer.music.load(self.sounds[sound_name].get_sound_file_path())
                pygame.mixer.music.play(loops=loops)
            except Exception as e:
                 print(f"ERROR playing music {sound_name}: {e}")
        else:
            print(f"ERROR: Sound '{sound_name}' not loaded.")
            
    def get_sound_length(self, sound_name):
        self.sounds_loaded_event.wait()
        if sound_name in self.sounds:
            return self.sounds[sound_name].get_length()
        return 0

    def stop_all_sounds(self):
        if not pygame.mixer: return
        pygame.mixer.music.stop()
        pygame.mixer.stop()
        print("All sounds stopped.")

    def stop_alert_sounds(self):
        if not pygame.mixer: return
        pygame.mixer.stop()
        print("Alert sounds stopped.")
        
    def is_alert_sound_playing(self):
        if not pygame.mixer: return False
        return pygame.mixer.get_busy()

    def play_speaker(self):
        self._play_sound("check_again")

    def play_alarm(self):
        self._play_sound("alert")
        
    def play_startup_sound(self):
        self._play_sound("start_engine")

    def play_idle_sound(self):
        if pygame.mixer and not pygame.mixer.music.get_busy():
            self._play_music("car_idle", loop=True)

    def play_engine_off_sound(self):
        self._play_sound("turnoff_engine")
        
    def play_safety_instructions(self):
        self.sounds_loaded_event.wait()
        self.log_event("Playing safety instructions.")
        self.stop_alert_sounds()
        if 'safety_instructions' in self.sounds and self.safety_channel:
            self.safety_channel.play(self.sounds['safety_instructions'])

    def is_safety_instruction_playing(self):
        if self.safety_channel:
            return self.safety_channel.get_busy()
        return False

    # --- Other methods unchanged ---
    
    def setup_session_logger(self):
        if self.logger and self.logger.hasHandlers():
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
        session_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = f"noc_logs/noc_session_{session_timestamp}.log"
        self.logger = logging.getLogger(f"NOC_Session_{session_timestamp}")
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        print(f"Session log file created: {log_filename}")
        self.log_event("Started new log session.")

    def log_event(self, message):
        print(f"[LOG] {message}")
        if self.logger:
            self.logger.info(message)
        else:
            logging.info(message)

    def _send_single_slack_message(self, user_id, message_body):
        if not SLACK_BOT_TOKEN:
            self.log_event("ERROR: SLACK_BOT_TOKEN is not configured.")
            return False
        url = "https://slack.com/api/chat.postMessage"
        headers = { "Authorization": f"Bearer {SLACK_BOT_TOKEN}" }
        payload = { "channel": user_id, "text": message_body }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status() 
            response_data = response.json()
            if not response_data.get("ok"):
                self.log_event(f"ERROR sending message to {user_id}: {response_data.get('error')}")
                return False
            return True
        except requests.exceptions.RequestException as e:
            self.log_event(f"Network error sending message to {user_id}: {e}")
            return False

    def _send_messages_for_user(self, user_id):
        personal_message = MESSAGE_TEXT_TEMPLATE.format(user_id)
        self.log_event(f"[Thread for {user_id}] Start repeated sending...")
        for i in range(SPAM_COUNT):
            self.log_event(f"[Thread for {user_id}] Attempt {i+1}/{SPAM_COUNT}: Sending...")
            success = self._send_single_slack_message(user_id, personal_message)
            if success:
                self.log_event(f"[Thread for {user_id}] Attempt {i+1} succeeded.")
            else:
                self.log_event(f"[Thread for {user_id}] Attempt {i+1} failed.")
            if i < SPAM_COUNT - 1:
                time.sleep(DELAY_SECONDS)
        self.log_event(f"[Thread for {user_id}] Finished repeated sending.")

    def send_sos_message(self):
        self.log_event("Starting SOS message threads...")
        if not SLACK_USER_IDS_LIST or not SLACK_USER_IDS_LIST[0]:
             self.log_event("ERROR: SOS recipient list is empty.")
             return False
        threads = []
        for user_id in SLACK_USER_IDS_LIST:
            thread = threading.Thread(target=self._send_messages_for_user, args=(user_id,), daemon=True)
            threads.append(thread)
            thread.start()
        return True

    def send_emergency(self):
        self.log_event("Sent SOS message to authorities.")

class SoundWithGetPath(pygame.mixer.Sound):
    def __init__(self, file):
        self.file_path = file
        super().__init__(file)
    def get_sound_file_path(self):
        return self.file_path

if pygame.mixer:
    pygame.mixer.Sound = SoundWithGetPath