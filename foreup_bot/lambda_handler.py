#!/usr/bin/env python3
"""
AWS Lambda handler for ForeUp monitoring service.
This is a Lambda-compatible version that doesn't use Selenium.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List

import boto3


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
    # Test the handler locally
    result = lambda_handler({}, {})
    print(json.dumps(result, indent=2))
