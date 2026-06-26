"""Backward-compatible shim for the ALP Python implementation."""

from alpcom.protocol import *  # noqa: F401,F403
from alpcom.protocol import main


if __name__ == "__main__":
    main()
