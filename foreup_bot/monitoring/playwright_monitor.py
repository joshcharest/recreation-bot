#!/usr/bin/env python3
"""Playwright-based monitoring service for ForeUp tee time availability."""

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import boto3
from playwright.sync_api import Page, sync_playwright


@dataclass
class AvailabilityCheck:
    """Data class for storing availability check results."""

    timestamp: datetime
    date: str
    available_times: List[str]
    total_available: int
    success: bool
    error_message: Optional[str] = None


class PlaywrightForeUpMonitor:
    """Playwright-based monitoring service for ForeUp tee time availability."""

    def __init__(self, config_path: str, credentials_path: str, headless: bool = True):
        """Initialize the monitoring service.

        Args:
            config_path: Path to the configuration file
            credentials_path: Path to the credentials file
            headless: Whether to run browser in headless mode
        """
        self.config = self._load_config(config_path)
        self.credentials = self._load_config(credentials_path)
        self.headless = headless
        self.logger = self._setup_logger()

        # AWS services (optional for local monitoring)
        try:
            self.sns = boto3.client("sns")
            self.cloudwatch = boto3.client("cloudwatch")
        except Exception as e:
            self.logger.warning(f"AWS services not available: {str(e)}")
            self.sns = None
            self.cloudwatch = None

    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        with open(config_path, "r") as f:
            return json.load(f)

    def _login_to_foreup(self, page: Page) -> bool:
        """Log into ForeUp using Playwright.

        Args:
            page: Playwright page object

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Navigate to the booking page
            page.goto("https://foreupsoftware.com/index.php/booking/19348/1470")

            # Wait for the page to load
            page.wait_for_load_state("networkidle")

            # Fill in username/email
            username_input = page.locator(
                "input[name='username'], input[id='login_email']"
            )
            if username_input.count() > 0:
                username_input.first.fill(self.credentials["username"])
            else:
                self.logger.error("Username field not found")
                return False

            # Fill in password
            password_input = page.locator(
                "input[name='password'], input[id='login_password']"
            )
            if password_input.count() > 0:
                password_input.first.fill(self.credentials["password"])
            else:
                self.logger.error("Password field not found")
                return False

            # Submit the form
            submit_button = page.locator("input[type='submit'], button[type='submit']")
            if submit_button.count() > 0:
                submit_button.first.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)  # Wait for login to process
            else:
                self.logger.error("Submit button not found")
                return False

            # Check if login was successful
            # Look for logout button or user info
            logout_button = page.locator("a[href*='logout'], button.logout, .user-info")
            if logout_button.count() > 0:
                self.logger.info("Login successful - found logout button")
                return True
            else:
                # Check if there's an error message
                error_elements = page.locator(".alert-danger, .error, .login-error")
                if error_elements.count() > 0:
                    error_text = error_elements.first.text_content()
                    self.logger.error(f"Login failed: {error_text}")
                    return False
                else:
                    # Check if we're still on the login page
                    current_url = page.url
                    if "login" in current_url.lower():
                        self.logger.error("Still on login page, login may have failed")
                        return False
                    else:
                        # If we're not on login page and no errors, login was likely successful
                        self.logger.info(
                            "Login appears successful - proceeding to next step"
                        )
                        return True

        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            return False

    def _navigate_to_tee_times(self, page: Page) -> bool:
        """Navigate to the tee times page.

        Args:
            page: Playwright page object

        Returns:
            True if navigation successful, False otherwise
        """
        try:
            # Navigate to tee times page
            page.goto(
                "https://foreupsoftware.com/index.php/booking/19348/1470#/teetimes"
            )
            page.wait_for_load_state("networkidle")

            # Wait for the page to load and look for tee times content
            # The page might take some time to load the JavaScript content
            page.wait_for_timeout(5000)  # Wait 5 seconds for JavaScript to load

            # Set the target date if specified in config
            target_date = self.config.get("target_date")

            # Look for tee times content
            tee_times_content = page.locator(
                ".teetimes, .tee-times, .booking-slot, .time-slot"
            )
            if tee_times_content.count() > 0:
                self.logger.info("Found tee times content")
                return True

            # If no tee times found, check if we need to click a button
            standard_button = page.locator("button:has-text('STANDARD TEE TIMES')")
            if standard_button.count() > 0:
                standard_button.first.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)  # Wait for content to load

                # Now set the target date if specified in config
                if target_date:
                    # Look for the date input field (should be visible now)
                    date_input = page.locator(
                        "input[name='date'], input[id='date-field'], input[placeholder*='MM-DD-YYYY']"
                    )
                    if date_input.count() > 0:
                        # Try multiple approaches to set the date
                        try:
                            # Method 1: Direct fill
                            date_input.first.fill(target_date)
                            page.wait_for_timeout(1000)

                            # Method 2: JavaScript set value
                            page.evaluate(f"""
                                document.getElementById('date-field').value = '{target_date}';
                                document.getElementById('date-field').dispatchEvent(new Event('change', {{ bubbles: true }}));
                                document.getElementById('date-field').dispatchEvent(new Event('input', {{ bubbles: true }}));
                            """)
                            page.wait_for_timeout(1000)

                            # Method 3: Trigger events
                            date_input.first.press("Enter")
                            page.wait_for_timeout(1000)
                            page.keyboard.press("Tab")
                            page.wait_for_timeout(1000)

                        except Exception as e:
                            self.logger.error(f"Error setting date: {str(e)}")
                    else:
                        self.logger.warning(
                            "Date input field not found after clicking button"
                        )

                return True

            self.logger.warning("No tee times content found")
            return False

        except Exception as e:
            self.logger.error(f"Navigation failed: {str(e)}")
            return False

    def _extract_tee_times(self, page: Page) -> List[str]:
        """Extract available tee times from the page.

        Args:
            page: Playwright page object

        Returns:
            List of available tee times
        """
        available_times = []
        required_players = self.config.get("num_players", 4)

        try:
            # Look for different types of tee time elements
            selectors = [
                ".booking-slot:not(.unavailable)",
                ".time-slot:not(.unavailable)",
                ".teetime:not(.unavailable)",
                ".time:not(.unavailable)",
                "[data-time]:not(.unavailable)",
                ".available-time",
                ".time-tile:not(.unavailable)",
            ]

            for selector in selectors:
                elements = page.locator(selector)
                if elements.count() > 0:
                    for i in range(min(elements.count(), 20)):  # Limit to first 20
                        try:
                            element = elements.nth(i)
                            text = element.text_content()

                            if text:
                                # Look for time patterns
                                import re

                                time_pattern = r"(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))"
                                time_matches = re.findall(time_pattern, text)

                                if time_matches:
                                    time_str = time_matches[0]

                                    # Look for player count
                                    player_pattern = r"(\d+)\s*(?:spots?|players?)"
                                    player_matches = re.findall(player_pattern, text)

                                    if player_matches:
                                        available_spots = int(player_matches[0])
                                        if available_spots >= required_players:
                                            available_times.append(
                                                f"{time_str} ({available_spots} spots)"
                                            )
                                    else:
                                        # Assume 4 spots if not specified
                                        available_times.append(f"{time_str} (4 spots)")

                        except Exception as e:
                            self.logger.warning(
                                f"Error processing element {i}: {str(e)}"
                            )
                            continue

                    if available_times:
                        break

            # If no structured elements found, try to extract from all text
            if not available_times:
                all_text = page.text_content()

                import re

                time_pattern = r"(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))"
                time_matches = re.findall(time_pattern, all_text)

                if time_matches:
                    unique_times = list(set(time_matches))
                    for time_str in unique_times[:10]:  # Limit to first 10
                        available_times.append(f"{time_str} (4 spots)")

            return available_times

        except Exception as e:
            self.logger.error(f"Error extracting tee times: {str(e)}")
            return []

    def check_availability(
        self, target_date: Optional[str] = None
    ) -> AvailabilityCheck:
        """Check tee time availability using Playwright.

        Args:
            target_date: Date to check (format: MM-DD-YYYY). If None, uses config date.

        Returns:
            AvailabilityCheck object with results
        """
        if target_date is None:
            target_date = self.config["target_date"]

        try:
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-accelerated-2d-canvas",
                        "--no-first-run",
                        "--no-zygote",
                        "--disable-gpu",
                    ],
                )

                # Create context
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )

                # Create page
                page = context.new_page()

                try:
                    # Login to ForeUp
                    if not self._login_to_foreup(page):
                        raise Exception("Failed to login to ForeUp")

                    # Navigate to tee times page
                    if not self._navigate_to_tee_times(page):
                        raise Exception("Failed to navigate to tee times page")

                    # Extract tee times
                    available_times = self._extract_tee_times(page)

                    return AvailabilityCheck(
                        timestamp=datetime.now(),
                        date=str(target_date),
                        available_times=available_times,
                        total_available=len(available_times),
                        success=True,
                    )

                finally:
                    # Clean up
                    page.close()
                    context.close()
                    browser.close()

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

                # Send SNS notification if configured and available
                if "sns_topic_arn" in self.config and self.sns:
                    self.sns.publish(
                        TopicArn=self.config["sns_topic_arn"],
                        Subject=f"Tee Time Alert - {check_result.date}",
                        Message=message,
                    )
                    self.logger.info("SNS notification sent")
                else:
                    self.logger.info(f"Notification: {message}")

        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}")

    def log_metrics(self, check_result: AvailabilityCheck) -> None:
        """Log metrics to CloudWatch.

        Args:
            check_result: AvailabilityCheck object with results
        """
        try:
            # Log availability count if CloudWatch is available
            if self.cloudwatch:
                self.cloudwatch.put_metric_data(
                    Namespace="ForeUpMonitor",
                    MetricData=[
                        {
                            "MetricName": "AvailableTeeTimes",
                            "Value": check_result.total_available,
                            "Unit": "Count",
                            "Dimensions": [
                                {"Name": "Course", "Value": "BalboaPark"},
                                {"Name": "Date", "Value": check_result.date},
                            ],
                        },
                        {
                            "MetricName": "CheckSuccess",
                            "Value": 1 if check_result.success else 0,
                            "Unit": "Count",
                            "Dimensions": [
                                {"Name": "Course", "Value": "BalboaPark"},
                            ],
                        },
                    ],
                )
                self.logger.info("Metrics logged to CloudWatch")
            else:
                self.logger.info("CloudWatch not available, skipping metrics")
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

        try:
            while True:
                self.logger.info("Starting availability check...")

                # Perform availability check
                check_result = self.check_availability()

                # Log results
                self.logger.info(
                    f"Check completed for {check_result.date}: {check_result.total_available} times available"
                )

                # Send notification if available times found
                if check_result.total_available > 0:
                    self.send_notification(check_result)

                # Log metrics
                self.log_metrics(check_result)

                # Wait for next check
                self.logger.info(
                    f"Waiting {check_interval_minutes} minutes until next check..."
                )
                time.sleep(check_interval_minutes * 60)

        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring failed: {str(e)}")


def lambda_handler(event, context):
    """AWS Lambda handler for Playwright-based monitoring."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config_path = "foreup_config.json"
        credentials_path = "credentials.json"

        # Create monitor
        monitor = PlaywrightForeUpMonitor(config_path, credentials_path, headless=True)

        # Perform single check
        check_result = monitor.check_availability()

        # Send notification if available times found
        if check_result.total_available > 0:
            monitor.send_notification(check_result)

        # Log metrics
        monitor.log_metrics(check_result)

        # Return result
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "success": check_result.success,
                    "date": check_result.date,
                    "available_times": check_result.available_times,
                    "total_available": check_result.total_available,
                    "timestamp": check_result.timestamp.isoformat(),
                    "message": "Playwright monitoring completed successfully"
                    if check_result.success
                    else check_result.error_message,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Lambda handler failed: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "success": False,
                    "error": str(e),
                    "message": "Lambda monitoring failed",
                }
            ),
        }


if __name__ == "__main__":
    # For local testing
    import sys

    if len(sys.argv) != 3:
        print("Usage: python playwright_monitor.py <config_path> <credentials_path>")
        sys.exit(1)

    config_path = sys.argv[1]
    credentials_path = sys.argv[2]

    monitor = PlaywrightForeUpMonitor(config_path, credentials_path, headless=True)
    monitor.run_continuous_monitoring()
