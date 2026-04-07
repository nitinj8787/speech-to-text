#!/usr/bin/env python3
"""
Test script to verify that the environment is properly configured.

Run this after setting up your environment to ensure everything works.
"""

import sys


def main():
    """Run all configuration checks."""
    print("=" * 60)
    print("  Speech-to-Text Environment Configuration Check")
    print("=" * 60 + "\n")

    all_passed = True

    # Test 1: Python version
    print("1. Checking Python version...")
    version_info = sys.version_info
    if version_info >= (3, 10):
        print(f"   ✓ Python {version_info.major}.{version_info.minor}.{version_info.micro} (meets requirement: 3.10+)")
    else:
        print(f"   ✗ Python {version_info.major}.{version_info.minor}.{version_info.micro} (requires 3.10+)")
        all_passed = False

    # Test 2: Virtual environment
    print("\n2. Checking virtual environment...")
    try:
        if sys.prefix != sys.base_prefix:
            print(f"   ✓ Virtual environment active")
            print(f"     Location: {sys.prefix}")
        else:
            print("   ⚠ Warning: Not running in a virtual environment")
            print("     (Recommended: activate .venv)")
    except Exception:
        print("   ⚠ Could not determine virtual environment status")

    # Test 3: Import pydub
    print("\n3. Checking pydub installation...")
    try:
        from pydub import AudioSegment
        print("   ✓ pydub imported successfully")
    except ImportError as e:
        print(f"   ✗ Failed to import pydub: {e}")
        print("     Run: pip install -r requirements.txt")
        all_passed = False

    # Test 4: Check ffmpeg
    print("\n4. Checking ffmpeg availability...")
    try:
        from audio_utils import check_ffmpeg
        if check_ffmpeg():
            print("   ✓ ffmpeg found and configured")
        else:
            print("   ✗ ffmpeg not found")
            if sys.platform == "win32":
                print("     Windows: See WINDOWS_SETUP.md for installation instructions")
            else:
                print("     Install ffmpeg for your platform (see README.md)")
            all_passed = False
    except Exception as e:
        print(f"   ✗ Error checking ffmpeg: {e}")
        all_passed = False

    # Test 5: Import whisper
    print("\n5. Checking OpenAI Whisper installation...")
    try:
        import whisper
        print("   ✓ whisper imported successfully")
    except ImportError as e:
        print(f"   ✗ Failed to import whisper: {e}")
        print("     Run: pip install -r requirements.txt")
        all_passed = False

    # Test 6: Import Flask
    print("\n6. Checking Flask installation (for web UI)...")
    try:
        import flask
        print(f"   ✓ Flask {flask.__version__} imported successfully")
    except ImportError as e:
        print(f"   ✗ Failed to import Flask: {e}")
        print("     Run: pip install -r requirements.txt")
        all_passed = False

    # Test 7: Check numpy
    print("\n7. Checking NumPy installation...")
    try:
        import numpy as np
        print(f"   ✓ NumPy {np.__version__} imported successfully")
    except ImportError as e:
        print(f"   ✗ Failed to import NumPy: {e}")
        print("     Run: pip install -r requirements.txt")
        all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All checks passed! Your environment is ready to use.")
        print("\nNext steps:")
        print("  • CLI: python app.py --help")
        print("  • Web: python web_app.py")
    else:
        print("⚠ Some checks failed. Please fix the issues above.")
        if sys.platform == "win32":
            print("\nWindows users: Check WINDOWS_SETUP.md for detailed setup instructions")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
