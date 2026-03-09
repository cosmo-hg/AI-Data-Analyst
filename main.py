#!/usr/bin/env python3
"""
AI Data Analyst - Main Entry Point
Launches the Streamlit application for natural language data analysis.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
UI_APP = PROJECT_ROOT / "ui" / "app.py"


def main():
    """Launch the AI Data Analyst Streamlit application."""
    print("=" * 50)
    print("  🤖 AI Data Analyst")
    print("  Powered by Google Gemini")
    print("=" * 50)
    print()

    if not UI_APP.exists():
        print("❌ UI app not found:", UI_APP)
        sys.exit(1)

    print("Starting Streamlit application...")
    print("Open http://localhost:8501 in your browser")
    print("Press Ctrl+C to stop")
    print()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(UI_APP),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        check=False,
    )


if __name__ == "__main__":
    main()
