#!/usr/bin/env python3
"""
Test runner script for the presearcher pipeline test suite.

This script provides a convenient way to run all tests or specific test categories.
"""
import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> int:
    """Run a command and return its exit code."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run tests for the presearcher pipeline"
    )
    parser.add_argument(
        "--component",
        choices=[
            "all",
            "purpose",
            "outline",
            "rag",
            "literature",
            "report",
            "presearcher",
            "dataclasses"
        ],
        default="all",
        help="Which component to test (default: all)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage",
        "-c",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--failfast",
        "-x",
        action="store_true",
        help="Stop on first failure"
    )
    
    args = parser.parse_args()
    
    # Map component names to test files
    component_map = {
        "purpose": "tests/test_purpose_generation.py",
        "outline": "tests/test_outline_generation.py",
        "rag": "tests/test_rag_agent.py",
        "literature": "tests/test_literature_search.py",
        "report": "tests/test_report_generation.py",
        "presearcher": "tests/test_presearcher_agent.py",
        "dataclasses": "tests/test_dataclasses.py",
        "all": "tests/"
    }
    
    # Build pytest command
    cmd = ["pytest"]
    
    # Add target
    cmd.append(component_map[args.component])
    
    # Add flags
    if args.verbose:
        cmd.append("-v")
    
    if args.failfast:
        cmd.append("-x")
    
    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
    
    # Add asyncio marker
    cmd.extend(["-m", "asyncio or not asyncio"])
    
    # Run tests
    component_name = args.component.title() if args.component != "all" else "All Components"
    exit_code = run_command(cmd, f"Running tests for: {component_name}")
    
    if exit_code == 0:
        print(f"\n✅ All tests passed!")
        if args.coverage:
            print(f"\n📊 Coverage report generated in htmlcov/index.html")
    else:
        print(f"\n❌ Some tests failed!")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

