import csv
from datetime import datetime
import os

LOG_FILE = "data/alert_log.csv"

def log_alert(alert):
    os.makedirs("data", exist_ok=True)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), alert])
