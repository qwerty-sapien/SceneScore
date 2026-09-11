"""Trusted standalone 06_sliding_contact generator."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from modules.blender.exporter import run
if __name__ == "__main__":
    run("06_sliding_contact")
