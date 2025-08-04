#!/usr/bin/env python3
"""
AWS deployment script for ForeUp monitoring service.

This script helps deploy the monitoring service to AWS Lambda or EC2
for continuous availability monitoring.
"""

import json
import logging
import os
import zipfile
from typing import Any, Dict

import boto3


class AWSDeployer:
    """Deployer for AWS infrastructure and monitoring service."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize the AWS deployer.

        Args:
            region: AWS region for deployment
        """
        self.region = region
        self.lambda_client = boto3.client("lambda", region_name=region)
        self.iam_client = boto3.client("iam", region_name=region)
        self.sns_client = boto3.client("sns", region_name=region)
        self.events_client = boto3.client("events", region_name=region)
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration.

        Returns:
            Configured logger instance
        """
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        return logging.getLogger(__name__)

    def create_sns_topic(self, topic_name: str) -> str:
        """Create SNS topic for notifications.

        Args:
            topic_name: Name of the SNS topic

        Returns:
            ARN of the created topic
        """
        try:
            response = self.sns_client.create_topic(Name=topic_name)
            topic_arn = response["TopicArn"]
            self.logger.info(f"Created SNS topic: {topic_arn}")
            return topic_arn
        except Exception as e:
            self.logger.error(f"Failed to create SNS topic: {str(e)}")
            raise

    def create_iam_role(self, role_name: str) -> str:
        """Create IAM role for Lambda execution.

        Args:
            role_name: Name of the IAM role

        Returns:
            ARN of the created role
        """
        try:
            # Create the role
            assume_role_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }

            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description="Role for ForeUp monitoring Lambda function",
            )
            role_arn = response["Role"]["Arn"]

            # Attach necessary policies
            policies = [
                "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                "arn:aws:iam::aws:policy/CloudWatchFullAccess",
                "arn:aws:iam::aws:policy/AmazonSNSFullAccess",
            ]

            for policy_arn in policies:
                self.iam_client.attach_role_policy(
                    RoleName=role_name, PolicyArn=policy_arn
                )

            self.logger.info(f"Created IAM role: {role_arn}")
            return role_arn

        except Exception as e:
            self.logger.error(f"Failed to create IAM role: {str(e)}")
            raise

    def create_lambda_package(self, source_dir: str, output_path: str) -> str:
        """Create Lambda deployment package.

        Args:
            source_dir: Directory containing source files
            output_path: Path for the output ZIP file

        Returns:
            Path to the created ZIP file
        """
        try:
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Add Python files
                for file in os.listdir(source_dir):
                    if file.endswith(".py") or file.endswith(".json"):
                        file_path = os.path.join(source_dir, file)
                        if os.path.isfile(file_path):
                            zipf.write(file_path, file)
                            self.logger.info(f"Added to package: {file}")

                # Add requirements.txt from parent directory
                requirements_path = os.path.join(
                    os.path.dirname(source_dir), "requirements.txt"
                )
                if os.path.exists(requirements_path):
                    zipf.write(requirements_path, "requirements.txt")
                    self.logger.info("Added to package: requirements.txt")

            # Verify the package is not empty
            if os.path.getsize(output_path) < 100:
                raise Exception("Created package is too small, likely empty")

            self.logger.info(
                f"Created Lambda package: {output_path} ({os.path.getsize(output_path)} bytes)"
            )
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to create Lambda package: {str(e)}")
            raise

    def deploy_lambda_function(
        self,
        function_name: str,
        role_arn: str,
        package_path: str,
        handler: str = "monitoring_service.lambda_handler",
    ) -> str:
        """Deploy Lambda function.

        Args:
            function_name: Name of the Lambda function
            role_arn: ARN of the execution role
            package_path: Path to the deployment package
            handler: Lambda handler function

        Returns:
            ARN of the deployed function
        """
        try:
            with open(package_path, "rb") as f:
                zip_content = f.read()

            response = self.lambda_client.create_function(
                FunctionName=function_name,
                Runtime="python3.9",
                Role=role_arn,
                Handler=handler,
                Code={"ZipFile": zip_content},
                Timeout=300,
                MemorySize=512,
                Environment={"Variables": {"PYTHONPATH": "/var/task"}},
            )

            function_arn = response["FunctionArn"]
            self.logger.info(f"Deployed Lambda function: {function_arn}")
            return function_arn

        except Exception as e:
            self.logger.error(f"Failed to deploy Lambda function: {str(e)}")
            raise

    def create_eventbridge_rule(
        self, rule_name: str, schedule_expression: str, target_arn: str
    ) -> str:
        """Create EventBridge rule for periodic execution.

        Args:
            rule_name: Name of the EventBridge rule
            schedule_expression: Cron expression for scheduling
            target_arn: ARN of the Lambda function to invoke

        Returns:
            ARN of the created rule
        """
        try:
            # Create the rule
            response = self.events_client.put_rule(
                Name=rule_name,
                ScheduleExpression=schedule_expression,
                State="ENABLED",
                Description="ForeUp monitoring schedule",
            )
            rule_arn = response["RuleArn"]

            # Add Lambda as target
            self.events_client.put_targets(
                Rule=rule_name,
                Targets=[{"Id": "ForeUpMonitorTarget", "Arn": target_arn}],
            )

            # Add permission for EventBridge to invoke Lambda
            self.lambda_client.add_permission(
                FunctionName=target_arn,
                StatementId="EventBridgeInvoke",
                Action="lambda:InvokeFunction",
                Principal="events.amazonaws.com",
                SourceArn=rule_arn,
            )

            self.logger.info(f"Created EventBridge rule: {rule_arn}")
            return rule_arn

        except Exception as e:
            self.logger.error(f"Failed to create EventBridge rule: {str(e)}")
            raise

    def deploy_monitoring_service(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Deploy the complete monitoring service.

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary with ARNs of created resources
        """
        try:
            resources = {}

            # Create SNS topic
            topic_name = f"foreup-monitoring-{config['monitoring']['aws_region']}"
            resources["sns_topic_arn"] = self.create_sns_topic(topic_name)

            # Create IAM role
            role_name = "ForeUpMonitorLambdaRole"
            resources["role_arn"] = self.create_iam_role(role_name)

            # Create Lambda package
            package_path = "foreup_monitor_lambda.zip"
            self.create_lambda_package(".", package_path)

            # Deploy Lambda function
            function_name = "ForeUpMonitor"
            resources["function_arn"] = self.deploy_lambda_function(
                function_name, resources["role_arn"], package_path
            )

            # Create EventBridge rule for periodic execution
            interval_minutes = config["monitoring"]["check_interval_minutes"]
            schedule_expression = f"rate({interval_minutes} minutes)"
            rule_name = "ForeUpMonitorSchedule"
            resources["rule_arn"] = self.create_eventbridge_rule(
                rule_name, schedule_expression, resources["function_arn"]
            )

            # Update config with SNS topic ARN
            config["monitoring"]["sns_topic_arn"] = resources["sns_topic_arn"]

            self.logger.info("Monitoring service deployment completed successfully!")
            return resources

        except Exception as e:
            self.logger.error(f"Deployment failed: {str(e)}")
            raise

    def cleanup_resources(self, resources: Dict[str, str]) -> None:
        """Clean up deployed resources.

        Args:
            resources: Dictionary with ARNs of resources to clean up
        """
        try:
            # Delete EventBridge rule
            if "rule_arn" in resources:
                self.events_client.delete_rule(Name="ForeUpMonitorSchedule")
                self.logger.info("Deleted EventBridge rule")

            # Delete Lambda function
            if "function_arn" in resources:
                self.lambda_client.delete_function(FunctionName="ForeUpMonitor")
                self.logger.info("Deleted Lambda function")

            # Delete IAM role
            if "role_arn" in resources:
                role_name = "ForeUpMonitorLambdaRole"
                # Detach policies first
                policies = [
                    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                    "arn:aws:iam::aws:policy/CloudWatchFullAccess",
                    "arn:aws:iam::aws:policy/AmazonSNSFullAccess",
                ]
                for policy_arn in policies:
                    try:
                        self.iam_client.detach_role_policy(
                            RoleName=role_name, PolicyArn=policy_arn
                        )
                    except:
                        pass
                self.iam_client.delete_role(RoleName=role_name)
                self.logger.info("Deleted IAM role")

            # Delete SNS topic
            if "sns_topic_arn" in resources:
                self.sns_client.delete_topic(TopicArn=resources["sns_topic_arn"])
                self.logger.info("Deleted SNS topic")

            self.logger.info("Cleanup completed successfully!")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")


def main():
    """Main deployment function."""
    # Load configuration
    with open("foreup_config.json", "r") as f:
        config = json.load(f)

    # Initialize deployer
    deployer = AWSDeployer(region=config["monitoring"]["aws_region"])

    try:
        # Deploy monitoring service
        resources = deployer.deploy_monitoring_service(config)

        # Save updated config
        with open("foreup_config.json", "w") as f:
            json.dump(config, f, indent=4)

        print("\nDeployment completed successfully!")
        print("Resources created:")
        for resource_type, arn in resources.items():
            print(f"  {resource_type}: {arn}")

        print(
            f"\nMonitoring will check every {config['monitoring']['check_interval_minutes']} minutes"
        )
        print("You can view logs in CloudWatch Logs")
        print("Notifications will be sent to the SNS topic when availability is found")

    except Exception as e:
        print(f"Deployment failed: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
