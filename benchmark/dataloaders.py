"""
dataloaders.py — subset loaders for the ODAQ Collection.

Each loader class yields all unique (target, reference) audio pairs for its
subset, along with metadata needed for reporting.

To add a new subset:
  1. Subclass ODAQSubsetLoader and implement pairs() and subjective_csvs().
  2. Add an entry to LOADER_REGISTRY in dataloaders_registry.py.
  3. Add the key to ACTIVE_SUBSETS in config.py.
"""

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd


REF_CONDITIONS = {"Ref", "reference"}
ANCHOR_CONDITIONS = {"LP3.5", "LP7", "LP35", "LP70", "Mono", "anchor35", "anchor70"}


class ODAQSubsetLoader(ABC):
    def __init__(self, name: str, root: Path):
        self.name = name
        self.root = root

    @abstractmethod
    def pairs(self) -> list[dict]:
        """Return list of dicts: subset, item, condition, method_group, target_wav, ref_wav"""
        ...

    @abstractmethod
    def subjective_csvs(self) -> list[str]:
        """Return relative paths to all results CSVs for this subset."""
        ...

    def _load_csv(self, rel_path: str) -> pd.DataFrame:
        return pd.read_csv(self.root / rel_path)


class ICASSP2024Loader(ODAQSubsetLoader):
    """2024-icassp audio + subjective scores from 2024-icassp and 2024-aes (cohorts B1, B2)."""
    CSV_PATHS = [
        "2024-icassp/ODAQ_listening_test/ODAQ_results.csv",
        "2024-aes/Cohort_B1_results.csv",
        "2024-aes/Cohort_B2_results.csv",
    ]
    WAV_ROOT = "2024-icassp/ODAQ_listening_test"

    def __init__(self, root: Path):
        super().__init__("2024-icassp + 2024-aes", root)

    def subjective_csvs(self):
        return self.CSV_PATHS

    def pairs(self):
        df = pd.concat([self._load_csv(p) for p in self.CSV_PATHS], ignore_index=True)
        wav_root = self.root / self.WAV_ROOT
        unique = df[~df["condition"].isin(REF_CONDITIONS)].drop_duplicates(
            subset=["item", "process"]
        )
        return [
            {
                "subset": self.name,
                "item": r["item"],
                "condition": r["condition"],
                "method_group": r["method"],
                "target_wav": str(wav_root / r["item"] / f"{r['process']}.wav"),
                "ref_wav": str(wav_root / r["item"] / "reference.wav"),
            }
            for _, r in unique.iterrows()
        ]


class AES2025Loader(ODAQSubsetLoader):
    CSV_PATH = "2025-aes/ODAQ_v1.5_listening_test/ODAQ_1.5_results.csv"
    WAV_ROOT = "2025-aes/ODAQ_v1.5_listening_test"

    def __init__(self, root: Path):
        super().__init__("2025-aes", root)

    def subjective_csvs(self):
        return [self.CSV_PATH]

    def _content_prefix(self, item_dir: Path) -> str:
        refs = list(item_dir.glob("*_reference.wav"))
        if refs:
            return refs[0].name.replace("_reference.wav", "")
        method_prefix = item_dir.name.split("_", 1)[0] + "_"
        return item_dir.name[len(method_prefix):]

    def pairs(self):
        df = self._load_csv(self.CSV_PATH)
        wav_root = self.root / self.WAV_ROOT
        unique = df[~df["condition"].isin(REF_CONDITIONS)].drop_duplicates(
            subset=["item", "process"]
        )
        prefix_cache = {}
        results = []
        for _, r in unique.iterrows():
            item_dir = wav_root / r["item"]
            if r["item"] not in prefix_cache:
                prefix_cache[r["item"]] = self._content_prefix(item_dir)
            content = prefix_cache[r["item"]]
            results.append({
                "subset": self.name,
                "item": r["item"],
                "condition": r["condition"],
                "method_group": r["method"],
                "target_wav": str(item_dir / f"{content}_{r['process']}.wav"),
                "ref_wav": str(item_dir / f"{content}_reference.wav"),
            })
        return results


class ProposedAdditionLoader(ODAQSubsetLoader):
    CSV_PATHS = [
        "proposed-addition/odaq_binauralcue_listening_test/odaq_binauralcue_results.csv",
        "proposed-addition/odaq_binauralcue_de_listening_test/odaq_binauralcue_de_results.csv",
    ]
    WAV_ROOTS = [
        "proposed-addition/odaq_binauralcue_listening_test",
        "proposed-addition/odaq_binauralcue_de_listening_test",
    ]

    def __init__(self, root: Path):
        super().__init__("proposed-addition", root)

    def subjective_csvs(self):
        return self.CSV_PATHS

    def pairs(self):
        results = []
        for csv_path, wav_rel in zip(self.CSV_PATHS, self.WAV_ROOTS):
            df = self._load_csv(csv_path)
            wav_root = self.root / wav_rel
            unique = df[~df["condition"].isin(REF_CONDITIONS)].drop_duplicates(
                subset=["item", "process"]
            )
            for _, r in unique.iterrows():
                results.append({
                    "subset": self.name,
                    "item": r["item"],
                    "condition": r["condition"],
                    "method_group": r["method"],
                    "target_wav": str(wav_root / r["item"] / f"{r['process']}.wav"),
                    "ref_wav": str(wav_root / r["item"] / "reference.wav"),
                })
        return results


class LanzendorferLoader(ODAQSubsetLoader):
    CSV_PATH = "2025-lanzendorfer/lanzendorfer_2025_results.csv"
    LZ_ROOT = "2025-lanzendorfer"
    WAV_REMAP = {"anchor35": "low", "anchor70": "mid"}

    def __init__(self, root: Path):
        super().__init__("2025-lanzendorfer", root)

    def subjective_csvs(self):
        return [self.CSV_PATH]

    def pairs(self):
        df = self._load_csv(self.CSV_PATH)
        lz_root = self.root / self.LZ_ROOT
        unique = df[~df["condition"].isin(REF_CONDITIONS)].drop_duplicates(
            subset=["item", "condition", "dataset_type"]
        )
        results = []
        for _, r in unique.iterrows():
            dtype = r["dataset_type"]
            wav_dir = lz_root / f"dataset_folder_{dtype}" / r["item"]
            wav_name = self.WAV_REMAP.get(r["condition"], r["condition"])
            results.append({
                "subset": self.name,
                "item": r["item"],
                "condition": r["condition"],
                "method_group": dtype,
                "target_wav": str(wav_dir / f"{wav_name}.wav"),
                "ref_wav": str(wav_dir / "reference.wav"),
            })
        return results
