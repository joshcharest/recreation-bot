#!/usr/bin/env python3
"""AWS Lambda handler for ForeUp tee time monitoring using Playwright."""

import json
import logging
import sys

# Add the monitoring directory to the path so we can import the Playwright monitor
sys.path.append("monitoring")

from playwright_monitor import PlaywrightForeUpMonitor


def lambda_handler(event, context):
    """AWS Lambda handler for Playwright-based monitoring."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config_path = "config/foreup_config.json"
        credentials_path = "config/credentials.json"

        # Create monitor with headless=True for Lambda
        monitor = PlaywrightForeUpMonitor(config_path, credentials_path, headless=True)

        # Perform single check
        check_result = monitor.check_availability()

        # Convert to Lambda response format
        available_times = []
        for time_slot in check_result.available_times:
            # Parse the time slot format (e.g., "4:48pm (4 spots)")
            import re

            time_match = re.search(r"(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))", time_slot)
            spots_match = re.search(r"(\d+)\s*spots?", time_slot)

            if time_match:
                time_str = time_match.group(1)
                available_spots = int(spots_match.group(1)) if spots_match else 4
                available_times.append(
                    {
                        "time": time_str,
                        "available_spots": available_spots,
                        "price": None,
                    }
                )

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
                    "available_times": available_times,
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
