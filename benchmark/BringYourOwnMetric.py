"""
 This is an example of how to 'bring your own metric' and evaluate using ODAQ

 Please refer to
 call_metric() in ProcessAndAnalyzeODAQScores.py for more information
"""
import math
import numpy as np

from pesq import pesq
import librosa as lr


def calculate_pesq(ref_path, sut_path, target_sr=16000):
    """
    Load audio files and runs PESQ on them.
    This function performs mono downmix while loading the audio files!

    Args:
        sut_path: str, filepath of the system-under-test signal
        ref_path: str, filepath of the reference signal
        target_sr: int, sampling frequency used to compute PESQ
    
    Returns:
        pesq_value: float, P.862.2 Prediction (MOS-LQO)
    """
    ref_sr = target_sr
    ref, _ = lr.load(path=ref_path, sr=target_sr, mono=True)
    sut, _ = lr.load(path=sut_path, sr=ref_sr, mono=True)
    print("Calculating PESQ for " + sut_path + "...")
    pesq_value = pesq(ref_sr, ref, sut, 'wb')
    return pesq_value


def calculate_sisdr(sut_path, ref_path, scaling=True):
    """
    A simple function for calculating SI-SDR (adapted from https://github.com/sigsep/bsseval/issues/3)
    This function performs mono downmix while loading the audio files!

    Args:
        sut_path: str, filepath of the system-under-test signal
        ref_path: str, filepath of the reference signal
        scaling: bool, true/false to activate/deactivate scale-invariance
    
    Returns:
        SDR: float, Scale-Invariant Signal-to-Distortion Ratio (SI-SDR)
    
    """

    reference_signals, ref_sr = lr.load(path=ref_path, sr=None, mono=True)
    estimated_signal, sut_sr = lr.load(path=sut_path, sr=None, mono=True)

    if ref_sr != sut_sr:
        raise ValueError("Sampling rates of the reference and test files do not match.")

    if len(reference_signals) != len(estimated_signal):
        raise ValueError("The reference and test files must have the same length.")

    Rss = np.dot(reference_signals.transpose(), reference_signals)
    this_s = reference_signals[:]

    if scaling:
        # get the scaling factor for clean sources
        a = np.dot(this_s, estimated_signal) / Rss
    else:
        a = 1

    e_true = a * this_s
    e_res = estimated_signal - e_true

    Sss = (e_true ** 2).sum()
    Snn = (e_res ** 2).sum()

    SDR = 10 * math.log10(Sss / Snn)
    return SDR