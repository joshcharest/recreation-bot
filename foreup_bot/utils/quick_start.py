#!/usr/bin/env python3
"""
Quick start script for ForeUp Golf Tee Time Bot.
This script helps users get up and running quickly.
"""

import os
import shutil
import sys


def check_environment():
    """Check if the environment is properly set up."""
    print("🔍 Checking environment...")

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False

    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")

    # Check if virtual environment is activated
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        print("✅ Virtual environment is active")
    else:
        print("⚠️  Virtual environment not detected")

    return True


def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n📦 Checking dependencies...")

    required_packages = ["selenium", "boto3", "requests", "webdriver_manager"]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False

    return True


def check_config_files():
    """Check if configuration files exist."""
    print("\n⚙️  Checking configuration files...")

    config_files = {
        "../config/foreup_config.json": "Main configuration file",
        "../config/credentials_template.json": "Credentials template",
        "../config/credentials.json": "Your credentials (create from template)",
    }

    for file, description in config_files.items():
        if os.path.exists(file):
            print(f"✅ {file} - {description}")
        else:
            print(f"❌ {file} - {description}")

    return True


def setup_credentials():
    """Help user set up credentials."""
    print("\n🔐 Setting up credentials...")

    if os.path.exists("../config/credentials.json"):
        print("✅ Credentials file already exists")
        return True

    if os.path.exists("../config/credentials_template.json"):
        print("📝 Creating credentials file from template...")
        shutil.copy("../config/credentials_template.json", "../config/credentials.json")
        print("✅ Created credentials.json")
        print("⚠️  Please edit credentials.json with your actual ForeUp login details")
        return True
    else:
        print("❌ Credentials template not found")
        return False


def show_next_steps():
    """Show next steps for the user."""
    print("\n" + "=" * 50)
    print("🚀 Quick Start Complete!")
    print("=" * 50)

    print("\n📋 Next Steps:")
    print("1. Edit config/credentials.json with your ForeUp login details")
    print("2. Edit config/foreup_config.json with your preferred settings")
    print("3. Choose how to run the bot:")
    print("   • Local booking: python core/foreup_bot.py")
    print("   • Local monitoring: python monitoring/run_monitoring.py")
    print("   • AWS deployment: python aws/deploy_aws.py")

    print("\n📚 Documentation:")
    print("• README.md - Complete project overview")
    print("• README_MONITORING.md - AWS monitoring details")

    print("\n🔧 Troubleshooting:")
    print("• Check the troubleshooting section in README.md")
    print("• Test locally before deploying to AWS")
    print("• Check CloudWatch logs for AWS issues")


def main():
    """Main quick start function."""
    print("🏌️‍♂️ ForeUp Golf Tee Time Bot - Quick Start")
    print("=" * 50)

    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed")
        return 1

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependencies check failed")
        return 1

    # Check config files
    check_config_files()

    # Setup credentials
    setup_credentials()

    # Show next steps
    show_next_steps()

    return 0


if __name__ == "__main__":
    exit(main())
