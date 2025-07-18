import os
import json
import logging
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

# Load environment variables
load_dotenv()

# Configuration
VISA_EMAIL = os.getenv("VISA_EMAIL")
VISA_PASS = os.getenv("VISA_PASS")
MAILGUN_SENDING_API_KEY = os.getenv("MAILGUN_SENDING_API_KEY")
MAILGUN_SENDING_DOMAIN = os.getenv("MAILGUN_SENDING_DOMAIN")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
BCC_ADDRESS = os.getenv("BCC_ADDRESS")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 600))
STATE_FILE = "last_slots.json"
LOGIN_URL = "https://ais.usvisa-info.com/es-mx/niv/users/sign_in"
APPT_URL = "https://ais.usvisa-info.com/es-mx/niv/schedule/62993213/appointment"

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("visa-alerta")

#@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            ),
            locale="es-MX",
        )
        page = context.new_page()
        page.add_init_script("""
          Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
          window.chrome = { runtime: {} };
          Object.defineProperty(navigator, 'languages', { get: () => ['es-MX','es'] });
          Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        """)

        # now navigate as before
        page.goto(LOGIN_URL, wait_until='networkidle', timeout=120_000)
        logger.info("Reached login page (no 403)")

        # Wait for login fields and inject via JS to ensure compatibility
        page.wait_for_selector('#user_email', timeout=120_000)
        page.fill("#user_email", VISA_EMAIL)
        logger.info("email filled")
        page.wait_for_selector('#user_password', timeout=120_000)
        page.fill("#user_password", VISA_PASS)
        logger.info("password filled")

        #Check term and conditions checkbox
        checkbox = page.locator('#policy_confirmed')
        checkbox.wait_for(timeout=120_000)
        logger.info("checkbox found")
        checkbox.check(force=True)
        logger.info("policy_confirmed checkbox checked")
        page.screenshot(path="debug.png", full_page=True)

        # Ensure submit button is ready
        page.wait_for_selector('input[name="commit"]', timeout=120_000)
        logger.info("Submit button ready, submitting form")
        page.click('input[name="commit"]')
        logger.info("Submitted login form, awaiting navigation to schedule page")

        # Wait for navigation to schedule
        page.wait_for_url(lambda url: "/groups/" in url, timeout=120_000)
        logger.info("Logged in successfully")

        # Navigate to appointment page
        page.goto(APPT_URL)
        logger.info("Navigated to appointment page")

        # Optional: save debug screenshot
        page.screenshot(path="debug.png", full_page=True)

        # Extract HTML content
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
    with open(STATE_FILE, "w") as f:
        json.dump(slots, f)


def send_email(new_slots):
    earliest = new_slots[0]
    data = {
        "from": EMAIL_FROM,
        "to": EMAIL_TO,
        "subject": "🛎️ New US Visa Appointment Slot",
        "text": f"Earliest slot: {earliest}"
    }
    if BCC_ADDRESS:
        data["bcc"] = BCC_ADDRESS
    return requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_SENDING_DOMAIN}/messages",
        auth=("api", MAILGUN_SENDING_API_KEY),
        data=data
    )


def main():
    logger.info("Routine Started")
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
            logger.error(f"Error checking slots: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()