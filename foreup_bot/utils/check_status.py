#!/usr/bin/env python3
"""
Status checking script for ForeUp monitoring service.
This script helps users check the health of their AWS deployment.
"""

import json
import os
from datetime import datetime, timedelta

import boto3


def check_lambda_function():
    """Check Lambda function status."""
    print("🔍 Checking Lambda function...")

    try:
        lambda_client = boto3.client("lambda", region_name="us-east-1")
        response = lambda_client.get_function(FunctionName="ForeUpMonitor")

        function_info = response["Configuration"]
        print(f"✅ Function: {function_info['FunctionName']}")
        print(f"   Status: {function_info['State']}")
        print(f"   Runtime: {function_info['Runtime']}")
        print(f"   Handler: {function_info['Handler']}")
        print(f"   Last Modified: {function_info['LastModified']}")

        return True
    except Exception as e:
        print(f"❌ Lambda function error: {e}")
        return False


def check_eventbridge_rule():
    """Check EventBridge rule status."""
    print("\n📅 Checking EventBridge rule...")

    try:
        events_client = boto3.client("events", region_name="us-east-1")
        response = events_client.describe_rule(Name="ForeUpMonitorSchedule")

        rule_info = response
        print(f"✅ Rule: {rule_info['Name']}")
        print(f"   State: {rule_info['State']}")
        print(f"   Schedule: {rule_info['ScheduleExpression']}")

        return True
    except Exception as e:
        print(f"❌ EventBridge rule error: {e}")
        return False


def check_sns_topic():
    """Check SNS topic status."""
    print("\n📧 Checking SNS topic...")

    try:
        sns_client = boto3.client("sns", region_name="us-east-1")

        # Get topic ARN from config
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "..", "config", "foreup_config.json")
        with open(config_path, "r") as f:
            config = json.load(f)

        topic_arn = config["monitoring"]["sns_topic_arn"]

        # List subscriptions
        response = sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)

        print(f"✅ Topic: {topic_arn.split(':')[-1]}")
        print(f"   Subscriptions: {len(response['Subscriptions'])}")

        for sub in response["Subscriptions"]:
            status = sub.get("Status", "Unknown")
            print(f"   - {sub['Endpoint']} ({status})")

        return True
    except Exception as e:
        print(f"❌ SNS topic error: {e}")
        return False


def check_cloudwatch_logs():
    """Check recent CloudWatch logs."""
    print("\n📊 Checking CloudWatch logs...")

    try:
        logs_client = boto3.client("logs", region_name="us-east-1")

        # Get recent log streams
        response = logs_client.describe_log_streams(
            logGroupName="/aws/lambda/ForeUpMonitor",
            orderBy="LastEventTime",
            descending=True,
            limit=3,
        )

        if not response["logStreams"]:
            print("⚠️  No log streams found")
            return False

        print(f"✅ Found {len(response['logStreams'])} recent log streams")

        # Get events from the most recent stream
        latest_stream = response["logStreams"][0]
        print(f"   Latest stream: {latest_stream['logStreamName']}")

        # Get recent events
        events_response = logs_client.get_log_events(
            logGroupName="/aws/lambda/ForeUpMonitor",
            logStreamName=latest_stream["logStreamName"],
            startTime=int((datetime.now() - timedelta(hours=1)).timestamp() * 1000),
            limit=10,
        )

        if events_response["events"]:
            print("   Recent events:")
            for event in events_response["events"][-3:]:  # Show last 3 events
                timestamp = datetime.fromtimestamp(event["timestamp"] / 1000)
                print(f"   - {timestamp}: {event['message'].strip()}")
        else:
            print("   No recent events")

        return True
    except Exception as e:
        print(f"❌ CloudWatch logs error: {e}")
        return False


def check_cloudwatch_metrics():
    """Check CloudWatch metrics."""
    print("\n📈 Checking CloudWatch metrics...")

    try:
        cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

        # Get metrics from the last hour
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)

        response = cloudwatch.get_metric_statistics(
            Namespace="ForeUpMonitoring",
            MetricName="AvailableTimes",
            StartTime=start_time,
            EndTime=end_time,
            Period=300,  # 5-minute periods
            Statistics=["Average", "Maximum"],
        )

        if response["Datapoints"]:
            print("✅ Recent metrics found:")
            for datapoint in response["Datapoints"]:
                timestamp = datapoint["Timestamp"]
                avg = datapoint["Average"]
                max_val = datapoint["Maximum"]
                print(f"   {timestamp}: Avg={avg:.1f}, Max={max_val}")
        else:
            print("⚠️  No recent metrics found")

        return True
    except Exception as e:
        print(f"❌ CloudWatch metrics error: {e}")
        return False


def check_current_configuration():
    """Check the current configuration being used by AWS."""
    print("\n⚙️  Checking current AWS configuration...")

    try:
        # Load configuration from the main config file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "..", "foreup_config.json")

        with open(config_path, "r") as f:
            config = json.load(f)

        print("✅ Current configuration:")
        print(f"   Target Date: {config.get('target_date', 'Not set')}")
        print(f"   Number of Players: {config.get('num_players', 'Not set')}")
        print(f"   Start Time: {config.get('start_time', 'Not set')}")
        print(
            f"   Window: {config.get('window_start_time', 'Not set')} - {config.get('window_end_time', 'Not set')}"
        )

        if "monitoring" in config:
            monitoring = config["monitoring"]
            print(f"   AWS Region: {monitoring.get('aws_region', 'Not set')}")
            print(
                f"   Check Interval: {monitoring.get('check_interval_minutes', 'Not set')} minutes"
            )
            print(
                f"   Notification Email: {monitoring.get('notification_email', 'Not set')}"
            )
            print(
                f"   SNS Topic: {monitoring.get('sns_topic_arn', 'Not set').split(':')[-1] if monitoring.get('sns_topic_arn') else 'Not set'}"
            )

        return True
    except Exception as e:
        print(f"❌ Configuration check error: {e}")
        return False


def main():
    """Main status checking function."""
    print("🏌️‍♂️ ForeUp Monitoring Service - Status Check")
    print("=" * 50)

    checks = [
        check_lambda_function,
        check_eventbridge_rule,
        check_sns_topic,
        check_cloudwatch_logs,
        check_cloudwatch_metrics,
        check_current_configuration,
    ]

    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Check failed: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("📋 Status Summary")
    print("=" * 50)

    passed = sum(results)
    total = len(results)

    print(f"✅ Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All systems operational!")
    elif passed > total // 2:
        print("⚠️  Some issues detected")
    else:
        print("❌ Multiple issues detected")

    print("\n💡 Tips:")
    print("• Check AWS Console for detailed error messages")
    print("• Review CloudWatch logs for debugging")
    print("• Ensure AWS credentials are properly configured")
    print("• Run 'python aws_scripts/cleanup_aws.py' to reset if needed")


if __name__ == "__main__":
    main()
