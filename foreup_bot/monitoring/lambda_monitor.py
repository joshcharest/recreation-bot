#!/usr/bin/env python3
"""
Lambda-compatible ForeUp monitoring service using requests and BeautifulSoup.
This version is designed to work in AWS Lambda without Playwright dependencies.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import boto3
import requests
from bs4 import BeautifulSoup


@dataclass
class TeeTime:
    """Represents a tee time slot."""

    time: str
    available_spots: int
    price: Optional[str] = None


@dataclass
class CheckResult:
    """Result of a tee time availability check."""

    success: bool
    date: str
    available_times: List[TeeTime]
    total_available: int
    timestamp: datetime
    error_message: Optional[str] = None


class LambdaForeUpMonitor:
    """Lambda-compatible ForeUp monitoring service."""

    def __init__(self, config_path: str, credentials_path: str):
        """Initialize the monitor.

        Args:
            config_path: Path to configuration file
            credentials_path: Path to credentials file
        """
        self.logger = logging.getLogger(__name__)

        # Load configuration
        with open(config_path, "r") as f:
            self.config = json.load(f)

        with open(credentials_path, "r") as f:
            self.credentials = json.load(f)

        # Initialize session
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

        # AWS services (optional for local monitoring)
        try:
            self.sns = boto3.client("sns")
            self.cloudwatch = boto3.client("cloudwatch")
        except Exception as e:
            self.logger.warning(f"AWS services not available: {str(e)}")
            self.sns = None
            self.cloudwatch = None

    def _login_to_foreup(self) -> bool:
        """Login to ForeUp website.

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Get login page first
            login_url = "https://foreupsoftware.com/index.php/booking/19348/1470#/login"
            response = self.session.get(login_url)
            response.raise_for_status()

            # Extract CSRF token if needed
            soup = BeautifulSoup(response.text, "html.parser")
            csrf_token = soup.find("input", {"name": "_token"})
            csrf_value = ""
            if csrf_token and hasattr(csrf_token, "get"):
                csrf_value = csrf_token.get("value", "")

            # Prepare login data
            login_data = {
                "username": self.credentials["username"],
                "password": self.credentials["password"],
                "_token": csrf_value,
            }

            # Attempt login
            login_response = self.session.post(login_url, data=login_data)

            # Check if login was successful
            if (
                "logout" in login_response.text.lower()
                or "dashboard" in login_response.text.lower()
            ):
                self.logger.info("Login successful")
                return True
            else:
                self.logger.error(
                    "Login failed - could not find logout/dashboard indicators"
                )
                return False

        except Exception as e:
            self.logger.error(f"Login error: {str(e)}")
            return False

    def _get_tee_times_page(self) -> Optional[str]:
        """Navigate to tee times page and get content.

        Returns:
            Page HTML content or None if failed
        """
        try:
            # Navigate to tee times page
            tee_times_url = (
                "https://foreupsoftware.com/index.php/booking/19348/1470#/teetimes"
            )
            response = self.session.get(tee_times_url)
            response.raise_for_status()

            return response.text

        except Exception as e:
            self.logger.error(f"Error getting tee times page: {str(e)}")
            return None

    def _extract_tee_times(self, html_content: str) -> List[TeeTime]:
        """Extract tee times from HTML content.

        Args:
            html_content: HTML content of the tee times page

        Returns:
            List of available tee times
        """
        tee_times = []
        required_players = self.config.get("num_players", 4)

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Look for different types of tee time elements (similar to Playwright selectors)
            selectors = [
                ".booking-slot:not(.unavailable)",
                ".time-slot:not(.unavailable)",
                ".teetime:not(.unavailable)",
                ".time:not(.unavailable)",
                "[data-time]:not(.unavailable)",
                ".available-time",
                ".time-tile:not(.unavailable)",
                ".tee-time",
                ".time-slot",
                ".time",
                ".booking-slot",
                ".teetime",
            ]

            for selector in selectors:
                # Convert CSS selector to BeautifulSoup find_all
                if selector.startswith("."):
                    class_name = selector[1:]  # Remove the dot
                    if ":not(.unavailable)" in selector:
                        class_name = class_name.replace(":not(.unavailable)", "")
                        elements = soup.find_all(attrs={"class": class_name})
                        # Filter out elements with "unavailable" class
                        elements = [
                            el
                            for el in elements
                            if "unavailable" not in (el.get("class") or [])
                        ]
                    else:
                        elements = soup.find_all(attrs={"class": class_name})
                elif selector.startswith("[data-time]"):
                    elements = soup.find_all(attrs={"data-time": True})
                    if ":not(.unavailable)" in selector:
                        elements = [
                            el
                            for el in elements
                            if "unavailable" not in (el.get("class") or [])
                        ]
                else:
                    elements = []

                for element in elements[:20]:  # Limit to first 20
                    try:
                        text = element.get_text().strip()
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
                                        tee_times.append(
                                            TeeTime(
                                                time=time_str,
                                                available_spots=available_spots,
                                            )
                                        )
                                else:
                                    # Assume 4 spots if not specified
                                    tee_times.append(
                                        TeeTime(time=time_str, available_spots=4)
                                    )

                    except Exception as e:
                        self.logger.warning(f"Error processing element: {str(e)}")
                        continue

                if tee_times:
                    break

            # If no structured elements found, try to extract from all text
            if not tee_times:
                all_text = soup.get_text()
                import re

                time_pattern = r"(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))"
                time_matches = re.findall(time_pattern, all_text)

                if time_matches:
                    unique_times = list(set(time_matches))
                    for time_str in unique_times[:10]:  # Limit to first 10
                        tee_times.append(TeeTime(time=time_str, available_spots=4))

        except Exception as e:
            self.logger.error(f"Error extracting tee times: {str(e)}")

        return tee_times

    def check_availability(self) -> CheckResult:
        """Check tee time availability.

        Returns:
            CheckResult with availability information
        """
        try:
            self.logger.info("Starting availability check...")

            # Login to ForeUp
            if not self._login_to_foreup():
                return CheckResult(
                    success=False,
                    date=self.config.get("target_date", "unknown"),
                    available_times=[],
                    total_available=0,
                    timestamp=datetime.now(),
                    error_message="Login failed",
                )

            # Get tee times page
            html_content = self._get_tee_times_page()
            if not html_content:
                return CheckResult(
                    success=False,
                    date=self.config.get("target_date", "unknown"),
                    available_times=[],
                    total_available=0,
                    timestamp=datetime.now(),
                    error_message="Failed to get tee times page",
                )

            # Extract tee times
            available_times = self._extract_tee_times(html_content)
            total_available = len(available_times)

            self.logger.info(f"Found {total_available} available tee times")

            return CheckResult(
                success=True,
                date=self.config.get("target_date", "unknown"),
                available_times=available_times,
                total_available=total_available,
                timestamp=datetime.now(),
            )

        except Exception as e:
            self.logger.error(f"Availability check failed: {str(e)}")
            return CheckResult(
                success=False,
                date=self.config.get("target_date", "unknown"),
                available_times=[],
                total_available=0,
                timestamp=datetime.now(),
                error_message=str(e),
            )

    def send_notification(self, result: CheckResult) -> None:
        """Send notification about available tee times.

        Args:
            result: Check result with availability information
        """
        if not self.sns:
            self.logger.warning("SNS not available, skipping notification")
            return

        try:
            topic_arn = self.config["monitoring"]["sns_topic_arn"]

            # Create message
            if result.available_times:
                times_list = "\n".join(
                    [
                        f"  - {t.time} ({t.available_spots} spots)"
                        for t in result.available_times
                    ]
                )
                message = f"""🏌️‍♂️ Tee Times Available!

Date: {result.date}
Available Times: {result.total_available}

{times_list}

Check: https://foreupsoftware.com/index.php/booking/19348/1470#/teetimes
"""
            else:
                message = f"No tee times available for {result.date}"

            # Send notification
            self.sns.publish(
                TopicArn=topic_arn, Subject="ForeUp Tee Time Alert", Message=message
            )

            self.logger.info("Notification sent successfully")

        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}")

    def log_metrics(self, result: CheckResult) -> None:
        """Log metrics to CloudWatch.

        Args:
            result: Check result with availability information
        """
        if not self.cloudwatch:
            self.logger.warning("CloudWatch not available, skipping metrics")
            return

        try:
            # Log availability count
            self.cloudwatch.put_metric_data(
                Namespace="ForeUpMonitor",
                MetricData=[
                    {
                        "MetricName": "AvailableTeeTimes",
                        "Value": result.total_available,
                        "Unit": "Count",
                        "Timestamp": result.timestamp,
                    },
                    {
                        "MetricName": "CheckSuccess",
                        "Value": 1 if result.success else 0,
                        "Unit": "Count",
                        "Timestamp": result.timestamp,
                    },
                ],
            )

            self.logger.info("Metrics logged successfully")

        except Exception as e:
            self.logger.error(f"Failed to log metrics: {str(e)}")
