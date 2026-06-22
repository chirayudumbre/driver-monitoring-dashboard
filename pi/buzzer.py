"""
pi/buzzer.py
============
Active buzzer control — supports both Pi 4 (RPi.GPIO) and Pi 5 (lgpio).
Falls back to silent mode if neither is available (for testing on PC).

Wiring:
  GPIO 17 (Pin 11) ──── Buzzer + (red wire)
  GND     (Pin 9)  ──── Buzzer - (black wire)
"""

import time
import threading


class Buzzer:
    def __init__(self, pin: int = 17):
        self.pin      = pin
        self._lock    = threading.Lock()
        self._mode    = None   # 'lgpio', 'rpi', or None (silent)
        self._handle  = None

        # Try lgpio first (Pi 5)
        try:
            import lgpio
            self._lgpio  = lgpio
            self._handle = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_output(self._handle, self.pin)
            lgpio.gpio_write(self._handle, self.pin, 0)
            self._mode = "lgpio"
            print(f"[BUZZ] lgpio buzzer enabled on GPIO {self.pin} (Pi 5 mode)")
            return
        except Exception:
            pass

        # Try RPi.GPIO (Pi 4)
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)
            self._gpio = GPIO
            self._mode = "rpi"
            print(f"[BUZZ] RPi.GPIO buzzer enabled on GPIO {self.pin} (Pi 4 mode)")
            return
        except Exception:
            pass

        print(f"[BUZZ] No GPIO library found — buzzer running in silent mode")

    def _buzz(self, duration: float):
        if self._mode == "lgpio":
            with self._lock:
                self._lgpio.gpio_write(self._handle, self.pin, 1)
                time.sleep(duration)
                self._lgpio.gpio_write(self._handle, self.pin, 0)
        elif self._mode == "rpi":
            with self._lock:
                self._gpio.output(self.pin, self._gpio.HIGH)
                time.sleep(duration)
                self._gpio.output(self.pin, self._gpio.LOW)
        # silent mode: do nothing

    def beep(self, times: int = 1, duration: float = 0.2, gap: float = 0.1):
        """Beep `times` times. Runs in daemon thread — never blocks main loop."""
        def _run():
            for i in range(times):
                self._buzz(duration)
                if i < times - 1:
                    time.sleep(gap)
        threading.Thread(target=_run, daemon=True).start()

    def cleanup(self):
        if self._mode == "lgpio":
            try:
                self._lgpio.gpio_write(self._handle, self.pin, 0)
                self._lgpio.gpiochip_close(self._handle)
            except Exception:
                pass
        elif self._mode == "rpi":
            try:
                self._gpio.output(self.pin, self._gpio.LOW)
                self._gpio.cleanup(self.pin)
            except Exception:
                pass
