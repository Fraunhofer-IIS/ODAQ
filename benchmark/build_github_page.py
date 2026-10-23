#!/usr/bin/env python3
"""Build the GitHub Pages HTML shell without computing or modifying analysis data."""

import argparse
import csv
import html
import json
from pathlib import Path
from typing import Any

import numpy as np

import config


ROOT = Path(__file__).resolve().parent
# Reference papers per subset, shown in the "About the subsets" table.
SUBSET_REFERENCES = config.COLLECTION_ROOT / "subset_references.csv"
PAGE_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ODAQ | Metric Analysis</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%23087f78'/%3E%3Cpath fill='white' d='M32%205%2039.5%2023%2059%2023%2043.5%2035%2049%2055%2032%2043%2015%2055%2020.5%2035%205%2023%2024.5%2023Z'/%3E%3C/svg%3E">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {
      color-scheme: light;
      --ink: #1c2928;
      --muted: #61716e;
      --line: #dce5e2;
      --paper: #f4f7f5;
      --surface: #fff;
      --teal: #087f78;
      --blue: #247ab5;
      --orange: #df7624;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: "Avenir Next", Avenir, "Segoe UI", sans-serif;
    }
    header {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 24px;
      padding: 28px max(24px, calc((100vw - 1440px) / 2));
      border-bottom: 1px solid var(--line);
      background: var(--surface);
    }
    .eyebrow {
      margin: 0 0 7px;
      color: var(--teal);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }
    h1 { margin: 0; font-size: 28px; font-weight: 650; }
    .subtitle { margin: 8px 0 0; color: var(--muted); font-size: 14px; }
    .subtitle a { color: var(--blue); }
    main { max-width: 1440px; margin: 0 auto; padding: 24px; }
    .app-layout {
      display: grid;
      grid-template-columns: 260px minmax(0, 1fr);
      align-items: start;
      gap: 24px;
    }
    .filters-panel {
      position: sticky;
      top: 16px;
      align-self: start;
      max-height: calc(100vh - 32px);
      overflow-y: auto;
      padding-right: 18px;
      border-right: 1px solid var(--line);
    }
    .workspace { min-width: 0; }
    .filters-toggle { display: none; }
    .header-actions { display: flex; align-items: center; gap: 10px; }
    .repo-link {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 14px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      color: var(--ink);
      font-size: 14px;
      font-weight: 600;
      text-decoration: none;
      white-space: nowrap;
    }
    .repo-link:hover, .repo-link:focus-visible { border-color: var(--teal); color: var(--teal); }
    .repo-link svg { width: 18px; height: 18px; fill: currentColor; }
    .toolbar {
      display: grid;
      align-items: stretch;
      gap: 20px;
      padding: 0;
    }
    .control { display: grid; gap: 8px; }
    .content-type-options { flex-wrap: wrap; gap: 3px; }
    .control-label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .segments {
      display: flex;
      width: 100%;
      flex-wrap: wrap;
      padding: 3px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--surface);
    }
    .segments button {
      position: relative;
      min-height: 30px;
      padding: 0 10px;
      border: 0;
      border-radius: 4px;
      background: transparent;
      color: var(--muted);
      font: inherit;
      font-size: 13px;  /* after the font shorthand, which would reset it */
      cursor: pointer;
    }
    .segments button:disabled { cursor: not-allowed; opacity: 0.45; }
    .option-tooltip {
      position: fixed;
      z-index: 1000;
      width: max-content;
      max-width: min(280px, calc(100vw - 16px));
      padding: 8px 10px;
      border-radius: 5px;
      background: var(--ink);
      color: white;
      font-size: 12px;
      line-height: 1.4;
      text-align: left;
      white-space: normal;
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
      transition: opacity 120ms ease, visibility 120ms;
    }
    .option-tooltip.is-visible {
      opacity: 1;
      visibility: visible;
    }
    .segments button[aria-pressed="true"] {
      background: var(--teal);
      color: white;
    }
    button:focus-visible, input:focus-visible {
      outline: 3px solid #86c9c3;
      outline-offset: 2px;
    }
    .section-head {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin: 0 0 8px;
    }
    h2 { margin: 0; font-size: 18px; font-weight: 650; }
    .status { color: var(--muted); font-size: 13px; white-space: pre-line; }
    .section-note { margin: 0 0 8px; color: var(--muted); font-size: 12px; }
    .overview-tools {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px 14px;
      margin: 0 0 8px;
    }
    .overview-tools .section-note { flex-basis: 100%; margin: 0; }  /* always on its own line */
    .segments.compact { width: auto; padding: 2px; }
    .segments.compact button { min-height: 26px; padding: 0 10px; font-size: 13px; white-space: nowrap; }
    .compare { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
    .compare input {
      width: 170px;
      min-height: 30px;
      padding: 0 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--surface);
      color: var(--ink);
      font: inherit;
      font-size: 13px;
    }
    .compare-chips { display: contents; }
    .compare-chip {
      min-height: 26px;
      padding: 0 8px;
      border: 1px solid var(--teal);
      border-radius: 13px;
      background: var(--surface);
      color: var(--teal);
      font: inherit;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }
    .compare-chip:hover, .compare-chip:focus-visible { background: var(--teal); color: white; }
    .chart-frame {
      min-height: 460px;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--surface);
    }
    #overview-chart { width: 100%; height: 500px; }
    .histogram-frame { min-height: 380px; }
    #mean-score-histogram { width: 100%; height: 380px; }
    #detail { margin-top: 28px; }
    #detail[hidden] { display: none; }
    .detail-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }
    .detail-source { margin: 4px 0 0; color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }
    .back-button {
      padding: 8px 12px;
      border: 1px solid var(--line);
      border-radius: 5px;
      background: var(--surface);
      color: var(--ink);
      font: inherit;
      cursor: pointer;
    }
    .detail-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 18px; }
    .detail-block {
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--surface);
    }
    .detail-block h3 { margin: 0 0 12px; font-size: 15px; }
    .method-chart-scroll { overflow-x: auto; }
    #method-chart { width: 100%; height: 460px; }
    #pair-chart { width: 100%; height: 430px; }
    .empty { color: var(--muted); font-size: 14px; }
    .control-head { display: flex; align-items: center; gap: 6px; }
    /* Collapsible sections: the heading becomes a toggle button (see setupCollapsibles). */
    .collapse-toggle {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 0;
      border: 0;
      background: none;
      color: inherit;
      font: inherit;
      text-align: left;
      cursor: pointer;
    }
    .collapse-toggle::before {
      content: "";
      flex: none;
      width: 6px;
      height: 6px;
      border: solid var(--muted);
      border-width: 0 2px 2px 0;
      transform: translateY(-2px) rotate(45deg);
    }
    .collapse-toggle:hover::before { border-color: var(--teal); }
    .collapsed .collapse-toggle::before { transform: rotate(-45deg); }
    [data-collapsible].collapsed > :not(.section-head, h3) { display: none; }
    .detail-block.collapsed h3 { margin-bottom: 0; }
    .help-link {
      display: inline-grid;
      place-items: center;
      width: 16px;
      height: 16px;
      border: 1px solid var(--muted);
      border-radius: 50%;
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
      line-height: 1;
      text-decoration: none;
    }
    .help-link:hover, .help-link:focus-visible { border-color: var(--teal); color: var(--teal); }
    #subsets-info { margin-top: 28px; scroll-margin-top: 16px; }
    .table-frame {
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--surface);
    }
    .info-table { width: 100%; border-collapse: collapse; font-size: 14px; line-height: 1.45; }
    .info-table th, .info-table td {
      padding: 10px 14px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }
    .info-table tr:last-child td { border-bottom: 0; }
    .info-table th { color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .info-table td:first-child { white-space: nowrap; font-weight: 600; }
    .info-table p { margin: 0; }
    .info-table p + p { margin-top: 6px; }
    .info-table a { color: var(--blue); }
    footer {
      max-width: 1440px;
      margin: 0 auto;
      padding: 0 24px 24px;
      color: var(--muted);
      font-size: 12px;
    }
    @media (max-width: 900px) {
      .app-layout { display: block; }
      .filters-toggle {
        display: inline-flex;
        min-height: 36px;
        align-items: center;
        gap: 8px;
        padding: 0 10px;
        border: 1px solid var(--line);
        border-radius: 5px;
        background: var(--surface);
        color: var(--ink);
        font: inherit;
        cursor: pointer;
      }
      .menu-icon { display: grid; gap: 3px; width: 16px; }
      .menu-icon span { height: 2px; border-radius: 1px; background: currentColor; }
      .filters-panel {
        display: none;
        position: static;
        max-height: none;
        overflow: visible;
        margin-bottom: 20px;
        padding: 0 0 18px;
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }
      .filters-panel.is-open { display: block; }
    }
    @media (max-width: 700px) {
      header { align-items: start; padding: 22px 18px; }
      .repo-link { padding: 8px 10px; }
      .repo-link-text { display: none; }
      h1 { font-size: 23px; }
      main { padding: 18px; }
      .section-head { align-items: start; flex-direction: column; gap: 4px; }
      .toolbar { gap: 16px; }
      .segments button { flex: 1; padding: 0 8px; }
      .content-type-options { width: 100%; }
      .chart-frame { min-height: 400px; }
      #overview-chart { height: 420px; }
      .histogram-frame { min-height: 330px; }
      #mean-score-histogram { height: 330px; }
      .detail-block { padding: 12px; }
      #pair-chart { height: 360px; }
      /* Stack each subset row: name on top, summary and papers below. */
      .info-table thead { display: none; }
      .info-table tr, .info-table td { display: block; }
      .info-table td { border-bottom: 0; }
      .info-table td:first-child { padding-bottom: 0; }
      .info-table tr { border-bottom: 1px solid var(--line); }
      .info-table tr:last-child { border-bottom: 0; }
    }
    @media (prefers-reduced-motion: no-preference) {
      html { scroll-behavior: smooth; }
      .collapse-toggle::before { transition: transform 0.15s; }
    }
    #overview-chart .xtick text { pointer-events: all; cursor: pointer; }
    #overview-chart .xtick text:hover { fill: #247ab5 !important; text-decoration: underline; }
  </style>
</head>
<body>
  <header>
    <div>
      <p class="eyebrow">ODAQ / Benchmark</p>
      <h1>Metric correlation</h1>
      <p class="subtitle">Objective metrics against expert listener ratings from the ODAQ datasets · <a href="https://github.com/Fraunhofer-IIS/ODAQ" target="_blank" rel="noopener">What's ODAQ?</a></p>
    </div>
    <div class="header-actions">
      <a class="repo-link" href="https://github.com/Fraunhofer-IIS/ODAQ" target="_blank" rel="noopener" aria-label="View ODAQ on GitHub">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/></svg>
        <span class="repo-link-text">View on GitHub</span>
      </a>
      <button id="filters-toggle" class="filters-toggle" type="button" aria-label="Open filters" aria-controls="filters-panel" aria-expanded="false">
        <span class="menu-icon" aria-hidden="true"><span></span><span></span><span></span></span>
        <span>Filters</span>
      </button>
    </div>
  </header>
  <main class="app-layout">
    <aside id="filters-panel" class="filters-panel" aria-label="Analysis filters">
      <section class="toolbar" aria-label="Chart filters">
      <div class="control">
        <span class="control-label">Subset scope</span>
        <div class="segments content-type-options" data-control="scope" role="group" aria-label="Dataset scope">
          <button type="button" data-value="mono" aria-describedby="scope-mono-tooltip" aria-pressed="true">Mono<span class="option-tooltip" id="scope-mono-tooltip" role="tooltip">Although all files in ODAQ are stereo, these subsets focus on mono distortions.</span></button>
          <button type="button" data-value="stereo" aria-describedby="scope-stereo-tooltip" aria-pressed="true">Stereo<span class="option-tooltip" id="scope-stereo-tooltip" role="tooltip">Although all files in ODAQ are stereo, these subsets focus on spatial distortions.</span></button>
        </div>
      </div>
      <div class="control">
        <div class="control-head">
          <span class="control-label">Subsets included</span>
          <a class="help-link" href="#subsets-info" title="About the subsets" aria-label="About the subsets">?</a>
        </div>
        <div id="subset-options" class="segments content-type-options" data-control="subsets" role="group" aria-label="Subsets included"></div>
      </div>
      <div class="control">
        <span class="control-label">Data aggregation</span>
        <div class="segments" data-control="aggregation" role="group" aria-label="Subset aggregation">
          <button type="button" data-value="macro" aria-label="Macro" aria-describedby="macro-tooltip" aria-pressed="true">Macro<span class="option-tooltip" id="macro-tooltip" role="tooltip">Correlation coefficients are computed for each subset and processing method and then averaged in the Fisher-z space, with equal weights; whiskers show the ±1 SD range in Fisher-z space, transformed back to r.</span></button>
          <button type="button" data-value="micro" aria-label="Micro" aria-describedby="micro-tooltip" aria-pressed="false">Micro<span class="option-tooltip" id="micro-tooltip" role="tooltip">One correlation over all stimuli pooled together; whiskers show approximate 95% analytic Fisher-z intervals, assuming independent observations.</span></button>
        </div>
      </div>
      <div class="control">
        <span class="control-label">Anchors</span>
        <div class="segments" data-control="anchors" role="group" aria-label="Anchor inclusion">
          <button type="button" data-value="false" aria-describedby="anchors-excluded-tooltip" aria-pressed="true">Excluded<span class="option-tooltip" id="anchors-excluded-tooltip" role="tooltip">Low-pass and mono anchors excluded from the correlation analysis. Hidden references are always excluded.</span></button>
          <button type="button" data-value="true" aria-describedby="anchors-included-tooltip" aria-pressed="false">Included<span class="option-tooltip" id="anchors-included-tooltip" role="tooltip">Low-pass and mono anchors included in the correlation analysis. Hidden references are always excluded.</span></button>
        </div>
      </div>
      <div class="control">
        <span class="control-label">Content types</span>
        <div id="content-type-options" class="segments content-type-options" data-control="content-types" role="group" aria-label="Content types included"></div>
      </div>
      <div class="control">
        <span class="control-label">Metric reference</span>
        <div class="segments content-type-options" data-control="reference-types" role="group" aria-label="Metric reference types shown">
          <button type="button" data-value="full-reference" aria-describedby="reference-full-tooltip" aria-pressed="true">Full<span class="option-tooltip" id="reference-full-tooltip" role="tooltip">Full-reference metrics compare the processed signal with its own reference.</span></button>
          <button type="button" data-value="no-reference" aria-describedby="reference-none-tooltip" aria-pressed="true">None<span class="option-tooltip" id="reference-none-tooltip" role="tooltip">No-reference metrics judge the processed signal alone.</span></button>
          <button type="button" data-value="non-matching-reference" aria-describedby="reference-nonmatching-tooltip" aria-pressed="true">Non-matching<span class="option-tooltip" id="reference-nonmatching-tooltip" role="tooltip">Non-matching-reference metrics need a clean reference that does not have to match the processed signal. Here they are given the matching reference.</span></button>
        </div>
      </div>
      </section>
    </aside>

    <div class="workspace">
      <section aria-labelledby="overview-title">
        <div class="section-head">
          <h2 id="overview-title">Aggregate correlations</h2>
          <span id="overview-status" class="status"></span>
        </div>
        <div class="overview-tools">
          <div class="segments compact" data-control="shownMetrics" role="group" aria-label="Metrics shown">
            <button type="button" data-value="all" aria-describedby="shown-all-tooltip" aria-pressed="true">All Metrics<span class="option-tooltip" id="shown-all-tooltip" role="tooltip">Show all metrics.</span></button>
            <button type="button" data-value="top10" aria-describedby="shown-top10-tooltip" aria-pressed="false">Top 10<span class="option-tooltip" id="shown-top10-tooltip" role="tooltip">Show the ten metrics with the highest correlation in the sorted series, for the current filters.</span></button>
            <button type="button" data-value="selected" aria-describedby="shown-selected-tooltip" aria-pressed="false">Selected<span class="option-tooltip" id="shown-selected-tooltip" role="tooltip">Show only the selected metrics.</span></button>
          </div>
          <div class="segments compact" data-control="metricOrder" role="group" aria-label="Metric order">
            <button type="button" data-value="score" aria-describedby="order-sorted-tooltip" aria-pressed="true">Sorted<span class="option-tooltip" id="order-sorted-tooltip" role="tooltip">Sort by correlation.</span></button>
            <button type="button" data-value="locked" aria-describedby="order-locked-tooltip" aria-pressed="false">Locked<span class="option-tooltip" id="order-locked-tooltip" role="tooltip">Keep the current order when filters change.</span></button>
          </div>
          <div class="compare">
            <input id="compare-input" list="compare-options" placeholder="Select metrics…" aria-label="Select a metric to highlight" aria-describedby="compare-tooltip">
            <span class="option-tooltip" id="compare-tooltip" role="tooltip">Type a metric name and press Enter to highlight it; the other metrics are dimmed.</span>
            <datalist id="compare-options"></datalist>
            <div id="compare-chips" class="compare-chips"></div>
          </div>
          <p class="section-note">Click on the metrics for the detailed view. Legends are clickable, too!</p>
        </div>
        <div class="chart-frame"><div id="overview-chart"></div></div>
      </section>

      <section id="mean-score-section" data-collapsible aria-labelledby="mean-score-histogram-title">
        <div class="section-head">
          <h2 id="mean-score-histogram-title">Mean subjective scores by subset</h2>
        </div>
        <div class="chart-frame histogram-frame"><div id="mean-score-histogram"></div></div>
      </section>

      <section id="detail" hidden aria-labelledby="detail-title">
        <div class="detail-head">
          <div>
            <h2 id="detail-title">Metric detail</h2>
            <p id="detail-source" class="detail-source" hidden>Implementation from: <a target="_blank" rel="noopener"></a></p>
          </div>
          <button id="back-button" class="back-button" type="button">Back to overview</button>
        </div>
        <div class="detail-grid">
          <section id="pairs-section" class="detail-block" data-collapsible aria-labelledby="pairs-title">
            <h3 id="pairs-title">Stimulus-level scores</h3>
            <p id="pair-correlations" class="section-note"></p>
            <div id="pair-chart"></div>
            <p id="pair-empty" class="empty" hidden></p>
          </section>
          <section id="method-section" class="detail-block" data-collapsible aria-labelledby="method-chart-title">
            <h3 id="method-chart-title">Correlation by processing method</h3>
            <div class="method-chart-scroll"><div id="method-chart"></div></div>
            <p id="method-chart-empty" class="empty" hidden></p>
          </section>
        </div>
      </section>

      <section id="subsets-info" data-collapsible aria-labelledby="subsets-info-title">
        <div class="section-head">
          <h2 id="subsets-info-title">About the subsets</h2>
        </div>
        <div class="table-frame">
          <table class="info-table">
            <thead>
              <tr><th scope="col">Subset</th><th scope="col">Summary</th><th scope="col">Reference paper</th></tr>
            </thead>
            <tbody>
<!-- SUBSET_REFERENCE_ROWS -->
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </main>

  <script>
    let DATA = null;
    const detailData = new Map();
    const detailDataRequests = new Map();
    const state = {
      // The subset selection is the only subset state; the Mono/Stereo scope follows from it.
      subsets: new Set(), aggregation: "macro", includeAnchors: false,
      contentTypes: new Set(), metric: null,
      referenceTypes: new Set(["full-reference", "no-reference", "non-matching-reference"]),
      // Metrics selected for comparison: highlighted, all others dimmed (or hidden with "Selected").
      compare: new Set(),
      hiddenSeries: new Set(), shownMetrics: "all",
      // "locked" keeps lockedOrder, the order shown when it was chosen, across filter changes.
      metricOrder: "score", lockedOrder: null
    };
    const chart = document.getElementById("overview-chart");
    const meanScoreHistogram = document.getElementById("mean-score-histogram");
    const pairChart = document.getElementById("pair-chart");
    const pairCorrelations = document.getElementById("pair-correlations");
    let pairCorrelationTexts = null;  // set by renderDetail(), read by updatePairCorrelations()
    const detail = document.getElementById("detail");
    const filtersPanel = document.getElementById("filters-panel");
    const filtersToggle = document.getElementById("filters-toggle");
    const palette = ["#247ab5", "#df7624", "#087f78", "#bd4b72", "#7275b8", "#7c8832"];
    let subsetColors = new Map();
    // Per-metric label colors, generated at export (DATA.metric_colors) and fixed per metric.
    let metricColors = new Map();
    let overviewMetrics = [];
    const metricTickAngle = () => chart.clientWidth < 500 ? -90 : -25;

    // Display names of the correlation types exported by evaluate.py (CORRELATION_LABELS).
    const correlationNames = { pearson: "Pearson", spearman: "Spearman", kendall: "Kendall sin(πτ/2)" };

    let activeTooltip = null;

    function hideOptionTooltip() {
      activeTooltip?.classList.remove("is-visible");
      activeTooltip = null;
    }

    function showOptionTooltip(button, tooltip) {
      hideOptionTooltip();
      const anchor = button.getBoundingClientRect();
      const bounds = tooltip.getBoundingClientRect();
      const left = Math.max(8, Math.min(
        anchor.left + (anchor.width - bounds.width) / 2, innerWidth - bounds.width - 8));
      const above = anchor.top - bounds.height - 8;
      const top = Math.max(8, Math.min(
        above >= 8 ? above : anchor.bottom + 8, innerHeight - bounds.height - 8));
      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${top}px`;
      tooltip.classList.add("is-visible");
      activeTooltip = tooltip;
    }

    // Each tooltip belongs to the element that references it with aria-describedby
    // (a button around it, or e.g. the metric-selection field next to it).
    document.querySelectorAll(".option-tooltip").forEach(tooltip => {
      const anchor = document.querySelector(`[aria-describedby="${tooltip.id}"]`);
      document.body.append(tooltip);
      anchor.addEventListener("pointerenter", () => showOptionTooltip(anchor, tooltip));
      anchor.addEventListener("focus", () => showOptionTooltip(anchor, tooltip));
      anchor.addEventListener("pointerleave", () => {
        if (document.activeElement !== anchor) hideOptionTooltip();
      });
      anchor.addEventListener("blur", () => {
        if (!anchor.matches(":hover")) hideOptionTooltip();
      });
    });
    window.addEventListener("scroll", hideOptionTooltip, true);
    document.addEventListener("keydown", event => {
      if (event.key === "Escape") hideOptionTooltip();
    });

    window.addEventListener("resize", () => {
      hideOptionTooltip();
      const angle = metricTickAngle();
      if (chart._fullLayout?.xaxis && chart._fullLayout.xaxis.tickangle !== angle) {
        Plotly.relayout(chart, { "xaxis.tickangle": angle, "margin.r": angle === -90 ? 24 : 80 });
      }
      if (!detail.hidden && state.metric) renderDetail();
    });

    // Make every [data-collapsible] section foldable from its heading; the collapsed
    // set is remembered per browser (best effort, the page works without storage).
    const COLLAPSED_KEY = "odaq-collapsed-sections";

    function setupCollapsibles() {
      let collapsedIds = new Set();
      try { collapsedIds = new Set(JSON.parse(localStorage.getItem(COLLAPSED_KEY)) ?? []); } catch {}
      const save = () => {
        try { localStorage.setItem(COLLAPSED_KEY, JSON.stringify([...collapsedIds])); } catch {}
      };
      const setCollapsed = (section, collapsed) => {
        section.classList.toggle("collapsed", collapsed);
        section.querySelector(".collapse-toggle").setAttribute("aria-expanded", String(!collapsed));
        if (collapsed) collapsedIds.add(section.id); else collapsedIds.delete(section.id);
        save();
        // Charts drawn or resized while hidden have the wrong size: resize them on expand.
        if (!collapsed) window.dispatchEvent(new Event("resize"));
      };
      document.querySelectorAll("[data-collapsible]").forEach(section => {
        const heading = section.querySelector("h2, h3");
        const button = document.createElement("button");
        button.type = "button";
        button.className = "collapse-toggle";
        button.append(...heading.childNodes);
        heading.append(button);
        section.classList.toggle("collapsed", collapsedIds.has(section.id));
        button.setAttribute("aria-expanded", String(!collapsedIds.has(section.id)));
        button.addEventListener("click", () =>
          setCollapsed(section, !section.classList.contains("collapsed")));
      });
      // In-page links (e.g. the "?" next to the subsets) open their target section.
      document.querySelectorAll('a[href^="#"]').forEach(link => {
        const target = document.getElementById(link.getAttribute("href").slice(1));
        if (target?.matches("[data-collapsible]")) {
          link.addEventListener("click", () => setCollapsed(target, false));
        }
      });
    }

    setupCollapsibles();

    filtersToggle.addEventListener("click", () => {
      const expanded = filtersToggle.getAttribute("aria-expanded") === "true";
      filtersPanel.classList.toggle("is-open", !expanded);
      filtersToggle.setAttribute("aria-expanded", String(!expanded));
      filtersToggle.setAttribute("aria-label", expanded ? "Open filters" : "Close filters");
    });

    // Spatial focus of the selected subsets: "all" (mono and stereo), "mono", "stereo" or "none".
    function selectedScope() {
      const types = new Set([...state.subsets].map(subset => DATA.subset_spatial[subset]));
      return types.size === 2 ? "all" : [...types][0] ?? "none";
    }

    // The data has rows per scope too, but a scope's rows equal the "all" rows with the same
    // subsets, so only the "all" rows are used.
    function selectedAggregates() {
      const subsetKey = JSON.stringify([...state.subsets].sort());
      const contentTypeKey = JSON.stringify([...state.contentTypes].sort());
      return DATA.aggregates.filter(row =>
        row.scope === "all" &&
        row.agg_method === state.aggregation &&
        row.include_anchors === state.includeAnchors &&
        row.subset_filter !== null && JSON.stringify(row.subset_filter) === subsetKey &&
        JSON.stringify(row.content_type_filter) === contentTypeKey
      );
    }

    function correlationAxisValue(value) {
      return Math.sign(value) * Math.abs(value) ** 2;
    }

    function selectedPairs(metric = null) {
      return (detailData.get(metric)?.pairs ?? []).filter(row =>
        (metric === null || row.metric === metric) &&
        (state.includeAnchors || !row.is_anchor) &&
        state.subsets.has(row.subset) &&
        state.contentTypes.has(row.content_type)
      );
    }

    function selectedMeanScores() {
      return DATA.mean_scores.filter(row =>
        (state.includeAnchors || !row.is_anchor) &&
        state.subsets.has(row.subset) &&
        state.contentTypes.has(row.content_type)
      );
    }

    function updateMeanScoreHistogram() {
      const meanScores = selectedMeanScores();
      const subsets = [...new Set(meanScores.map(row => row.subset))].sort();
      const traces = subsets.map(subset => ({
        type: "histogram",
        name: subset,
        x: meanScores.filter(row => row.subset === subset).map(row => row.mean_score),
        xbins: { start: 0, end: 100, size: 5 },
        marker: { color: subsetColors.get(subset) },
        hovertemplate: "<b>%{fullData.name}</b><br>Mean score bin: %{x}<br>Count: %{y}<extra></extra>"
      }));
      Plotly.react(meanScoreHistogram, traces, {
        autosize: true,
        barmode: "stack",
        bargap: 0.04,
        margin: { l: 62, r: 24, t: 48, b: 55 },
        paper_bgcolor: "#fff",
        plot_bgcolor: "#fff",
        font: { family: "Avenir Next, Avenir, Segoe UI, sans-serif", color: "#1c2928" },
        xaxis: {
          title: "Mean subjective score",
          range: [0, 100],
          dtick: 10,
          fixedrange: true,
          gridcolor: "#edf1ef",
          zeroline: false
        },
        yaxis: { title: "Count", rangemode: "tozero", gridcolor: "#dfe6e3", zeroline: false },
        legend: { orientation: "h", x: 0, y: 1.16 },
        hoverlabel: { bgcolor: "#1c2928", font: { color: "#fff" } }
      }, { responsive: true, displaylogo: false });
    }

    function initializeMultiSelectOptions(containerId, values, selectedValues) {
      const container = document.getElementById(containerId);
      container.replaceChildren();
      for (const value of values) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.value = value;
        button.setAttribute("aria-pressed", String(selectedValues.has(value)));
        button.textContent = value;
        container.append(button);
      }
      }

    function updateSubsetOptions() {
      initializeMultiSelectOptions("subset-options", DATA.subsets, state.subsets);
      updateScopeButtons();
      updateContentTypeAvailability();
    }

    // A scope toggle is on when at least one of its subsets is selected.
    function updateScopeButtons() {
      const scope = selectedScope();
      for (const button of document.querySelectorAll('[data-control="scope"] button')) {
        button.setAttribute("aria-pressed", String(scope === "all" || scope === button.dataset.value));
      }
    }

    function updateContentTypeAvailability() {
      const includedSubsets = state.subsets;
      const available = new Set([...includedSubsets].flatMap(
        subset => DATA.subset_content_types[subset] ?? []));
      for (const button of document.querySelectorAll("#content-type-options button")) {
        button.disabled = !available.has(button.dataset.value);
        button.title = button.disabled ? "Unavailable in the selected subsets" : "";
      }
    }

    function updateOverview() {
      const rows = selectedAggregates();
      const byMetric = new Map(rows.map(row => [row.metric, row]));
      const series = [
          { key: "pearson", errorPlus: "pearson_error_plus", errorMinus: "pearson_error_minus", name: correlationNames.pearson, marker: "x", offset: -0.2, color: "#247ab5" },
          { key: "spearman", errorPlus: "spearman_error_plus", errorMinus: "spearman_error_minus", name: correlationNames.spearman, marker: "square", offset: 0, color: "#df7624" },
          { key: "kendall", errorPlus: "kendall_error_plus", errorMinus: "kendall_error_minus", name: correlationNames.kendall, marker: "diamond", offset: 0.2, color: "#087f78" }
      ];
      // Order by the first series still shown in the legend (Pearson by default).
      const shownSeries = series.filter(item => !state.hiddenSeries.has(item.name));
      const sortSeries = shownSeries[0] ?? series[0];
      // Skip metrics with no value in any shown series (e.g. rho-perfect has Pearson only).
      const rankedMetrics = DATA.metrics
        .filter(metric => metric === "rho-perfect" ||
          state.referenceTypes.has(DATA.metric_reference_types[metric]))
        .filter(metric => {
          const row = byMetric.get(metric);
          return row && (shownSeries.length ? shownSeries : series).some(item => row[item.key] !== null);
        })
        .sort((left, right) => {
          const leftValue = byMetric.get(left)[sortSeries.key] ?? -Infinity;
          const rightValue = byMetric.get(right)[sortSeries.key] ?? -Infinity;
          return leftValue - rightValue || left.localeCompare(right);
        });
      // "Top 10": the ten best metrics in the sorted series; rho-perfect stays as the upper bound.
      const top = new Set(rankedMetrics.filter(metric => metric !== "rho-perfect").slice(-10));
      const shown = state.shownMetrics === "top10"
        ? rankedMetrics.filter(metric => metric === "rho-perfect" || top.has(metric))
        : state.shownMetrics === "selected"
          ? rankedMetrics.filter(metric => metric === "rho-perfect" || state.compare.has(metric))
          : rankedMetrics;
      // Locked order: metrics shown when it was locked keep their positions; others go first,
      // by score (so the most recent overviewMetrics is captured on the first locked render).
      state.lockedOrder = state.metricOrder === "locked" ? state.lockedOrder ?? overviewMetrics : null;
      const metrics = state.lockedOrder
        ? [...shown.filter(metric => !state.lockedOrder.includes(metric)),
           ...state.lockedOrder.filter(metric => shown.includes(metric))]
        : shown;
      // With metrics selected for comparison, each series is split into a highlighted trace and a
      // dimmed one; the dimmed trace shares the series' legend entry.
      const highlighted = metric => !state.compare.size || metric === "rho-perfect" || state.compare.has(metric);
      const traces = series.flatMap(item => {
        const points = metrics.map((metric, index) => ({
          metric,
          x: index + item.offset,
          row: byMetric.get(metric)
        })).filter(point => point.row[item.key] !== null);
        return [
          seriesTrace(item, points.filter(point => highlighted(point.metric)), false),
          ...(state.compare.size ? [seriesTrace(item, points.filter(point => !highlighted(point.metric)), true)] : [])
        ];
      });
      function seriesTrace(item, points, dimmed) {
        const color = dimmed ? withAlpha(item.color, 0.18) : item.color;
        return {
          type: "scatter",
          mode: "markers",
          name: item.name,
          legendgroup: item.name,
          showlegend: !dimmed,
          visible: state.hiddenSeries.has(item.name) ? "legendonly" : true,
          x: points.map(point => point.x),
          y: points.map(point => correlationAxisValue(point.row[item.key])),
          customdata: points.map(point => [displayName(point.metric), point.row[item.key], point.metric,
            DATA.metric_reference_types[point.metric]?.replace(/-reference$/, " reference") ?? "upper bound",
            hoverDetails(point.metric, item, point.row)]),
          marker: { color, size: 11, symbol: item.marker, line: { width: 1.5, color: dimmed ? withAlpha("#1c2928", 0.18) : "#1c2928" } },
          error_y: {
            type: "data",
            array: points.map(point => {
              const value = point.row[item.key];
              return correlationAxisValue(value + (point.row[item.errorPlus] ?? 0)) -
                correlationAxisValue(value);
            }),
            arrayminus: points.map(point => {
              const value = point.row[item.key];
              return correlationAxisValue(value) -
                correlationAxisValue(value - (point.row[item.errorMinus] ?? 0));
            }),
            visible: true,
            color,
            thickness: 1.5,
            width: 4
          },
          hovertemplate: `<b>%{customdata[0]}</b> · %{customdata[3]}<br>${item.name}: %{customdata[1]:.3f}%{customdata[4]}<extra></extra>`
        };
      }
      const layout = {
        autosize: true,
        // Extra right margin so a long slanted label in the last slot is not clipped.
        margin: { l: 62, r: metricTickAngle() === -90 ? 24 : 80, t: 58, b: 55 },
        paper_bgcolor: "#fff",
        plot_bgcolor: "#fff",
        font: { family: "Avenir Next, Avenir, Segoe UI, sans-serif", color: "#1c2928" },
        xaxis: {
          side: "top",
          title: { text: "Metric", standoff: 16 },
          tickmode: "array",
          tickvals: metrics.map((_, index) => index),
          ticktext: metrics.map(metric => !highlighted(metric)
            ? `<span style="color:#b9c3c0">${escapeHtml(metric)}</span>`
            : state.compare.has(metric)
              ? `<b style="color:${metricColors.get(metric)}">${escapeHtml(metric)}</b>`
              : `<span style="color:${metricColors.get(metric)}">${escapeHtml(metric)}</span>`),
          tickangle: metricTickAngle(),
          range: [-0.6, Math.max(0.6, metrics.length - 0.4)],
          fixedrange: true,
          gridcolor: "#edf1ef",
          zeroline: false
        },
        yaxis: {
          title: "Correlation",
          range: [0, 1],
          tickvals: [0, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1].map(correlationAxisValue),
          ticktext: ["0.0", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0"],
          gridcolor: "#dfe6e3",
          zeroline: false
        },
        legend: { orientation: "h", x: 1, xanchor: "right", y: 1.24 },
        hoverlabel: { bgcolor: "#1c2928", font: { color: "#fff" } }
      };
      overviewMetrics = metrics;
      const rendered = Plotly.react(chart, traces, layout, { responsive: true, displaylogo: false });
      const includedPairs = selectedMeanScores();
      const subsetCount = new Set(includedPairs.map(row => row.subset)).size;
      const methodCount = new Set(includedPairs.map(row =>
        JSON.stringify([row.subset, row.method_group])
      )).size;
      const stimulusCount = includedPairs.length;
      document.getElementById("overview-status").textContent =
        `${metrics.filter(metric => metric !== "rho-perfect").length} metrics · ${state.lockedOrder ? "order locked" : `${sortSeries.name} low to high`} · ${selectedScope()} · ${state.aggregation} · ${state.includeAnchors ? "anchors included" : "anchors excluded"}\n${subsetCount} subsets · ${methodCount} subset-method groups · ${stimulusCount} stimuli`;
      updateMeanScoreHistogram();
      return rendered;
    }

    // Metrics negated so that higher is better are shown as "−Name" where values are shown.
    function displayName(metric) {
      return DATA.negated_metrics.includes(metric) ? `−${metric}` : metric;
    }

    // "#rrggbb" with an alpha channel, for dimmed traces.
    function withAlpha(hex, alpha) {
      const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    // Comparison selection: type a metric name to add it; click its chip to remove it.
    const compareInput = document.getElementById("compare-input");
    function renderCompare() {
      document.getElementById("compare-options").replaceChildren(...DATA.metrics
        .filter(metric => metric !== "rho-perfect" && !state.compare.has(metric))
        .map(metric => Object.assign(document.createElement("option"), { value: metric })));
      document.getElementById("compare-chips").replaceChildren(...[...state.compare].map(metric => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "compare-chip";
        chip.textContent = `${metric} ×`;
        chip.title = `Deselect ${metric}`;
        chip.addEventListener("click", () => {
          state.compare.delete(metric);
          renderCompare();
          updateOverview();
        });
        return chip;
      }));
    }
    // A metric is added only on an explicit choice, never while typing (so typing "PESQ" does not
    // add PESQ before "PESQc2" is complete): picking a suggestion, or Enter. Enter takes the exact
    // name or, failing that, the only metric containing the typed text.
    function addTypedMetric(allowPartial) {
      const typed = compareInput.value.trim().toLowerCase();
      const candidates = DATA.metrics.filter(name => name !== "rho-perfect" && !state.compare.has(name));
      const metric = candidates.find(name => name.toLowerCase() === typed) ??
        (allowPartial && typed ? candidates.filter(name => name.toLowerCase().includes(typed)) : [])
          .reduce((only, name, index, all) => all.length === 1 ? name : only, undefined);
      if (!metric) return;
      state.compare.add(metric);
      compareInput.value = "";
      renderCompare();
      updateOverview();
    }
    compareInput.addEventListener("input", event => {
      // Typing fires "insertText"/"deleteContent..."; picking a datalist suggestion does not.
      if (DATA && !/^(insert(Text|CompositionText)|delete)/.test(event.inputType ?? "")) addTypedMetric(false);
    });
    compareInput.addEventListener("keydown", event => {
      if (event.key === "Enter" && DATA) addTypedMetric(true);
    });

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
      })[character]);
    }

    // Decode _pack_table() output: dictionary-encoded columns hold indices into table.dictionaries.
    function unpackTable(table) {
      const decoders = table.columns.map(column => table.dictionaries[column]);
      return table.rows.map(values => Object.fromEntries(
        table.columns.map((column, index) =>
          [column, decoders[index] ? decoders[index][values[index]] : values[index]])));
    }

    async function loadDetailData(metric) {
      if (detailData.has(metric)) return detailData.get(metric);
      if (!detailDataRequests.has(metric)) {
        const path = DATA.detail_files[metric];
        const request = fetch(new URL(path, document.baseURI))
          .then(response => {
            if (!response.ok) throw new Error(`Could not load ${path} (${response.status})`);
            return response.json();
          })
          .then(data => {
            const unpacked = { groups: unpackTable(data.groups), pairs: unpackTable(data.pairs) };
            detailData.set(metric, unpacked);
            return unpacked;
          })
          .catch(error => {
            detailDataRequests.delete(metric);
            throw error;
          });
        detailDataRequests.set(metric, request);
      }
      return detailDataRequests.get(metric);
    }

    async function openDetail(metric) {
      state.metric = metric;
      detail.hidden = false;
      document.getElementById("detail-title").textContent = `${metric} / detail`;
      const source = document.getElementById("detail-source");
      const sourceUrl = DATA.metric_sources?.[metric];
      source.hidden = !sourceUrl;
      const sourceLink = source.querySelector("a");
      sourceLink.href = sourceUrl ?? "";
      sourceLink.textContent = sourceUrl ? sourceUrl.replace(/^https?:\/\//, "") : "";
      detail.scrollIntoView({ behavior: "smooth", block: "start" });
      if (!detailData.has(metric)) {
        document.getElementById("method-chart").hidden = true;
        document.getElementById("method-chart-empty").textContent = "Loading detail data…";
        document.getElementById("method-chart-empty").hidden = false;
        document.getElementById("pair-chart").hidden = true;
        document.getElementById("pair-empty").textContent = "Loading detail data…";
        document.getElementById("pair-empty").hidden = false;
        try {
          await loadDetailData(metric);
        } catch (error) {
          console.error(error);
          if (state.metric !== metric) return;
          document.getElementById("method-chart-empty").textContent = "Detail data could not be loaded.";
          document.getElementById("pair-empty").textContent = "Detail data could not be loaded.";
          return;
        }
      }
      if (state.metric !== metric) return;
      renderDetail();
    }

    function renderMethodChart(groups) {
      const methodChart = document.getElementById("method-chart");
      const empty = document.getElementById("method-chart-empty");
      const rows = groups.filter(row =>
          ["pearson", "spearman", "kendall"].some(key => Number.isFinite(row[key])))
        .sort((left, right) => left.subset.localeCompare(right.subset) ||
          left.method_group.localeCompare(right.method_group));
      methodChart.hidden = rows.length === 0;
      empty.hidden = rows.length > 0;
      empty.textContent = "No method-group correlations for these filters.";
      if (!rows.length) return;
      const subsetBands = [];
      rows.forEach((row, index) => {
        const previous = subsetBands[subsetBands.length - 1];
        if (previous?.subset === row.subset) previous.end = index;
        else subsetBands.push({ subset: row.subset, start: index, end: index });
      });
      const slotWidth = Math.max(85, ...subsetBands.map(band =>
        (band.subset.length * 7 + 24) / (band.end - band.start + 1)));
      methodChart.style.minWidth = `${Math.max(360, rows.length * slotWidth + 82)}px`;
      const shapes = subsetBands.map(band => ({
        type: "rect", xref: "x", yref: "paper",
        x0: band.start - 0.5, x1: band.end + 0.5, y0: 0, y1: 1,
        fillcolor: subsetColors.get(band.subset), opacity: 0.07,
        line: { width: 0 }, layer: "below"
      }));
      shapes.push(...subsetBands.slice(1).map(band => ({
        type: "line", xref: "x", yref: "paper",
        x0: band.start - 0.5, x1: band.start - 0.5, y0: 0, y1: 1,
        line: { color: "#aab9b5", width: 1, dash: "dot" }
      })));
      const compactLabels = methodChart.parentElement.clientWidth < 500;
      const annotations = subsetBands.map(band => ({
        x: compactLabels ? band.start - 0.4 : (band.start + band.end) / 2,
        y: 1.06, xref: "x", yref: "paper",
        text: escapeHtml(band.subset), showarrow: false,
        xanchor: compactLabels ? "left" : "center",
        yanchor: "bottom", font: { size: 12, color: "#1c2928" }
      }));
      const series = [
        { key: "pearson", name: correlationNames.pearson, symbol: "x", color: "#247ab5", offset: -0.2 },
        { key: "spearman", name: correlationNames.spearman, symbol: "square", color: "#df7624", offset: 0 },
        { key: "kendall", name: correlationNames.kendall, symbol: "diamond", color: "#087f78", offset: 0.2 }
      ];
      const traces = series.map(seriesItem => {
        const points = rows.map((row, index) => ({ row, index }))
          .filter(point => Number.isFinite(point.row[seriesItem.key]));
        return {
          type: "scatter", mode: "markers", name: seriesItem.name,
          x: points.map(point => point.index + seriesItem.offset),
          y: points.map(point => point.row[seriesItem.key]),
          customdata: points.map(point => [point.row.subset, point.row.method_group, point.row.N]),
          marker: { color: seriesItem.color, symbol: seriesItem.symbol, size: 10 },
          hovertemplate: "<b>%{customdata[1]}</b><br>Subset: %{customdata[0]}<br>N: %{customdata[2]}" +
            `<br>${seriesItem.name}: %{y:.3f}<extra></extra>`
        };
      }).filter(trace => trace.y.length > 0);
      Plotly.react(methodChart, traces, {
        autosize: true,
        margin: { l: 62, r: 20, t: 95, b: 130 },
        shapes, annotations,
        paper_bgcolor: "#fff", plot_bgcolor: "#fff",
        font: { family: "Avenir Next, Avenir, Segoe UI, sans-serif", color: "#1c2928" },
        xaxis: {
          title: { text: "Processing method", standoff: 18 },
          tickmode: "array", tickvals: rows.map((_, index) => index),
          ticktext: rows.map(row => row.method_group), tickangle: -45,
          range: [-0.6, rows.length - 0.4], fixedrange: true, gridcolor: "#edf1ef", zeroline: false
        },
        yaxis: { title: "Correlation", range: [-1, 1], dtick: 0.2, gridcolor: "#edf1ef" },
        legend: { orientation: "h", x: 0, xanchor: "left", y: 1.35 },
        hoverlabel: { bgcolor: "#1c2928", font: { color: "#fff" } }
      }, { responsive: true, displaylogo: false });
    }

    // Per-group correlations of a metric for the current filters ([] until its detail file is loaded).
    function selectedGroups(metric) {
      const contentTypeKey = JSON.stringify([...state.contentTypes].sort());
      return (detailData.get(metric)?.groups ?? []).filter(row =>
        row.scope === "all" &&
        row.agg_method === state.aggregation &&
        row.include_anchors === state.includeAnchors &&
        state.subsets.has(row.subset) &&
        JSON.stringify(row.content_type_filter) === contentTypeKey
      );
    }

    // Extra hover lines in the overview: the highest and lowest subset-method group (macro),
    // or the 95% interval (micro).
    function hoverDetails(metric, item, row) {
      if (state.aggregation === "micro") {
        const low = row[item.key] - row[item.errorMinus], high = row[item.key] + row[item.errorPlus];
        return Number.isFinite(low) && Number.isFinite(high)
          ? `<br>95% interval: ${low.toFixed(3)} – ${high.toFixed(3)}` : "";
      }
      const groups = selectedGroups(metric).filter(group => Number.isFinite(group[item.key]))
        .sort((left, right) => right[item.key] - left[item.key]);
      if (!groups.length) return "";
      const describe = group => `${escapeHtml(group.subset)} / ${escapeHtml(group.method_group)} (${group[item.key].toFixed(3)})`;
      return `<br>Highest: ${describe(groups[0])}<br>Lowest: ${describe(groups[groups.length - 1])}`;
    }

    function renderDetail() {
      const metric = state.metric;
      if (!metric || !detailData.has(metric)) return;
      const groups = selectedGroups(metric);
      renderMethodChart(groups);

      const pairs = selectedPairs(metric);
      const pairEmpty = document.getElementById("pair-empty");
      // Stored correlations shown above the scatter: the aggregate for the current filters
      // (as in the overview) and each method group's own values (as in the method chart).
      pairCorrelationTexts = pairs.length ? {
        all: correlationText(selectedAggregates().find(row => row.metric === metric),
          state.aggregation === "macro" ? "Macro (averaged over method groups)" : "Micro (pooled stimuli)"),
        groups: new Map(groups.map(row => [`${row.subset} / ${row.method_group}`,
          correlationText(row, `${row.subset} / ${row.method_group}`)]))
      } : null;
      if (!pairs.length) {
        pairChart.hidden = true;
        pairEmpty.hidden = false;
        pairEmpty.textContent = metric === "rho-perfect"
          ? "Not available"
          : "No pair-level results for these filters.";
        updatePairCorrelations();
        return;
      }
      pairChart.hidden = false;
      pairEmpty.hidden = true;
      const grouped = new Map();
      for (const row of pairs) {
        const key = `${row.subset} / ${row.method_group}`;
        if (!grouped.has(key)) grouped.set(key, []);
        grouped.get(key).push(row);
      }
      const traces = Array.from(grouped, ([name, rows], index) => ({
        type: "scattergl",
        mode: "markers",
        name,
        x: rows.map(row => row.obj_score),
        y: rows.map(row => row.mean_score),
        customdata: rows.map(row => [row.subset, row.method_group, row.item, row.condition]),
        marker: { color: palette[index % palette.length], size: 7, opacity: 0.68 },
        hovertemplate: "<b>%{customdata[2]}</b><br>Subset: %{customdata[0]}<br>Method: %{customdata[1]}" +
          "<br>Condition: %{customdata[3]}<br>Objective: %{x:.3f}<br>Listener mean: %{y:.2f}<extra></extra>"
      }));
      const narrow = pairChart.clientWidth < 700;
      const legendHeight = traces.length * 22 + 12;
      pairChart.style.height = `${narrow ? 360 + legendHeight : Math.max(430, legendHeight + 70)}px`;
      Plotly.react(pairChart, traces, {
        autosize: true,
        margin: { l: 64, r: narrow ? 20 : 330, t: 12, b: narrow ? legendHeight + 85 : 54, autoexpand: false },
        paper_bgcolor: "#fff",
        plot_bgcolor: "#fff",
        font: { family: "Avenir Next, Avenir, Segoe UI, sans-serif", color: "#1c2928" },
        xaxis: { title: `Objective score (${escapeHtml(displayName(metric))})`, gridcolor: "#edf1ef" },
        yaxis: { title: { text: "Mean listener score", standoff: 16 }, gridcolor: "#edf1ef" },
        legend: narrow
          ? { orientation: "v", xref: "container", x: 0, xanchor: "left", y: -0.25, yanchor: "top" }
          : { orientation: "v", x: 1.02, xanchor: "left", y: 1, yanchor: "top" },
        hoverlabel: { bgcolor: "#1c2928", font: { color: "#fff" } }
      }, { responsive: true, displaylogo: false });
      updatePairCorrelations();
      if (!pairChart.dataset.listening) {
        pairChart.on("plotly_restyle", updatePairCorrelations);
        pairChart.dataset.listening = "true";
      }
    }

    // "<label>: Pearson 0.826 · Spearman 0.799 · ..." from a row with correlation columns, or null.
    function correlationText(row, label) {
      const values = Object.entries(correlationNames)
        .filter(([key]) => Number.isFinite(row?.[key]))
        .map(([key, name]) => `${name} ${row[key].toFixed(3)}`);
      return values.length ? `${label}: ${values.join(" · ")}` : null;
    }

    // Correlations are stored for all method groups together and for each group alone.
    // Hiding groups in the legend can leave another combination, without stored values:
    // then the line is hidden.
    function updatePairCorrelations() {
      const shown = (pairChart.data ?? []).filter(trace =>
        trace.visible === undefined || trace.visible === true);
      let text = null;
      if (pairCorrelationTexts && shown.length === pairChart.data.length) {
        text = pairCorrelationTexts.all;
      } else if (pairCorrelationTexts && shown.length === 1) {
        text = pairCorrelationTexts.groups.get(shown[0].name) ?? null;
      }
      pairCorrelations.textContent = text ?? "";
      pairCorrelations.hidden = text === null;
    }

    document.querySelectorAll("[data-control]").forEach(group => {
      group.addEventListener("click", event => {
        const button = event.target.closest("button[data-value]");
        if (!button || !DATA) return;
        if (group.dataset.control === "scope") {
          // Shortcut on the subset selection: switch all subsets of this spatial focus off or on.
          const ofScope = DATA.subsets.filter(subset => DATA.subset_spatial[subset] === button.dataset.value);
          const turnOff = button.getAttribute("aria-pressed") === "true";
          ofScope.forEach(subset => turnOff ? state.subsets.delete(subset) : state.subsets.add(subset));
          updateSubsetOptions();
        } else if (["subsets", "content-types", "reference-types"].includes(group.dataset.control)) {
          const selected = {
            subsets: state.subsets,
            "content-types": state.contentTypes,
            "reference-types": state.referenceTypes
          }[group.dataset.control];
          if (selected.has(button.dataset.value)) {
            selected.delete(button.dataset.value);
          } else {
            selected.add(button.dataset.value);
          }
          button.setAttribute("aria-pressed", String(selected.has(button.dataset.value)));
          if (group.dataset.control === "subsets") {
            updateScopeButtons();
            updateContentTypeAvailability();
          }
        } else if (group.dataset.control === "anchors") {
          state.includeAnchors = button.dataset.value === "true";
          group.querySelectorAll("button").forEach(option =>
            option.setAttribute("aria-pressed", String(option === button)));
        } else {
          state[group.dataset.control] = button.dataset.value;
          group.querySelectorAll("button").forEach(option =>
            option.setAttribute("aria-pressed", String(option === button)));
        }
        updateOverview();
        renderDetail();
      });
    });
    document.getElementById("back-button").addEventListener("click", () => {
      detail.hidden = true;
      state.metric = null;
      chart.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    async function initializePage() {
      try {
        const response = await fetch(new URL("analysis.json", document.baseURI));
        if (!response.ok) throw new Error(`Could not load analysis.json (${response.status})`);
        DATA = await response.json();
        DATA.aggregates = unpackTable(DATA.aggregates);
        DATA.mean_scores = unpackTable(DATA.mean_scores);
        state.subsets = new Set(DATA.subsets);
        state.contentTypes = new Set(DATA.content_types);
        renderCompare();
        subsetColors = new Map(DATA.subsets.map((subset, index) =>
          [subset, palette[index % palette.length]]));
        metricColors = new Map(Object.entries(DATA.metric_colors ?? {}));
        updateSubsetOptions();
        initializeMultiSelectOptions("content-type-options", DATA.content_types, state.contentTypes);
        updateContentTypeAvailability();
        await updateOverview();
        // Load every metric's detail file in the background for the hover's highest/lowest groups.
        Promise.all(DATA.metrics.map(metric => loadDetailData(metric).catch(() => null)))
          .then(() => updateOverview());
        chart.on("plotly_click", event => {
          const point = event.points[0];
          const metric = point?.customdata?.[2];
          if (metric) openDetail(metric);
        });
        // Handle legend toggles ourselves so the metric order follows the visible series.
        chart.on("plotly_legendclick", event => {
          const name = event.data[event.curveNumber].name;
          if (!state.hiddenSeries.delete(name)) state.hiddenSeries.add(name);
          updateOverview();
          return false;
        });
        chart.on("plotly_legenddoubleclick", () => false);
        chart.addEventListener("click", event => {
          const tick = event.target.closest(".xtick");
          if (!tick) return;
          const tickIndex = Math.round(tick.__data__?.x ?? NaN);
          const metric = overviewMetrics[tickIndex];
          if (metric) openDetail(metric);
        });
      } catch (error) {
        console.error(error);
        document.getElementById("overview-status").textContent =
          "Analysis data could not be loaded. Open this page over HTTP.";
      }
    }

    initializePage();
  </script>
</body>
</html>
'''


def _json_safe(value: Any) -> Any:
  if isinstance(value, dict):
    return {key: _json_safe(item) for key, item in value.items()}
  if isinstance(value, (list, tuple)):
    return [_json_safe(item) for item in value]
  if isinstance(value, np.generic):
    return _json_safe(value.item())
  if isinstance(value, float) and not np.isfinite(value):
    return None
  return value


def _website_payload(records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
  """Partition full-precision records for the compact website exporter."""
  pair_rows = [row for row in records if row["record_type"] == "pair"]
  aggregates = [row for row in records if row.get("result_type") == "aggregate"]
  groups = [row for row in records if row.get("result_type") == "method_group"]
  subset_spatial = {}
  subset_content_types: dict[str, set[str]] = {}
  mean_scores = {}
  for row in pair_rows:
    subset_spatial.setdefault(row["subset"], row["spatial"])
    subset_content_types.setdefault(row["subset"], set()).add(row["content_type"])
    key = (row["subset"], row["method_group"], row["item"], row["condition"])
    mean_scores.setdefault(key, {
      field: row[field] for field in (
        "subset", "spatial", "method_group", "content_type", "is_anchor", "mean_score",
      )
    })
  overview = {
    "metrics": sorted({row["metric"] for row in aggregates}),
    "subsets": sorted(subset_spatial),
    "subset_spatial": subset_spatial,
    "subset_content_types": {
      subset: sorted(types) for subset, types in subset_content_types.items()
    },
    "content_types": sorted({row["content_type"] for row in pair_rows}),
    "mean_scores": list(mean_scores.values()),
    "aggregates": aggregates,
  }
  return _json_safe(overview), _json_safe({"groups": groups, "pairs": pair_rows})


def _srgb_channels_linear(hex_color: str) -> list[float]:
  channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
  return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]


def _oklab(hex_color: str) -> tuple[float, float, float]:
  r, g, b = _srgb_channels_linear(hex_color)
  l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
  m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
  s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
  return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
          1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
          0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _contrast_on_white(hex_color: str) -> float:
  r, g, b = _srgb_channels_linear(hex_color)
  return 1.05 / (0.2126 * r + 0.7152 * g + 0.0722 * b + 0.05)


def _distinct_text_colors(count: int, min_contrast: float = 4.5) -> list[str]:
  """Generate `count` text colors readable on white and maximally separated in OKLab.

  Greedy farthest-point selection from a fixed candidate grid, so the result is
  deterministic and prefix-stable: the first k colors never depend on `count`.
  """
  import colorsys
  import math

  candidates = ["#1c2928"]  # page ink
  for hue in range(0, 360, 4):
    for lightness in (0.22, 0.28, 0.34, 0.40):
      for saturation in (0.6, 0.9):
        rgb = colorsys.hls_to_rgb(hue / 360, lightness, saturation)
        color = "#" + "".join(f"{round(channel * 255):02x}" for channel in rgb)
        if _contrast_on_white(color) >= min_contrast:
          candidates.append(color)
  points = {color: _oklab(color) for color in candidates}
  chosen = ["#1d5fb4"]  # first metric gets the page's blue
  points[chosen[0]] = _oklab(chosen[0])
  nearest = {color: math.dist(point, points[chosen[0]]) for color, point in points.items()}
  while len(chosen) < count:
    color = max(candidates, key=lambda candidate: (nearest[candidate], candidate))
    chosen.append(color)
    for candidate in candidates:
      nearest[candidate] = min(nearest[candidate], math.dist(points[candidate], points[color]))
  return chosen[:count]


def _metric_colors(metrics: list[str], registry_order: list[str]) -> dict[str, str]:
  """Assign label colors over the whole registry order, so a metric's color does not change
  when other metrics are run, skipped, or appended to the registry."""
  ordered = list(registry_order) + sorted(set(metrics) - set(registry_order))
  colors = dict(zip(ordered, _distinct_text_colors(len(ordered))))
  return {metric: colors[metric] for metric in metrics}


def _subset_reference_rows(path: Path = SUBSET_REFERENCES) -> str:
  """Render the "About the subsets" table rows from the references CSV.

  The CSV is ";"-separated, one row per paper (columns: subset, summary, reference, url;
  url may be empty). Papers of the same subset are grouped into one table row, in file
  order; the subset's summary is taken from its first row with one.
  """
  papers: dict[str, list[str]] = {}
  summaries: dict[str, str] = {}
  with path.open(newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f, delimiter=";"):
      if row["summary"].strip():
        summaries.setdefault(row["subset"], row["summary"].strip())
      text = html.escape(row["reference"])
      url = row["url"].strip()
      if url:
        # arXiv links are shown as "arXiv:<id>", anything else as the bare URL.
        label = "arXiv:" + url.rsplit("/", 1)[-1] if "arxiv.org/abs/" in url else url
        text += f' (<a href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(label)}</a>)'
      papers.setdefault(row["subset"], []).append(f"<p>{text}</p>")
  return "\n".join(
    f"              <tr><td>{html.escape(subset)}</td><td>{html.escape(summaries.get(subset, ''))}</td>"
    f"<td>{''.join(items)}</td></tr>"
    for subset, items in papers.items()
  )


def _build_page() -> str:
  """Render the HTML shell for the static dashboard (no analysis data is embedded)."""
  return PAGE_TEMPLATE.replace("<!-- SUBSET_REFERENCE_ROWS -->", _subset_reference_rows())


def _is_number(value: Any) -> bool:
  return isinstance(value, (int, float)) and not isinstance(value, bool)


def _pack_table(rows: list[dict[str, Any]], columns: list[str]) -> dict[str, Any]:
  """Keep only displayed fields, with column names shared across all rows.

  Non-numeric columns (labels, flags, filter lists) repeat a few values over many rows,
  so they are dictionary-encoded: each distinct value is stored once in
  "dictionaries"[column] and rows hold its index. unpackTable() in the page decodes them.
  """
  table = [[float(format(row[column], ".6g")) if isinstance(row.get(column), float)
            else row.get(column) for column in columns] for row in rows]
  dictionaries = {}
  for index, column in enumerate(columns):
    if any(_is_number(values[index]) for values in table):
      continue
    lookup: dict[str, int] = {}
    for values in table:
      # JSON text as key, since filter lists are not hashable.
      key = json.dumps(values[index])
      values[index] = lookup.setdefault(key, len(lookup))
    dictionaries[column] = [json.loads(key) for key in lookup]
  return {"columns": columns, "dictionaries": dictionaries, "rows": table}


def _write_json(path: Path, data: dict[str, Any]) -> None:
  path.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False), encoding="utf-8")


def export_website_data(records: list[dict[str, Any]], output_dir: Path = ROOT / "docs") -> None:
  """Write compact website JSON from evaluation's in-memory records."""
  analysis, details = _website_payload(records)
  analysis_path = output_dir / "analysis.json"
  output_dir.mkdir(parents=True, exist_ok=True)
  data_dir = output_dir / "data"
  data_dir.mkdir(exist_ok=True)
  from evaluate import CORRELATION_TYPES
  # The aggregates hold every filter combination, so they dominate the file size:
  # drop rows without any value (the page skips them) and keep 4 decimals (it shows 3).
  correlation_columns = [
    *CORRELATION_TYPES,
    *(f"{corr_type}_{error}" for corr_type in CORRELATION_TYPES
      for error in ("error_plus", "error_minus")),
  ]
  aggregates = [
    {**row, **{column: None if row.get(column) is None else round(row[column], 4)
               for column in correlation_columns}}
    for row in analysis["aggregates"]
    if any(row.get(column) is not None for column in correlation_columns)
  ]
  analysis["aggregates"] = _pack_table(aggregates, [
    "metric", "scope", "agg_method", "include_anchors", "subset_filter",
    "content_type_filter", *correlation_columns,
  ])
  analysis["mean_scores"] = _pack_table(analysis["mean_scores"], [
    "subset", "method_group", "content_type", "spatial", "is_anchor", "mean_score",
  ])
  from metrics_registry import METRIC_REFERENCE_TYPES, METRIC_SOURCES, NEGATED_METRICS
  analysis["metric_sources"] = {metric: METRIC_SOURCES[metric] for metric in analysis["metrics"]}
  analysis["negated_metrics"] = sorted(NEGATED_METRICS & set(analysis["metrics"]))
  # Every metric must declare its reference type (KeyError otherwise); rho-perfect is not a metric.
  analysis["metric_reference_types"] = {
    metric: METRIC_REFERENCE_TYPES[metric] for metric in analysis["metrics"] if metric != "rho-perfect"
  }
  analysis["metric_colors"] = _metric_colors(analysis["metrics"], list(METRIC_SOURCES))
  analysis["detail_files"] = {}
  for metric in analysis["metrics"]:
    filename = f"{metric}.json"
    analysis["detail_files"][metric] = f"./data/{filename}"
    _write_json(data_dir / filename, {
      "groups": _pack_table([row for row in details["groups"] if row["metric"] == metric], [
        "scope", "agg_method", "include_anchors", "subset", "method_group",
        "content_type_filter", "N", *CORRELATION_TYPES,
      ]),
      "pairs": _pack_table([row for row in details["pairs"] if row["metric"] == metric], [
        "metric", "subset", "method_group", "item", "condition", "content_type",
        "spatial", "is_anchor", "obj_score", "mean_score",
      ]),
    })
  _write_json(analysis_path, analysis)
  print(f"Exported {analysis_path} and {len(analysis['metrics'])} metric files in {data_dir}")


def _main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
    "--output", type=Path, default=ROOT / "docs" / "index.html",
    help="HTML output path for GitHub Pages",
  )
  args = parser.parse_args()
  try:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(_build_page(), encoding="utf-8")
  except (OSError, ValueError) as error:
    parser.error(str(error))
  print(f"Built {args.output}; analysis data unchanged")


if __name__ == "__main__":
    _main()
