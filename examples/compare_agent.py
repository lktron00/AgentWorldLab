"""Compatibility entry point; ./scripts/experiment is the one-command interface."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from worldlab.experiment import main

if __name__ == "__main__":
    raise SystemExit(main())
