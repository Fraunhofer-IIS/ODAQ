# ODAQ Benchmark

This folder contains the code to reproduce the benchmark and extend it with new
metrics or subsets. The result is an interactive page showing how well objective audio quality metrics correlate with the ODAQ listening test scores. It's available here:

<div align="center">

### [📊 fraunhofer-iis.github.io/ODAQ](https://fraunhofer-iis.github.io/ODAQ/)

</div>

## Setup and Usage

### 1. Download the ODAQ Collection

First, download the ODAQ collection from [Zenodo](https://doi.org/10.5281/zenodo.23425817)
and unpack it, so that you have the `odaq-collection` directory on your machine.

### 2. Configure the Collection Path

Edit [config.py](config.py) and set the `COLLECTION_ROOT` variable to point to your `odaq-collection` folder:

```python
COLLECTION_ROOT = Path("./odaq-collection")  # Update this path
```

A relative path is resolved against the folder you run `evaluate.py` from, so run the
commands below from this `benchmark/` folder or use an absolute path.

You can change the list of metrics under test (see [metrics_registry.py](metrics_registry.py) for the full list of available metrics):

```python
METRICS = ["PESQc2", "SI-SDR"]  # or "ALL"
```

Metric names are case-sensitive! Set `METRICS = "ALL"` to run every registered metric.

`METRICS` and `ACTIVE_SUBSETS` select the evaluation workload. The website data
written by `evaluate.py` to `docs/analysis.json` contains the correlation analysis for every filter combination (anchors, aggregation method, ...). Hidden reference conditions are always excluded.


### 3. Set Up the Environment and the Metrics

Create a conda environment using Python 3.11 and install the shared dependencies:

```bash
conda create -n odaq python=3.11
conda activate odaq
pip install -r requirements.txt
```

#### How metrics are installed

Every metric is independent. `METRICS` in `config.py` selects the metrics to compute;
all other metrics with cached scores are loaded from their caches, so a run only adds
to the existing results (see step 4). You therefore only need to install the metrics
you want to compute. Each metric imports its packages only when it is computed, so a
missing tool does not affect the others.

`requirements.txt` installs most metrics. The others need
[an extra manual step](#metrics-that-need-an-extra-manual-step): cloning a repository,
installing a package without its dependencies, or building a native tool.

This keeps a single environment and simple code: each metric calls its upstream
implementation, pinned to a fixed version, instead of copies of that code, separate
environments or subprocess wrappers. NOMAD and SMAQ are the exceptions: their small
networks are rebuilt in this repository because their packages require outdated
frameworks (fairseq, TensorFlow on Python 3.7).

#### Metrics that need an extra manual step

Clone these repositories into this `benchmark/` folder (the metrics load their code from there):

```bash
git clone https://github.com/soham97/PAM.git            # PAM
git clone https://github.com/QxLabIreland/Binaqual.git  # BINAQUAL
git clone https://github.com/cwu307/mtl_audio_qual.git  # SMAQ 
```

Install these packages without their dependencies, because their own version pins
conflict with the shared environment (e.g. `protobuf<=3.20.1` for SHEET, `numpy>=2` for
pyclarity); the dependencies they actually need are in `requirements.txt`:

```bash
pip install --no-deps sheet-sqa==0.2.5                    # SHEET
pip install --no-deps pyclarity==0.9.0                    # HASQIv2, HASPIv2, HAAQI
pip install --no-deps "utmosv2 @ git+https://github.com/sarulab-speech/UTMOSv2.git@v1.3.0"
pip install --no-deps "urgent_mos @ git+https://github.com/vvwangvv/URGENT-MOS.git@79fb39277ba8989d1dea28bf109a2d1631530fbe"
# CD, fwSNRseg (pysepm imports SRMRpy, which imports Gammatone)
pip install --no-deps "pysepm @ git+https://github.com/schmiph2/pysepm.git@7ef88aff2c56201a2d0470aaeb58e77e47a914d2" \
  "SRMRpy @ git+https://github.com/jfsantos/SRMRpy.git@fee009779cef96bed34db3a7e31d10f3ad1ea133" \
  "Gammatone @ git+https://github.com/detly/gammatone.git@0626328ef7c31d3b33214db2fdcd52e8601eb4c5"
```

Build the native tools:

- **ViSQOLAudio-v3**: build and install the official [ViSQOL Python API](https://github.com/google/visqol#python-api-usage)
  following its instructions.
- **PEAQ-ODG and NMR**: compile `PQevalAudio` from Peter Kabal's
  [AFsp-v8r2](https://www-mmsp.ece.mcgill.ca/Documents/Downloads/AFsp/index.html) and set
  `PQEVALAUDIO_PATH` in `config.py` to the executable.


### 4. Evaluate

Compute metric scores (reusing caches), correlations, and website data:

```bash
python evaluate.py
```

This maintains metric score caches in `scores/<metric>.csv` and exports compact
website JSON directly to `docs/`.

`METRICS` in `config.py` selects the metrics to compute. Every other registered
metric with a cache is loaded from it and included in the results, so adding a
new metric only requires `METRICS = ["<new metric>"]`. A cache missing scores
for some pairs (e.g., after adding a subset) is skipped with a warning; add that
metric to `METRICS` to complete it.

Only the score caches are inputs: each run recomputes all correlations from them and
rewrites the json files in `docs/` from scratch. Deleting `docs/` therefore
loses nothing, while deleting `scores/<metric>.csv` means recomputing that metric.
Old detail files are not removed: if a metric leaves the results, delete its
`docs/data/<metric>.json` by hand.

To build or update only the static HTML page:

```bash
python build_github_page.py
```

The HTML builder writes only `docs/index.html`. It does not load metric caches,
compute correlations or rho-perfect, or modify the website JSON. Run evaluation
when scores, listening-test data, or configured metrics/subsets change; run the
HTML builder when the page layout changes. For a complete site, run both commands.

The "About the subsets" table on the page is built from `subset_references.csv`, which
comes with the ODAQ collection (downloaded separately, see step 1) and is read from
`COLLECTION_ROOT`.


## How Results Are Reported

### Score direction

All scores are higher-is-better. The functions in [metrics.py](metrics.py) return each
metric's own scale; metrics where lower is better (distances, distortion measures) are
listed in `NEGATED_METRICS` in [metrics_registry.py](metrics_registry.py), and
`evaluate.py` negates their scores before caching them (`score_pair`). Cached scores
and correlations therefore use the negated values. On the website these metrics
are shown as `−Name`, e.g. `−NMR`.

### Stereo input

The ODAQ stimuli are stereo. Metrics that accept stereo input get it as is, and whatever they
do with it (e.g. a downmix in their own file loader) is part of their design. Metrics that
take mono input only are run on each channel separately, and the channel scores are averaged.

### Correlation coefficients

Objective scores are correlated with the mean listener scores within each subset and
processing method (e.g. LP, TM or DE in 2024-icassp), with three coefficients:

- **Pearson** r: linear relationship.
- **Spearman** ρ: rank order.
- **Kendall sin(πτ/2)**: Kendall's τ-b, mapped to the Pearson scale with sin(πτ/2) (Greiner's relation) so that it is comparable with the other two. 

### Aggregation

- **Macro** (default): Correlations computed for each subset and processing method are averaged in Fisher’s z-space, giving equal weight to every subset–method combination. This approach aims to minimize the influence of differences in how listeners use the rating scale across tests, subsets, or processing methods. See also: M. Torcoli, T. Kastner, J. Herre, "Objective Measures of Perceptual Audio Quality Reviewed: An Evaluation of Their Application Domain Dependence," IEEE/ACM Trans. Audio, Speech, Lang. Process., vol. 29, pp. 1530–1541, 2021 ([doi:10.1109/TASLP.2021.3069302](https://doi.org/10.1109/TASLP.2021.3069302)). The whiskers on the website show the mean ± one standard deviation of the per-subset, per-method z-values, transformed back. 
- **Micro**: one correlation over all stimuli pooled together, which mixes such
  differences between listening tests into the correlation. The whiskers on the website show approximate 95% Fisher-z intervals.

## Adding a Metric

1. Implement `mymetric(ref_path: str, target_path: str) -> float` in [metrics.py](metrics.py),
   returning the metric's own scale. No-reference metrics simply ignore `ref_path`.
2. Register it in `METRICS_REGISTRY`, add its source URL to `METRIC_SOURCES` and its
   reference type (`full-reference`, `no-reference` or `non-matching-reference`) to
   `METRIC_REFERENCE_TYPES` in [metrics_registry.py](metrics_registry.py).
3. If lower is better, add it to `NEGATED_METRICS`.
4. Add it to `METRICS` in [config.py](config.py) and run `python evaluate.py`.

**Precomputed scores.** Implementing the metric as above is the preferred way: only then
can others reproduce its scores, and the benchmark compute them for new subsets. If that
is not possible, scores computed
elsewhere could be added without implementing the metric: write `scores/<name>.csv`
with one row per pair, in the format of the existing files (`target_wav`, `ref_wav` relative
to the collection root, `score`). The scores must already be higher-is-better, because
`NEGATED_METRICS` is only applied when scores are computed. The metric still needs step 2, with a function in `metrics.py` that raises `NotImplementedError`; do not add it to `METRICS`.


## Adding a Subset

A subset is one listening test (or a group of tests on the same stimuli):

1. Add its audio and ratings to the collection: the ratings as CSV files with one row
   per rating. Example: `2024-icassp/ODAQ_listening_test/` in the collection, with
   `ODAQ_results.csv` (columns `score`, `method`, `condition`, `process`, `item`,
   `subject`) and one folder per trial (`item`) holding `reference.wav` and one
   `<process>.wav` per condition; its loader is `ICASSP2024Loader`.
2. Write a loader in [dataloaders.py](dataloaders.py) by subclassing `ODAQSubsetLoader`:
   `subjective_csvs()` returns the ratings files, `pairs()` the (target, reference) WAV
   pairs with their item, condition and method group.
3. Register it in `LOADER_REGISTRY` in [dataloaders_registry.py](dataloaders_registry.py)
   and add its key to `ACTIVE_SUBSETS` in [config.py](config.py).
4. Add one row per item to the collection's `odaq-collection-content-analysis.csv`
   (`subset` = the registry key, `item`, `content_type`, and `spatial` = `mono` or
   `stereo`, the same for the whole subset); `evaluate.py` stops with an error otherwise.
5. Add a row to the collection's `subset_references.csv` (`subset`, `summary`,
   `reference`, optional `url`) for the "About the subsets" table on the website.
6. Set `METRICS = "ALL"` (or list the metrics to include) and run `python evaluate.py`.
7. Consider contacting the ODAQ authors to include the subset in the next release of the
   ODAQ-Collection.

## Citing

If you use this benchmark, please cite:

```bibtex
@article{wu2026odaqcollection,
  title   = {{ODAQ-Collection}: Expanding the Open Dataset of Audio Quality with a Focus on Spatial Distortions},
  author  = {Wu, Chih-Wei and Torcoli, Matteo and Halimeh, Mhd Modar and Delgado, Pablo M. and Dick, Sascha and Thompson, Christoph and Williams, Phillip A. and Habets, Emanu{\"e}l A. P.},
  journal = {arXiv preprint arXiv:2610.37959},
  url     = {https://arxiv.org/abs/2610.37959},
  year    = {2026}
}
```
