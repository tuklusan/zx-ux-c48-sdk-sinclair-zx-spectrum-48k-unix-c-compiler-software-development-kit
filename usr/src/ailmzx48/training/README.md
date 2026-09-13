<!--
============================================================================
Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
Proprietary rights reserved except as expressly licensed herein.

ZX-UX C48 SDK
This file is governed by the SANYALnet Labs Non-Commercial License in the
root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
for AI/ML model training are prohibited unless separately authorized.

Attribution is required: "Based on original work by Supratim Sanyal of
SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
patent, trademark, and governing-law provisions.
============================================================================
-->
# ailmzx48 training

This directory contains the admitted seed corpus, provenance/record-lineage
metadata, retained iteration requests, convergence criteria and final training
goal status.  Host construction is intentionally separate from shipped target
inference.  The retained training goal reached `GOALS_ACHIEVED` at iteration 54;
that token describes the training/convergence program, not native ZX-UX release
certification.

`provenance.json` identifies the admitted synthetic source classes and explicit
project authorization basis.  `record-lineage.json` gives one content-addressed
lineage entry for every seed record, including split and record hash.  Repository
and upstream prose/source remain excluded from model training unless separately
authorized; design-authority use is not silently treated as corpus permission.
