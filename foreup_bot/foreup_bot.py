import json
import logging
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

_debug = True


class ForeUpBot:
    """Bot for automating golf tee time bookings on ForeUp software.

    This bot automates the process of booking golf tee times on ForeUp-powered
    golf course websites. It handles login, date selection, and booking process.
    """

    def __init__(self, config_path, credentials_path, headless=False):
        """Initialize the ForeUp booking bot.

        Args:
            config_path (str): Path to the JSON configuration file
            credentials_path (str): Path to the JSON credentials file
            headless (bool): Whether to run Chrome in headless mode
        """
        self.logger = self._setup_logger()
        self.config = self._load_config(config_path)
        self.credentials = self._load_config(credentials_path)
        self.base_url = "https://foreupsoftware.com/index.php/booking/19348/1470"
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 60)

    def _setup_logger(self):
        """Set up logging configuration.

        Returns:
            logging.Logger: Configured logger instance
        """
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        return logging.getLogger(__name__)

    def _load_config(self, config_path):
        """Load configuration from JSON file.

        Args:
            config_path (str): Path to the configuration file

        Returns:
            dict: Configuration dictionary
        """
        with open(config_path) as f:
            return json.load(f)

    def login(self):
        """Log in to the ForeUp booking system.

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            self.driver.get(self.base_url)
            time.sleep(1)  # Allow page to load

            # Enter credentials
            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "login_email"))
            )
            email_field.send_keys(self.credentials["username"])

            password_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "login_password"))
            )
            password_field.send_keys(self.credentials["password"])

            # Submit login
            submit_button = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "login_button"))
            )
            submit_button.click()

            # Click Reservations link
            time.sleep(1)  # Wait for login to complete
            reservations_link = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#/teetimes']"))
            )
            reservations_link.click()

            return True

        except Exception as e:
            self.logger.error(f"Login failed with error: {str(e)}")
            return False

    def _parse_time(self, time_str):
        """Parse time string from the website into datetime object.

        Args:
            time_str (str): Time string in format like "5:51pm"

        Returns:
            datetime.time: Parsed time object
        """
        return datetime.strptime(time_str.lower(), "%I:%M%p").time()

    def _get_time_difference(self, time1, time2):
        """Calculate time difference in minutes between two times.

        Args:
            time1 (datetime.time): First time
            time2 (datetime.time): Second time

        Returns:
            int: Absolute difference in minutes
        """
        t1_minutes = time1.hour * 60 + time1.minute
        t2_minutes = time2.hour * 60 + time2.minute
        return abs(t1_minutes - t2_minutes)

    def navigate_and_setup(self):
        """Navigate to booking page and set up booking parameters.

        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            # Wait for tee times page to load and click BOOK NOW button
            book_now_button = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "button.btn.btn-primary.col-md-4.col-xs-12.col-md-offset-4",
                    )
                )
            )
            book_now_button.click()

            # Select date
            date_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "date-field"))
            )

            # Use keyboard shortcut to select all and delete
            date_field.send_keys(Keys.CONTROL + "a")
            date_field.send_keys(Keys.DELETE)

            # Use the date string directly from config
            self.logger.info(f"Setting date to: {self.config['target_date']}")
            date_field.send_keys(self.config["target_date"])
            date_field.send_keys(Keys.RETURN)  # Press Enter to submit the date

            # Wait for the page to load after date selection
            self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "div.btn-group.btn-group-justified.hidden-xs.players",
                    )
                )
            )

            # Select number of players
            num_players = str(self.config["num_players"])
            player_button = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        f"div.btn-group.btn-group-justified.hidden-xs.players a[data-value='{num_players}']",
                    )
                )
            )
            player_button.click()

            # Wait for results and find closest time to target
            time.sleep(0.5)  # Allow time tiles to load
            available_times = self.driver.find_elements(
                By.CSS_SELECTOR, "div.time.time-tile:not(.unavailable)"
            )

            if not available_times:
                self.logger.error("No available tee times found")
                return False

            # Parse target times from config
            target_time = datetime.strptime(
                self.config["start_time"], "%I:%M %p"
            ).time()
            window_start = datetime.strptime(
                self.config["window_start_time"], "%I:%M %p"
            ).time()
            window_end = datetime.strptime(
                self.config["window_end_time"], "%I:%M %p"
            ).time()
            self.logger.info(f"Target time: {target_time.strftime('%I:%M %p')}")
            self.logger.info(
                f"Time window: {window_start.strftime('%I:%M %p')} - {window_end.strftime('%I:%M %p')}"
            )

            # Filter times within window and calculate differences in one pass
            valid_times = []
            for time_element in available_times:
                time_str = time_element.find_element(
                    By.CSS_SELECTOR, "div.booking-start-time-label"
                ).text
                current_time = self._parse_time(time_str)
                if window_start <= current_time <= window_end:
                    time_diff = self._get_time_difference(target_time, current_time)
                    valid_times.append((time_element, time_str, time_diff))

            if not valid_times:
                self.logger.error(
                    "No available tee times found within specified time window"
                )
                return False

            # Find closest time from valid times
            closest_time, closest_time_str, min_diff = min(
                valid_times, key=lambda x: x[2]
            )
            self.logger.info(
                f"Selected closest time: {closest_time_str} (diff: {min_diff} minutes)"
            )

            # Click the closest time
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", closest_time
            )

            if not _debug:
                closest_time.click()

            # Select number of players in the booking field
            booking_player_button = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        f"div.js-booking-field-buttons[data-field='players'] a[data-value='{num_players}']",
                    )
                )
            )
            booking_player_button.click()

            # Wait for and click the Book Time button
            book_time_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.btn.btn-success.js-book-button")
                )
            )
            if not _debug:
                book_time_button.click()

            return self.handle_booking_result()

        except Exception as e:
            self.logger.error(f"Setup failed with error: {str(e)}")
            self.logger.error(f"Current URL: {self.driver.current_url}")
            return False

    def handle_booking_result(self):
        """Handle the result of the booking attempt.

        Returns:
            bool: True if booking successful, False otherwise
        """
        try:
            # Check for confirmation page
            if self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.booking-confirmation")
                )
            ):
                self.logger.info("Successfully reached booking confirmation")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Failed to handle booking result with error: {str(e)}")
            return False

    def close(self):
        """Close the browser and clean up resources."""
        self.driver.quit()


if __name__ == "__main__":
    reserved = False

    # Wait until 1 minute before target time to login
    target_hour = 11
    target_minute = 29
    while True:
        current_time = datetime.now().time()
        print(f"Current time: {current_time}")

        # Calculate seconds until 1 minute before target time
        time_to_wait = (
            (target_hour - current_time.hour) * 3600
            + (target_minute - 1 - current_time.minute) * 60
            - current_time.second
        )

        print(f"Seconds to wait: {time_to_wait}")
        if time_to_wait > 0:
            print(
                f"Waiting {time_to_wait} seconds until 1 minute before {target_hour}:{target_minute:02d}..."
            )
            time.sleep(time_to_wait)
        else:
            break

    # Launch browser and login
    bot = ForeUpBot("foreup_bot/foreup_config.json", "foreup_bot/credentials.json")
    try:
        # Login first
        bot.login()
        time.sleep(2)

        # Wait until target time to start booking
        while True:
            current_time = datetime.now().time()
            if (
                current_time.hour >= target_hour
                and current_time.minute >= target_minute
            ):
                break
            time_to_wait = (
                (target_hour - current_time.hour) * 3600
                + (target_minute - current_time.minute) * 60
                - current_time.second
            )
            if time_to_wait > 0:
                print(
                    f"Waiting {time_to_wait} seconds until {target_hour}:{target_minute:02d}..."
                )
                time.sleep(time_to_wait)
            else:
                break

        # Start booking process
        while not reserved:
            if bot.navigate_and_setup():
                reserved = True
                break
            else:
                bot.logger.info("No available times found, reloading page...")
                bot.driver.refresh()
                continue

    finally:
        bot.close()
