"""Trusted subprocess for one prospect. Fetches public pages, decides, runs the sandbox."""

import sys

from .sales.agent import run_prospect
from .sales.prospects import Prospects

if __name__ == "__main__":
    run_prospect(Prospects(), sys.argv[1])
