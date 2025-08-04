#!/usr/bin/env python3
"""
AWS deployment script for ForeUp monitoring service.

This script helps deploy the monitoring service to AWS Lambda or EC2
for continuous availability monitoring.
"""

import json
import logging
import os
import time
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
            # Check if topic already exists
            try:
                response = self.sns_client.list_topics()
                for topic in response["Topics"]:
                    if topic_name in topic["TopicArn"]:
                        self.logger.info(
                            f"SNS topic already exists: {topic['TopicArn']}"
                        )
                        return topic["TopicArn"]
            except Exception:
                pass

            # Create the topic
            response = self.sns_client.create_topic(Name=topic_name)
            topic_arn = response["TopicArn"]
            self.logger.info(f"Created SNS topic: {topic_arn}")
            return topic_arn
        except Exception as e:
            self.logger.error(f"Failed to create SNS topic: {str(e)}")
            raise

    def subscribe_email_to_sns(self, topic_arn: str, email: str) -> str:
        """Subscribe an email address to an SNS topic.

        Args:
            topic_arn: ARN of the SNS topic
            email: Email address to subscribe

        Returns:
            Subscription ARN
        """
        try:
            # Check if subscription already exists
            try:
                response = self.sns_client.list_subscriptions_by_topic(
                    TopicArn=topic_arn
                )
                for subscription in response["Subscriptions"]:
                    if (
                        subscription["Protocol"] == "email"
                        and subscription["Endpoint"] == email
                    ):
                        self.logger.info(
                            f"Email subscription already exists: {subscription['SubscriptionArn']}"
                        )
                        return subscription["SubscriptionArn"]
            except Exception:
                pass

            # Create the subscription
            response = self.sns_client.subscribe(
                TopicArn=topic_arn, Protocol="email", Endpoint=email
            )
            subscription_arn = response["SubscriptionArn"]
            self.logger.info(f"Created email subscription: {subscription_arn}")
            return subscription_arn
        except Exception as e:
            self.logger.error(f"Failed to create email subscription: {str(e)}")
            raise

    def create_iam_role(self, role_name: str) -> str:
        """Create IAM role for Lambda execution.

        Args:
            role_name: Name of the IAM role

        Returns:
            ARN of the created role
        """
        try:
            # Check if role already exists
            try:
                response = self.iam_client.get_role(RoleName=role_name)
                role_arn = response["Role"]["Arn"]
                self.logger.info(f"IAM role already exists: {role_arn}")
                return role_arn
            except self.iam_client.exceptions.NoSuchEntityException:
                pass  # Role doesn't exist, create it

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

            # Wait for role to be fully propagated
            self.logger.info("Waiting for IAM role to propagate...")
            time.sleep(10)

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
                # Add Python files from current directory
                for file in os.listdir(source_dir):
                    if file.endswith(".py") or file.endswith(".json"):
                        file_path = os.path.join(source_dir, file)
                        if os.path.isfile(file_path):
                            zipf.write(file_path, file)
                            self.logger.info(f"Added to package: {file}")

                # Add Lambda handler file
                lambda_handler_path = os.path.join(
                    source_dir, "aws", "lambda_handler.py"
                )
                if os.path.exists(lambda_handler_path):
                    zipf.write(lambda_handler_path, "lambda_handler.py")
                    self.logger.info("Added to package: lambda_handler.py")
                else:
                    raise Exception("lambda_handler.py not found in aws directory")

                # Add requirements.txt from parent directory
                requirements_path = os.path.join(
                    os.path.dirname(source_dir), "requirements.txt"
                )
                if os.path.exists(requirements_path):
                    zipf.write(requirements_path, "requirements.txt")
                    self.logger.info("Added to package: requirements.txt")

                # Install key Python dependencies to the package
                import subprocess
                import tempfile

                # Create a temporary directory for dependencies
                with tempfile.TemporaryDirectory() as temp_dir:
                    subprocess.run(
                        [
                            "pip",
                            "install",
                            "selenium==4.18.1",
                            "boto3>=1.34.0",
                            "requests>=2.31.0",
                            "-t",
                            temp_dir,
                            "--platform",
                            "manylinux2014_x86_64",
                            "--only-binary=:all:",
                        ],
                        check=True,
                    )

                    # Add all installed packages to the ZIP
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_name = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arc_name)

                    self.logger.info("Added Python dependencies to package")

                # Add credentials file
                credentials_path = os.path.join(
                    source_dir, "config", "credentials.json"
                )
                if os.path.exists(credentials_path):
                    zipf.write(credentials_path, "credentials.json")
                    self.logger.info("Added to package: credentials.json")
                else:
                    self.logger.warning("Credentials file not found, Lambda may fail")

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
        handler: str = "lambda_handler.lambda_handler",
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
            # Check if function already exists
            try:
                response = self.lambda_client.get_function(FunctionName=function_name)
                function_arn = response["Configuration"]["FunctionArn"]
                self.logger.info(f"Lambda function already exists: {function_arn}")

                # Update function code
                with open(package_path, "rb") as f:
                    self.lambda_client.update_function_code(
                        FunctionName=function_name, ZipFile=f.read()
                    )
                self.logger.info(f"Updated Lambda function code: {function_arn}")

                # Update function configuration for browser automation
                try:
                    self.lambda_client.update_function_configuration(
                        FunctionName=function_name,
                        Timeout=300,  # 5 minutes for browser automation
                        MemorySize=1024,  # 1GB for Chrome
                        Environment={
                            "Variables": {
                                "PYTHONPATH": "/opt/python",
                                "PATH": "/opt/chrome:/opt/chromedriver:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                            }
                        },
                    )
                    self.logger.info(
                        "Updated Lambda configuration for browser automation"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Could not update Lambda configuration: {str(e)}"
                    )
                    self.logger.info(
                        "Lambda function updated successfully, configuration will be updated on next deployment"
                    )

                return function_arn
            except self.lambda_client.exceptions.ResourceNotFoundException:
                pass  # Function doesn't exist, create it

            # Create new function
            with open(package_path, "rb") as f:
                response = self.lambda_client.create_function(
                    FunctionName=function_name,
                    Runtime="python3.9",
                    Role=role_arn,
                    Handler=handler,
                    Code={"ZipFile": f.read()},
                    Description="ForeUp tee time monitoring service",
                    Timeout=300,  # 5 minutes for browser automation
                    MemorySize=1024,  # 1GB for Chrome
                    Environment={
                        "Variables": {
                            "PYTHONPATH": "/opt/python",
                            "PATH": "/opt/chrome:/opt/chromedriver:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                        }
                    },
                )

            function_arn = response["FunctionArn"]
            self.logger.info(f"Created Lambda function: {function_arn}")
            return function_arn

        except Exception as e:
            self.logger.error(f"Failed to deploy Lambda function: {str(e)}")
            raise

    def create_lambda_layer(self) -> str:
        """Create Lambda layer with Chrome and ChromeDriver."""
        try:
            # Import the layer creation function
            from create_lambda_layer import create_lambda_layer

            layer_path = create_lambda_layer()
            if not layer_path:
                raise Exception("Failed to create Lambda layer")

            # Upload layer to AWS
            layer_name = "ForeUpMonitorChromeLayer"
            with open(layer_path, "rb") as f:
                response = self.lambda_client.publish_layer_version(
                    LayerName=layer_name,
                    Description="Chrome and ChromeDriver for ForeUp monitoring",
                    Content={"ZipFile": f.read()},
                    CompatibleRuntimes=["python3.9"],
                    CompatibleArchitectures=["x86_64"],
                )

            layer_arn = response["LayerVersionArn"]
            self.logger.info(f"Created Lambda layer: {layer_arn}")
            return layer_arn

        except Exception as e:
            self.logger.error(f"Failed to create Lambda layer: {str(e)}")
            raise

    def attach_layer_to_function(self, function_name: str, layer_arn: str) -> None:
        """Attach layer to Lambda function."""
        try:
            # Get current function configuration
            response = self.lambda_client.get_function(FunctionName=function_name)
            current_layers = response["Configuration"].get("Layers", [])

            # Add new layer
            new_layers = [layer["Arn"] for layer in current_layers]
            if layer_arn not in new_layers:
                new_layers.append(layer_arn)

            # Update function configuration
            self.lambda_client.update_function_configuration(
                FunctionName=function_name, Layers=new_layers
            )

            self.logger.info(f"Attached layer to function: {layer_arn}")

        except Exception as e:
            self.logger.error(f"Failed to attach layer: {str(e)}")
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
            # Check if rule already exists
            try:
                response = self.events_client.describe_rule(Name=rule_name)
                rule_arn = response["Arn"]
                self.logger.info(f"EventBridge rule already exists: {rule_arn}")

                # Update the rule schedule if needed
                if response.get("ScheduleExpression") != schedule_expression:
                    self.events_client.put_rule(
                        Name=rule_name,
                        ScheduleExpression=schedule_expression,
                        State="ENABLED",
                        Description="ForeUp monitoring schedule",
                    )
                    self.logger.info(f"Updated EventBridge rule schedule: {rule_arn}")

                return rule_arn

            except self.events_client.exceptions.ResourceNotFoundException:
                pass  # Rule doesn't exist, create it

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

            # Add permission for EventBridge to invoke Lambda (only if it doesn't exist)
            try:
                self.lambda_client.add_permission(
                    FunctionName=target_arn,
                    StatementId="EventBridgeInvoke",
                    Action="lambda:InvokeFunction",
                    Principal="events.amazonaws.com",
                    SourceArn=rule_arn,
                )
            except self.lambda_client.exceptions.ResourceConflictException:
                self.logger.info("Lambda permission already exists, skipping...")

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

            # Subscribe email to SNS topic if email is configured
            if "notification_email" in config["monitoring"]:
                email = config["monitoring"]["notification_email"]
                resources["subscription_arn"] = self.subscribe_email_to_sns(
                    resources["sns_topic_arn"], email
                )

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

            # Note: Lambda layer creation is complex and requires additional setup
            # For now, the Lambda will use system Chrome if available
            self.logger.info("Lambda layer creation skipped - using system Chrome")
            self.logger.info(
                "For full Chrome support, manually create and attach a Lambda layer"
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

            # Delete Lambda layer
            if "layer_arn" in resources:
                layer_name = "ForeUpMonitorChromeLayer"
                try:
                    response = self.lambda_client.list_layer_versions(
                        LayerName=layer_name
                    )
                    if response["LayerVersions"]:
                        latest_version = response["LayerVersions"][0]["Version"]
                        self.lambda_client.delete_layer_version(
                            LayerName=layer_name, VersionNumber=latest_version
                        )
                        self.logger.info(
                            f"Deleted Lambda layer version {latest_version}"
                        )
                except self.lambda_client.exceptions.ResourceNotFoundException:
                    self.logger.info(
                        f"Lambda layer {layer_name} not found, skipping deletion."
                    )
                except Exception as e:
                    self.logger.error(f"Failed to delete Lambda layer: {str(e)}")

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
