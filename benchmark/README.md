# How to benchmark a metric with ODAQ?

This subfolder presents an example pipeline for benchmarking objective quality metrics using ODAQ. The experiment was described in the following paper:
```
@inproceedings{Dick2024ODAQBSU,
author = {Dick, S. and Thompson, C. and Wu, C.-W. and Torcoli, M. and Delgado, P. M. and Williams, P. A. and Habets, E. A. P.},
year = {2024},
month = {October},
title = {Expanding and Analyzing {ODAQ} – the Open Dataset of Audio Quality},
booktitle={Audio Engineering Society Convention 157}
}
```
The script was developed and tested in Python 3.10.

## Instruction

Here are the steps to evaluate your metric using ODAQ v1 [1]:

1) Implement a wrapper function in `BringYourOwnMetric.py`. This function would take the filepaths of reference and target (i.e. system under test, sut) signals and return one objective score
2) Import your function in `ProcessAndAnalyzeODAQScores.py` and insert your function inside `call_metric()`
3) In `config.py`, make sure the `audio_folder` is set to where your `ODAQ/ODAQ_listening_test/` resides. The ODAQ package can be downloaded [here](https://doi.org/10.5281/zenodo.10405774)  
4) In `config.py`, make sure the `LT_results_folders` is set to where your data resides. Note that you could include the results from [1] and [2] by providing a list. See `config.py` for more details.
5) Make sure all the dependencies are installed (see `requirements.txt`) and run the following commands:
```
>> Python ProcessAndAnalyzeODAQScores.py
```
6) The results will be stored in the `output_dir` specified in `config.py`


## Current Results (Latest update: 2024.09)

An initial set of results was presented in [2]. Here, we present a similar table that tracks the latest results. The performance metric is the absolute Pearson's linear correlation between ground-truth subjective scores and outputs from the objective metrics. Hidden reference and anchor conditions are excluded. The aggregated score (AGG) is the mean of the per-method correlation coefficients, averaged in the Fisher’s Z-transform domain, es explained in [2], and implemented in the code in this repo.

Note that we expect this table to evolve as new approaches are introduced to the research field, and we welcome any contribution from the community. 

Please make a Pull Request to this repository with your results or reach out to any of the co-authors in ODAQ for assistance. Alternatively, you could also contribute directly to our [papers_with_code](https://paperswithcode.com/dataset/odaq-open-dataset-of-audio-quality) page, and we will keep track of the results here as best as we could. 

As ground-truth subjective scores, we pool together the results from [ODAQ v1](https://doi.org/10.5281/zenodo.10405774) and [its first expansion](https://zenodo.org/records/13377284).

| Objective Quality Metric |  DE  |  LP  |  PE  |  SH  |  TM  |  UN  | AGG (aggregated) | Contribution Date | Source/Publication/Reference where the evaluation appeared |
|:------------------------:|:----:|:----:|:----:|:----:|:----:|:----:|:----------------:|:-----------------:|:-----------------------------------------------------------:|
|        NMR [3, 7]        | 0.90 | 0.90 | 0.93 | 0.83 | 0.79 | 0.94 |       0.89       |      2024.09      |                             [2]                             | 
|       PEAQ-CSM [4]       | 0.87 | 0.97 | 0.94 | 0.86 | 0.84 | 0.72 |       0.89       |      2024.09      |                             [2]                             | 
|     2f-model [5, 7]      | 0.64 | 0.96 | 0.95 | 0.94 | 0.69 | 0.73 |       0.87       |      2024.09      |                             [2]                             |
|    PEAQ (ODG) [6, 7]     | 0.71 | 0.95 | 0.90 | 0.80 | 0.76 | 0.95 |       0.87       |      2024.09      |                             [2]                             |
|    ViSQOLAudio V3 [8]    | 0.73 | 0.89 | 0.86 | 0.61 | 0.62 | 0.78 |       0.77       |      2024.09      |                             [2]                             |
|         SMAQ [9]         | 0.51 | 0.84 | 0.75 | 0.85 | 0.56 | 0.89 |       0.77       |      2024.09      |                             [2]                             |
|      PESQ [10, 11]       | 0.79 | 0.65 | 0.79 | 0.80 | 0.55 | 0.77 |       0.74       |      2024.09      |                             Can be reproduced by the code in this repo                             |
|       SI-SDR [12]        | 0.14 | 0.72 | 0.57 | 0.53 | 0.52 | 0.00 |       0.44       |      2024.09      |                             Can be reproduced by the code in this repo                             |
|       DNSMOS [13]        | 0.35 | 0.19 | 0.65 | 0.47 | 0.22 | 0.33 |       0.38       |      2024.09      |                             [2]                             |


## Further References

```
[1] Torcoli, M., Wu, C.-W., Dick, S., Williams, P. A., Halimeh, M. M., Wolcott, W., & Habets, E. A. P. (2023). ODAQ: OPEN DATASET OF AUDIO QUALITY [Data set]. Zenodo. https://doi.org/10.5281/zenodo.10405774
[2] Dick, S., Thompson, C., Wu, C.-W., Torcoli, M., Delgado, P., Williams, P. A., & Habets, E. A. P. (2024). ODAQ v1: Additional Results from Ball State University (BSU) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.13377284
[3] Brandenburg, K. "Evaluation of Quality for Audio Encoding at Low Bit Rates," in Audio Eng. Soc. (AES) Conv. 82, 1987.
[4] Delgado, P. M. and Herre, J., “A data-Driven Cognitive Salience Model for Objective Perceptual Audio Quality Assessment,” in IEEE Int. Conf. Acoustics, Speech and Sig. Proc. (ICASSP), pp. 986–990, 2022.
[5] Kastner, T. and Herre, J., “An Efficient Model for Estimating Subjective Quality of Separated Audio Source Signals,” in IEEE Workshop on Applications of Sig. Proc. to Audio and Acoustics (WASPAA), 2019, implementation details: https://www.audiolabs-erlangen.de/resources/2019-WASPAA-SEBASS.
[6] ITU-R Rec. BS.1387-2, “Method for Objective Measurements of Perceived Audio Quality,” Int. Telecom. Union (ITU), Radiocommunication Sector, 2023.
[7] Kabal, P., “An Examination and Interpretation of ITU-R BS.1387: Perceptual Evaluation of Audio Quality,” Technical report, MMSP Lab Technical Report, McGill University, 2002, code available at http://www-mmsp.ece.mcgill.ca/Documents/Software/.
[8] Chinen, M., Lim, F. S. C., et al., “ViSQOL v3: An Open Source Production Ready Objective Speech and Audio Metric,” in Int. Conf. on Quality of Multimedia Experience (QoMEX), 2020, code available at https://github.com/google/visqol.
[9] Wu, C.-W., Williams, P. A., and Wolcott, W., “A Multitask Teacher-Student Framework for Perceptual Audio Quality Assessment,” in European Sig. Proc. Conf. (EUSIPCO), pp. 396–400, 2021.
[10] ITU-R Rec. P.862.2, “Wideband Extension to Recommendation P.862 for the Assessment of Wideband Telephone Networks and Speech Codecs,” Int. Telecom. Union (ITU), Radiocommunication Sector, 2007.
[11] Wang, M., Boeddeker, C., et al., “PESQ (Perceptual Evaluation of Speech Quality) Wrapper for Python Users,” 2022, code available at https://doi.org/10.5281/zenodo.6549559 and https://github.com/ludlows/PESQ.
[12] Le Roux, J., Wisdom, S., et al., “SDR – Half-Baked or Well Done?” in IEEE Int. Conf. Acoustics, Speech and Sig. Proc. (ICASSP), pp. 626–630, 2019, code for mono signals available at: https://github.com/sigsep/bsseval/issues/3.
[13] Reddy, C. K., Gopal, V., and Cutler, R., “DNS-MOS P.835: A Non-Intrusive Perceptual Objective Speech Quality Metric to Evaluate Noise Suppressors,” in IEEE Int. Conf. Acoustics, Speech and Sig. Proc. (ICASSP), pp. 886–890, 2022, code available at: https://github.com/microsoft/DNS-Challenge/tree/master/DNSMOS.
```






