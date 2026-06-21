"""
pi/buzzer.py
============
Active buzzer control via RPi.GPIO.
Falls back to a silent stub if not running on real Pi hardware
(so code can be tested on Windows/Linux without GPIO errors).

Wiring:
  GPIO 17 (Pin 11) ──── Buzzer + (red wire)
  GND     (Pin 9)  ──── Buzzer - (black wire)
"""

import time
import threading


class Buzzer:
    def __init__(self, pin: int = 17):
        self.pin     = pin
        self._gpio   = None
        self._lock   = threading.Lock()
        self._enabled = False

        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)
            self._gpio    = GPIO
            self._enabled = True
            print(f"[BUZZ] GPIO buzzer enabled on pin {self.pin}")
        except (ImportError, RuntimeError):
            print(f"[BUZZ] RPi.GPIO not available — buzzer running in silent mode")

    def _buzz(self, duration: float):
        """Turn buzzer ON for `duration` seconds then OFF."""
        if not self._enabled:
            return
        with self._lock:
            self._gpio.output(self.pin, self._gpio.HIGH)
            time.sleep(duration)
            self._gpio.output(self.pin, self._gpio.LOW)

    def beep(self, times: int = 1, duration: float = 0.2, gap: float = 0.1):
        """
        Beep `times` times, each beep `duration` seconds long.
        Runs in a daemon thread so it never blocks the main loop.
        """
        def _run():
            for i in range(times):
                self._buzz(duration)
                if i < times - 1:
                    time.sleep(gap)

        threading.Thread(target=_run, daemon=True).start()

    def cleanup(self):
        """Release GPIO resources."""
        if self._enabled and self._gpio:
            try:
                self._gpio.output(self.pin, self._gpio.LOW)
                self._gpio.cleanup(self.pin)
            except Exception:
                pass
