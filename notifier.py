import csv
import os
import sys
import signal
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from data_fetcher import get_current_level
from calculator import calculate_surcharge

# --- THE KILL SWITCH ---
# If this script runs for more than 45 seconds, the OS will kill it.
def timeout_handler(signum, frame):
    print("\n❌ FATAL: Script hung for 45 seconds. The network is deadlocking.", flush=True)
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(45)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # CHANGED to 465 (Implicit SSL) to bypass STARTTLS deadlocks

DEFAULT_CARGO_TONS = 1000
SUBSCRIBERS_FILE = "subscribers.csv"

# ---------------------------------------------------------------------------
# Email sender
# ---------------------------------------------------------------------------

def send_alert_email(target_email: str, current_level: float, surcharge_per_ton: float):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_pass:
        print("⚠  GMAIL_USER / GMAIL_APP_PASSWORD not set – skipping email.", flush=True)
        return

    subject = "URGENT: Rhine Low Water Surcharge Alert"

    body = (
        f"Rhine Freight Radar – Low Water Alert\n"
        f"{'=' * 42}\n\n"
        f"The current water level at the Kaub gauge has dropped to {current_level:.0f} cm.\n\n"
        f"  Surcharge rate : €{surcharge_per_ton:.2f} per metric ton\n"
        f"  Reference cargo: {DEFAULT_CARGO_TONS:,} tons → €{surcharge_per_ton * DEFAULT_CARGO_TONS:,.2f} total\n\n"
        f"— Rhine Freight Radar"
    )

    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = target_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    print(f"   ➤ Connecting to Gmail SMTP on Port {SMTP_PORT}...", flush=True)
    try:
        # CHANGED to SMTP_SSL. It encrypts instantly, preventing handshake hangs.
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, target_email, msg.as_string())
        print(f"   ✅ Alert email successfully sent to {target_email}", flush=True)
    except smtplib.SMTPAuthenticationError:
        print("   ❌ SMTP authentication failed – check GMAIL_APP_PASSWORD.", flush=True)
    except Exception as exc:
        print(f"   ❌ Failed to send email: {exc}", flush=True)

# ---------------------------------------------------------------------------
# Scheduled job
# ---------------------------------------------------------------------------

def job():
    print("\n🔄 Running scheduled water-level check …", flush=True)
    print("   ➤ Pinging PEGELONLINE API...", flush=True)

    current_data = get_current_level("Kaub")

    if "error" in current_data:
        print(f"   ⚠  Could not fetch water level: {current_data['error']}", flush=True)
        return

    level = current_data["value"]
    timestamp = current_data["timestamp"]

    print(f"   🌊 Kaub level : {level:.0f} cm (As of {timestamp})", flush=True)

    if not os.path.isfile(SUBSCRIBERS_FILE):
        print(f"   ℹ  No {SUBSCRIBERS_FILE} found – no subscribers to notify.", flush=True)
        return

    with open(SUBSCRIBERS_FILE, newline="") as f:
        reader = csv.DictReader(f)
        subscribers = list(reader)

    if not subscribers:
        print("   ℹ  Subscriber list is empty – nothing to do.", flush=True)
        return

    print(f"   📋 {len(subscribers)} subscriber(s) loaded", flush=True)

    for row in subscribers:
        target_email = row["email"]
        user_threshold = float(row["threshold_cm"])

        if level <= user_threshold:
            result = calculate_surcharge(water_level_cm=level, cargo_tonnage=DEFAULT_CARGO_TONS)
            surcharge = result["surcharge_per_ton"]
            print(f"   ⚠  {target_email} — threshold {user_threshold:.0f} cm BREACHED → sending alert", flush=True)
            send_alert_email(target_email, level, surcharge)
        else:
            print(f"   ✅ {target_email} — threshold {user_threshold:.0f} cm, level {level:.0f} cm → safe", flush=True)

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50, flush=True)
    print("  Rhine Freight Radar – Alert Engine (X-Ray Mode)", flush=True)
    print("=" * 50, flush=True)
    job()
