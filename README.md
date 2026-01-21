# ODAQ: Open Dataset of Audio Quality


## Latest News
- 2026.01: new contribution to ODAQ is available. For a complete list of contributions, see the [ODAQ-Collection](#odaq-collection) and [Community Contributions](#community-contributions) tables below.

## Introduction

ODAQ (Open Dataset of Audio Quality) is a growing collection of openly available audio datasets accompanied by corresponding subjective quality scores. The collection addresses the scarcity of such resources for research into the prediction and analysis of perceived audio quality.

All ODAQ datasets are created using the MUSHRA listening test methodology, conducted by expert listeners from international laboratories including Fraunhofer IIS (Germany), Netflix, Inc. (USA), and Ball State University (USA). The audio material consists of stereo signals sampled at 44.1 or 48 kHz, including music excerpts (solo recordings and ensemble pieces) as well as movie-like soundtracks with dialogues mixed with music and effects.

Key characteristics of ODAQ:
- **Diverse processing conditions**: Audio samples processed by various method classes designed to generate quality degradations encountered during audio coding and source separation
- **Full quality range coverage**: Quality levels for each processing method span the entire quality range
- **High-fidelity audio**: Stereo audio with 44.1 or 48 kHz sampling frequency
- **International expert listeners**: Ratings from trained listeners across multiple laboratories
- **Permissive licensing**: All content released under Creative Commons licenses
- **Open tools**: The [listening test app](https://github.com/Netflix-Skunkworks/listening-test-app) used to conduct the tests is publicly available

### ODAQ-Collection

The **ODAQ-Collection** is the unified dataset containing all official ODAQ subsets. You can download the complete collection or individual subsets from the table below:

| | Identifier | Paper | Description | Audio Samples | Processing Methods | Subjects | Download |
|:--|:----------:|:------|:------------|:-------------:|:------------------:|:--------:|:--------:|
| **Collection** | ODAQ-Collection | — | All official subsets combined | — | — | — | [Zenodo](TBD) |
| -- Subset | 2024-icassp | [ODAQ: Open Dataset of Audio Quality](https://arxiv.org/abs/2401.00197) | Initial release with 6 method classes spanning the full quality range | 240 | 6 (LP, PE, SH, TM, UN, DE) | 26 | [Zenodo](https://doi.org/10.5281/zenodo.10405774) |
| -- Subset | 2024-aes | [Expanding and Analyzing ODAQ](https://arxiv.org/abs/2504.00742) | +16 trained university listeners; benchmark analysis of objective metrics | — | — | +16 | [Zenodo](https://doi.org/10.5281/zenodo.13377284) |
| -- Subset | 2025-aes | [Investigating the impact of stereo processing](https://arxiv.org/abs/2512.14259) | LR/MS stereo processing extension; investigation of presentation context effects | 176 | 6 (QNLR, QNMS, QNmix, SHLR, SHMS, SHmix) | 16 | [Zenodo](https://doi.org/10.5281/zenodo.17162670) |

*Note: The ODAQ-Collection Zenodo link will provide all subsets as subfolders named by their identifier (e.g., `2024-icassp/`, `2024-aes/`, `2025-aes/`).*

### Community Contributions

The following are datasets derived from or extending ODAQ, contributed by external researchers:

| Identifier | Paper | Description | Audio Samples | Subjects | Download |
|:----------:|:------|:------------|:-------------:|:--------:|:--------:|
| 2025-lanzendorfer | [Evaluating Objective Speech Quality Metrics for Neural Audio Codecs](https://arxiv.org/abs/2511.19734) | Neural audio codec quality evaluation; derived from 2024-icassp speech items with two variants (speech, combined) | 99 each | 11 (speech), 17 (combined) | [Zenodo](https://doi.org/10.5281/zenodo.18184035) |


## License

All ODAQ content is released under permissive Creative Commons licenses, enabling broad use for research purposes:

- **CC BY 4.0 / CC BY 3.0 / CC BY 2.5** (Attribution): Most audio material, including content from Freesound, Blender Studio, and Fraunhofer IIS
- **CC0 1.0** (Public Domain): Selected items with no restrictions
- **CC BY-NC 4.0** (Attribution-NonCommercial): Netflix-owned content, restricted to non-commercial use

A detailed license file (`_detailed_license.csv`) is included in each Zenodo download, specifying the license for each individual audio file.


## Call for Contributions

We make this data available to the community and we welcome contributions and extensions from the community!

### How to contribute? 

There are many ways to contribute to ODAQ (and we welcome all of them!). Here, we will provide examples of two main types of contributions:

#### Type 1: Extend with additional materials:

This type of contribution extends the dataset with materials such as new audio content and/or new subjective scores. Please refer to [./extend/](./extend/) subfolder for more information. 

#### Type 2: Benchmark with the existing dataset: 

This type of contribution utilizes the dataset for benchmarking and provides the results in a reproducible manner. Please refer to [./benchmark/](./benchmark/) subfolder for more information.
