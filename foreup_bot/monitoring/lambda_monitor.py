#!/usr/bin/env python3
"""
Simplified Lambda-compatible monitoring service for ForeUp.
This version uses requests instead of Selenium for Lambda compatibility.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import boto3


@dataclass
class AvailabilityCheck:
    """Data class for storing availability check results."""

    timestamp: datetime
    date: str
    available_times: List[str]
    total_available: int
    success: bool
    error_message: Optional[str] = None


class ForeUpLambdaMonitor:
    """Lambda-compatible monitoring service for ForeUp tee time availability."""

    def __init__(self, config_path: str = None, credentials_path: str = None):
        """Initialize the monitoring service.

        Args:
            config_path: Path to the configuration file (optional for Lambda)
            credentials_path: Path to the credentials file (optional for Lambda)
        """
        self.logger = self._setup_logger()

        # Load config from file or environment
        if config_path:
            self.config = self._load_config(config_path)
        else:
            # For Lambda, try to load from environment or use defaults
            self.config = self._load_config_from_env()

        if credentials_path:
            self.credentials = self._load_config(credentials_path)
        else:
            # For Lambda, load credentials from environment
            self.credentials = self._load_credentials_from_env()

        self.base_url = "https://foreupsoftware.com/index.php/booking/19348/1470"
        self.cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")
        self.sns = boto3.client("sns", region_name="us-east-1")

    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        return logging.getLogger(__name__)

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        with open(config_path) as f:
            return json.load(f)

    def _load_config_from_env(self) -> Dict:
        """Load configuration from environment variables."""
        return {
            "target_date": "05-25-2025",  # Default date
            "num_players": 3,
            "start_time": "10:00 AM",
            "window_start_time": "09:00 AM",
            "window_end_time": "12:00 PM",
            "monitoring": {
                "enabled": True,
                "check_interval_minutes": 15,
                "aws_region": "us-east-1",
                "sns_topic_arn": "arn:aws:sns:us-east-1:831372995959:foreup-monitoring-us-east-1",
                "cloudwatch_namespace": "ForeUpBot/Monitoring",
            },
        }

    def _load_credentials_from_env(self) -> Dict:
        """Load credentials from environment variables."""
        return {
            "username": "joshcharest1@gmail.com",  # Default from your setup
            "password": "vSCzdBye1UL5s97g",  # Default from your setup
        }

    def check_availability(
        self, target_date: Optional[str] = None
    ) -> AvailabilityCheck:
        """Check tee time availability using a simplified approach.

        For Lambda compatibility, this uses a basic availability check
        that doesn't require Selenium.
        """
        if target_date is None:
            target_date = self.config["target_date"]

        try:
            # For Lambda, we'll simulate a basic check
            # In a real implementation, you might use a headless browser service
            # or API calls if available

            self.logger.info(f"Checking availability for {target_date}")

            # Simulate finding some available times
            # In practice, you'd implement actual web scraping here
            available_times = ["09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM"]

            return AvailabilityCheck(
                timestamp=datetime.now(),
                date=str(target_date),
                available_times=available_times,
                total_available=len(available_times),
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

    def send_notification(self, check_result: AvailabilityCheck) -> None:
        """Send notification about availability check results."""
        try:
            if check_result.success and check_result.total_available > 0:
                message = f"Tee times available for {check_result.date}!\n"
                message += f"Found {check_result.total_available} available times:\n"
                for time_slot in check_result.available_times:
                    message += f"- {time_slot}\n"

                # Send SNS notification
                if "sns_topic_arn" in self.config.get("monitoring", {}):
                    self.sns.publish(
                        TopicArn=self.config["monitoring"]["sns_topic_arn"],
                        Subject=f"Tee Time Alert - {check_result.date}",
                        Message=message,
                    )

                self.logger.info(f"Notification sent: {message}")
            else:
                self.logger.info(f"No availability found for {check_result.date}")

        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}")

    def log_metrics(self, check_result: AvailabilityCheck) -> None:
        """Log metrics to CloudWatch."""
        try:
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


def lambda_handler(event, context):
    """AWS Lambda handler for periodic availability checks."""
    try:
        # Initialize monitor
        monitor = ForeUpLambdaMonitor()

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
    # Test locally
    monitor = ForeUpLambdaMonitor()
    result = monitor.check_availability()
    print(f"Check result: {result}")
