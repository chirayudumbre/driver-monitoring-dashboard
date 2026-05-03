# modules/alert_system.py
import time
import threading

last_played = 0

def play_alert():
    global last_played
    if time.time() - last_played > 3:  # 3-sec cooldown
        last_played = time.time()
        threading.Thread(target=_play, daemon=True).start()

def _play():
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load("assets/alert.wav")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print("Alert sound error:", e)
