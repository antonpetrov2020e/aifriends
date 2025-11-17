#!/usr/bin/env python3
"""
Convenience script to run the AI Friends bot
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import main

if __name__ == "__main__":
    print("=" * 60)
    print("AI Friends Bot - Wellness Companion")
    print("Version: 0.1.0 (MVP Phase 1)")
    print("=" * 60)
    print()

    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBot stopped by user. Goodbye! 👋")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error starting bot: {e}")
        print("\nPlease check:")
        print("1. .env file exists and contains valid tokens")
        print("2. All dependencies are installed (pip install -r requirements.txt)")
        print("3. Python version is 3.10+")
        sys.exit(1)
