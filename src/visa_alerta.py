import os
import json
import logging
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from tenacity import retry, stop_after_attempt, wait_exponential

# Load env
load_dotenv()

# Config
VISA_EMAIL = os.getenv("VISA_EMAIL")
VISA_PASS = os.getenv("VISA_PASS")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 600))
STATE_FILE = "last_slots.json"
LOGIN_URL = "https://ais.usvisa-info.com/es-mx/niv/users/sign_in"
APPT_URL = "https://ais.usvisa-info.com/es-mx/niv/schedule/62993213/appointment"

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("visa-alerta")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(LOGIN_URL)
        page.fill('input[name="user[email]"]', VISA_EMAIL)
        page.fill('input[name="user[password]"]', VISA_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url(lambda u: "/schedule/" in u)
        page.goto(APPT_URL)
        content = page.content()
        browser.close()
    return content


def parse_slots(html):
    soup = BeautifulSoup(html, "html.parser")
    slots = soup.select("td.available")
    return sorted({cell.get_text(strip=True) for cell in slots})


def load_previous():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return []


def save_current(slots):
    json.dump(slots, open(STATE_FILE, "w"))


def send_email(new_slots):
    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=EMAIL_TO,
        subject="🛎️ New US Visa Appointment Slot",
        plain_text_content=f"Earliest slot: {new_slots[0]}"
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)


def main():
    while True:
        try:
            html = fetch_page()
            current = parse_slots(html)
            previous = load_previous()
            added = [d for d in current if d not in previous]
            if added:
                send_email(added)
                logger.info(f"Notified for slot: {added[0]}")
            else:
                logger.info("No new slots.")
            save_current(current)
        except Exception as e:
            logger.error(f"Error: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()