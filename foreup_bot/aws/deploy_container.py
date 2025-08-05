#!/usr/bin/env python3
"""
Script to build and deploy container-based Lambda function with Playwright.
"""

import json
import logging
import subprocess
import sys

import boto3


class ContainerLambdaDeployer:
    """Deploy container-based Lambda function with Playwright."""

    def __init__(self, region: str = "us-east-1"):
        """Initialize the deployer.

        Args:
            region: AWS region
        """
        self.region = region
        self.logger = self._setup_logger()

        # Initialize AWS clients
        self.ecr = boto3.client("ecr", region_name=region)
        self.lambda_client = boto3.client("lambda", region_name=region)
        self.sns = boto3.client("sns", region_name=region)
        self.events = boto3.client("events", region_name=region)
        self.iam = boto3.client("iam", region_name=region)

    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)

    def get_account_id(self) -> str:
        """Get AWS account ID."""
        sts = boto3.client("sts")
        return sts.get_caller_identity()["Account"]

    def create_ecr_repository(self, repo_name: str) -> str:
        """Create ECR repository if it doesn't exist.

        Args:
            repo_name: Name of the ECR repository

        Returns:
            Repository URI
        """
        try:
            response = self.ecr.create_repository(repositoryName=repo_name)
            self.logger.info(f"Created ECR repository: {repo_name}")
            return response["repository"]["repositoryUri"]
        except self.ecr.exceptions.RepositoryAlreadyExistsException:
            account_id = self.get_account_id()
            repo_uri = f"{account_id}.dkr.ecr.{self.region}.amazonaws.com/{repo_name}"
            self.logger.info(f"ECR repository already exists: {repo_uri}")
            return repo_uri

    def build_and_push_image(self, repo_uri: str, image_tag: str = "latest") -> str:
        """Build and push Docker image to ECR.

        Args:
            repo_uri: ECR repository URI
            image_tag: Docker image tag

        Returns:
            Full image URI
        """
        try:
            # Get ECR login token
            auth_response = self.ecr.get_authorization_token()
            import base64

            auth_token = auth_response["authorizationData"][0]["authorizationToken"]
            decoded_token = base64.b64decode(auth_token).decode("utf-8")
            username, password = decoded_token.split(":")
            registry = auth_response["authorizationData"][0]["proxyEndpoint"]

            # Login to ECR
            subprocess.run(
                ["sudo", "docker", "login", "-u", username, "-p", password, registry],
                check=True,
            )

            # Build image
            full_image_uri = f"{repo_uri}:{image_tag}"
            self.logger.info(f"Building Docker image: {full_image_uri}")

            subprocess.run(
                ["sudo", "docker", "build", "-t", full_image_uri, "."], check=True
            )

            # Push image
            self.logger.info("Pushing image to ECR...")
            subprocess.run(["sudo", "docker", "push", full_image_uri], check=True)

            self.logger.info(f"Successfully pushed image: {full_image_uri}")
            return full_image_uri

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to build/push image: {e}")
            raise

    def create_lambda_function(
        self, function_name: str, image_uri: str, role_arn: str
    ) -> str:
        """Create Lambda function from container image.

        Args:
            function_name: Name of the Lambda function
            image_uri: ECR image URI
            role_arn: IAM role ARN

        Returns:
            Function ARN
        """
        try:
            response = self.lambda_client.create_function(
                FunctionName=function_name,
                PackageType="Image",
                Code={"ImageUri": image_uri},
                Role=role_arn,
                Timeout=300,  # 5 minutes
                MemorySize=2048,  # 2GB RAM
                Environment={
                    "Variables": {
                        "DISPLAY": ":99",
                        "PLAYWRIGHT_BROWSERS_PATH": "/opt/playwright/.local-browsers",
                    }
                },
            )

            function_arn = response["FunctionArn"]
            self.logger.info(f"Created Lambda function: {function_arn}")
            return function_arn

        except self.lambda_client.exceptions.ResourceConflictException:
            # Function already exists, update it
            response = self.lambda_client.update_function_code(
                FunctionName=function_name, ImageUri=image_uri
            )
            function_arn = response["FunctionArn"]
            self.logger.info(f"Updated Lambda function: {function_arn}")
            return function_arn

    def create_eventbridge_rule(
        self, rule_name: str, schedule_expression: str, target_arn: str
    ) -> str:
        """Create EventBridge rule for periodic execution.

        Args:
            rule_name: Name of the EventBridge rule
            schedule_expression: Cron or rate expression
            target_arn: Lambda function ARN

        Returns:
            Rule ARN
        """
        try:
            # Create rule
            response = self.events.put_rule(
                Name=rule_name, ScheduleExpression=schedule_expression, State="ENABLED"
            )
            rule_arn = response["RuleArn"]
            self.logger.info(f"Created EventBridge rule: {rule_arn}")

            # Add Lambda target
            self.events.put_targets(
                Rule=rule_name,
                Targets=[{"Id": "ForeUpMonitorTarget", "Arn": target_arn}],
            )

            # Add permission for EventBridge to invoke Lambda
            try:
                self.lambda_client.add_permission(
                    FunctionName=target_arn.split(":")[-1],
                    StatementId="EventBridgeInvoke",
                    Action="lambda:InvokeFunction",
                    Principal="events.amazonaws.com",
                    SourceArn=rule_arn,
                )
            except self.lambda_client.exceptions.ResourceConflictException:
                # Permission already exists
                pass

            return rule_arn

        except Exception as e:
            self.logger.error(f"Failed to create EventBridge rule: {e}")
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
                response = self.iam.get_role(RoleName=role_name)
                role_arn = response["Role"]["Arn"]
                self.logger.info(f"IAM role already exists: {role_arn}")

                # Add ECR permissions (don't check if they exist to avoid permission issues)
                self.logger.info("Adding ECR permissions to existing role...")
                ecr_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchGetImage",
                                "ecr:BatchCheckLayerAvailability",
                                "ecr:DescribeImages",
                                "ecr:DescribeRepositories",
                                "ecr:ListImages",
                                "ecr:GetAuthorizationToken",
                            ],
                            "Resource": "*",
                        }
                    ],
                }

                try:
                    self.iam.put_role_policy(
                        RoleName=role_name,
                        PolicyName="ECRAccessPolicy",
                        PolicyDocument=json.dumps(ecr_policy),
                    )
                    self.logger.info("ECR permissions added successfully")
                except Exception as e:
                    self.logger.warning(f"Could not add ECR permissions: {e}")

                # Wait longer for role propagation
                self.logger.info("Waiting for IAM role changes to propagate...")
                import time

                time.sleep(30)

                return role_arn
            except self.iam.exceptions.NoSuchEntityException:
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

            response = self.iam.create_role(
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
                self.iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

            # Add ECR permissions for Lambda to access container images
            ecr_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:BatchGetImage",
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:DescribeImages",
                            "ecr:DescribeRepositories",
                            "ecr:ListImages",
                            "ecr:GetAuthorizationToken",
                        ],
                        "Resource": "*",
                    }
                ],
            }

            self.iam.put_role_policy(
                RoleName=role_name,
                PolicyName="ECRAccessPolicy",
                PolicyDocument=json.dumps(ecr_policy),
            )

            # Wait for role to be fully propagated
            self.logger.info("Waiting for IAM role to propagate...")
            import time

            time.sleep(30)

            self.logger.info(f"Created IAM role: {role_arn}")
            return role_arn

        except Exception as e:
            self.logger.error(f"Failed to create IAM role: {e}")
            raise

    def deploy_container_lambda(self, config: dict) -> dict:
        """Deploy container-based Lambda function.

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary with resource ARNs
        """
        try:
            resources = {}

            # Create ECR repository
            repo_name = "foreup-monitor"
            repo_uri = self.create_ecr_repository(repo_name)

            # Build and push image
            image_uri = self.build_and_push_image(repo_uri)

            # Create/update Lambda function
            function_name = "ForeUpMonitor"

            # Create IAM role if not provided in config
            role_arn = config.get("role_arn")
            if not role_arn:
                role_name = "ForeUpMonitorRole"
                role_arn = self.create_iam_role(role_name)

            resources["function_arn"] = self.create_lambda_function(
                function_name, image_uri, role_arn
            )

            # Create EventBridge rule
            interval_minutes = config.get("check_interval_minutes", 15)
            schedule_expression = f"rate({interval_minutes} minutes)"
            rule_name = "ForeUpMonitorSchedule"

            resources["rule_arn"] = self.create_eventbridge_rule(
                rule_name, schedule_expression, resources["function_arn"]
            )

            self.logger.info(
                "Container-based Lambda deployment completed successfully!"
            )
            return resources

        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            raise


def main():
    """Main deployment function."""
    try:
        # Load configuration
        config_path = "config/foreup_config.json"
        with open(config_path, "r") as f:
            config = json.load(f)

        # Create deployer
        deployer = ContainerLambdaDeployer()

        # Deploy
        resources = deployer.deploy_container_lambda(config)

        print("\n✅ Container-based Lambda deployment completed!")
        print(f"Function ARN: {resources['function_arn']}")
        print(f"EventBridge Rule ARN: {resources['rule_arn']}")
        print("\n🎯 Your Playwright-based monitoring is now running in the cloud!")

    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
