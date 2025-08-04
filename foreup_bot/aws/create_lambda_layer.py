#!/usr/bin/env python3
"""
Script to create a Lambda layer with Chrome, ChromeDriver, and Selenium for ForeUp monitoring.
"""

import os
import shutil
import subprocess
import urllib.request
import zipfile


def create_lambda_layer():
    """Create a Lambda layer with Chrome, ChromeDriver, and Selenium dependencies."""

    # Create temporary directory for building
    build_dir = "lambda_layer_build"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    print("📦 Creating Lambda layer with Chrome and Selenium...")

    try:
        # Create the layer structure
        layer_dir = os.path.join(build_dir, "python")
        os.makedirs(layer_dir)

        # Install Python dependencies
        print("Installing Python dependencies...")
        subprocess.run(
            [
                "pip",
                "install",
                "-r",
                "../requirements.txt",
                "-t",
                layer_dir,
                "--platform",
                "manylinux2014_x86_64",
                "--only-binary=all",
            ],
            check=True,
        )

        # Download and install Chrome
        print("Downloading Chrome...")
        chrome_dir = os.path.join(build_dir, "chrome")
        os.makedirs(chrome_dir)

        # Download Chrome for Amazon Linux 2
        chrome_url = (
            "https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm"
        )
        chrome_rpm = os.path.join(chrome_dir, "google-chrome.rpm")

        urllib.request.urlretrieve(chrome_url, chrome_rpm)

        # Extract Chrome from RPM
        subprocess.run(
            ["rpm2cpio", chrome_rpm, "|", "cpio", "-idmv"],
            shell=True,
            cwd=chrome_dir,
            check=True,
        )

        # Download ChromeDriver
        print("Downloading ChromeDriver...")
        chromedriver_url = "https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip"
        chromedriver_zip = os.path.join(chrome_dir, "chromedriver.zip")

        urllib.request.urlretrieve(chromedriver_url, chromedriver_zip)

        # Extract ChromeDriver
        with zipfile.ZipFile(chromedriver_zip, "r") as zip_ref:
            zip_ref.extractall(chrome_dir)

        # Make ChromeDriver executable
        chromedriver_path = os.path.join(chrome_dir, "chromedriver")
        os.chmod(chromedriver_path, 0o755)

        # Create the layer ZIP file
        layer_zip_path = "foreup_monitor_layer.zip"
        print(f"Creating layer ZIP file: {layer_zip_path}")

        with zipfile.ZipFile(layer_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add Python packages
            for root, dirs, files in os.walk(layer_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, build_dir)
                    zipf.write(file_path, arc_name)

            # Add Chrome and ChromeDriver
            for root, dirs, files in os.walk(chrome_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, build_dir)
                    zipf.write(file_path, arc_name)

        # Get file size
        size = os.path.getsize(layer_zip_path)
        print(f"✅ Created Lambda layer: {layer_zip_path} ({size:,} bytes)")

        # Clean up build directory
        shutil.rmtree(build_dir)

        return layer_zip_path

    except Exception as e:
        print(f"❌ Failed to create layer: {e}")
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        return None


if __name__ == "__main__":
    create_lambda_layer()
