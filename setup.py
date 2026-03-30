#!/usr/bin/env python3
"""
Realviax Outreach Setup Script
Creates directories, initializes database, checks dependencies
"""
import os
import sys
import sqlite3
from pathlib import Path

def create_directories():
    dirs = [
        "database",
        "logs",
        "output/videos",
        "assets/music",
        "config",
        "scraper/cache",
        "dashboard/static",
        "dashboard/templates"
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {d}")

def init_database():
    from database.models import init_db, engine
    init_db(engine)
    print("✓ Database initialized at database/leads.db")

def check_dependencies():
    """Check if required external tools are installed"""
    import subprocess
    
    # Check ffmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ ffmpeg found")
        else:
            print("✗ ffmpeg not found or not working")
    except FileNotFoundError:
        print("✗ ffmpeg not installed. Install with: sudo apt-get install ffmpeg")
    
    # Check if Python packages are available
    required = ["requests", "beautifulsoup4", "sqlalchemy", "pillow", "jinja2", "fastapi", "uvicorn"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"✓ {pkg}")
        except ImportError:
            missing.append(pkg)
            print(f"✗ {pkg} not installed")
    
    if missing:
        print(f"\nInstall missing packages: pip install {' '.join(missing)}")

def main():
    print("🎬 Realviax Outreach Setup\n")
    print("1. Creating directory structure...")
    create_directories()
    print()
    print("2. Initializing database...")
    try:
        init_database()
    except Exception as e:
        print(f"✗ Database init failed: {e}")
        print("  Make sure you're in the realviax-outreach directory")
    print()
    print("3. Checking dependencies...")
    check_dependencies()
    print()
    print("✅ Setup complete!")
    print("\nNext steps:")
    print("1. Copy config/.env.example to .env and fill in your API keys")
    print("2. Place logo at assets/logo.png")
    print("3. Add royalty-free music to assets/music/")
    print("4. Run: python3 main.py --dashboard")

if __name__ == "__main__":
    main()