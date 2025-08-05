#!/usr/bin/env python3
"""
Script to set up AWS permissions for ForeUp monitoring service.
This script creates the necessary IAM policies and attaches them to the user.
"""

import json


def create_foreup_monitoring_policy():
    """Create IAM policy for ForeUp monitoring service."""

    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:CreateFunction",
                    "lambda:UpdateFunctionCode",
                    "lambda:UpdateFunctionConfiguration",
                    "lambda:DeleteFunction",
                    "lambda:GetFunction",
                    "lambda:InvokeFunction",
                    "lambda:AddPermission",
                    "lambda:RemovePermission",
                    "lambda:ListVersionsByFunction",
                    "lambda:ListAliases",
                    "lambda:CreateAlias",
                    "lambda:UpdateAlias",
                    "lambda:DeleteAlias",
                ],
                "Resource": [
                    "arn:aws:lambda:us-east-1:245706660322:function:ForeUpMonitor",
                    "arn:aws:lambda:us-east-1:245706660322:function:ForeUpMonitor:*",
                ],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "sns:CreateTopic",
                    "sns:DeleteTopic",
                    "sns:GetTopicAttributes",
                    "sns:SetTopicAttributes",
                    "sns:Subscribe",
                    "sns:Unsubscribe",
                    "sns:Publish",
                    "sns:ListTopics",
                    "sns:ListSubscriptions",
                    "sns:ListSubscriptionsByTopic",
                ],
                "Resource": [
                    "arn:aws:sns:us-east-1:245706660322:foreup-monitoring*",
                    "arn:aws:sns:us-east-1:245706660322:foreup-monitoring*:*",
                ],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "events:CreateRule",
                    "events:DeleteRule",
                    "events:DescribeRule",
                    "events:PutRule",
                    "events:PutTargets",
                    "events:RemoveTargets",
                    "events:ListRules",
                    "events:ListTargetsByRule",
                ],
                "Resource": [
                    "arn:aws:events:us-east-1:245706660322:rule/ForeUpMonitor*"
                ],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iam:CreateRole",
                    "iam:DeleteRole",
                    "iam:GetRole",
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:PutRolePolicy",
                    "iam:DeleteRolePolicy",
                    "iam:PassRole",
                ],
                "Resource": ["arn:aws:iam::245706660322:role/ForeUpMonitor*"],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:PutMetricData",
                    "cloudwatch:GetMetricData",
                    "cloudwatch:GetMetricStatistics",
                ],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams",
                    "logs:GetLogEvents",
                    "logs:FilterLogEvents",
                ],
                "Resource": [
                    "arn:aws:logs:us-east-1:245706660322:log-group:/aws/lambda/ForeUpMonitor*",
                    "arn:aws:logs:us-east-1:245706660322:log-group:/aws/lambda/ForeUpMonitor*:*",
                    "arn:aws:logs:us-east-1:245706660322:log-group:*",
                ],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken",
                ],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ecr:CreateRepository",
                    "ecr:DeleteRepository",
                    "ecr:DescribeRepositories",
                    "ecr:ListRepositories",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload",
                    "ecr:PutImage",
                ],
                "Resource": [
                    "arn:aws:ecr:us-east-1:245706660322:repository/foreup-monitor*",
                    "arn:aws:ecr:us-east-1:245706660322:repository/foreup-monitor*:*",
                ],
            },
        ],
    }

    return policy_document


def print_setup_instructions():
    """Print instructions for setting up permissions."""

    policy_document = create_foreup_monitoring_policy()

    print("🔧 Setting up AWS permissions for ForeUp monitoring...")
    print("\n" + "=" * 60)
    print("STEP-BY-STEP INSTRUCTIONS")
    print("=" * 60)

    print("\n1. Go to AWS IAM Console:")
    print("   https://console.aws.amazon.com/iam/")

    print("\n2. Navigate to Policies:")
    print("   - Click 'Policies' in the left sidebar")
    print("   - Click 'Create policy'")

    print("\n3. Create Policy:")
    print("   - Click 'JSON' tab")
    print("   - Replace the content with this policy:")
    print("\n" + json.dumps(policy_document, indent=2))

    print("\n4. Save Policy:")
    print("   - Click 'Next: Tags' (skip tags)")
    print("   - Click 'Next: Review'")
    print("   - Name: ForeUpMonitoringPolicy")
    print("   - Description: Policy for ForeUp tee time monitoring service")
    print("   - Click 'Create policy'")

    print("\n5. Attach Policy to User:")
    print("   - Go to 'Users' in left sidebar")
    print("   - Click on 'foreup-monitor' user")
    print("   - Click 'Add permissions'")
    print("   - Click 'Attach policies directly'")
    print("   - Search for 'ForeUpMonitoringPolicy'")
    print("   - Check the box and click 'Add permissions'")

    print("\n6. Test Permissions:")
    print("   - Run: aws sts get-caller-identity")
    print("   - Run: aws sns list-topics")
    print("   - Run: aws lambda list-functions")

    print("\n" + "=" * 60)
    print("ALTERNATIVE: Use AWS CLI (if you have admin access)")
    print("=" * 60)

    print("\nIf you have admin access, you can run these commands:")
    print("\n# Create the policy")
    print("aws iam create-policy \\")
    print("  --policy-name ForeUpMonitoringPolicy \\")
    print("  --policy-document file://foreup_monitoring_policy.json \\")
    print("  --description 'Policy for ForeUp tee time monitoring service'")

    print("\n# Attach policy to user")
    print("aws iam attach-user-policy \\")
    print("  --user-name foreup-monitor \\")
    print("  --policy-arn arn:aws:iam::245706660322:policy/ForeUpMonitoringPolicy")

    # Save policy to file
    with open("foreup_monitoring_policy.json", "w") as f:
        json.dump(policy_document, f, indent=2)

    print("\n✅ Policy document saved to: foreup_monitoring_policy.json")
    print("\nAfter setting up permissions, you can deploy with:")
    print("python aws/deploy_aws.py")


if __name__ == "__main__":
    print_setup_instructions()
