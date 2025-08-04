#!/usr/bin/env python3
"""
Script to create a proper Lambda deployment package with all dependencies.
"""

import os
import shutil
import subprocess
import zipfile


def create_lambda_package():
    """Create a Lambda deployment package with all dependencies."""

    # Create temporary directory for building
    build_dir = "lambda_build"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    print("📦 Creating Lambda deployment package...")

    try:
        # Install dependencies to the build directory
        print("Installing dependencies...")
        subprocess.run(
            [
                "pip",
                "install",
                "-r",
                "../requirements.txt",
                "-t",
                build_dir,
                "--platform",
                "manylinux2014_x86_64",
                "--only-binary=all",
            ],
            check=True,
        )

        # Copy our source files
        print("Copying source files...")
        source_files = [
            "../monitoring/monitoring_service.py",
            "../config/foreup_config.json",
            "../config/credentials.json",
        ]

        for file in source_files:
            if os.path.exists(file):
                shutil.copy2(file, build_dir)
                print(f"  ✅ Added: {file}")
            else:
                print(f"  ⚠️  Missing: {file}")

        # Create the ZIP file
        zip_path = "foreup_monitor_lambda_complete.zip"
        print(f"Creating ZIP file: {zip_path}")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(build_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, build_dir)
                    zipf.write(file_path, arc_name)

        # Get file size
        size = os.path.getsize(zip_path)
        print(f"✅ Created Lambda package: {zip_path} ({size:,} bytes)")

        # Clean up build directory
        shutil.rmtree(build_dir)

        return zip_path

    except Exception as e:
        print(f"❌ Failed to create package: {e}")
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        return None


if __name__ == "__main__":
    create_lambda_package()
