#!/usr/bin/env python3
"""
dataloaders_registry.py — Registry of all available dataloaders for the ODAQ Collection.

This file defines LOADER_REGISTRY which maps subset names to their loader implementations.
To see all available dataloaders, simply look at the registry below.

To add a new dataloader:
  1. Implement a new loader class in dataloaders.py by subclassing ODAQSubsetLoader
     - Implement the pairs() method to yield all (target, reference) audio pairs
     - Implement the subjective_csvs() method to return paths to results CSVs
  2. Add an entry to LOADER_REGISTRY below with a descriptive string key
  3. Add the key to ACTIVE_SUBSETS in config.py to enable evaluation

Example:
    If you created MyNewLoader in dataloaders.py, add:
        "my-new-subset": MyNewLoader
"""

from dataloaders import *

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

LOADER_REGISTRY = {
    "2024-icassp + 2024-aes": ICASSP2024Loader,
    "2025-aes": AES2025Loader,
    "proposed-addition": ProposedAdditionLoader,
    "2025-lanzendorfer": LanzendorferLoader,
}
