#!/usr/bin/env python3
"""
Cleanup script for ForeUp monitoring AWS resources.
"""

import logging

import boto3


def cleanup_resources():
    """Clean up existing AWS resources."""
    logger = logging.getLogger(__name__)

    # Initialize AWS clients
    lambda_client = boto3.client("lambda", region_name="us-east-1")
    iam_client = boto3.client("iam", region_name="us-east-1")
    sns_client = boto3.client("sns", region_name="us-east-1")
    events_client = boto3.client("events", region_name="us-east-1")

    try:
        # Delete Lambda function
        try:
            lambda_client.delete_function(FunctionName="ForeUpMonitor")
            print("✅ Deleted Lambda function: ForeUpMonitor")
        except Exception as e:
            print(f"⚠️  Lambda function not found or already deleted: {e}")

        # Delete EventBridge rule
        try:
            # Remove targets first
            events_client.remove_targets(
                Rule="ForeUpMonitorSchedule", Ids=["ForeUpMonitorTarget"]
            )
            events_client.delete_rule(Name="ForeUpMonitorSchedule")
            print("✅ Deleted EventBridge rule: ForeUpMonitorSchedule")
        except Exception as e:
            print(f"⚠️  EventBridge rule not found or already deleted: {e}")

        # Delete IAM role
        try:
            role_name = "ForeUpMonitorLambdaRole"
            # Detach policies first
            policies = [
                "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                "arn:aws:iam::aws:policy/CloudWatchFullAccess",
                "arn:aws:iam::aws:policy/AmazonSNSFullAccess",
            ]
            for policy_arn in policies:
                try:
                    iam_client.detach_role_policy(
                        RoleName=role_name, PolicyArn=policy_arn
                    )
                except:
                    pass
            iam_client.delete_role(RoleName=role_name)
            print("✅ Deleted IAM role: ForeUpMonitorLambdaRole")
        except Exception as e:
            print(f"⚠️  IAM role not found or already deleted: {e}")

        # Delete SNS topic
        try:
            # List topics to find the one we created
            response = sns_client.list_topics()
            for topic in response["Topics"]:
                if "foreup-monitoring" in topic["TopicArn"]:
                    sns_client.delete_topic(TopicArn=topic["TopicArn"])
                    print(f"✅ Deleted SNS topic: {topic['TopicArn']}")
                    break
        except Exception as e:
            print(f"⚠️  SNS topic not found or already deleted: {e}")

        print("\n🎉 Cleanup completed successfully!")

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")


if __name__ == "__main__":
    cleanup_resources()
