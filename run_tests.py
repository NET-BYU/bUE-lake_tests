#!/usr/bin/env python3
"""
Test runner for bUE-lake_tests project.
Run all tests with coverage reporting.
"""

import subprocess
import sys
import os


def run_tests():
    """Run the test suite"""

    # Change to the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # Install test requirements if pytest is not available
    try:
        import pytest
    except ImportError:
        print("Installing test requirements...")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                "setup/requirements_test.txt",
            ],
            check=True,
        )

    # Run pytest with coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--cov=ota",
        "--cov-report=html:htmlcov",
        "--cov-report=term-missing",
    ]

    print("Running tests...")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n✅ All tests passed!")
        print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
