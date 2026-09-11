"""Trusted standalone 03_passing_ascent generator."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from modules.blender.exporter import run
if __name__ == "__main__":
    run("03_passing_ascent")
