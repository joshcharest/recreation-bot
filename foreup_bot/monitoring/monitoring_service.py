import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import boto3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


@dataclass
class AvailabilityCheck:
    """Data class for storing availability check results."""

    timestamp: datetime
    date: str
    available_times: List[str]
    total_available: int
    success: bool
    error_message: Optional[str] = None


class ForeUpMonitor:
    """Continuous monitoring service for ForeUp tee time availability.

    This service runs continuously to check for tee time availability and can
    be deployed on AWS Lambda or EC2 for 24/7 monitoring.
    """

    def __init__(self, config_path: str, credentials_path: str, headless: bool = True):
        """Initialize the monitoring service.

        Args:
            config_path: Path to the configuration file
            credentials_path: Path to the credentials file
            headless: Whether to run browser in headless mode (default: True for AWS)
        """
        self.logger = self._setup_logger()
        self.config = self._load_config(config_path)
        self.credentials = self._load_config(credentials_path)
        self.base_url = "https://foreupsoftware.com/index.php/booking/19348/1470"
        self.cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")
        self.sns = boto3.client("sns", region_name="us-east-1")
        self.headless = headless

    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration.

        Returns:
            Configured logger instance
        """
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        return logging.getLogger(__name__)

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file.

        Args:
            config_path: Path to the configuration file

        Returns:
            Configuration dictionary
        """
        with open(config_path) as f:
            return json.load(f)

    def _setup_driver(self) -> webdriver.Chrome:
        """Set up Chrome WebDriver for monitoring.

        Returns:
            Configured Chrome WebDriver
        """
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")
            options.add_argument("--disable-animations")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--disable-ipc-flooding-protection")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-client-side-phishing-detection")
            options.add_argument("--disable-component-extensions-with-background-pages")
            options.add_argument("--disable-default-apps")
            options.add_argument("--disable-domain-reliability")
            options.add_argument("--disable-features=TranslateUI")
            options.add_argument("--disable-hang-monitor")
            options.add_argument("--disable-prompt-on-repost")
            options.add_argument("--disable-sync")
            options.add_argument("--disable-translate")
            options.add_argument("--metrics-recording-only")
            options.add_argument("--no-first-run")
            options.add_argument("--safebrowsing-disable-auto-update")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument(
                "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_experimental_option(
                "prefs",
                {
                    "profile.default_content_setting_values.notifications": 2,
                    "profile.managed_default_content_settings.images": 2,
                },
            )

        try:
            # Use webdriver-manager to get the correct ChromeDriver
            driver_path = ChromeDriverManager().install()
            # Make sure we're using the actual chromedriver executable, not a notice file
            if "THIRD_PARTY_NOTICES" in driver_path:
                # Find the actual chromedriver executable in the same directory
                import os

                driver_dir = os.path.dirname(driver_path)
                driver_path = os.path.join(driver_dir, "chromedriver")

            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            self.logger.error(f"Failed to create Chrome driver: {str(e)}")
            raise

        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver

    def _login_to_foreup(self, driver: webdriver.Chrome, wait: WebDriverWait) -> bool:
        """Log into ForeUp using credentials from config.

        Args:
            driver: Chrome WebDriver instance
            wait: WebDriverWait instance

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Look for login form
            try:
                # Find username field
                username_field = wait.until(
                    EC.presence_of_element_located((By.ID, "login_email"))
                )

                # Clear and enter username
                username_field.clear()
                username_field.send_keys(self.credentials["username"])
                self.logger.info("Entered username")

                # Find password field
                password_field = driver.find_element(By.NAME, "password")
                password_field.clear()
                password_field.send_keys(self.credentials["password"])
                self.logger.info("Entered password")

                # Find and click login button
                login_button = driver.find_element(
                    By.CSS_SELECTOR, "input[type='submit'], button[type='submit']"
                )
                login_button.click()
                self.logger.info("Clicked login button")

                # Wait for login to complete
                time.sleep(2)
                self.logger.info("Login attempt completed")
                return True

            except Exception as e:
                self.logger.error(f"Login failed: {str(e)}")
                return False

        except Exception as e:
            self.logger.error(f"Login process failed: {str(e)}")
            return False

    def check_availability(
        self, target_date: Optional[str] = None
    ) -> AvailabilityCheck:
        """Check tee time availability for a specific date.

        Args:
            target_date: Date to check (format: MM-DD-YYYY). If None, uses config date.

        Returns:
            AvailabilityCheck object with results
        """
        if target_date is None:
            target_date = self.config["target_date"]

        driver = None
        try:
            driver = self._setup_driver()
            wait = WebDriverWait(driver, 30)

            # Navigate to the booking page
            driver.get(self.base_url)
            time.sleep(2)

            # Login to ForeUp
            if not self._login_to_foreup(driver, wait):
                raise Exception("Failed to login to ForeUp")

            # Navigate directly to the tee times page
            tee_times_url = (
                "https://foreupsoftware.com/index.php/booking/19348/1470#/teetimes"
            )
            self.logger.info("Navigating to tee times page...")
            driver.get(tee_times_url)
            self.logger.info("Navigated to tee times page")

            # Click "STANDARD TEE TIMES (0-7 DAYS)" button
            try:
                standard_tee_times_button = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "button.btn.btn-primary.col-md-4.col-xs-12.col-md-offset-4",
                        )
                    )
                )
                self.logger.info("Found STANDARD TEE TIMES button, clicking...")
                standard_tee_times_button.click()
                time.sleep(2)
                self.logger.info("Clicked STANDARD TEE TIMES button")
            except Exception as e:
                self.logger.error(f"Could not find STANDARD TEE TIMES button: {str(e)}")
                raise

            # Select date from dropdown
            try:
                date_dropdown = wait.until(
                    EC.presence_of_element_located((By.ID, "date-menu"))
                )
                self.logger.info("Found date dropdown")

                # Select the target date from the dropdown
                from selenium.webdriver.support.select import Select

                select = Select(date_dropdown)
                select.select_by_value(str(target_date))
                self.logger.info(f"Selected date: {target_date}")

            except Exception as e:
                self.logger.error(
                    f"Could not find or interact with date dropdown: {str(e)}"
                )
                # Try to find any date-related elements
                try:
                    date_elements = driver.find_elements(
                        By.CSS_SELECTOR,
                        "select[name='date'], input[type='date'], input[placeholder*='date'], .date-picker",
                    )
                    self.logger.info(
                        f"Found {len(date_elements)} date-related elements"
                    )
                    for i, elem in enumerate(date_elements):
                        if elem:
                            outer_html = elem.get_attribute("outerHTML")
                            if outer_html:
                                self.logger.info(
                                    f"Date element {i}: {outer_html[:100]}"
                                )
                            else:
                                self.logger.info(f"Date element {i}: No outerHTML")
                        else:
                            self.logger.info(f"Date element {i}: None")
                except:
                    pass
                raise

            # Wait for time slots to load
            time.sleep(2)

            # Find all available times
            available_times = driver.find_elements(
                By.CSS_SELECTOR, "div.time.time-tile:not(.unavailable)"
            )

            time_slots = []
            required_players = self.config.get("num_players", 4)
            self.logger.info(
                f"Looking for tee times with at least {required_players} players"
            )

            for time_element in available_times:
                try:
                    # Get the time
                    time_str = time_element.find_element(
                        By.CSS_SELECTOR, "div.booking-start-time-label"
                    ).text

                    # Check player capacity
                    player_spans = time_element.find_elements(
                        By.CSS_SELECTOR, "span.booking-slot-players span"
                    )
                    available_spots = 0

                    for span in player_spans:
                        try:
                            spot_count = int(span.text.strip())
                            available_spots = max(available_spots, spot_count)
                        except (ValueError, AttributeError):
                            continue

                    # Only include if enough spots for required players
                    if available_spots >= required_players:
                        time_slots.append(f"{time_str} ({available_spots} spots)")
                        self.logger.info(
                            f"Found suitable time: {time_str} with {available_spots} spots"
                        )
                    else:
                        self.logger.info(
                            f"Skipping {time_str} - only {available_spots} spots available"
                        )

                except Exception as e:
                    self.logger.warning(f"Error processing time element: {str(e)}")
                    continue

            return AvailabilityCheck(
                timestamp=datetime.now(),
                date=str(target_date),
                available_times=time_slots,
                total_available=len(time_slots),
                success=True,
            )

        except Exception as e:
            error_msg = f"Availability check failed: {str(e)}"
            self.logger.error(error_msg)
            return AvailabilityCheck(
                timestamp=datetime.now(),
                date=str(target_date),
                available_times=[],
                total_available=0,
                success=False,
                error_message=error_msg,
            )
        finally:
            if driver:
                driver.quit()

    def send_notification(self, check_result: AvailabilityCheck) -> None:
        """Send notification about availability check results.

        Args:
            check_result: AvailabilityCheck object with results
        """
        try:
            if check_result.success and check_result.total_available > 0:
                message = f"Tee times available for {check_result.date}!\n"
                message += f"Found {check_result.total_available} available times:\n"
                for time_slot in check_result.available_times:
                    message += f"- {time_slot}\n"

                # Send SNS notification if configured
                if "sns_topic_arn" in self.config:
                    self.sns.publish(
                        TopicArn=self.config["sns_topic_arn"],
                        Subject=f"Tee Time Alert - {check_result.date}",
                        Message=message,
                    )

                self.logger.info(f"Notification sent: {message}")
            else:
                self.logger.info(f"No availability found for {check_result.date}")

        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}")

    def log_metrics(self, check_result: AvailabilityCheck) -> None:
        """Log metrics to CloudWatch.

        Args:
            check_result: AvailabilityCheck object with results
        """
        try:
            # Log availability count
            self.cloudwatch.put_metric_data(
                Namespace="ForeUpBot/Monitoring",
                MetricData=[
                    {
                        "MetricName": "AvailableTeeTimes",
                        "Value": check_result.total_available,
                        "Unit": "Count",
                        "Timestamp": check_result.timestamp,
                        "Dimensions": [{"Name": "Date", "Value": check_result.date}],
                    },
                    {
                        "MetricName": "CheckSuccess",
                        "Value": 1 if check_result.success else 0,
                        "Unit": "Count",
                        "Timestamp": check_result.timestamp,
                    },
                ],
            )
        except Exception as e:
            self.logger.error(f"Failed to log metrics: {str(e)}")

    def run_continuous_monitoring(self, check_interval_minutes: int = 15) -> None:
        """Run continuous monitoring with specified interval.

        Args:
            check_interval_minutes: Interval between checks in minutes
        """
        self.logger.info(
            f"Starting continuous monitoring with {check_interval_minutes} minute intervals"
        )

        while True:
            try:
                # Check availability
                check_result = self.check_availability()

                # Log metrics
                self.log_metrics(check_result)

                # Send notification if availability found
                if check_result.success and check_result.total_available > 0:
                    self.send_notification(check_result)

                # Log results
                self.logger.info(
                    f"Check completed for {check_result.date}: "
                    f"{check_result.total_available} times available"
                )

                # Wait for next check
                time.sleep(check_interval_minutes * 60)

            except KeyboardInterrupt:
                self.logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retrying


def lambda_handler(event, context):
    """AWS Lambda handler for periodic availability checks.

    Args:
        event: Lambda event
        context: Lambda context

    Returns:
        Dictionary with status and results
    """
    import json
    import logging
    from datetime import datetime

    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Initialize AWS clients
        sns = boto3.client("sns", region_name="us-east-1")
        cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

        # Load configuration
        try:
            with open("foreup_config.json", "r") as f:
                config = json.load(f)
        except FileNotFoundError:
            # Fallback configuration for Lambda
            config = {
                "target_date": "08-09-2025",
                "monitoring": {
                    "aws_region": "us-east-1",
                    "check_interval_minutes": 15,
                    "sns_topic_arn": "arn:aws:sns:us-east-1:831372995959:foreup-monitoring-us-east-1",
                },
            }

        # Create a test availability check result
        check_result = AvailabilityCheck(
            timestamp=datetime.now(),
            date=config.get("target_date", "08-09-2025"),
            available_times=["10:00 AM", "10:30 AM", "11:00 AM"],
            total_available=3,
            success=True,
        )

        # Log metrics to CloudWatch
        try:
            cloudwatch.put_metric_data(
                Namespace="ForeUpMonitoring",
                MetricData=[
                    {
                        "MetricName": "AvailabilityChecks",
                        "Value": 1,
                        "Unit": "Count",
                        "Timestamp": check_result.timestamp,
                    },
                    {
                        "MetricName": "AvailableTimes",
                        "Value": check_result.total_available,
                        "Unit": "Count",
                        "Timestamp": check_result.timestamp,
                    },
                ],
            )
            logger.info("Metrics logged to CloudWatch")
        except Exception as e:
            logger.error(f"Failed to log metrics: {str(e)}")

        # Send notification to SNS
        try:
            sns_topic_arn = config["monitoring"]["sns_topic_arn"]
            message = {
                "subject": f"ForeUp Tee Time Alert - {check_result.date}",
                "body": f"Found {check_result.total_available} available tee times: {', '.join(check_result.available_times)}",
                "timestamp": check_result.timestamp.isoformat(),
                "date": check_result.date,
                "available_times": check_result.available_times,
                "total_available": check_result.total_available,
            }

            sns.publish(
                TopicArn=sns_topic_arn,
                Subject=message["subject"],
                Message=json.dumps(message, indent=2),
            )
            logger.info(f"Notification sent to SNS topic: {sns_topic_arn}")
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")

        logger.info(f"Lambda execution completed successfully for {check_result.date}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "success": check_result.success,
                    "date": check_result.date,
                    "available_times": check_result.available_times,
                    "total_available": check_result.total_available,
                    "timestamp": check_result.timestamp.isoformat(),
                    "message": "Lambda test execution completed successfully",
                }
            ),
        }

    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


if __name__ == "__main__":
    # Example usage for local testing
    monitor = ForeUpMonitor(
        config_path="../config/foreup_config.json",
        credentials_path="../config/credentials.json",
    )

    # Run continuous monitoring
    monitor.run_continuous_monitoring(check_interval_minutes=15)
