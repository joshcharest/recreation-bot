#!/usr/bin/env python3
"""
ForeUp Golf Tee Time Bot - Launcher
A simple menu-driven launcher for different bot functions.
"""

import os
import subprocess


def print_menu():
    """Print the main menu."""
    print("\n" + "=" * 50)
    print("🏌️‍♂️ ForeUp Golf Tee Time Bot - Launcher")
    print("=" * 50)
    print("1. 🎯 Run Main Bot (GUI Configuration)")
    print("2. 🔍 Run Local Monitoring")
    print("3. ☁️  Deploy to AWS")
    print("4. 🧹 Clean up AWS Resources")
    print("5. 📧 Subscribe to Notifications")
    print("6. 📊 Check AWS Status")
    print("7. 🚀 Quick Start Setup")
    print("8. 📚 View Documentation")
    print("0. ❌ Exit")
    print("=" * 50)


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}...")
    try:
        # Set environment variables for AWS commands
        env = os.environ.copy()
        if any(
            aws_cmd in command
            for aws_cmd in [
                "check_status.py",
                "deploy_aws.py",
                "cleanup_aws.py",
                "subscribe_notifications.py",
            ]
        ):
            env["AWS_PROFILE"] = "personal"
            env["AWS_DEFAULT_REGION"] = "us-east-1"

        # Use python3 explicitly
        command = command.replace("python ", "python3 ")
        result = subprocess.run(command, shell=True, check=True, env=env)
        print(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n⚠️  {description} interrupted by user")
        return False


def run_main_bot():
    """Run the main ForeUp bot."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return run_command(
        f"cd {script_dir} && python core/foreup_bot.py", "Starting main bot"
    )


def run_local_monitoring():
    """Run local monitoring."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return run_command(
        f"cd {script_dir} && python monitoring/run_monitoring.py",
        "Starting local monitoring",
    )


def deploy_to_aws():
    """Deploy to AWS."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return run_command(
        f"cd {script_dir} && python aws/deploy_aws.py",
        "Deploying to AWS",
    )


def cleanup_aws():
    """Clean up AWS resources."""
    print("\n⚠️  This will remove all AWS resources (Lambda, SNS, EventBridge, IAM)")
    confirm = input("Are you sure? (y/N): ").lower().strip()
    if confirm == "y":
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return run_command(
            f"cd {script_dir} && python aws/cleanup_aws.py",
            "Cleaning up AWS resources",
        )
    else:
        print("❌ Cleanup cancelled")
        return False


def subscribe_notifications():
    """Subscribe to notifications."""
    email = input("Enter your email address: ").strip()
    if email:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return run_command(
            f"cd {script_dir} && python aws/subscribe_notifications.py {email}",
            f"Subscribing {email} to notifications",
        )
    else:
        print("❌ No email provided")
        return False


def check_aws_status():
    """Check AWS deployment status."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return run_command(
        f"cd {script_dir} && python utils/check_status.py",
        "Checking AWS status",
    )


def quick_start():
    """Run quick start setup."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return run_command(
        f"cd {script_dir} && python utils/quick_start.py", "Running quick start setup"
    )


def view_documentation():
    """View documentation."""
    print("\n📚 Documentation:")
    print("• README.md - Complete project overview")
    print("• README_MONITORING.md - AWS monitoring details")
    print("\n📖 Quick Reference:")
    print("• Main bot: python foreup_bot.py")
    print("• Local monitoring: python monitoring_scripts/run_monitoring.py")
    print("• AWS deployment: python aws_scripts/deploy_aws.py")
    print("• Status check: python check_status.py")
    print("• Quick start: python quick_start.py")
    try:
        input("\nPress Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def main():
    """Main launcher function."""
    while True:
        print_menu()

        try:
            choice = input("\nSelect an option (0-8): ").strip()

            if choice == "0":
                print("👋 Goodbye!")
                break
            elif choice == "1":
                run_main_bot()
            elif choice == "2":
                run_local_monitoring()
            elif choice == "3":
                deploy_to_aws()
            elif choice == "4":
                cleanup_aws()
            elif choice == "5":
                subscribe_notifications()
            elif choice == "6":
                check_aws_status()
            elif choice == "7":
                quick_start()
            elif choice == "8":
                view_documentation()
            else:
                print("❌ Invalid option. Please select 0-8.")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

        try:
            input("\nPress Enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass


if __name__ == "__main__":
    main()
