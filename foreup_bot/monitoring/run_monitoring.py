"""
Local monitoring runner for ForeUp tee time availability.

This script runs the monitoring service locally for testing purposes.
It can be used to verify the monitoring functionality before deploying to AWS.
"""

import json
import logging
import os
import sys

# Add the monitoring directory to the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from monitoring_service import ForeUpMonitor


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("monitoring.log"), logging.StreamHandler()],
    )
    return logging.getLogger(__name__)


def main():
    """Main function to run local monitoring."""
    logger = setup_logging()

    try:
        # Get the script directory and construct absolute paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "..", "config", "foreup_config.json")
        credentials_path = os.path.join(script_dir, "..", "config", "credentials.json")

        # Load configuration
        with open(config_path, "r") as f:
            config = json.load(f)

        logger.info("Starting ForeUp monitoring service...")
        logger.info(f"Target date: {config['target_date']}")
        logger.info(
            f"Check interval: {config['monitoring']['check_interval_minutes']} minutes"
        )

        # Initialize monitor
        monitor = ForeUpMonitor(
            config_path=config_path,
            credentials_path=credentials_path,
        )

        # Run a single check first
        logger.info("Performing initial availability check...")
        check_result = monitor.check_availability()

        if check_result.success:
            logger.info(
                f"Initial check successful: {check_result.total_available} times available"
            )
            if check_result.available_times:
                logger.info("Available times:")
                for time_slot in check_result.available_times:
                    logger.info(f"  - {time_slot}")
        else:
            logger.error(f"Initial check failed: {check_result.error_message}")

        # Ask user if they want to run continuous monitoring
        print("\n" + "=" * 50)
        print("Initial check completed!")
        print("=" * 50)

        if check_result.success and check_result.total_available > 0:
            print(f"✅ Found {check_result.total_available} available tee times!")
            print("Available times:")
            for time_slot in check_result.available_times:
                print(f"  - {time_slot}")
        else:
            print("❌ No available tee times found or check failed")

        print("\nOptions:")
        print("1. Run continuous monitoring")
        print("2. Run another single check")
        print("3. Exit")

        while True:
            choice = input("\nEnter your choice (1-3): ").strip()

            if choice == "1":
                print("\nStarting continuous monitoring...")
                print("Press Ctrl+C to stop")
                try:
                    monitor.run_continuous_monitoring(
                        check_interval_minutes=config["monitoring"][
                            "check_interval_minutes"
                        ]
                    )
                except KeyboardInterrupt:
                    print("\nMonitoring stopped by user")
                    break

            elif choice == "2":
                print("\nPerforming another availability check...")
                check_result = monitor.check_availability()

                if check_result.success:
                    print(
                        f"Check completed: {check_result.total_available} times available"
                    )
                    if check_result.available_times:
                        print("Available times:")
                        for time_slot in check_result.available_times:
                            print(f"  - {time_slot}")
                else:
                    print(f"Check failed: {check_result.error_message}")

            elif choice == "3":
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        print(
            "Error: Configuration file not found. Please ensure config/foreup_config.json and config/credentials.json exist."
        )
        return 1
    except Exception as e:
        logger.error(f"Monitoring failed: {str(e)}")
        print(f"Error: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
