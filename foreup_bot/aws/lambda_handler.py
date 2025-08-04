#!/usr/bin/env python3
"""
AWS Lambda handler for ForeUp monitoring service.
This uses the same Selenium-based approach as local monitoring.
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List

import boto3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait


@dataclass
class AvailabilityCheck:
    """Data class for storing availability check results."""

    timestamp: datetime
    date: str
    available_times: List[str]
    total_available: int
    success: bool
    error_message: str = ""


def lambda_handler(event, context):
    """AWS Lambda handler for periodic availability checks.

    Args:
        event: Lambda event
        context: Lambda context

    Returns:
        Dictionary with status and results
    """
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
                "num_players": 4,
                "monitoring": {
                    "aws_region": "us-east-1",
                    "check_interval_minutes": 15,
                    "sns_topic_arn": "arn:aws:sns:us-east-1:831372995959:foreup-monitoring-us-east-1",
                },
            }

        # Load credentials
        try:
            with open("credentials.json", "r") as f:
                credentials = json.load(f)
        except FileNotFoundError:
            logger.error("Credentials file not found")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Credentials not found"}),
            }

        # Perform actual availability check using Selenium
        check_result = perform_availability_check(config, credentials, logger)

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

        # Send notification to SNS if availability found
        if check_result.success and check_result.total_available > 0:
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
                    "message": "Lambda monitoring completed successfully",
                }
            ),
        }

    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def setup_chrome_driver(logger: logging.Logger) -> webdriver.Chrome:
    """Set up Chrome WebDriver for Lambda environment."""

    options = Options()

    # Lambda-specific Chrome options
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--disable-animations")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-features=TranslateUI")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-component-extensions-with-background-pages")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--mute-audio")
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

    # Try to use Chrome from Lambda layer if available
    chrome_paths = [
        "/opt/chrome/chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
    ]

    chrome_binary = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_binary = path
            break

    if chrome_binary:
        options.binary_location = chrome_binary
        logger.info(f"Using Chrome binary: {chrome_binary}")
    else:
        logger.warning("Chrome binary not found, using system default")

    # Try to use ChromeDriver from Lambda layer if available
    chromedriver_paths = [
        "/opt/chromedriver",
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
    ]

    chromedriver_path = None
    for path in chromedriver_paths:
        if os.path.exists(path):
            chromedriver_path = path
            break

    if chromedriver_path:
        service = Service(executable_path=chromedriver_path)
        logger.info(f"Using ChromeDriver: {chromedriver_path}")
    else:
        service = Service()
        logger.warning("ChromeDriver not found, using system default")

    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return driver
    except Exception as e:
        logger.error(f"Failed to create Chrome driver: {str(e)}")
        raise


def login_to_foreup(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    credentials: dict,
    logger: logging.Logger,
) -> bool:
    """Log into ForeUp using credentials."""

    try:
        # Look for login form
        try:
            # Find username field
            username_field = wait.until(
                EC.presence_of_element_located((By.ID, "login_email"))
            )

            # Clear and enter username
            username_field.clear()
            username_field.send_keys(credentials["username"])
            logger.info("Entered username")

            # Find password field
            password_field = driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(credentials["password"])
            logger.info("Entered password")

            # Find and click login button
            login_button = driver.find_element(
                By.CSS_SELECTOR, "input[type='submit'], button[type='submit']"
            )
            login_button.click()
            logger.info("Clicked login button")

            # Wait for login to complete
            time.sleep(2)
            logger.info("Login attempt completed")
            return True

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"Login process failed: {str(e)}")
        return False


def perform_availability_check(
    config: dict, credentials: dict, logger: logging.Logger
) -> AvailabilityCheck:
    """Perform availability check using Selenium (same as local monitoring)."""

    driver = None
    try:
        logger.info("Setting up Chrome driver...")
        driver = setup_chrome_driver(logger)
        wait = WebDriverWait(driver, 30)

        # Navigate to the booking page
        base_url = "https://foreupsoftware.com/index.php/booking/19348/1470"
        logger.info("Navigating to ForeUp...")
        driver.get(base_url)
        time.sleep(2)

        # Login to ForeUp
        logger.info("Attempting login...")
        if not login_to_foreup(driver, wait, credentials, logger):
            raise Exception("Failed to login to ForeUp")

        # Navigate directly to the tee times page
        tee_times_url = (
            "https://foreupsoftware.com/index.php/booking/19348/1470#/teetimes"
        )
        logger.info("Navigating to tee times page...")
        driver.get(tee_times_url)
        logger.info("Navigated to tee times page")

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
            logger.info("Found STANDARD TEE TIMES button, clicking...")
            standard_tee_times_button.click()
            time.sleep(2)
            logger.info("Clicked STANDARD TEE TIMES button")
        except Exception as e:
            logger.error(f"Could not find STANDARD TEE TIMES button: {str(e)}")
            raise

        # Select date from dropdown
        try:
            date_dropdown = wait.until(
                EC.presence_of_element_located((By.ID, "date-menu"))
            )
            logger.info("Found date dropdown")

            # Select the target date from the dropdown
            select = Select(date_dropdown)
            target_date = config.get("target_date", "08-09-2025")
            select.select_by_value(str(target_date))
            logger.info(f"Selected date: {target_date}")

        except Exception as e:
            logger.error(f"Could not find or interact with date dropdown: {str(e)}")
            raise

        # Wait for time slots to load
        time.sleep(2)

        # Find all available times
        available_times = driver.find_elements(
            By.CSS_SELECTOR, "div.time.time-tile:not(.unavailable)"
        )

        time_slots = []
        required_players = config.get("num_players", 4)
        logger.info(f"Looking for tee times with at least {required_players} players")

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
                    logger.info(
                        f"Found suitable time: {time_str} with {available_spots} spots"
                    )
                else:
                    logger.info(
                        f"Skipping {time_str} - only {available_spots} spots available"
                    )

            except Exception as e:
                logger.warning(f"Error processing time element: {str(e)}")
                continue

        logger.info(f"Found {len(time_slots)} available tee times")

        return AvailabilityCheck(
            timestamp=datetime.now(),
            date=config.get("target_date", "08-09-2025"),
            available_times=time_slots,
            total_available=len(time_slots),
            success=True,
        )

    except Exception as e:
        logger.error(f"Availability check failed: {str(e)}")
        return AvailabilityCheck(
            timestamp=datetime.now(),
            date=config.get("target_date", "08-09-2025"),
            available_times=[],
            total_available=0,
            success=False,
            error_message=str(e),
        )
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    # Test the handler locally
    result = lambda_handler({}, {})
    print(json.dumps(result, indent=2))
