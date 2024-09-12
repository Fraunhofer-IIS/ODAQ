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
|           NMR            | 0.90 | 0.90 | 0.93 | 0.83 | 0.79 | 0.94 |       0.89       |      2024.09      |                             [2]                             | 
|         PEAQ-CSM         | 0.87 | 0.97 | 0.94 | 0.86 | 0.84 | 0.72 |       0.89       |      2024.09      |                             [2]                             | 
|         2f-model         | 0.64 | 0.96 | 0.95 | 0.94 | 0.69 | 0.73 |       0.87       |      2024.09      |                             [2]                             |
|        PEAQ (ODG)        | 0.71 | 0.95 | 0.90 | 0.80 | 0.76 | 0.95 |       0.87       |      2024.09      |                             [2]                             |
|      ViSQOLAudio V3      | 0.73 | 0.89 | 0.86 | 0.61 | 0.62 | 0.78 |       0.77       |      2024.09      |                             [2]                             |
|           SMAQ           | 0.51 | 0.84 | 0.75 | 0.85 | 0.56 | 0.89 |       0.77       |      2024.09      |                             [2]                             |
|           PESQ           | 0.79 | 0.65 | 0.79 | 0.80 | 0.55 | 0.77 |       0.74       |      2024.09      |                             Can be reproduced by the code in this repo                             |
|          SI-SDR          | 0.14 | 0.72 | 0.57 | 0.53 | 0.52 | 0.00 |       0.44       |      2024.09      |                             Can be reproduced by the code in this repo                             |
|          DNSMOS          | 0.35 | 0.19 | 0.65 | 0.47 | 0.22 | 0.33 |       0.38       |      2024.09      |                             [2]                             |


## Further References

```
[1] Torcoli, M., Wu, C.-W., Dick, S., Williams, P. A., Halimeh, M. M., Wolcott, W., & Habets, E. A. P. (2023). ODAQ: OPEN DATASET OF AUDIO QUALITY [Data set]. Zenodo. https://doi.org/10.5281/zenodo.10405774
[2] Dick, S., Thompson, C., Wu, C.-W., Torcoli, M., Delgado, P., Williams, P. A., & Habets, E. A. P. (2024). ODAQ v1: Additional Results from Ball State University (BSU) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.13377284
```






