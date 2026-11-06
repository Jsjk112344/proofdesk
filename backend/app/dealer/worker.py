"""Trusted leased worker; never passes controller credentials into Docker."""

import sys

from ..execution.controller import interruptions
from .jobs import run_job
from .store import DealerStore

if __name__ == "__main__":
    with interruptions():
        run_job(DealerStore(), sys.argv[1], sys.argv[2])
