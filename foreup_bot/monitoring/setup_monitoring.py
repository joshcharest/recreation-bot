#!/usr/bin/env python3
"""
Setup script for ForeUp monitoring service.

This script helps configure the monitoring service by creating necessary files
and guiding through the setup process.
"""

import json
import os
import shutil


def create_credentials_file():
    """Create credentials.json file from template or existing credentials."""
    template_path = "../config/credentials_template.json"
    credentials_path = "../config/credentials.json"

    if os.path.exists(credentials_path):
        print("✅ Credentials file already exists")
        return True

    if os.path.exists(template_path):
        print("📝 Creating credentials file from template...")
        shutil.copy(template_path, credentials_path)
        print(f"✅ Created {credentials_path}")
        print("⚠️  Please edit this file with your actual ForeUp credentials")
        return True
    else:
        print("❌ No credentials template found")
        return False


def check_aws_credentials():
    """Check if AWS credentials are configured."""
    try:
        import boto3

        sts = boto3.client("sts")
        sts.get_caller_identity()
        print("✅ AWS credentials are configured")
        return True
    except Exception:
        print("❌ AWS credentials not configured or invalid")
        print("Please run 'aws configure' or set environment variables")
        return False


def validate_config():
    """Validate the configuration file."""
    try:
        with open("../config/foreup_config.json", "r") as f:
            config = json.load(f)

        required_fields = ["target_date", "num_players", "start_time", "monitoring"]
        for field in required_fields:
            if field not in config:
                print(f"❌ Missing required field: {field}")
                return False

        if "enabled" not in config["monitoring"]:
            print("❌ Missing monitoring.enabled field")
            return False

        print("✅ Configuration file is valid")
        return True

    except Exception as e:
        print(f"❌ Configuration file error: {e}")
        return False


def main():
    """Main setup function."""
    print("🚀 ForeUp Monitoring Service Setup")
    print("=" * 40)

    # Check if we're in the right directory
    if not os.path.exists("../config/foreup_config.json"):
        print("❌ Please run this script from the foreup_bot directory")
        return 1

    # Create credentials file
    print("\n1. Setting up credentials...")
    if not create_credentials_file():
        return 1

    # Validate configuration
    print("\n2. Validating configuration...")
    if not validate_config():
        return 1

    # Check AWS credentials
    print("\n3. Checking AWS credentials...")
    aws_configured = check_aws_credentials()

    print("\n" + "=" * 40)
    print("📋 Setup Summary:")
    print("✅ Configuration file: ../config/foreup_config.json")
    print("✅ Credentials file: ../config/credentials.json")

    if aws_configured:
        print("✅ AWS credentials: Configured")
        print("\n🎉 Ready to deploy to AWS!")
        print("\nNext steps:")
        print("1. Edit ../config/credentials.json with your ForeUp login details")
        print("2. Run: python deploy_aws.py")
    else:
        print("❌ AWS credentials: Not configured")
        print("\nNext steps:")
        print("1. Edit ../config/credentials.json with your ForeUp login details")
        print("2. Configure AWS credentials:")
        print("   - Run: aws configure")
        print("   - Or set environment variables")
        print("3. Run: python deploy_aws.py")

    print("\n💡 For local testing, run: python run_monitoring.py")

    return 0


if __name__ == "__main__":
    exit(main())
