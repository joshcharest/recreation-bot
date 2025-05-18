import json
import logging
import time
from datetime import datetime

from pytz import timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class RecreationBot:
    def __init__(self, config_path, headless=False):
        self.logger = self._setup_logger()
        self.config = self._load_config(config_path)
        options = webdriver.ChromeOptions()

        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 60)

    def _setup_logger(self):
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        return logging.getLogger(__name__)

    def _load_config(self, config_path):
        with open(config_path) as f:
            return json.load(f)

    def login(self):
        try:
            self.driver.get("https://www.recreation.gov")
            time.sleep(0.5)

            login_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "ga-global-nav-log-in-link"))
            )
            login_button.click()

            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            email_field.send_keys(self.config["username"])

            password_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "rec-acct-sign-in-password"))
            )
            password_field.send_keys(self.config["password"])

            login_submit = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.rec-acct-sign-in-btn")
                )
            )
            login_submit.click()

        except Exception as e:
            self.logger.error(f"Login failed with error: {str(e)}")
            return False

    def navigateAndSetup(self):
        try:
            self.driver.get(self.config["url"])
            time.sleep(0.5)

            target_date = datetime.strptime(self.config["start_date"], "%Y-%m-%d")

            month_field = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'div[role="spinbutton"][aria-label="month, "]')
                )
            )
            month_field.click()

            action = webdriver.ActionChains(self.driver)
            action.send_keys(str(target_date.month))
            action.send_keys(str(target_date.day))
            action.send_keys(str(target_date.year))
            action.perform()

            group_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "guest-counter"))
            )
            group_button.click()

            people_input = self.wait.until(
                EC.element_to_be_clickable((By.ID, "guest-counter-number-field-People"))
            )
            people_input.clear()
            people_input.send_keys(str(self.config["num_people"]))

            close_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[.//span[text()='Close']]")
                )
            )
            close_button.click()

            first_date = self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        f"//button[.//span[text()='{self.config['trailhead']}']]/ancestor::div[@role='gridcell']/following-sibling::div//button[contains(@class, 'rec-availability-date')][1]",
                    )
                )
            )
            if "sarsa-button-disabled" in first_date.get_attribute("class"):
                self.logger.error("No availability for selected date")
                return False

            self.driver.execute_script("arguments[0].scrollIntoView(true);", first_date)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", first_date)
            self.logger.info("Spots Available, clicked date")

            book_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[.//span[text()='Book Now']]")
                )
            )
            book_button.click()

            return self.handleBookingResult()

        except Exception as e:
            self.logger.error(f"Setup failed with error: {str(e)}")
            self.logger.error(f"Current URL: {self.driver.current_url}")
            return False

    def handleBookingResult(self):
        try:
            try:
                if self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(@class, 'modal')]")
                    )
                ):
                    self.logger.info("Error popup detected, reloading page")
                    self.driver.refresh()
                    return False
            except Exception:
                if self.driver.find_elements(By.XPATH, "//h1[text()='Order Details']"):
                    self.logger.info("Successfully reached checkout page")
                    return True

        except Exception as e:
            self.logger.error(f"Failed to handle booking result with error: {str(e)}")
            return False

    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    reserved = False
    bot = RecreationBot("rec_config.json")
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

            end_time = time.time() + (22 * 60)

            while time.time() < end_time:
                if bot.navigateAndSetup():
                    reserved = True
                    break

    finally:
        bot.close()
