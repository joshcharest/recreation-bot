#!/usr/bin/env python3
"""AWS Lambda handler for ForeUp tee time monitoring using requests/BeautifulSoup."""

import json
import logging
import sys

# Add the monitoring directory to the path so we can import the Lambda monitor
sys.path.append("monitoring")

from lambda_monitor import LambdaForeUpMonitor


def lambda_handler(event, context):
    """AWS Lambda handler for Playwright-based monitoring."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config_path = "config/foreup_config.json"
        credentials_path = "config/credentials.json"

        # Create monitor
        monitor = LambdaForeUpMonitor(config_path, credentials_path)

        # Perform single check
        check_result = monitor.check_availability()

        # Send notification if available times found
        if check_result.total_available > 0:
            monitor.send_notification(check_result)

        # Log metrics
        monitor.log_metrics(check_result)

        # Convert TeeTime objects to dictionaries for JSON serialization
        available_times = []
        for tee_time in check_result.available_times:
            available_times.append(
                {
                    "time": tee_time.time,
                    "available_spots": tee_time.available_spots,
                    "price": tee_time.price,
                }
            )

        # Return result
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "success": check_result.success,
                    "date": check_result.date,
                    "available_times": available_times,
                    "total_available": check_result.total_available,
                    "timestamp": check_result.timestamp.isoformat(),
                    "message": "Lambda monitoring completed successfully"
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
