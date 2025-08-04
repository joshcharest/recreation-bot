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

    def __init__(self, config_path: str, credentials_path: str):
        """Initialize the monitoring service.

        Args:
            config_path: Path to the configuration file
            credentials_path: Path to the credentials file
        """
        self.logger = self._setup_logger()
        self.config = self._load_config(config_path)
        self.credentials = self._load_config(credentials_path)
        self.base_url = "https://foreupsoftware.com/index.php/booking/19348/1470"
        self.cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")
        self.sns = boto3.client("sns", region_name="us-east-1")

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

    def _setup_driver(self, headless: bool = True) -> webdriver.Chrome:
        """Set up Chrome WebDriver for monitoring.

        Args:
            headless: Whether to run in headless mode

        Returns:
            Configured Chrome WebDriver
        """
        options = Options()
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")
            options.add_argument("--disable-javascript")
            options.add_argument("--disable-css")
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
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

        try:
            # Try to use system ChromeDriver first
            service = Service("chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
        except Exception:
            # Fall back to webdriver-manager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver

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

            # Click on Reservations link (if not logged in)
            try:
                reservations_link = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "a[href='#/teetimes']")
                    )
                )
                reservations_link.click()
                time.sleep(1)
            except:
                # Already on reservations page or different layout
                pass

            # Click BOOK NOW button
            book_now_button = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "button.btn.btn-primary.col-md-4.col-xs-12.col-md-offset-4",
                    )
                )
            )
            book_now_button.click()

            # Select date
            date_field = wait.until(
                EC.presence_of_element_located((By.ID, "date-field"))
            )
            date_field.clear()
            date_field.send_keys(target_date)
            date_field.send_keys("\n")  # Press Enter

            # Wait for time slots to load
            time.sleep(2)

            # Find all available times
            available_times = driver.find_elements(
                By.CSS_SELECTOR, "div.time.time-tile:not(.unavailable)"
            )

            time_slots = []
            for time_element in available_times:
                try:
                    time_str = time_element.find_element(
                        By.CSS_SELECTOR, "div.booking-start-time-label"
                    ).text
                    time_slots.append(time_str)
                except:
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
    try:
        # Initialize monitor
        monitor = ForeUpMonitor(
            config_path="../config/foreup_config.json",
            credentials_path="../config/credentials.json",
        )

        # Check availability
        check_result = monitor.check_availability()

        # Log metrics
        monitor.log_metrics(check_result)

        # Send notification if availability found
        if check_result.success and check_result.total_available > 0:
            monitor.send_notification(check_result)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "success": check_result.success,
                    "date": check_result.date,
                    "available_times": check_result.available_times,
                    "total_available": check_result.total_available,
                    "timestamp": check_result.timestamp.isoformat(),
                }
            ),
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


if __name__ == "__main__":
    # Example usage for local testing
    monitor = ForeUpMonitor(
        config_path="../config/foreup_config.json",
        credentials_path="../config/credentials.json",
    )

    # Run continuous monitoring
    monitor.run_continuous_monitoring(check_interval_minutes=15)
