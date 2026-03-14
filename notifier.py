"""
notifier.py – Automated Low-Water Alert Engine
================================================
Monitors the Kaub gauge daily and sends an email alert when
a Kleinwasserzuschlag (low-water surcharge) is active.

Environment variables required for email delivery:
    GMAIL_USER          – your Gmail address
    GMAIL_APP_PASSWORD  – a Google App Password (not your login password)
"""

import csv
import os
import time
import smtplib
import schedule
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from data_fetcher import get_current_level
from calculator import calculate_surcharge

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587  # TLS

DEFAULT_CARGO_TONS = 1000
SUBSCRIBERS_FILE = "subscribers.csv"

# ---------------------------------------------------------------------------
# Email sender
# ---------------------------------------------------------------------------

def send_alert_email(target_email: str, current_level: float, surcharge_per_ton: float):
    """Compose and send a low-water surcharge alert via Gmail SMTP/TLS.

    Credentials are read from the environment:
        GMAIL_USER, GMAIL_APP_PASSWORD
    """
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_pass:
        print("⚠  GMAIL_USER / GMAIL_APP_PASSWORD not set – skipping email.")
        return

    subject = "URGENT: Rhine Low Water Surcharge Alert"

    body = (
        f"Rhine Freight Radar – Low Water Alert\n"
        f"{'=' * 42}\n\n"
        f"The current water level at the Kaub gauge (Rhine, km 546) has\n"
        f"dropped to {current_level:.0f} cm, triggering a Kleinwasserzuschlag\n"
        f"(low-water surcharge).\n\n"
        f"  Surcharge rate : €{surcharge_per_ton:.2f} per metric ton\n"
        f"  Reference cargo: {DEFAULT_CARGO_TONS:,} tons → "
        f"€{surcharge_per_ton * DEFAULT_CARGO_TONS:,.2f} total\n\n"
        f"Please review your current shipping commitments and consider\n"
        f"adjusting logistics plans accordingly.\n\n"
        f"— Rhine Freight Radar (automated alert)\n"
    )

    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = target_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, target_email, msg.as_string())
        print(f"✅ Alert email sent to {target_email}")
    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP authentication failed – check GMAIL_APP_PASSWORD.")
    except Exception as exc:
        print(f"❌ Failed to send email: {exc}")


# ---------------------------------------------------------------------------
# Scheduled job
# ---------------------------------------------------------------------------

def job():
    """Check the current Kaub level and alert each subscriber whose threshold is breached."""
    print("\n🔄 Running scheduled water-level check …")

    current_data = get_current_level("Kaub")

    if "error" in current_data:
        print(f"⚠  Could not fetch water level: {current_data['error']}")
        return

    level = current_data["value"]
    timestamp = current_data["timestamp"]

    print(f"   Kaub level : {level:.0f} cm (As of {timestamp})")

    # --- Load subscriber list ---
    if not os.path.isfile(SUBSCRIBERS_FILE):
        print(f"   ℹ  No {SUBSCRIBERS_FILE} found – no subscribers to notify.")
        return

    with open(SUBSCRIBERS_FILE, newline="") as f:
        reader = csv.DictReader(f)
        subscribers = list(reader)

    if not subscribers:
        print("   ℹ  Subscriber list is empty – nothing to do.")
        return

    print(f"   📋 {len(subscribers)} subscriber(s) loaded\n")

    for row in subscribers:
        # Note: Ensure your subscribers.csv has the headers "email,threshold_cm"
        target_email = row["email"]
        user_threshold = float(row["threshold_cm"])

        if level <= user_threshold:
            result = calculate_surcharge(
                water_level_cm=level, cargo_tonnage=DEFAULT_CARGO_TONS
            )
            surcharge = result["surcharge_per_ton"]
            print(
                f"   ⚠  {target_email} — threshold {user_threshold:.0f} cm BREACHED "
                f"(level {level:.0f} cm, €{surcharge:.2f}/ton) → sending alert"
            )
            send_alert_email(target_email, level, surcharge)
        else:
            print(
                f"   ✅ {target_email} — threshold {user_threshold:.0f} cm, "
                f"level {level:.0f} cm → safe, skipping"
            )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Run once immediately for testing
    print("=" * 50)
    print("  Rhine Freight Radar – Alert Engine")
    print("=" * 50)
    job()


