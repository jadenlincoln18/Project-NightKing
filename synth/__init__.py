"""Synthetic validation of the density extractor (see FINDINGS_SYNTHETIC.md).

The forward map is many tiny matrix products; multithreaded BLAS makes them 3x slower
in one process and 100x slower when several worker processes compete. Pin to one thread
before numpy is imported (a no-op if numpy is already loaded).
"""
import os as _os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")
