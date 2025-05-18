import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

from pytz import timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class ReserveCABot:
    def __init__(self, config_path, credentials_dir=None, headless=False):
        """
        Initialize the ReserveCABot.

        Args:
            config_path (str): Path to the configuration file containing non-sensitive settings.
            credentials_dir (str, optional): Directory containing credential files. If None, looks for
                credentials in the same directory as config_path.
            headless (bool, optional): Whether to run Chrome in headless mode. Defaults to False.
        """
        self.logger = self._setup_logger()
        self.config = self._load_config(config_path)

        # Handle credentials
        if credentials_dir is None:
            credentials_dir = Path(config_path).parent
        else:
            credentials_dir = Path(credentials_dir)

        self.credentials = self._load_credentials(
            credentials_dir / "reserve_ca_credentials.json"
        )

        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")

        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 60)

    def _setup_logger(self):
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        return logging.getLogger(__name__)

    def _load_config(self, config_path):
        """Load non-sensitive configuration settings."""
        with open(config_path) as f:
            return json.load(f)

    def _load_credentials(self, credentials_path):
        """
        Load sensitive credentials from a service-specific file.

        Args:
            credentials_path (Path): Path to the service-specific credentials file.

        Returns:
            dict: Credentials for the service.

        Raises:
            FileNotFoundError: If credentials file doesn't exist.
            json.JSONDecodeError: If credentials file is invalid JSON.
        """
        try:
            with open(credentials_path) as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(
                f"Credentials file not found at {credentials_path}. "
                "Please create a service-specific credentials file."
            )
            raise
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in credentials file at {credentials_path}")
            raise

    def login(self):
        try:
            self.driver.get(self.config["url"])
            time.sleep(2)

            login_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "login-btn"))
            )
            login_button.click()

            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "txtEmail"))
            )
            email_field.send_keys(self.credentials["username"])

            password_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "txtPassword"))
            )
            password_field.send_keys(self.credentials["password"])

            time.sleep(2)

            login_submit = self.wait.until(
                EC.element_to_be_clickable((By.ID, "divOnlyLogin"))
            )
            login_submit.click()

        except Exception as e:
            self.logger.error(f"Login failed with error: {str(e)}")
            return False

    def clickPreviousDay(self, config_start_date):
        # Parse the ISO format date
        date_obj = datetime.strptime(config_start_date, "%Y-%m-%d")
        previous_date = date_obj - timedelta(days=1)

        # Format the date for the aria-label (like "August 4th, 2025")
        formatted_date = previous_date.strftime("%B %-d")  # Gets "August 4"
        day_suffix = (
            "th"
            if 11 <= previous_date.day <= 13
            else {1: "st", 2: "nd", 3: "rd"}.get(previous_date.day % 10, "th")
        )
        formatted_date = f"{formatted_date}{day_suffix}, {previous_date.year}"

        # Wait for and click the date
        previous_day = self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, f"div[aria-label*='{formatted_date}']")
            )
        )
        previous_day.click()

    def clickEndDate(self, config_end_date):
        date_obj = datetime.strptime(config_end_date, "%Y-%m-%d")

        # Format the date for the aria-label (like "August 9th, 2025")
        formatted_date = date_obj.strftime("%B %-d")
        day_suffix = (
            "th"
            if 11 <= date_obj.day <= 13
            else {1: "st", 2: "nd", 3: "rd"}.get(date_obj.day % 10, "th")
        )
        formatted_date = f"{formatted_date}{day_suffix}, {date_obj.year}"

        # Find the element first
        end_date = self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, f"div[aria-label*='{formatted_date}']")
            )
        )

        time.sleep(2)

        # Scroll the element into view
        self.driver.execute_script("arguments[0].scrollIntoView(true);", end_date)
        time.sleep(0.5)

        # Now wait for it to be clickable and click it
        end_date = self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, f"div[aria-label*='{formatted_date}']")
            )
        )
        end_date.click()

    def clickCampsiteButton(self):
        try:
            button = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        f"//td[contains(text(), '{self.config['campsite']}')]/../td[3]//button[not(@disabled)]",
                    )
                )
            )
            button.click()
            return True
        except Exception:
            # If button not clickable, find and click refresh button
            self.logger.info("Not clickable refreshing...")
            refresh_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.icons[title='Refresh']")
                )
            )
            refresh_button.click()
            time.sleep(1)
        return False

    def clickCaptcha(self):
        # Switch to the reCAPTCHA iframe first
        recaptcha_iframe = self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "iframe[title*='reCAPTCHA']")
            )
        )
        self.driver.switch_to.frame(recaptcha_iframe)

        recaptcha_checkbox = self.wait.until(
            EC.element_to_be_clickable((By.CLASS_NAME, "recaptcha-checkbox-border"))
        )
        recaptcha_checkbox.click()

        self.driver.switch_to.default_content()

    def navigateAndSetup(self):
        try:
            self.driver.get(self.config["url"])
            time.sleep(0.5)

            set_date_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "custom-datepicker-calendar"))
            )

            set_date_button.click()

            self.clickPreviousDay(self.config["start_date"])

            self.clickEndDate(self.config["end_date"])

            return self.clickCampsiteButton

        except Exception as e:
            self.logger.error(f"Setup failed with error: {str(e)}")
            self.logger.error(f"Current URL: {self.driver.current_url}")
            return False

    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    reserved = False
    bot = ReserveCABot("res_ca_config.json")
    try:
        bot.login()
        time.sleep(2)

        bot.navigateAndSetup()

        while not reserved:
            current_time = datetime.now(timezone(bot.config["timezone"]))

            start_hour, start_minute = map(int, bot.config["start_time"].split(":"))
            target_start_time = current_time.replace(
                hour=start_hour, minute=start_minute, second=0, microsecond=0
            )

            if current_time < target_start_time:
                time.sleep(0.1)
                continue

            end_time = time.time() + (10 * 60)

            while time.time() < end_time:
                if bot.clickCampsiteButton:
                    bot.clickCaptcha
                    book_now_button = bot.wait.until(
                        EC.element_to_be_clickable((By.ID, "checkout-button"))
                    )
                    book_now_button.click()
                    break

    finally:
        bot.close()
