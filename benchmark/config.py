"""
config.py — metric/data selection and output settings for the ODAQ benchmark.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
# For a full list of available metrics, see METRICS_REGISTRY in metrics_registry.py
# METRICS can be a single metric or a list of metrics to run
# Use "ALL" to run all available metrics from METRICS_REGISTRY
# Example: single metric "PESQc2" or multiple ["PESQc2", "SI-SDR"] or "ALL"
METRICS = [
    "2f", "AvgModDiff1", "ADB", "NMR", "PEAQ-ODG", "SI-SDR", "MCD", "CD", "fwSNRseg", "PESQc2", "STOI",
    "ESTOI", "ViSQOLAudio-v3", "CLAP-FAD", "SCOREQ_nr", "SCOREQ_ref", "PAM", "SHEET-SSL-MOS", "UTMOSv2", "NOMAD",
    "SQUIM_STOI", "SQUIM_PESQ", "SQUIM_SI-SDR", "SQUIM_MOS", "URGENT-MOS", "URGENT-CMOS",
    "ITU-T-P.566", "DNSMOS-P835-OVRL", "DNSMOS-P808", "HASQIv2", "HASPIv2", "HAAQI", "SMAQ", "BINAQUAL",
]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Root of the odaq-collection directory (sibling of this benchmark/ folder).
COLLECTION_ROOT = Path("./odaq-collection")

# PQevalAudio executable from AFsp, used by the PEAQ-ODG and NMR metrics (see README).
PQEVALAUDIO_PATH = Path(__file__).resolve().parent / "PQevalAudio.darwin"

# ---------------------------------------------------------------------------
# Subset Selection
# ---------------------------------------------------------------------------
# Comment out subsets to exclude them from the evaluation run.
#
# Subset notes:
#   2024-icassp + 2024-aes — LP + PE + SH + TM + UN + DE processing methods;
#                            2024-aes provides additional listener cohorts (B1, B2)
#                            for the same 2024-icassp audio items
#   2025-aes               — SHMS + SHLR + QNMS + QNLR (spatially processed)
#   proposed-addition      — ICC + ILD + DE (binaural-cue conditions)
#   2025-lanzendorfer      — codec conditions (speech / combined)
ACTIVE_SUBSETS = [
    "proposed-addition",
    "2024-icassp + 2024-aes",  # download from odaq-collection/2024-icassp/ and 2024-aes/
    "2025-aes",                # download from odaq-collection/2025-aes/
    "2025-lanzendorfer",       # download from odaq-collection/2025-lanzendorfer/
]

# ---------------------------------------------------------------------------
# Scores
# ---------------------------------------------------------------------------
# Metric score caches (one CSV per metric) are written to SCORES_DIR.
SCORES_DIR = Path(__file__).resolve().parent / "scores"
