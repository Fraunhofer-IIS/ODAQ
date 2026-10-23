#!/usr/bin/env python3
"""
metrics.py — metric implementations or wrappers for the ODAQ benchmark.

Each metric is a standalone function with signature:
    compute(ref_path: str, target_path: str) -> float

To add a new metric:
  1. Define a function below following the same signature.
  2. Register it in METRICS_REGISTRY in metrics_registry.py
  3. Add "<your_key>" to the METRICS list in config.py.

Functions return each metric's own scale. evaluate.py negates the lower-is-better ones
(NEGATED_METRICS in metrics_registry.py), so that all scores are higher-is-better.

Available metrics:
  twof        — 2f model (seabass), returns 0–100 MUSHRA scale
  avg_mod_diff1 — PEAQ MOV AvgModDiff1 (lower is better), from seabass
  adb         — PEAQ MOV ADB (lower is better), from seabass
  nmr         — PEAQ MOV Total NMRB (dB, lower is better), from PQevalAudio
  peaq_odg    — PEAQ basic version ODG (-4 to 0), from PQevalAudio
  si_sdr      — Scale-Invariant SDR (dB), native sample rate, mono
  pesq_c2     — PESQ (P.862.2) with Corrigendum 2, wideband at 16 kHz, mono
  pesq        — PESQ (P.862.2) without Corrigendum 2 (ludlows/pesq), wideband at 16 kHz, mono
  stoi        — Short-Time Objective Intelligibility (0-1), pystoi, mono
  estoi       — Extended STOI, pystoi, mono
  visqol_audio_v3 — ViSQOL v3 audio mode, 48 kHz mono, higher-is-better MOS-LQO
  clap_fad    — Per-pair Fréchet Audio Distance using CLAP-music embeddings (lower is better)
  scoreq_nr   — ScoreQ no-reference mode (natural speech), returns MOS (1-5)
  scoreq_ref  — ScoreQ reference-based mode (natural speech), returns distance (lower is better)
  pam         — PAM (Prompting Audio-Language Models), no-reference quality assessment (higher is better)
  sheet_ssl_mos — SHEET SSL-MOS no-reference speech MOS predictor (1-5), 16 kHz mono
  utmosv2     — UTMOSv2 no-reference speech naturalness MOS predictor (1-5), 16 kHz mono
  nomad       — NOMAD non-matching reference distance (ref_path as reference, lower is better), 16 kHz mono
  squim_stoi, squim_pesq, squim_si_sdr — TorchAudio-SQUIM no-reference estimates, 16 kHz mono
  squim_mos   — TorchAudio-SQUIM MOS (1-5) with ref_path as non-matching reference, 16 kHz mono
  urgent_mos  — URGENT-MOS absolute MOS (1-5), no reference, 16 kHz mono
  urgent_cmos — URGENT-MOS comparative MOS of target vs reference (-3 to +3), 16 kHz mono
  itu_t_p566  — ITU-T P.566 overall speech quality (MOS 1-5), no reference, 48 kHz mono
  dnsmos_p835_ovrl — DNSMOS P.835 overall quality (OVRL, 1-5), no reference, 16 kHz mono
  hasqiv2, haspiv2, haaqi — Clarity HASQI v2 / HASPI v2 / HAAQI v1, normal-hearing audiogram, mean over channels
  smaq        — SMAQ multitask teacher-student MOS (1-5), 48 kHz mono
  binaqual    — Binaural audio quality assessment (higher is better)"""

import contextlib
import io
from functools import lru_cache
from pathlib import Path

import librosa
import numpy as np
# Load SciPy's OpenMP runtime before any torch import: the other order aborts with
# "OMP: Error #15" in this conda env (torch and SciPy bundle separate libomp copies).
import scipy.signal  # noqa: F401


# ---------------------------------------------------------------------------
# twof
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _twof_with_movs(ref_path: str, target_path: str) -> tuple[float, float, float]:
    """2f score and its two PEAQ MOVs, cached so the three metrics share one computation."""
    from seabass.core.models.mms import estimated_mean_mushra_score_file
    score, movs = estimated_mean_mushra_score_file(target_path, ref_path, _return_movs=True)
    return float(score), float(movs["avg_mod_diff1"]), float(movs["adb"])


def twof(ref_path: str, target_path: str) -> float:
    """2f model (seabass) — returns 0–100 MUSHRA scale."""
    return _twof_with_movs(ref_path, target_path)[0]


def avg_mod_diff1(ref_path: str, target_path: str) -> float:
    """PEAQ MOV AvgModDiff1 used by 2f (lower is better)."""
    return _twof_with_movs(ref_path, target_path)[1]


def adb(ref_path: str, target_path: str) -> float:
    """PEAQ MOV ADB (average distorted block) used by 2f (lower is better)."""
    return _twof_with_movs(ref_path, target_path)[2]


# ---------------------------------------------------------------------------
# PQevalAudio (PEAQ basic version): nmr, peaq_odg
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _pqevalaudio(ref_path: str, target_path: str) -> dict[str, float]:
    """Run PQevalAudio once per pair and parse its MOVs and ODG.

    PQevalAudio only accepts 48 kHz input, so other rates are resampled to temporary files.
    Requires the PQevalAudio executable at config.PQEVALAUDIO_PATH.
    """
    import re
    import subprocess
    import config
    import soundfile as sf
    from tempfile import TemporaryDirectory

    sample_rate = 48000
    executable = config.PQEVALAUDIO_PATH
    if not Path(executable).is_file():
        raise FileNotFoundError(f"PQevalAudio not found at {executable}; set PQEVALAUDIO_PATH in config.py")
    with TemporaryDirectory() as directory:
        paths = []
        for name, path in (("reference.wav", ref_path), ("target.wav", target_path)):
            if sf.info(path).samplerate != sample_rate:
                signal, _ = librosa.load(path, sr=sample_rate, mono=False)
                path = str(Path(directory) / name)
                sf.write(path, signal.T, sample_rate)
            paths.append(path)
        output = subprocess.run([str(executable), *paths],
                                capture_output=True, text=True, check=True).stdout

    values = {}
    for key, label in (("nmr", "Total NMRB"), ("odg", "Objective Difference Grade")):
        match = re.search(rf"{label}: (-?\d+\.?\d*)", output)
        if match is None:
            raise ValueError(f"PQevalAudio output has no '{label}' for {target_path}")
        values[key] = float(match[1])
    return values


def nmr(ref_path: str, target_path: str) -> float:
    """PEAQ MOV Total NMRB (dB) from PQevalAudio (lower is better)."""
    return _pqevalaudio(ref_path, target_path)["nmr"]


def peaq_odg(ref_path: str, target_path: str) -> float:
    """PEAQ basic version Objective Difference Grade (ODG, -4 to 0) from PQevalAudio."""
    return _pqevalaudio(ref_path, target_path)["odg"]


# ---------------------------------------------------------------------------
# si_sdr
# ---------------------------------------------------------------------------

def si_sdr(ref_path: str, target_path: str) -> float:
    """Scale-Invariant Signal-to-Distortion Ratio (dB), native sample rate, mono."""
    ref, _ = librosa.load(ref_path, sr=None, mono=True)
    deg, _ = librosa.load(target_path, sr=None, mono=True)
    min_len = min(len(ref), len(deg))
    ref, deg = ref[:min_len], deg[:min_len]
    alpha = np.dot(ref, deg) / np.dot(ref, ref)
    e_true = alpha * ref
    e_res = deg - e_true
    with np.errstate(divide="ignore", invalid="ignore"):
        score = 10 * np.log10(np.sum(e_true ** 2) / np.sum(e_res ** 2))
    return float(np.clip(score, -100, 100)) # avoid +/- Inf


# ---------------------------------------------------------------------------
# pesq_c2
# ---------------------------------------------------------------------------

def pesq_c2(ref_path: str, target_path: str, sr: int = 16000) -> float:
    """PESQ with Corrigendum 2 (P.862.2), wideband at 16 kHz, mono downmix."""
    from pesqc2 import pesq
    ref, _ = librosa.load(ref_path, sr=sr, mono=True)
    deg, _ = librosa.load(target_path, sr=sr, mono=True)
    return pesq(sr, ref, deg, "wb")


# ---------------------------------------------------------------------------
# pesq
# ---------------------------------------------------------------------------

def pesq(ref_path: str, target_path: str, sr: int = 16000) -> float:
    """PESQ using pesq package (pip install pesq), wideband at 16 kHz, mono downmix."""
    from pesq import pesq as pesq_fn
    ref, _ = librosa.load(ref_path, sr=sr, mono=True)
    deg, _ = librosa.load(target_path, sr=sr, mono=True)
    return pesq_fn(sr, ref, deg, "wb")


# ---------------------------------------------------------------------------
# stoi, estoi
# ---------------------------------------------------------------------------

def _pystoi(ref_path: str, target_path: str, extended: bool) -> float:
    """Run pystoi on a mono downmix of both files.

    pystoi resamples to 10 kHz itself (as the original MATLAB code) and needs equal lengths,
    so both signals are loaded at their native rate and trimmed to the shorter one.
    """
    from pystoi import stoi as stoi_fn
    ref, sr = librosa.load(ref_path, sr=None, mono=True)
    deg, _ = librosa.load(target_path, sr=sr, mono=True)  # same rate as ref
    min_len = min(len(ref), len(deg))
    return float(stoi_fn(ref[:min_len], deg[:min_len], sr, extended=extended))


def stoi(ref_path: str, target_path: str) -> float:
    """Short-Time Objective Intelligibility (STOI, 0-1, higher is better), mono downmix."""
    return _pystoi(ref_path, target_path, extended=False)


def estoi(ref_path: str, target_path: str) -> float:
    """Extended STOI (ESTOI, Jensen & Taal 2016, higher is better), mono downmix."""
    return _pystoi(ref_path, target_path, extended=True)


# ---------------------------------------------------------------------------
# visqol_audio_v3 (ViSQOL v3 audio mode)
# ---------------------------------------------------------------------------

_visqol_audio_api = None


def _get_visqol_audio_api():
    """Initialize ViSQOL and register its result protobuf for native conversion."""
    global _visqol_audio_api
    if _visqol_audio_api is None:
        try:
            from visqol import visqol_lib_py
            from visqol.pb2 import similarity_result_pb2 as _similarity_result_pb2
            from visqol.pb2 import visqol_config_pb2
        except ImportError as error:
            raise ImportError(
                "ViSQOL_audio requires the optional Google ViSQOL Python bindings. "
                "See the ViSQOL setup section in README.md."
            ) from error
        model_path = Path(visqol_lib_py.__file__).parent / "model" / "libsvm_nu_svr_model.txt"
        if not model_path.is_file():
            raise FileNotFoundError(f"ViSQOL audio model not found: {model_path}")
        configuration = visqol_config_pb2.VisqolConfig()
        configuration.audio.sample_rate = 48000
        configuration.options.use_speech_scoring = False
        configuration.options.svr_model_path = str(model_path)
        api = visqol_lib_py.VisqolApi()
        api.Create(configuration)
        _visqol_audio_api = api
    return _visqol_audio_api


def visqol_audio_v3(ref_path: str, target_path: str) -> float:
    """ViSQOL audio-mode MOS-LQO, resampled to 48 kHz and downmixed to mono."""
    api = _get_visqol_audio_api()
    reference, _ = librosa.load(ref_path, sr=48000, mono=True, dtype=np.float64)
    degraded, _ = librosa.load(target_path, sr=48000, mono=True, dtype=np.float64)
    result = api.Measure(np.ascontiguousarray(reference), np.ascontiguousarray(degraded))
    return float(result.moslqo)


# ---------------------------------------------------------------------------
# clap_fad
#
# Checkpoint: music_audioset_epoch_15_esc_90.14.pt (HTSAT-base, music model)
# Download:   https://huggingface.co/lukewys/laion_clap/blob/main/music_audioset_epoch_15_esc_90.14.pt
# ---------------------------------------------------------------------------

CLAP_CKPT_URL = "https://huggingface.co/lukewys/laion_clap/resolve/main/music_audioset_epoch_15_esc_90.14.pt"
CLAP_CKPT_NAME = "music_audioset_epoch_15_esc_90.14.pt"

_clap_model = None

def _download_clap_checkpoint() -> Path:
    """Download CLAP checkpoint to cache directory if not already present."""
    import urllib.request
    from tqdm import tqdm
    
    # Use a cache directory in the project
    cache_dir = Path(__file__).parent / "cache" / "clap"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = cache_dir / CLAP_CKPT_NAME
    
    if ckpt_path.exists():
        return ckpt_path
    
    print(f"Downloading CLAP checkpoint to {ckpt_path}...")
    
    class DownloadProgressBar(tqdm):
        def update_to(self, b=1, bsize=1, tsize=None):
            if tsize is not None:
                self.total = tsize
            self.update(b * bsize - self.n)
    
    with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=CLAP_CKPT_NAME) as t:
        urllib.request.urlretrieve(CLAP_CKPT_URL, ckpt_path, reporthook=t.update_to)
    
    print(f"Downloaded CLAP checkpoint to {ckpt_path}")
    return ckpt_path


def _get_clap_model():
    global _clap_model
    if _clap_model is None:
        import laion_clap
        import sys
        import os
        ckpt_path = _download_clap_checkpoint()
        _clap_model = laion_clap.CLAP_Module(enable_fusion=False, amodel="HTSAT-base")
        # Suppress verbose checkpoint loading output
        print("Loading CLAP checkpoint...")
        old_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        try:
            _clap_model.load_ckpt(str(ckpt_path))
        finally:
            sys.stdout.close()
            sys.stdout = old_stdout
        print("CLAP checkpoint loaded successfully")
    return _clap_model


def _clap_embeddings(filepath: str, sr: int = 48000) -> np.ndarray:
    """Extract CLAP embeddings: 10s chunks, 1s hop. Returns (N, 512)."""
    import torch
    wav, _ = librosa.load(filepath, sr=sr, mono=True)
    wav = wav.reshape(1, -1)
    wav = np.float32(np.int16(wav * 32768) / 32768)
    chunk_size = 10 * sr
    hop_size = sr
    model = _get_clap_model()
    embeddings = []
    for i in range(0, wav.shape[1], hop_size):
        chunk = wav[:, i:i + chunk_size]
        if chunk.shape[1] < chunk_size:
            chunk = np.pad(chunk, ((0, 0), (0, chunk_size - chunk.shape[1])))
        with torch.no_grad():
            emb = model.get_audio_embedding_from_data(
                x=torch.from_numpy(chunk).float(), use_tensor=True)
            embeddings.append(emb.cpu().numpy())
    return np.concatenate(embeddings, axis=0)


def clap_fad(ref_path: str, target_path: str) -> float:
    """Per-pair Fréchet Audio Distance using CLAP-music embeddings (lower is better)."""
    from fadtk.fad import calc_frechet_distance
    ref_emb = _clap_embeddings(ref_path)
    tar_emb = _clap_embeddings(target_path)
    min_n = min(ref_emb.shape[0], tar_emb.shape[0])
    ref_emb, tar_emb = ref_emb[:min_n], tar_emb[:min_n]
    mu1, mu2 = np.mean(ref_emb, axis=0), np.mean(tar_emb, axis=0)
    cov1, cov2 = np.cov(ref_emb, rowvar=False), np.cov(tar_emb, rowvar=False)
    return float(calc_frechet_distance(mu1, cov1, mu2, cov2))


# ---------------------------------------------------------------------------
# scoreq_nr
# ---------------------------------------------------------------------------

_scoreq_nr_model = None

def _get_scoreq_nr_model():
    """Lazy-load ScoreQ no-reference model."""
    global _scoreq_nr_model
    if _scoreq_nr_model is None:
        import scoreq
        _scoreq_nr_model = scoreq.Scoreq(data_domain='natural', mode='nr')
    return _scoreq_nr_model


def scoreq_nr(ref_path: str, target_path: str) -> float:
    """ScoreQ no-reference mode for natural speech quality (MOS 1-5).
    
    Note: This metric ignores ref_path and only evaluates target_path quality.
    Returns Mean Opinion Score (MOS) between 1-5, higher is better.
    Automatically resamples to 16 kHz.
    """
    model = _get_scoreq_nr_model()
    pred_mos = model.predict(test_path=target_path, ref_path=None)
    return float(pred_mos)


# ---------------------------------------------------------------------------
# scoreq_ref
# ---------------------------------------------------------------------------

_scoreq_ref_model = None

def _get_scoreq_ref_model():
    """Lazy-load ScoreQ reference-based model."""
    global _scoreq_ref_model
    if _scoreq_ref_model is None:
        import scoreq
        _scoreq_ref_model = scoreq.Scoreq(data_domain='natural', mode='ref')
    return _scoreq_ref_model


def scoreq_ref(ref_path: str, target_path: str) -> float:
    """ScoreQ reference-based mode for natural speech quality.
    
    Returns Euclidean distance to clean speech. Lower values indicate better quality.
    Automatically resamples to 16 kHz.
    """
    model = _get_scoreq_ref_model()
    return float(model.predict(test_path=target_path, ref_path=ref_path))


# ---------------------------------------------------------------------------
# pam
# ---------------------------------------------------------------------------

_pam_model = None

def _get_pam_model():
    """Lazy-load PAM model.
    
    Requires PAM to be cloned in the current directory:
        git clone https://github.com/soham97/PAM.git
    """
    global _pam_model
    if _pam_model is None:
        import torch
        import sys
        from pathlib import Path
        
        # Add PAM to path
        pam_path = Path(__file__).parent / "PAM"
        if str(pam_path) not in sys.path:
            sys.path.insert(0, str(pam_path))
        
        from PAM import PAM
        _pam_model = PAM(use_cuda=torch.cuda.is_available())
    
    return _pam_model


def pam(ref_path: str, target_path: str) -> float:
    """PAM (Prompting Audio-Language Models for Audio Quality Assessment).
    
    No-reference metric that assesses audio quality by prompting Audio-Language Models.
    Note: This metric ignores ref_path and only evaluates target_path quality.
    Returns quality score where higher values indicate better quality.
    
    Requires: git clone https://github.com/soham97/PAM.git
    """
    model = _get_pam_model()
    
    # Import PAM's dataset (path already set in _get_pam_model)
    from dataset import AudioDataset
    
    # Create a minimal single-file dataset
    class SingleFileDataset(AudioDataset):
        def __init__(self, filepath):
            self.filelist = [filepath]
            self.repro = False  # Process entire audio, not just first 7 seconds
    
    # Load and process audio using PAM's dataset
    dataset = SingleFileDataset(target_path)
    file, audio = dataset[0]
    
    # Use dataset's collate to create batch and sample_index
    files, batch_chunks, sample_index = dataset.collate([(file, audio)])
    
    # Evaluate
    pam_scores, _ = model.evaluate(batch_chunks, sample_index)
    
    return float(pam_scores[0])


# ---------------------------------------------------------------------------
# sheet_ssl_mos
# ---------------------------------------------------------------------------

# Default model of SHEET's torch.hub entry "sheet_ssqa" (v0.2.5post1, as of Sep 2025):
# SSL-MOS (WavLM large) trained on all eight MOS-Bench training sets.
SHEET_MODEL_REPO = "unilight/sheet-models"
SHEET_MODEL_ID = "bvcc+somos+singmos+nisqa+tmhint-qi+tencent+pstn+urgent2024-mos/sslmos-wavlm_large/1337"
SHEET_MODEL_REVISION = "2a5bf30fd1f015e10f6bce10e54f1a1c037b3099"  # SHEET_MODEL_REPO commit, 2025-09-26
SHEET_MODEL_URL = f"https://huggingface.co/{SHEET_MODEL_REPO}/tree/{SHEET_MODEL_REVISION}/{SHEET_MODEL_ID}"
SHEET_SR = 16000
SHEET_MIN_SAMPLES = 1040  # minimum input length required by the model (from SHEET's hubconf.py)

_sheet_model = None

def _patch_torchaudio_for_s3prl():
    """Stub torchaudio APIs removed in 2.9 that s3prl touches at import time.

    s3prl imports all its upstreams; a few call torchaudio.set_audio_backend or import
    torchaudio.sox_effects. SSL-MOS only uses WavLM, which needs neither.
    """
    import sys
    import types
    import torchaudio

    if not hasattr(torchaudio, "set_audio_backend"):
        torchaudio.set_audio_backend = lambda *_, **__: None
    if "torchaudio.sox_effects" not in sys.modules:
        try:
            import torchaudio.sox_effects  # noqa: F401
        except ImportError:
            def unavailable(*_, **__):
                raise RuntimeError("torchaudio.sox_effects is not available in this torchaudio")
            stub = types.ModuleType("torchaudio.sox_effects")
            stub.apply_effects_tensor = stub.apply_effects_file = unavailable
            sys.modules["torchaudio.sox_effects"] = stub
            torchaudio.sox_effects = stub


def _get_sheet_model():
    """Lazy-load the SHEET SSL-MOS model, mirroring sheet_ssqa() in SHEET's hubconf.py."""
    global _sheet_model
    if _sheet_model is None:
        import torch
        import yaml
        from huggingface_hub import hf_hub_download

        _patch_torchaudio_for_s3prl()
        from sheet.models.sslmos import SSLMOS

        config_path = hf_hub_download(SHEET_MODEL_REPO, f"{SHEET_MODEL_ID}/config.yml",
                                    revision=SHEET_MODEL_REVISION)
        ckpt_path = hf_hub_download(SHEET_MODEL_REPO, f"{SHEET_MODEL_ID}/checkpoint-best.bin",
                                    revision=SHEET_MODEL_REVISION)
        with open(config_path) as f:
            config = yaml.load(f, Loader=yaml.Loader)
        model = SSLMOS(config["model_input"], **config["model_params"])
        model.load_state_dict(torch.load(ckpt_path, weights_only=True, map_location="cpu"))
        model.eval()
        _sheet_model = (model, config)
    return _sheet_model


def sheet_ssl_mos(ref_path: str, target_path: str) -> float:
    """SHEET SSL-MOS no-reference speech quality predictor (MOS 1-5).

    Note: This metric ignores ref_path and only evaluates target_path quality.
    The model is mono 16 kHz, so stereo input is downmixed and resampled.
    Returns predicted MOS, higher is better.
    """
    import torch

    model, config = _get_sheet_model()
    signal, _ = librosa.load(target_path, sr=SHEET_SR, mono=True)
    if len(signal) < SHEET_MIN_SAMPLES:
        to_pad = (SHEET_MIN_SAMPLES - len(signal)) // 2
        signal = np.pad(signal, (to_pad, to_pad))
    wav = torch.from_numpy(signal).float().unsqueeze(0)
    inputs = {
        config["model_input"]: wav,
        config["model_input"] + "_lengths": wav.new_tensor([wav.size(1)]).long(),
    }
    with torch.no_grad():
        if config["inference_mode"] == "mean_listener":
            outputs = model.mean_listener_inference(inputs)
        else:
            outputs = model.mean_net_inference(inputs)
    return float(outputs["scores"].cpu().numpy()[0])


# ---------------------------------------------------------------------------
# utmosv2
# ---------------------------------------------------------------------------

# UTMOSv2 (VoiceMOS Challenge 2024) default model, as in the UTMOSv2 README:
# config "fusion_stage3", fold 0, seed 42.
#
# Why we download the weights ourselves instead of letting create_model() do it:
#   - create_model() always downloads the latest weights, so results could change silently
#     if the authors update them. We pin a fixed commit (UTMOSV2_MODEL_REVISION).
# UTMOSV2_MODEL_FILE points to the same fold-0 file that create_model() would load by default as of today.
UTMOSV2_MODEL_REPO = "sarulab-speech/UTMOSv2"
UTMOSV2_MODEL_FILE = "fold0_s42_best_model.pth"
UTMOSV2_MODEL_REVISION = "506474f2b33dc77c234d668cc419be1861899cad"  # UTMOSV2_MODEL_REPO commit, 2025-05-10

_utmosv2_model = None

def utmosv2(ref_path: str, target_path: str) -> float:
    """UTMOSv2 no-reference speech naturalness MOS predictor (1-5).

    Note: This metric ignores ref_path and only evaluates target_path quality.
    The model (with the pinned pretrained weights) is loaded lazily on first call.
    UTMOSv2 loads the file itself (librosa, downmixed to mono, resampled to 16 kHz).
    It scores randomly selected short frames, so we average 5 repetitions as in the paper
    (docs/inference.md; the paper also averages all 5 folds, we use fold 0 only) and seed
    NumPy, which drives the frame selection, so scores are reproducible.
    Returns predicted MOS, higher is better.
    """
    import torch

    global _utmosv2_model
    if _utmosv2_model is None:
        import utmosv2 as utmosv2_lib  # aliased: this function is also named utmosv2
        from huggingface_hub import hf_hub_download

        checkpoint = hf_hub_download(UTMOSV2_MODEL_REPO, UTMOSV2_MODEL_FILE,
                                     revision=UTMOSV2_MODEL_REVISION)
        _utmosv2_model = utmosv2_lib.create_model(pretrained=True, checkpoint_path=checkpoint)

    np.random.seed(0)
    # num_workers=0: v1.3.0 defaults to 4 DataLoader workers, which fail with the "spawn" start
    # method (default on macOS/Windows) because the model config holds an unpicklable module.
    return float(_utmosv2_model.predict(
        input_path=target_path, num_repetitions=5, num_workers=0, verbose=False,
        device="cuda" if torch.cuda.is_available() else "cpu"))


# ---------------------------------------------------------------------------
# nomad
# ---------------------------------------------------------------------------

# NOMAD (Non-Matching Audio Distance) official weights, same URL as nomad_audio 0.0.9.
#
# Why we don't use the nomad_audio package:
#   - it needs fairseq and pins torch==1.12.1, neither of which installs on Python >= 3.11.
#   - importing it downloads weights into ./pt-models and loads the model right away.
# Instead we rebuild the same network: wav2vec 2.0 base from s3prl (a copy of the fairseq
# model, already installed for SHEET) plus NOMAD's 768->256 embedding layer.
# The checkpoint holds all weights (wav2vec 2.0 included), so wav2vec_small.pt is not needed.
# Checked against the nomad_audio README example (data/nmr-data vs data/test-data):
# all 8 pairwise distances match to 3 decimals.
# The download is pinned by SHA-256, since the Dropbox link could change silently.
NOMAD_MODEL_URL = ("https://www.dropbox.com/scl/fi/uws3wk327adbwqo22cr0p/nomad_best_model.pt"
                   "?rlkey=cco21iba6xxi81a0dm9lpa7zj&dl=1")
NOMAD_MODEL_SHA256 = "82e861f025176918aa487ea3d2cf4356c4c7ec0cb60ee7001eed9c9dae78b13a"

_nomad_model = None

def _get_nomad_model():
    """Lazy-load NOMAD (wav2vec 2.0 base + embedding layer), downloading the weights once."""
    global _nomad_model
    if _nomad_model is None:
        import torch
        from s3prl.upstream.wav2vec2.wav2vec2_model import Wav2Vec2Config, Wav2Vec2Model

        path = Path(torch.hub.get_dir()) / "checkpoints" / "nomad_best_model.pt"
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            torch.hub.download_url_to_file(NOMAD_MODEL_URL, str(path), hash_prefix=NOMAD_MODEL_SHA256)
        state = torch.load(path, map_location="cpu")

        ssl = Wav2Vec2Model(Wav2Vec2Config())  # defaults are the wav2vec 2.0 base config
        ssl.remove_pretraining_modules()
        ssl.load_state_dict({k.removeprefix("ssl_model."): v for k, v in state.items()
                             if k.startswith("ssl_model.")})
        embedding = torch.nn.Linear(768, 256)
        embedding.load_state_dict({"weight": state["embedding_layer.1.weight"],
                                   "bias": state["embedding_layer.1.bias"]})
        _nomad_model = (ssl.eval(), embedding.eval())
    return _nomad_model


def _load_mono_16k_tensor(path: str):
    """Load a file as a (1, time) float32 tensor: mean over channels, torchaudio resampling to 16 kHz."""
    import soundfile as sf
    import torch
    import torchaudio

    audio, sr = sf.read(path, dtype="float32", always_2d=True)
    wave = torch.from_numpy(audio.mean(axis=1))[None]
    if sr != 16000:
        wave = torchaudio.functional.resample(wave, sr, 16000)
    return wave


@lru_cache(maxsize=None)
def _nomad_embedding(path: str) -> np.ndarray:
    """NOMAD embedding of one file, cached since each reference is shared by many conditions.

    As in nomad_audio: mean over channels, resampled to 16 kHz with torchaudio, no trimming,
    wav2vec 2.0 output averaged over time, ReLU + linear layer, L2-normalized.
    """
    import torch

    ssl, embedding = _get_nomad_model()
    wave = _load_mono_16k_tensor(path)
    with torch.no_grad():
        features = ssl(wave, mask=False, features_only=True)["x"].mean(dim=1)
        emb = torch.nn.functional.normalize(embedding(torch.relu(features)), dim=1)
    return emb[0].numpy()


def nomad(ref_path: str, target_path: str) -> float:
    """NOMAD (Non-Matching Audio Distance), 16 kHz mono.

    NOMAD is a Euclidean distance between embeddings trained to rank speech degradation.
    The reference does not need to match the target (nomad_audio averages the distance to
    a set of clean files); here the set is just the matching reference, ref_path.
    Returns the distance, lower is better (0 is best).
    """
    return float(np.linalg.norm(_nomad_embedding(target_path) - _nomad_embedding(ref_path)))


# ---------------------------------------------------------------------------
# squim_stoi, squim_pesq, squim_si_sdr, squim_mos (TorchAudio-SQUIM)
# ---------------------------------------------------------------------------

# TorchAudio-SQUIM (Kumar et al., ICASSP 2023), the pretrained models of torchaudio.pipelines:
#   SQUIM_OBJECTIVE  — no-reference estimates of STOI, wideband PESQ and SI-SDR (DNS 2020).
#   SQUIM_SUBJECTIVE — MOS given a non-matching clean reference (BVCC + DAPS).
# We build the models as the pipelines' get_model() does, but pass a pinned SHA-256 to
# torchaudio's downloader, which get_model() doesn't, so a changed upstream file is rejected.
SQUIM_MODEL_SHA256 = {
    "squim_objective_dns2020.pth": "2c54586fea83fb5eb5394d710038ee89f55cab7011a5bf730bebed4c8777e828",
    "squim_subjective_bvcc_daps.pth": "dd36e1e4a5e3b36a5e7c32c936097b57b3221663a0529704171a3bb792699718",
}

_squim_models = {}

def _get_squim_model(name: str):
    """Lazy-load a SQUIM model ("objective" or "subjective") with hash-checked weights."""
    if name not in _squim_models:
        import torch
        import torchaudio
        from torchaudio.models import squim_objective_base, squim_subjective_base

        file = {"objective": "squim_objective_dns2020.pth",
                "subjective": "squim_subjective_bvcc_daps.pth"}[name]
        model = {"objective": squim_objective_base, "subjective": squim_subjective_base}[name]()
        path = torchaudio.utils._download_asset(f"models/{file}", hash=SQUIM_MODEL_SHA256[file])
        model.load_state_dict(torch.load(path, weights_only=True))
        _squim_models[name] = model.eval()
    return _squim_models[name]


@lru_cache(maxsize=None)
def _squim_objective(target_path: str) -> tuple[float, float, float]:
    """SQUIM objective (STOI, PESQ, SI-SDR) estimates, cached so the three metrics share one pass."""
    import torch

    with torch.no_grad():
        scores = _get_squim_model("objective")(_load_mono_16k_tensor(target_path))
    return tuple(float(s[0]) for s in scores)


def squim_stoi(ref_path: str, target_path: str) -> float:
    """TorchAudio-SQUIM no-reference STOI estimate (0-1, higher is better), 16 kHz mono.

    Note: This metric ignores ref_path and only evaluates target_path quality.
    """
    return _squim_objective(target_path)[0]


def squim_pesq(ref_path: str, target_path: str) -> float:
    """TorchAudio-SQUIM no-reference wideband PESQ estimate (1-4.5, higher is better), 16 kHz mono.

    Note: This metric ignores ref_path and only evaluates target_path quality.
    """
    return _squim_objective(target_path)[1]


def squim_si_sdr(ref_path: str, target_path: str) -> float:
    """TorchAudio-SQUIM no-reference SI-SDR estimate (dB, higher is better), 16 kHz mono.

    Note: This metric ignores ref_path and only evaluates target_path quality.
    """
    return _squim_objective(target_path)[2]


def squim_mos(ref_path: str, target_path: str) -> float:
    """TorchAudio-SQUIM subjective MOS (1-5, higher is better), 16 kHz mono.

    The clean reference does not need to match the target; here it is the matching ref_path,
    as for NOMAD. Returns the predicted MOS.
    """
    import torch

    with torch.no_grad():
        mos = _get_squim_model("subjective")(_load_mono_16k_tensor(target_path),
                                             _load_mono_16k_tensor(ref_path))
    return float(mos[0])


# ---------------------------------------------------------------------------
# urgent_mos, urgent_cmos
# ---------------------------------------------------------------------------

# URGENT-MOS (VoiceMOS Challenge 2026 track 1 baseline, arXiv:2601.18438), default checkpoint.
# The checkpoints were retrained after an encoder bug fix and re-uploaded on 2026-06-24;
# we pin that upload (and install the package at the matching code commit 79fb392).
URGENT_MOS_MODEL_REPO = "urgent-challenge/urgent-mos-f1c1m5dcorpus"
URGENT_MOS_MODEL_REVISION = "3b7037122bdec18bcc83b48266d71e29e8e63ca0"  # 2026-06-24

_urgent_mos_model = None

def _get_urgent_mos_model():
    """Lazy-load the URGENT-MOS model from the pinned checkpoint."""
    global _urgent_mos_model
    if _urgent_mos_model is None:
        import os
        import torch
        from huggingface_hub import hf_hub_download
        from urgent_mos import load_model_from_checkpoint

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            # infer() runs through accelerate, which would otherwise pick Apple's MPS device,
            # where the model's transformer layers fail (an operator is not implemented).
            os.environ["ACCELERATE_USE_CPU"] = "true"
        checkpoint = hf_hub_download(URGENT_MOS_MODEL_REPO, "model.pt", revision=URGENT_MOS_MODEL_REVISION)
        _urgent_mos_model = load_model_from_checkpoint(checkpoint, device).eval()
    return _urgent_mos_model


def urgent_mos(ref_path: str, target_path: str) -> float:
    """URGENT-MOS absolute speech quality MOS (1-5, higher is better), 16 kHz mono.

    Note: This metric ignores ref_path and only evaluates target_path quality.
    The package downmixes to mono and resamples to 16 kHz itself. Clamped to 1-5,
    as in the official inference script.
    """
    from urgent_mos import infer

    model = _get_urgent_mos_model()
    with contextlib.redirect_stderr(io.StringIO()):  # infer() shows progress bars per call
        score = infer(model, [target_path], num_workers=0)[0]["mos_overall"]
    return float(np.clip(score, 1, 5))


def urgent_cmos(ref_path: str, target_path: str) -> float:
    """URGENT-MOS comparative MOS of the target against its reference (-3 to +3), 16 kHz mono.

    Positive means the target is preferred over the reference, so higher is better.
    Clamped to -3..+3, as in the official inference script.
    """
    from urgent_mos import infer_pairs

    model = _get_urgent_mos_model()
    with contextlib.redirect_stderr(io.StringIO()):  # infer_pairs() shows progress bars per call
        score = infer_pairs(model, [(target_path, ref_path)], num_workers=0)[0]["mos_overall"]
    return float(np.clip(score, -3, 3))


# ---------------------------------------------------------------------------
# itu_t_p566
# ---------------------------------------------------------------------------

# ITU-T Rec. P.566 (single-ended, multi-dimensional speech quality; formerly P.SAMD / SQ-AST,
# Wardah et al., Interspeech 2025), overall quality ("mos") only. Reimplements the inference of
# P566.py from https://github.com/WafaaWardah/psamd (commit 5bbab81): that script cannot be
# imported without its optional VAD wrapper (webrtcvad), which selects speech segments in
# long streams and is not used here. Reproduces the reference scores in the repository's
# README for its two sample files (samples/): MOS 4.32 for c00007_P501_C_english_m2_FB_48k.wav
# and 4.43 for c00001_P501_C_english_f1_FB_48k.wav.
P566_MOS_WEIGHTS_URL = "https://tubcloud.tu-berlin.de/s/K9owXP3Fnj4pnJg/download?path=%2F&files=mos.pth"
P566_MOS_WEIGHTS_SHA256 = "42e7640b71c5efb2b665cddef278b1b2ebdbe68e82993dc0aabd9984740f8207"
P566_BACKBONE_REPO = "MIT/ast-finetuned-audioset-10-10-0.4593"
P566_BACKBONE_REVISION = "f826b80d28226b62986cc218e5cec390b1096902"  # 2023-09-06
P566_SR = 48000
P566_FEATURE_MEAN, P566_FEATURE_STD = -10.25446422, 4.205750774  # as in P566.py

_p566_model = None

def _get_p566_model():
    """Lazy-load the AST backbone, the P.566 "mos" weights and the feature extractor."""
    global _p566_model
    if _p566_model is None:
        import torch
        from transformers import ASTFeatureExtractor, ASTModel, logging as hf_logging

        hf_logging.set_verbosity_error()
        path = Path(torch.hub.get_dir()) / "checkpoints" / "p566_mos.pth"
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            torch.hub.download_url_to_file(P566_MOS_WEIGHTS_URL, str(path), hash_prefix=P566_MOS_WEIGHTS_SHA256)
        model = torch.nn.ModuleDict({  # same parameter names as P566.py's ASTXL
            "ast": ASTModel.from_pretrained(P566_BACKBONE_REPO, revision=P566_BACKBONE_REVISION),
            "fc": torch.nn.Sequential(torch.nn.Linear(768, 1), torch.nn.Sigmoid()),
        })
        model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        extractor = ASTFeatureExtractor.from_pretrained(P566_BACKBONE_REPO, revision=P566_BACKBONE_REVISION)
        extractor.sampling_rate, extractor.max_length, extractor.num_mel_bins = P566_SR, 1024, 128
        extractor.mean, extractor.std = P566_FEATURE_MEAN, P566_FEATURE_STD
        _p566_model = (model.eval(), extractor)
    return _p566_model


def itu_t_p566(ref_path: str, target_path: str) -> float:
    """ITU-T P.566 overall speech quality (MOS 1-5, higher is better), no reference, 48 kHz mono.

    Note: This metric ignores ref_path and only evaluates target_path quality.
    As in P566.py: mean over channels, resampled to 48 kHz; the feature extractor uses
    1024 frames (10.24 s), so longer files are scored on their first 10.24 s.
    """
    import soundfile as sf
    import torch
    import torchaudio

    model, extractor = _get_p566_model()
    audio, sr = sf.read(target_path, dtype="float32", always_2d=True)
    wave = torch.from_numpy(audio.mean(axis=1))
    if sr != P566_SR:
        wave = torchaudio.functional.resample(wave, sr, P566_SR)
    features = extractor(wave.numpy(), sampling_rate=P566_SR, return_tensors="pt")["input_values"]
    with torch.no_grad():
        score = model["fc"](model["ast"](features).pooler_output).squeeze()
    # The sigmoid head outputs 0-1 (MOS rescaled for training); map back to MOS 1-5 as P566.py does.
    return float(score) * 4 + 1


# ---------------------------------------------------------------------------
# dnsmos_p835_ovrl
# ---------------------------------------------------------------------------

# DNSMOS P.835 (Reddy et al., ICASSP 2022) via torchmetrics, not personalized.
# torchmetrics downloads the ONNX models from the master branch of microsoft/DNS-Challenge
# when they are missing. We place them in its model folder first, from a fixed commit and
# checked against SHA-256, so the scores cannot change silently.
DNSMOS_MODEL_COMMIT = "591184a9fcb2cbdec02520fed81a32bbbf9d73ff"  # microsoft/DNS-Challenge, 2024-03-29
DNSMOS_MODEL_SHA256 = {
    "DNSMOS/model_v8.onnx": "9246480c58567bc6affd4200938e77eef49468c8bc7ed3776d109c07456f6e91",
    "DNSMOS/sig_bak_ovr.onnx": "269fbebdb513aa23cddfbb593542ecc540284a91849ac50516870e1ac78f6edd",
}


@lru_cache(maxsize=None)
def _prepare_dnsmos_models() -> None:
    """Download the pinned DNSMOS models once, or check the ones already in place."""
    import hashlib
    import torch
    from torchmetrics.functional.audio.dnsmos import DNSMOS_DIR

    for file, sha256 in DNSMOS_MODEL_SHA256.items():
        path = Path(DNSMOS_DIR).expanduser() / file
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            url = (f"https://raw.githubusercontent.com/microsoft/DNS-Challenge/"
                   f"{DNSMOS_MODEL_COMMIT}/DNSMOS/{file}")
            torch.hub.download_url_to_file(url, str(path), hash_prefix=sha256)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
            raise RuntimeError(f"{path} does not match the pinned DNSMOS model; delete it to re-download.")


def dnsmos_p835_ovrl(ref_path: str, target_path: str) -> float:
    """DNSMOS P.835 overall quality (OVRL, MOS 1-5, higher is better), no reference, mono downmix.

    Note: This metric ignores ref_path and only evaluates target_path quality.
    torchmetrics resamples to 16 kHz and averages 9 s windows taken every 1 s.
    """
    import torch
    from torchmetrics.functional.audio.dnsmos import deep_noise_suppression_mean_opinion_score

    _prepare_dnsmos_models()
    audio, sr = librosa.load(target_path, sr=None, mono=True)
    scores = deep_noise_suppression_mean_opinion_score(torch.from_numpy(audio), sr, personalized=False)
    return float(scores[3])  # [p808_mos, mos_sig, mos_bak, mos_ovr]


# ---------------------------------------------------------------------------
# hasqiv2, haspiv2, haaqi (Clarity / Cadenza challenge implementations, pyclarity)
# ---------------------------------------------------------------------------

# Kates' hearing-aid indices, computed for a normal-hearing listener (0 dB HL audiogram).
# As in the Cadenza recipes, each channel is scored separately and the ear scores are
# averaged, and level1 (dB SPL for RMS = 1) presents the reference at 65 dB SPL.
# Unlike the recipes, the level is set from the RMS of the whole reference (both channels),
# so the level difference between the channels is kept.
# equalisation=2 (HASQI, HAAQI) skips the NAL-R step: with 0 dB HL it is a pure delay.
CLARITY_PRESENTATION_LEVEL_DB_SPL = 65.0

def _clarity_index(ref_path: str, target_path: str, index: str) -> float:
    """Mean over channels of a Clarity index ("hasqi", "haspi" or "haaqi"), 0 dB HL audiogram."""
    import soundfile as sf
    from clarity.evaluator.haaqi import haaqi_v1
    from clarity.evaluator.haspi import haspi_v2
    from clarity.evaluator.hasqi import hasqi_v2
    from clarity.utils.audiogram import Audiogram

    ref, ref_sr = sf.read(ref_path, always_2d=True)
    deg, deg_sr = sf.read(target_path, always_2d=True)
    audiogram = Audiogram(levels=np.zeros(6), frequencies=np.array([250, 500, 1000, 2000, 4000, 6000]))
    level1 = CLARITY_PRESENTATION_LEVEL_DB_SPL - 20 * np.log10(np.sqrt(np.mean(ref ** 2)))

    scores = []
    for channel in range(ref.shape[1]):
        args = (ref[:, channel], ref_sr, deg[:, channel], deg_sr, audiogram)
        if index == "hasqi":
            score = hasqi_v2(*args, equalisation=2, level1=level1)[0]
        elif index == "haspi":
            score = haspi_v2(*args, level1=level1)[0]
        else:
            score = haaqi_v1(*args, equalisation=2, level1=level1)[0]
        scores.append(score)
    return float(np.mean(scores))


def hasqiv2(ref_path: str, target_path: str) -> float:
    """HASQI v2 speech quality index (0-1, higher is better), normal hearing, mean over channels."""
    return _clarity_index(ref_path, target_path, "hasqi")


def haspiv2(ref_path: str, target_path: str) -> float:
    """HASPI v2 speech intelligibility index (0-1, higher is better), normal hearing, mean over channels."""
    return _clarity_index(ref_path, target_path, "haspi")


def haaqi(ref_path: str, target_path: str) -> float:
    """HAAQI v1 music quality index (0-1, higher is better), normal hearing, mean over channels."""
    return _clarity_index(ref_path, target_path, "haaqi")


# ---------------------------------------------------------------------------
# smaq
# ---------------------------------------------------------------------------

# SMAQ (Wu, Williams & Wolcott, EUSIPCO 2021): 4 features (CepCorr, NMR, PSMt, NSIM) feed a
# small dense network trained to mimic HAAQI, PEAQ, PEMO-Q and ViSQOLAudio.
# Reimplements smaq_cli's SmaqPredictor without TensorFlow (and its Python 3.7 requirement):
# the network is evaluated in numpy from the .h5 weights. Reproduces the README example to
# within 0.005 (3.5722 vs 3.5673); the gap comes from resampy 0.4 vs the pinned 0.2.2 in PSMt.
SMAQ_LAYERS = ["dense_105", "dense_106", "dense_107", "dense_108", "dense_109"]

_smaq_model = None

def _get_smaq_model():
    """Lazy-load SMAQ's feature extractor module, feature scaler and network weights."""
    global _smaq_model
    if _smaq_model is None:
        import sys
        import h5py
        import joblib

        code_path = Path(__file__).parent / "mtl_audio_qual" / "code" / "smaq_cli"
        if str(code_path) not in sys.path:
            sys.path.insert(0, str(code_path))
        import feature_extractor

        with h5py.File(code_path / "data" / "smaq_mtl_model.h5") as f:
            weights = [(f["model_weights"][n][n]["kernel:0"][()], f["model_weights"][n][n]["bias:0"][()])
                       for n in SMAQ_LAYERS]
        scaler = joblib.load(code_path / "data" / "minmax_scaler.save")
        _smaq_model = (feature_extractor, scaler, weights)
    return _smaq_model


def smaq(ref_path: str, target_path: str) -> float:
    """SMAQ score (MOS 1-5, higher is better), 48 kHz mono.

    As smaq_cli: both signals are loaded at 48 kHz mono and truncated to the shorter one;
    the final score is the geometric mean of the 4 quality outputs mapped to 1-5.
    The features are computed one after the other (smaq_cli starts a process pool per file).
    Requires: git clone https://github.com/cwu307/mtl_audio_qual.git
    """
    from scipy.stats import gmean

    fe, scaler, weights = _get_smaq_model()
    duration = min(librosa.get_duration(path=target_path), librosa.get_duration(path=ref_path))
    tar, _ = librosa.load(target_path, sr=48000, mono=True, duration=duration)
    ref, _ = librosa.load(ref_path, sr=48000, mono=True, duration=duration)
    features = [extractor(tar, ref, 48000).extract_features() for extractor in (
        fe.CepcorrFeatureExtractor, fe.NmrFeatureExtractor, fe.PsmtFeatureExtractor, fe.NsimFeatureExtractor)]

    x = scaler.transform(np.asarray(features, dtype=float)[None])
    for i, (kernel, bias) in enumerate(weights):
        x = x @ kernel + bias
        x = np.maximum(x, 0) if i < len(weights) - 1 else 1 / (1 + np.exp(-x))  # ReLU..., sigmoid
    return float(min(gmean(x[0, :4]) * 4 + 1, 5))


# ---------------------------------------------------------------------------
# binaqual
# ---------------------------------------------------------------------------

def binaqual(ref_path: str, target_path: str) -> float:
    """BINAQUAL: Full-Reference Objective Localization Similarity Metric for Binaural Audio.
    
    Measures localization similarity between reference and degraded binaural audio signals.
    Returns Localization Similarity (LS) score between 0 and 1, where higher is better.
    
    Reference: Shariat Panah, D., et al. (JAES 2026). BINAQUAL: A Full-Reference Objective 
    Localization Similarity Metric for Binaural Audio. arXiv:2505.11915
    
    Requires: git clone https://github.com/QxLabIreland/Binaqual.git
    """
    import sys
    import soundfile as sf
    from tempfile import TemporaryDirectory
    
    # Add Binaqual to path
    binaqual_path = Path(__file__).parent / "Binaqual"
    if str(binaqual_path) not in sys.path:
        sys.path.insert(0, str(binaqual_path))
    
    # Import after adding to path
    from binaqual import calculate_binaqual
    
    sample_rate = 48000
    signals = []
    needs_temp_files = False
    for path in (ref_path, target_path):
        signal, source_rate = librosa.load(path, sr=None, mono=False)
        if source_rate != sample_rate:
            signal = librosa.resample(signal, orig_sr=source_rate, target_sr=sample_rate)
            needs_temp_files = True
        if signal.ndim == 1:
            signal = np.stack([signal, signal])
            needs_temp_files = True
        signals.append(signal)

    # binaqual throws an error if the input length is some samples more than a multiple of 12 seconds
    # https://github.com/QxLabIreland/Binaqual/issues/2
    ref_samples, target_samples = (signal.shape[1] for signal in signals)
    sample_count = min(ref_samples, target_samples)
    remainder = ref_samples % (12 * sample_rate)
    padding = sample_rate // 8000 * 128 if 1 <= remainder <= 10 else 0
    if padding:
        print(f"Warning: Prepending {padding} samples to avoid BINAQUAL's "
              f"12-second boundary error: {target_path}")
    needs_temp_files = needs_temp_files or ref_samples != target_samples or padding > 0

    with TemporaryDirectory() as directory:
        paths = [Path(ref_path), Path(target_path)]
        if needs_temp_files:
            paths = [Path(directory) / name for name in ("reference.wav", "target.wav")]
            for path, signal in zip(paths, signals):
                signal = signal[:, :sample_count]
                if padding:
                    signal = np.pad(signal, ((0, 0), (padding, 0)))
                sf.write(path, signal.T, sample_rate)
        _, score = calculate_binaqual(
            ref_path=paths[0],
            test_path=paths[1],
            intensity_threshold=-180,
            elc=0,
            ignore_freq_bands=0
        )
    return float(score)


