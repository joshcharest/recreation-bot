#!/usr/bin/env python3
"""
Script to create a Lambda layer with Chrome, ChromeDriver, and Selenium for ForeUp monitoring.
"""

import os
import shutil
import subprocess
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
                "--only-binary=:all:",
            ],
            check=True,
        )

        # Note: Chrome and ChromeDriver are complex to package for Lambda
        # For now, we'll create a layer with just Python dependencies
        # Chrome can be added later using a pre-built layer
        print("Creating layer with Python dependencies only...")
        print("Chrome and ChromeDriver will need to be added separately")

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

            # Note: Chrome and ChromeDriver not included in this layer
            # They will need to be added separately

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
