#!/usr/bin/env python3
"""Score metrics, compute correlations, and export compact website JSON."""

import copy
import functools
import hashlib
import re
import sys
import warnings
from collections import Counter
from collections.abc import Generator
from contextlib import contextmanager
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import soundfile as sf
from scipy import stats

import config
from dataloaders import ANCHOR_CONDITIONS, ODAQSubsetLoader, REF_CONDITIONS
from dataloaders_registry import LOADER_REGISTRY
from metrics_registry import METRICS_REGISTRY, NEGATED_METRICS

from rho_perfect import calculate_rho_perfect_from_ratings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEP = "=" * 68  # just a visual separator


# ---------------------------------------------------------------------------
# Subjective scores
# ---------------------------------------------------------------------------

def _load_mean_subjective_scores(loaders: list[ODAQSubsetLoader], root: Path) -> pd.DataFrame:
    """Load and pool subjective scores for each subset.

    Args:
        loaders: Active subset loaders.
        root: Collection root containing the score files.

    Returns:
        Mean subjective scores grouped by subset, item, and condition.
    """
    frames = []
    for loader in loaders:
        for rel in loader.subjective_csvs():
            frames.append(pd.read_csv(root / rel).assign(subset=loader.name))
    df = pd.concat(frames, ignore_index=True)
    # reference conditions are excluded 
    df = df[~df["condition"].isin(REF_CONDITIONS)]
    return df.groupby(["subset", "item", "condition"])["score"].mean().reset_index(name="mean_score")


def _load_listener_ratings(
    loaders: list[ODAQSubsetLoader],
    root: Path,
    content_type_lookup: dict[tuple[str, str], str],
) -> pd.DataFrame:
    """Load individual listener ratings keyed by subset and method group.

    Args:
        loaders: Active subset loaders.
        root: Collection root containing the rating files.
        content_type_lookup: Catalogue map keyed by subset and unprefixed item ID.

    Returns:
        Individual ratings with subset, method group, and item metadata.
    """
    frames = []
    for loader in loaders:
        for rel in loader.subjective_csvs():
            df = pd.read_csv(root / rel)
            if "method" in df:
                method_group = df["method"].astype(str)
            else:
                method_group = df["dataset_type"].astype(str)

            content_types = [
                _content_type_for(loader.name, group, item, content_type_lookup)
                for group, item in zip(method_group, df["item"].astype(str))
            ]
            df = df.assign(
                subset=loader.name,
                method_group=method_group,
                content_type=content_types,
            )
            df = df[~df["condition"].isin(REF_CONDITIONS)]
            df = df.dropna(subset=["item", "condition", "score", "method_group"])
            # Keep listener ratings separate by target item, condition, and loader.
            df["filename"] = (
                df["subset"] + "::" + df["method_group"] + "::" +
                df["item"].astype(str) + "::" + df["condition"].astype(str)
            )
            df["is_anchor"] = df["condition"].isin(ANCHOR_CONDITIONS)
            frames.append(df[["subset", "method_group", "item", "content_type",
                              "filename", "condition", "is_anchor", "score"]]
                          .rename(columns={"score": "rating"}))
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def _preflight_check(pairs: list[dict[str, Any]]) -> bool:
    """Verify all pair WAV paths exist and are readable."""
    errors = []
    checked = set()
    for pair in pairs:
        for key in ("target_wav", "ref_wav"):
            path = pair[key]
            if path in checked:
                continue
            checked.add(path)
            if not Path(path).exists():
                errors.append(f"not found: {path}")
            else:
                try:
                    sf.info(path)
                except Exception as error:
                    errors.append(f"unreadable: {path} ({error})")
    if errors:
        print(f"ERROR: {len(errors)} WAV files failed preflight:")
        for error in errors[:20]:
            print(f"  {error}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        return False
    print(f"  OK — {len(pairs)} pairs, {len(checked)} unique WAV files verified")
    return True


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_path(scores_dir: Path, metric_name: str) -> Path:
    """Return the CSV file holding a metric's cached objective scores."""
    return scores_dir / f"{metric_name}.csv"


def _load_cache(
    path: Path,
    collection: Path,
    score_clip: tuple[float, float] | None = None,
) -> dict[tuple[str, str], float]:
    """Load cached objective scores.

    Args:
        path: CSV file containing target/reference paths and scores.
        collection: Collection root the stored relative paths are resolved against.
        score_clip: Optional inclusive bounds applied when loading cached scores.

    Returns:
        Scores keyed by absolute target and reference WAV paths.
    """
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    scores = {(str(collection / r["target_wav"]), str(collection / r["ref_wav"])): float(r["score"])
              for _, r in df.iterrows()}
    if score_clip is not None:
        scores = {key: float(np.clip(score, *score_clip)) for key, score in scores.items()}
    return scores


def _save_cache(cache: dict[tuple[str, str], float], path: Path, collection: Path) -> None:
    """Persist objective scores for reuse in later runs.

    Args:
        cache: Scores keyed by absolute target and reference WAV paths.
        path: Destination CSV file.
        collection: Collection root; paths are stored relative to it, so caches
            can be shared across machines.

    Returns:
        None.
    """
    def relative(wav: str) -> str:
        return Path(wav).relative_to(collection).as_posix()

    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"target_wav": relative(k[0]), "ref_wav": relative(k[1]), "score": v}
            for k, v in cache.items()]
    pd.DataFrame(rows).to_csv(path, index=False)

# ---------------------------------------------------------------------------
# Content type
# ---------------------------------------------------------------------------

def _load_content_type_lookup(collection: Path) -> dict[tuple[str, str], str]:
    """Load the collection's dynamic content-type map keyed by subset and item."""
    path = collection / "odaq-collection-content-analysis.csv"
    metadata = pd.read_csv(path, dtype=str)
    required = {"subset", "item", "content_type"}
    missing = required.difference(metadata.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")
    if metadata[list(required)].isna().any().any():
        raise ValueError(f"{path} contains empty subset, item, or content_type values")
    duplicates = metadata.duplicated(["subset", "item"], keep=False)
    if duplicates.any():
        examples = metadata.loc[duplicates, ["subset", "item"]].head().to_dict("records")
        raise ValueError(f"{path} contains duplicate subset/item entries: {examples}")
    return {
        (row["subset"], row["item"]): row["content_type"]
        for row in metadata.to_dict("records")
    }


def _load_spatial_status(collection: Path) -> dict[str, str]:
    """Load the per-subset spatial focus ("stereo"/"mono") from the content analysis."""
    path = collection / "odaq-collection-content-analysis.csv"
    metadata = pd.read_csv(path, dtype=str)
    if "spatial" not in metadata.columns or metadata["spatial"].isna().any():
        raise ValueError(f"{path} is missing spatial values")
    per_subset = metadata.groupby("subset")["spatial"].unique()
    inconsistent = per_subset[per_subset.map(len) > 1]
    if not inconsistent.empty:
        raise ValueError(f"{path} has conflicting spatial values for: {', '.join(inconsistent.index)}")
    return per_subset.map(lambda values: values[0]).to_dict()


def _content_type_for(
    subset: str,
    method_group: str,
    item: str,
    lookup: dict[tuple[str, str], str],
) -> str:
    """Resolve a loader item ID to its catalogue content type."""
    item_id = str(item)
    key = (str(subset), item_id)
    if key in lookup:
        return lookup[key]
    prefix = f"{method_group}_"
    if item_id.startswith(prefix):
        key = (str(subset), item_id[len(prefix):])
        if key in lookup:
            return lookup[key]
    raise ValueError(
        f"No content type for subset={subset!r}, method_group={method_group!r}, item={item!r}"
    )


def _attach_content_types(
    pairs: pd.DataFrame,
    lookup: dict[tuple[str, str], str],
) -> pd.DataFrame:
    """Add catalogue content types to scored pairs using their loader IDs."""
    result = pairs.copy()
    result["content_type"] = [
        _content_type_for(row["subset"], row["method_group"], row["item"], lookup)
        for row in result.to_dict("records")
    ]
    return result


def _inclusion_selections(labels: list[str]) -> list[tuple[str, ...]]:
    """Enumerate every combination of included labels, including the empty set."""
    labels = sorted(set(labels))
    return [
        selection
        for size in range(len(labels) + 1)
        for selection in combinations(labels, size)
    ]


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def score_pair(metric_name: str, ref_path: str, target_path: str) -> float:
    """Score one reference/target pair with a registered metric, higher is better.

    Lower-is-better metrics (NEGATED_METRICS) are negated, so that cached scores and
    correlations of all metrics are higher-is-better.
    """
    score = METRICS_REGISTRY[metric_name](ref_path, target_path)
    return -score if metric_name in NEGATED_METRICS else score


def _evaluate_metric(
    pairs: list[dict[str, Any]],
    metric_fn: Callable[[str, str], float],
    cache: dict[tuple[str, str], float],
    cache_path: Path,
    collection: Path,
) -> list[dict[str, Any]]:
    """Attach cached or newly computed objective scores to each pair.

    Args:
        pairs: Pair records to score; updated in place.
        metric_fn: Callable that scores a reference/target WAV pair.
        cache: Mutable score cache keyed by target/reference paths.
        cache_path: Destination used to persist updated cache entries.
        collection: Collection root used to store portable cache paths.

    Returns:
        The updated pair records.
    """
    total = len(pairs)
    new_computed = 0
    for i, p in enumerate(pairs):
        key = (p["target_wav"], p["ref_wav"])
        if key in cache:
            p["obj_score"] = cache[key]
        else:
            try:
                score = metric_fn(p["ref_wav"], p["target_wav"])
            except Exception as e:
                print(f"  WARNING: {p['item']}/{p['condition']}: {e}")
                score = np.nan
            p["obj_score"] = score
            cache[key] = score
            new_computed += 1
            if new_computed % 10 == 0:
                _save_cache(cache, cache_path, collection)
        if (i + 1) % 50 == 0 or i + 1 == total:
            print(f"  [{i+1}/{total}] ({new_computed} newly computed)")
    if new_computed > 0:
        _save_cache(cache, cache_path, collection)
    return pairs


# ---------------------------------------------------------------------------
# Correlation reporting
# ---------------------------------------------------------------------------

# Correlation coefficients computed for every metric, in display order.
# "kendall" is Kendall's tau-b mapped to the Pearson scale with sin(pi * tau / 2)
# (Greiner's relation), so that it is comparable with the other two.
CORRELATION_TYPES = ("pearson", "spearman", "kendall")
CORRELATION_LABELS = {"pearson": "Pearson", "spearman": "Spearman", "kendall": "Kendall sin(πτ/2)"}

# The analysis variants (scopes, subset/content filters, aggregations) correlate the same
# method groups many times over; results are memoized on a hash of the input scores.
_correlation_cache: dict[bytes, dict[str, float]] = {}


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson correlation of two non-constant vectors (scipy.stats.pearsonr without its overhead)."""
    x, y = x - x.mean(), y - y.mean()
    return float(x @ y / np.sqrt((x @ x) * (y @ y)))


def _compute_correlations(subj: np.ndarray, obj: np.ndarray) -> dict[str, float]:
    """Pearson, Spearman and Kendall (tau-b, as sin(pi * tau / 2)) on pairs with finite scores.

    Non-finite scores can arise from failed metric computations or missing data.
    Such pairs are excluded and their count is reported.
    Results are memoized in _correlation_cache.

    Args:
        subj: Subjective scores.
        obj: Objective scores corresponding to the subjective scores.

    Returns:
        Correlation coefficients keyed by CORRELATION_TYPES.
    """
    mask = np.isfinite(subj) & np.isfinite(obj)
    n_dropped = (~mask).sum()
    if n_dropped > 0:
        print(f"  WARNING: {n_dropped} pairs dropped from correlation (non-finite values)")
    s, o = subj[mask].astype(float), obj[mask].astype(float)
    key = hashlib.blake2b(s.tobytes() + b"|" + o.tobytes(), digest_size=16).digest()
    if key not in _correlation_cache:
        if len(s) < 3 or np.std(s) == 0 or np.std(o) == 0:
            result = {corr_type: np.nan for corr_type in CORRELATION_TYPES}
        else:
            result = {"pearson": _pearson(s, o),
                      "spearman": _pearson(stats.rankdata(s), stats.rankdata(o)),
                      "kendall": np.sin(np.pi / 2 * stats.kendalltau(s, o)[0])}
        _correlation_cache[key] = result
    return dict(_correlation_cache[key])


def _finite_pair_count(pairs: pd.DataFrame) -> int:
    """Count pair rows with finite subjective and objective scores."""
    return int((np.isfinite(pairs["mean_score"].to_numpy(dtype=float)) &
                np.isfinite(pairs["obj_score"].to_numpy(dtype=float))).sum())


def _fisher_z_correlation_bounds(value: float, n: int,
                                 corr_type: str = "pearson") -> tuple[float, float]:
    """Approximate a two-sided 95% interval with Fisher's z transform.

    z has variance 1 / (n - 3). For Kendall, the interval is computed for tau itself,
    whose z has variance 0.437 / (n - 4) (Fieller, Hartley & Pearson, 1957), and its
    endpoints are mapped with sin(pi * tau / 2) like the value.
    """
    offset, scale = (4, 0.437) if corr_type == "kendall" else (3, 1.0)
    if not np.isfinite(value) or n <= offset:
        return np.nan, np.nan
    if corr_type == "kendall":
        value = 2 / np.pi * np.arcsin(value)  # back to tau
    z = np.arctanh(np.clip(value, -0.999999, 0.999999))
    margin = stats.norm.ppf(0.975) * np.sqrt(scale / (n - offset))
    low, high = np.tanh([z - margin, z + margin])
    if corr_type == "kendall":
        low, high = np.sin(np.pi / 2 * np.array([low, high]))
    return float(low), float(high)


def _error_components(value: float, low: float, high: float) -> tuple[float, float]:
    """Convert interval endpoints to nonnegative upper and lower plotting errors."""
    if not np.isfinite(value) or not np.isfinite(low) or not np.isfinite(high):
        return np.nan, np.nan
    return float(max(0.0, high - value)), float(max(0.0, value - low))


def _fishers_z_aggregate(rs: list[float]) -> tuple[float, float, float]:
    """Return the macro mean and back-transformed one-SD Fisher-z range.

    Each method group contributes equally regardless of size (that's the intent
    of 'macro'). Groups with r=NaN are treated as r=0 (no predictive power).
    The SD is computed across group z-values; its endpoints are transformed to r.

    Args:
        rs: Correlation coefficients from method groups.

    Returns:
        The aggregate correlation and its lower and upper one-SD bounds.
    """
    n_nans = sum(np.isnan(r) for r in rs)
    if n_nans:
        print(f"  WARNING: {n_nans} NaN correlations replaced with 0.0 for Fisher z aggregation")
    rs = [0.0 if np.isnan(r) else r for r in rs]
    if not rs:
        return np.nan, np.nan, np.nan
    # Clip to avoid infinite Fisher z-transform values when r = ±1.0
    rs = [np.clip(r, -0.9999, 0.9999) for r in rs]
    z_values = np.arctanh(rs)
    z_avg = np.mean(z_values)
    r_avg = float(np.tanh(z_avg))
    if len(z_values) < 2:
        return r_avg, np.nan, np.nan
    z_sd = np.std(z_values, ddof=1)
    return r_avg, float(np.tanh(z_avg - z_sd)), float(np.tanh(z_avg + z_sd))


def _compute_results(
    df: pd.DataFrame, agg_method: str
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Compute correlations per method group and optionally aggregate.
    
    Args:
        df: DataFrame with subset, method_group, mean_score, and obj_score columns
        agg_method: "macro" for Fisher's z aggregation, "micro" for pooled correlation
    
    Returns:
        Per-group results and aggregate correlations with transformed SD bounds.
    """
    group_results = []
    for (subset, method_group), sub in df.groupby(["subset", "method_group"], sort=True):
        group_results.append({"subset": subset, "method_group": method_group,
                              "N": _finite_pair_count(sub),
                              **_compute_correlations(sub["mean_score"].values,
                                                      sub["obj_score"].values)})

    aggregate_results = {}
    if agg_method == "macro":
        for corr_type in CORRELATION_TYPES:
            value, low, high = _fishers_z_aggregate([g[corr_type] for g in group_results])
            aggregate_results.update(
                {corr_type: value, f"{corr_type}_low": low, f"{corr_type}_high": high})
    elif agg_method == "micro":
        n = _finite_pair_count(df)
        pooled = _compute_correlations(df["mean_score"].values, df["obj_score"].values)
        for corr_type, value in pooled.items():
            low, high = _fisher_z_correlation_bounds(value, n, corr_type)
            aggregate_results.update(
                {corr_type: value, f"{corr_type}_low": low, f"{corr_type}_high": high})
    else:
        raise ValueError(f"Unknown aggregation method: {agg_method}")
    return group_results, aggregate_results


def _metric_correlation_rows(metric: str, scope: str, include_anchors: bool,
                             agg_method: str, df: pd.DataFrame,
                             subset_filter: tuple[str, ...],
                             content_type_filter: tuple[str, ...],
                             include_method_groups: bool) -> list[dict[str, Any]]:
    """Compute aggregate and method-group rows for one metric view.

    Args:
        metric: Metric name.
        scope: Subset scope for this analysis view.
        include_anchors: Whether anchor conditions are included.
        agg_method: Aggregation method, either macro or micro.
        df: Pair observations to correlate.
        subset_filter: Subsets included in this analysis variant.
        content_type_filter: Content types included in this analysis variant.
        include_method_groups: Whether to emit method rows for the full subset set.

    Returns:
        Analysis rows for the aggregate and each method group.
    """
    groups, aggregate = _compute_results(df, agg_method)
    for corr_type in CORRELATION_TYPES:
        aggregate[f"{corr_type}_error_plus"], aggregate[f"{corr_type}_error_minus"] = (
            _error_components(aggregate[corr_type], aggregate[f"{corr_type}_low"],
                              aggregate[f"{corr_type}_high"]))
    common = {
        "record_type": "correlation", "metric": metric, "scope": scope,
        "subset_filter": list(subset_filter),
        "content_type_filter": list(content_type_filter),
        "include_anchors": include_anchors, "agg_method": agg_method,
    }
    rows = [{**common, "result_type": "aggregate",
             "N": _finite_pair_count(df), **aggregate}]
    if include_method_groups:
        method_common = {**common, "subset_filter": None}
        rows.extend({**method_common, "result_type": "method_group", **group} for group in groups)
    return rows


# ---------------------------------------------------------------------------
# Metric evaluation
# ---------------------------------------------------------------------------

def _run_single_metric(metric_name: str, loaders: list[ODAQSubsetLoader],
                      all_pairs: list[dict[str, Any]],
                      collection: Path, scores_dir: Path,
                      cache_only: bool = False) -> pd.DataFrame:
    """Score pairs once and match objective and subjective observations.

    Args:
        metric_name: Registered metric to evaluate.
        loaders: Active subset loaders.
        all_pairs: Pair records shared across the configured metrics.
        collection: Collection root.
        scores_dir: Directory of the metric score caches.
        cache_only: Load scores from the cache only; raise if any are missing.

    Returns:
        Pair observations with both subjective and objective scores.
    """
    cache_path = _cache_path(scores_dir, metric_name)
    
    if metric_name not in METRICS_REGISTRY:
        print(f"\nERROR: unknown metric '{metric_name}'. Choices: {list(METRICS_REGISTRY.keys())}")
        sys.exit(1)
    metric_fn = functools.partial(score_pair, metric_name)
    
    print(f"\n{'='*68}")
    print(f"EVALUATING METRIC: {metric_name}")
    print(f"{'='*68}")
    
    score_clip = (-100.0, 100.0) if metric_name == "SI-SDR" else None
    cache = _load_cache(cache_path, collection, score_clip)
    if cache_only:
        missing = sum((pair["target_wav"], pair["ref_wav"]) not in cache for pair in all_pairs)
        if missing:
            raise ValueError(
                f"{metric_name}: {missing} scores missing from {cache_path}. Run evaluate.py first."
            )
    print(f"  Cache: {len(cache)} entries from {cache_path}")
    print(f"  (delete {cache_path.parent}/ to force recomputation)")
    evaluated_pairs = _evaluate_metric(
        copy.deepcopy(all_pairs), metric_fn, cache, cache_path, collection)
    
    # [STAGE 4/4] Match subjective and objective observations
    print("\n[STAGE 4/4] Matching subjective and objective scores...")
    subj_df = _load_mean_subjective_scores(loaders, collection)
    pairs_df = pd.DataFrame(evaluated_pairs)
    merged = pairs_df.merge(subj_df, on=["subset", "item", "condition"], how="left")
    n_missing = merged["mean_score"].isna().sum()
    if n_missing:
        print(f"  WARNING: {n_missing} pairs have no matching subjective scores")
    merged = merged.dropna(subset=["mean_score", "obj_score"])
    print(f"  {len(merged)} pairs with both scores")
    
    return merged


def _append_pair_records(records: list[dict[str, Any]], metric: str,
                         pairs: pd.DataFrame, collection: Path,
                         spatial_status: dict[str, str]) -> None:
    """Add scored pair records with collection-relative audio paths.

    Args:
        records: Output records list to update.
        metric: Metric name associated with the pair scores.
        pairs: Scored pair observations.
        collection: Root used to make audio paths relative.
        spatial_status: Spatial classification keyed by subset.

    Returns:
        None.
    """
    for pair in pairs.to_dict("records"):
        records.append({
            "record_type": "pair",
            "metric": metric,
            "subset": pair["subset"],
            "spatial": spatial_status[pair["subset"]],
            "method_group": pair["method_group"],
            "item": pair["item"],
            "content_type": pair["content_type"],
            "condition": pair["condition"],
            "target_wav": Path(pair["target_wav"]).relative_to(collection).as_posix(),
            "ref_wav": Path(pair["ref_wav"]).relative_to(collection).as_posix(),
            "mean_score": pair["mean_score"],
            "obj_score": pair["obj_score"],
            "is_anchor": pair["condition"] in ANCHOR_CONDITIONS,
        })

# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------

def _rho_perfect_rows(ratings: pd.DataFrame, scope: str, subsets: set[str],
                      include_anchors: bool,
                      subset_filter: tuple[str, ...],
                      content_type_filter: tuple[str, ...],
                      include_method_groups: bool) -> list[dict[str, Any]]:
    """Compute rho-perfect rows from individual listener ratings.

    Args:
        ratings: Individual listener ratings.
        scope: Subset scope for this analysis view.
        subsets: Subsets included when scope is not all.
        include_anchors: Whether anchor ratings are included.
        subset_filter: Subsets included in this analysis variant.
        content_type_filter: Content types included in this analysis variant.
        include_method_groups: Whether to emit method rows for the full subset set.

    Returns:
        Aggregate and method-group rho-perfect analysis rows.
    """
    scoped_ratings = ratings
    if not include_anchors:
        scoped_ratings = scoped_ratings[~scoped_ratings["is_anchor"]]
    if scope != "all":
        scoped_ratings = scoped_ratings[scoped_ratings["subset"].isin(subsets)]
    scoped_ratings = scoped_ratings[
        scoped_ratings["subset"].isin(subset_filter)
    ]
    scoped_ratings = scoped_ratings[
        scoped_ratings["content_type"].isin(content_type_filter)
    ]
    methods = {
        (subset, group): calculate_rho_perfect_from_ratings(group_df[["filename", "rating"]])
        for (subset, group), group_df in scoped_ratings.groupby(["subset", "method_group"])
    }
    common = {
        "record_type": "correlation", "metric": "rho-perfect", "scope": scope,
        "subset_filter": list(subset_filter),
        "include_anchors": include_anchors,
        "content_type_filter": list(content_type_filter),
    }
    # Macro aggregates method-group values; Micro pools listener ratings.
    rows = []
    for agg_method in ("macro", "micro"):
        if agg_method == "macro":
            aggregate, low, high = _fishers_z_aggregate(list(methods.values()))
        else:
            n = scoped_ratings["filename"].nunique()
            if scoped_ratings.empty:
                aggregate = low = high = np.nan
            else:
                aggregate = calculate_rho_perfect_from_ratings(
                    scoped_ratings[["filename", "rating"]])
                low, high = _fisher_z_correlation_bounds(aggregate, n)
        error_plus, error_minus = _error_components(aggregate, low, high)
        rows.append({**common, "agg_method": agg_method, "result_type": "aggregate",
                     "N": scoped_ratings["filename"].nunique(),
                     "pearson": aggregate, "pearson_low": low, "pearson_high": high,
                     "pearson_error_plus": error_plus, "pearson_error_minus": error_minus})
        if include_method_groups:
            method_common = {**common, "subset_filter": None}
            for (subset, group), value in methods.items():
                rows.append({**method_common, "agg_method": agg_method,
                             "result_type": "method_group", "subset": subset,
                             "method_group": group, "pearson": value})
    return rows


def _compute_correlation_variants(
    pairs_by_metric: dict[str, pd.DataFrame],
    ratings: pd.DataFrame,
    spatial_status: dict[str, str],
) -> list[dict[str, Any]]:
    """Compute rows for every metric and rho-perfect analysis view.

    Args:
        pairs_by_metric: Scored pair observations keyed by metric name.
        ratings: Individual listener ratings used for rho-perfect.
        spatial_status: Spatial-audio classification keyed by subset.

    Returns:
        Correlation rows for every scope, anchor setting, aggregation, and
        content-type inclusion set.
    """
    rows = []
    content_types = sorted({
        content_type
        for pairs in pairs_by_metric.values()
        for content_type in pairs["content_type"].dropna().unique()
    })
    subset_names = sorted({
        subset
        for pairs in pairs_by_metric.values()
        for subset in pairs["subset"].dropna().unique()
    })
    # All collection files are stereo; this flag distinguishes distortion focus.
    scopes = {
        "all": set(subset_names),
        "mono": {s for s in subset_names if spatial_status[s] == "mono"},
        "stereo": {s for s in subset_names if spatial_status[s] == "stereo"},
    }
    # Enumerate only subsets valid for each scope to avoid redundant variants.
    for scope, scope_subsets in scopes.items():
        available_subsets = tuple(sorted(scope_subsets))
        for subset_filter in _inclusion_selections(list(available_subsets)):
            include_method_groups = subset_filter == available_subsets
            for content_type_filter in _inclusion_selections(content_types):
                selected_pairs = {
                    metric: pairs[
                        pairs["subset"].isin(subset_filter) &
                        pairs["content_type"].isin(content_type_filter)
                    ]
                    for metric, pairs in pairs_by_metric.items()
                }
                selected_ratings = ratings[
                    ratings["subset"].isin(subset_filter) &
                    ratings["content_type"].isin(content_type_filter)
                ]
                for include_anchors in (False, True):
                    subsets = set(subset_filter)
                    for metric, evaluation_df in selected_pairs.items():
                        df = evaluation_df
                        if not include_anchors:
                            df = df[~df["condition"].isin(ANCHOR_CONDITIONS)]
                        for agg_method in ("macro", "micro"):
                            rows.extend(_metric_correlation_rows(
                                metric, scope, include_anchors, agg_method, df,
                                subset_filter, content_type_filter,
                                include_method_groups))
                    rows.extend(_rho_perfect_rows(
                        selected_ratings, scope, subsets, include_anchors,
                        subset_filter, content_type_filter,
                        include_method_groups))
    return rows


def compute_analysis() -> list[dict[str, Any]]:
    """Compute full-precision analysis records."""
    # Resolve paths and configuration
    collection_path = config.COLLECTION_ROOT.resolve()
    metrics_to_run = config.METRICS if isinstance(config.METRICS, list) else [config.METRICS]
    active_subsets = config.ACTIVE_SUBSETS
    scores_dir = config.SCORES_DIR

    # Handle 'ALL' flag to run all available metrics
    if "ALL" in metrics_to_run:
        metrics_to_run = list(METRICS_REGISTRY.keys())
    # Every other registered metric with cached scores is included from its cache,
    # so adding one metric does not require re-running the others.
    cached_metrics = [
        metric for metric in METRICS_REGISTRY
        if metric not in metrics_to_run and _cache_path(scores_dir, metric).exists()
    ]

    # Print resolved paths and configuration
    print(f"Collection  : {collection_path}")
    print(f"Metrics     : {metrics_to_run}")
    print(f"From cache  : {cached_metrics}")
    print(f"Subsets     : {active_subsets}")
    print(f"Scores      : {scores_dir}")

    if not collection_path.is_dir():
        print(f"\nERROR: COLLECTION_ROOT does not exist: {collection_path}")
        sys.exit(1)

    # [STAGE 1/4] Load pairs of reference vs probe audio files (shared across all metrics)
    print("\n[STAGE 1/4] Loading pairs reference/probe...")
    loaders = [LOADER_REGISTRY[key](collection_path) for key in active_subsets]
    all_pairs = []
    for loader in loaders:
        pairs = loader.pairs()
        print(f"  {loader.name}: {len(pairs)} pairs")
        all_pairs.extend(pairs)
    print(f"  TOTAL: {len(all_pairs)} pairs")

    # [STAGE 2/4] Preflight
    print("\n[STAGE 2/4] Preflight...")
    # Check if all pairs have the required fields and are valid
    if not _preflight_check(all_pairs):
        sys.exit(1)

    # Reads flag about focus on spatial audio for each subset
    spatial_status = _load_spatial_status(collection_path)
    content_type_lookup = _load_content_type_lookup(collection_path)

    # [STAGE 3/4] Get scored pair rows now, either by running the metrics or loading cached results
    print("\n[STAGE 3/4] Running metrics...")
    # records stores pair observations and all precomputed correlation variants.
    records = [] 
    pairs_by_metric = {}

    for metric_name in metrics_to_run + cached_metrics:
        try:
            evaluation_df = _run_single_metric(
                metric_name, loaders, all_pairs, collection_path, scores_dir,
                metric_name in cached_metrics)
        except ValueError as error:
            if metric_name not in cached_metrics:
                raise
            print(f"  WARNING: skipping {metric_name}: {error}\n"
                  f"  Add it to METRICS in config.py to compute the missing scores.")
            continue
        evaluation_df = _attach_content_types(evaluation_df, content_type_lookup)
        pairs_by_metric[metric_name] = evaluation_df
        _append_pair_records(
            records, metric_name, evaluation_df, collection_path, spatial_status)

    # [STAGE 4/4] Get correlation coefficients based on the collected pair records and ratings
    print("\n[STAGE 4/4] Computing correlation coefficients...")
    # we need individual listener ratings to compute rho_perfect
    ratings = _load_listener_ratings(loaders, collection_path, content_type_lookup)
    
    correlation_rows = _compute_correlation_variants(
        pairs_by_metric, ratings, spatial_status)
    records.extend(correlation_rows)
    return records


@contextmanager
def _summarize_rho_perfect_warnings() -> Generator[None, None, None]:
    counts: Counter[tuple[str, str]] = Counter()
    with warnings.catch_warnings():
        warnings.filterwarnings("always", module=r"rho_perfect(?:\.|$)")
        original_showwarning = warnings.showwarning

        def collect_warning(message: Warning | str, category: type[Warning],
                            filename: str, lineno: int, file: Any = None,
                            line: str | None = None) -> None:
            if "rho_perfect" in Path(filename).parts:
                text = re.sub(r"Dataset has \d+ items;", "Small dataset;", str(message))
                counts[(category.__name__, text)] += 1
            else:
                original_showwarning(message, category, filename, lineno, file, line)

        warnings.showwarning = collect_warning
        try:
            yield
        finally:
            if counts:
                print(f"\nWARNING: rho-perfect emitted {sum(counts.values())} warnings "
                      "(summarized below):", file=sys.stderr)
                for (category, message), count in counts.items():
                    print(f"  {count}x {category}: {message}", file=sys.stderr)


def _main() -> None:
    from build_github_page import export_website_data

    with _summarize_rho_perfect_warnings():
        records = compute_analysis()

    export_website_data(records)


if __name__ == "__main__":
    _main()
