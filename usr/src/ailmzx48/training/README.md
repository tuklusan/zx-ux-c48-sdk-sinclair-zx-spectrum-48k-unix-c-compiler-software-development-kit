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

`provenance.json` schema 3 identifies non-generated factual authorities, their
immutable/license or project-authorization basis, dependent record indexes and
normalized-output hashes.  Synthetic generated material is admitted only for
style and is forbidden as factual authority.  `record-lineage.json` gives one
content-addressed lineage entry for every seed record.  Repository and upstream
prose/source remain excluded unless separately authorized; design authority is
not silently treated as corpus permission.  `goal-status.json` remains historical
convergence evidence; later release repairs are requalified against the current
source/binary/model identities in `evaluation/sdk-conformance/`.
