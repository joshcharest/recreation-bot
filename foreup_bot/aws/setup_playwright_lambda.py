#!/usr/bin/env python3
"""
Script to set up Playwright for AWS Lambda deployment.
This script installs Playwright and downloads the required browsers.
"""

import os
import subprocess
import sys
import zipfile
from pathlib import Path


def install_playwright_browsers():
    """Install Playwright browsers for Lambda."""
    print("🔧 Setting up Playwright for Lambda...")

    try:
        # Install Playwright
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "playwright>=1.40.0"], check=True
        )

        # Install browsers
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"], check=True
        )

        print("✅ Playwright and Chromium browser installed successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Playwright: {e}")
        return False


def create_playwright_layer():
    """Create a Lambda layer with Playwright and browsers."""
    print("📦 Creating Playwright Lambda layer...")

    try:
        # Get Playwright browser path
        result = subprocess.run(
            [sys.executable, "-c", "import playwright; print(playwright.__file__)"],
            capture_output=True,
            text=True,
            check=True,
        )

        playwright_path = Path(result.stdout.strip()).parent

        # Get browser path (browsers are installed in ~/.cache/ms-playwright)
        browser_path = Path.home() / ".cache" / "ms-playwright"
        if not browser_path.exists():
            print("❌ Browser path not found. Run install_playwright_browsers() first.")
            return None

        # Create layer directory
        layer_dir = Path("playwright_layer")
        layer_dir.mkdir(exist_ok=True)

        # Copy Playwright to layer
        python_dir = layer_dir / "python"
        python_dir.mkdir(exist_ok=True)

        # Copy Playwright package
        subprocess.run(
            ["cp", "-r", str(playwright_path), str(python_dir / "playwright")],
            check=True,
        )

        # Copy browsers to a standard location in the layer
        browsers_dir = python_dir / "playwright" / ".local-browsers"
        browsers_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", "-r", str(browser_path), str(browsers_dir)], check=True)

        # Create ZIP file
        layer_zip = "playwright_lambda_layer.zip"
        with zipfile.ZipFile(layer_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(layer_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, layer_dir)
                    zipf.write(file_path, arc_name)

        print(f"✅ Playwright layer created: {layer_zip}")
        return layer_zip

    except Exception as e:
        print(f"❌ Failed to create layer: {e}")
        return None


def main():
    """Main setup function."""
    print("🚀 Playwright Lambda Setup")
    print("=" * 40)

    # Install Playwright and browsers
    if not install_playwright_browsers():
        return

    # Create layer
    layer_path = create_playwright_layer()
    if layer_path:
        print(f"\n✅ Setup complete! Layer file: {layer_path}")
        print("\n📋 Next steps:")
        print("1. Upload the layer to AWS Lambda")
        print("2. Update your Lambda function to use the layer")
        print("3. Update the handler to use lambda_handler_playwright.py")
    else:
        print("\n❌ Setup failed!")


if __name__ == "__main__":
    main()
