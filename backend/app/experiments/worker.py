"""Trusted subprocess for one claimed job (worker <job_id> <lease_token>)."""

import sys

from .jobs import run_job
from .store import Store

if __name__ == "__main__":
    run_job(Store(), sys.argv[1], sys.argv[2])
