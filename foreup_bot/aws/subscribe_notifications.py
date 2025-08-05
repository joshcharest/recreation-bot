#!/usr/bin/env python3
"""
Script to subscribe to SNS notifications for ForeUp monitoring.
"""

import json
import os

import boto3


def subscribe_to_notifications(email: str):
    """Subscribe email to SNS notifications."""
    try:
        # Initialize SNS client
        sns = boto3.client("sns", region_name="us-east-1")

        # Get the topic ARN from config
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "foreup_config.json"
        )
        with open(config_path, "r") as f:
            config = json.load(f)

        topic_arn = config["monitoring"]["sns_topic_arn"]
        print(f"Using topic ARN: {topic_arn}")

        # Subscribe to the topic
        response = sns.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email)

        subscription_arn = response["SubscriptionArn"]
        print(f"✅ Successfully subscribed {email} to notifications")
        print(f"Subscription ARN: {subscription_arn}")
        print("\n📧 Please check your email and confirm the subscription!")

        return True

    except Exception as e:
        print(f"❌ Failed to subscribe: {str(e)}")
        return False


def list_subscriptions():
    """List current subscriptions."""
    try:
        sns = boto3.client("sns", region_name="us-east-1")

        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "foreup_config.json"
        )
        with open(config_path, "r") as f:
            config = json.load(f)

        topic_arn = config["monitoring"]["sns_topic_arn"]

        response = sns.list_subscriptions_by_topic(TopicArn=topic_arn)

        print("Current subscriptions:")
        for sub in response["Subscriptions"]:
            print(f"  - {sub['Endpoint']} ({sub['Status']})")

    except Exception as e:
        print(f"❌ Failed to list subscriptions: {str(e)}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        email = sys.argv[1]
        subscribe_to_notifications(email)
    else:
        print("Usage: python subscribe_notifications.py <email>")
        print("Example: python subscribe_notifications.py joshcharest1@gmail.com")

        # Show current subscriptions
        print("\nCurrent subscriptions:")
        list_subscriptions()
