#!/usr/bin/env python3
"""
metrics_registry.py — Registry of all available metrics for the ODAQ benchmark.

This file defines METRICS_REGISTRY which maps metric names to their implementations.
To see all available metrics, simply look at the registries below.

To add a new metric:
  1. Implement it in metrics.py
  2. Import it below and add to the appropriate registry
  3. Add a URL pointer to METRIC_SOURCES
  4. If it is lower-is-better, add it to NEGATED_METRICS (evaluate.py negates its scores)
  5. Add its reference type to METRIC_REFERENCE_TYPES
"""

from metrics import *

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

METRICS_REGISTRY = {
    "2f": twof,
    "AvgModDiff1": avg_mod_diff1,
    "ADB": adb,
    "NMR": nmr,
    "PEAQ-ODG": peaq_odg,
    "SI-SDR": si_sdr,
    "MCD": mcd,
    "CD": cd,
    "fwSNRseg": fwsnrseg,
    "PESQc2": pesq_c2,
    "PESQ": pesq,
    "STOI": stoi,
    "ESTOI": estoi,
    "ViSQOLAudio-v3": visqol_audio_v3,
    "CLAP-FAD": clap_fad,
    "SCOREQ_nr": scoreq_nr,
    "SCOREQ_ref": scoreq_ref,
    "PAM": pam,
    "SHEET-SSL-MOS": sheet_ssl_mos,
    "UTMOSv2": utmosv2,
    "NOMAD": nomad,
    "SQUIM_STOI": squim_stoi,
    "SQUIM_PESQ": squim_pesq,
    "SQUIM_SI-SDR": squim_si_sdr,
    "SQUIM_MOS": squim_mos,
    "URGENT-MOS": urgent_mos,
    "URGENT-CMOS": urgent_cmos,
    "ITU-T-P.566": itu_t_p566,
    "DNSMOS-P835-OVRL": dnsmos_p835_ovrl,
    "DNSMOS-P808": dnsmos_p808,
    "HASQIv2": hasqiv2,
    "HASPIv2": haspiv2,
    "HAAQI": haaqi,
    "SMAQ": smaq,
    "BINAQUAL": binaqual,
}

# Lower-is-better metrics: evaluate.py negates their scores so that all scores are
# higher-is-better (the functions in metrics.py return each metric's own scale).
# Shown as "−Name" on the website.
NEGATED_METRICS = {
    "AvgModDiff1",
    "ADB",
    "NMR",
    "MCD",
    "CD",
    "CLAP-FAD",
    "SCOREQ_ref",
    "NOMAD",
}

# ---------------------------------------------------------------------------
# Reference types — which reference each metric needs (filter on the website)
# ---------------------------------------------------------------------------

# "full-reference": compares the target with its own reference.
# "no-reference": judges the target alone.
# "non-matching-reference": needs a clean reference that need not match the target
#   (in this benchmark it is given the target's own reference).
METRIC_REFERENCE_TYPES = {
    "2f": "full-reference",
    "AvgModDiff1": "full-reference",
    "ADB": "full-reference",
    "NMR": "full-reference",
    "PEAQ-ODG": "full-reference",
    "SI-SDR": "full-reference",
    "MCD": "full-reference",
    "CD": "full-reference",
    "fwSNRseg": "full-reference",
    "PESQc2": "full-reference",
    "PESQ": "full-reference",
    "STOI": "full-reference",
    "ESTOI": "full-reference",
    "ViSQOLAudio-v3": "full-reference",
    "CLAP-FAD": "full-reference",
    "SCOREQ_nr": "no-reference",
    "SCOREQ_ref": "full-reference",
    "PAM": "no-reference",
    "SHEET-SSL-MOS": "no-reference",
    "UTMOSv2": "no-reference",
    "NOMAD": "non-matching-reference",
    "SQUIM_STOI": "no-reference",
    "SQUIM_PESQ": "no-reference",
    "SQUIM_SI-SDR": "no-reference",
    "SQUIM_MOS": "non-matching-reference",
    "URGENT-MOS": "no-reference",
    "URGENT-CMOS": "full-reference",
    "ITU-T-P.566": "no-reference",
    "DNSMOS-P835-OVRL": "no-reference",
    "DNSMOS-P808": "no-reference",
    "HASQIv2": "full-reference",
    "HASPIv2": "full-reference",
    "HAAQI": "full-reference",
    "SMAQ": "full-reference",
    "BINAQUAL": "full-reference",
}

# ---------------------------------------------------------------------------
# Sources — where each metric's reference code lives (shown on the website)
# ---------------------------------------------------------------------------

METRIC_SOURCES = {
    "2f": "https://github.com/kwatcharasupat/2f-model",
    "AvgModDiff1": "https://github.com/kwatcharasupat/2f-model",
    "ADB": "https://github.com/kwatcharasupat/2f-model",
    "NMR": "https://www-mmsp.ece.mcgill.ca/Documents/Downloads/AFsp/index.html",
    "PEAQ-ODG": "https://www-mmsp.ece.mcgill.ca/Documents/Downloads/AFsp/index.html",
    "SI-SDR": "https://github.com/sigsep/bsseval/issues/3",
    "MCD": "https://github.com/stefantaubert/mel-cepstral-distance",
    "CD": "https://github.com/schmiph2/pysepm",
    "fwSNRseg": "https://github.com/schmiph2/pysepm",
    "PESQc2": "https://github.com/audiolabs/PESQ",
    "PESQ": "https://github.com/ludlows/pesq",
    "STOI": "https://github.com/mpariente/pystoi",
    "ESTOI": "https://github.com/mpariente/pystoi",
    "ViSQOLAudio-v3": "https://github.com/google/visqol",
    "CLAP-FAD": "https://huggingface.co/lukewys/laion_clap/blob/main/music_audioset_epoch_15_esc_90.14.pt",
    "SCOREQ_nr": "https://github.com/alessandroragano/scoreq",
    "SCOREQ_ref": "https://github.com/alessandroragano/scoreq",
    "PAM": "https://github.com/soham97/PAM",
    "SHEET-SSL-MOS": "https://github.com/unilight/sheet",
    "UTMOSv2": "https://github.com/sarulab-speech/UTMOSv2",
    "NOMAD": "https://github.com/alessandroragano/nomad",
    "SQUIM_STOI": "https://docs.pytorch.org/audio/stable/tutorials/squim_tutorial.html",
    "SQUIM_PESQ": "https://docs.pytorch.org/audio/stable/tutorials/squim_tutorial.html",
    "SQUIM_SI-SDR": "https://docs.pytorch.org/audio/stable/tutorials/squim_tutorial.html",
    "SQUIM_MOS": "https://docs.pytorch.org/audio/stable/tutorials/squim_tutorial.html",
    "URGENT-MOS": "https://github.com/vvwangvv/URGENT-MOS",
    "URGENT-CMOS": "https://github.com/vvwangvv/URGENT-MOS",
    "ITU-T-P.566": "https://github.com/WafaaWardah/psamd",
    "DNSMOS-P835-OVRL": "https://lightning.ai/docs/torchmetrics/stable/audio/deep_noise_suppression_mean_opinion_score.html",
    "DNSMOS-P808": "https://lightning.ai/docs/torchmetrics/stable/audio/deep_noise_suppression_mean_opinion_score.html",
    "HASQIv2": "https://github.com/claritychallenge/clarity",
    "HASPIv2": "https://github.com/claritychallenge/clarity",
    "HAAQI": "https://github.com/claritychallenge/clarity",
    "SMAQ": "https://github.com/cwu307/mtl_audio_qual",
    "BINAQUAL": "https://github.com/QxLabIreland/Binaqual",
    "rho-perfect": "https://github.com/fcumlin/rho-perfect",
}

# ---------------------------------------------------------------------------
# Sanity check
# ---------------------------------------------------------------------------
# check that all metrics have sources

# rho-perfect is computed in evaluate.py, not registered as a metric, but is shown on the website too.
assert METRIC_SOURCES.keys() == METRICS_REGISTRY.keys() | {"rho-perfect"}, (
    "METRIC_SOURCES and METRICS_REGISTRY keys differ: "
    f"{sorted(METRIC_SOURCES.keys() ^ (METRICS_REGISTRY.keys() | {'rho-perfect'}))}"
)
