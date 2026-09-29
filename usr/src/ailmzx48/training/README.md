<!--
ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com

SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
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

`evaluation-partitions.json` makes the evidence split explicit.  Training,
active nonblind development probes and inspected deterministic regressions are
separate from the reserved blind-candidate set.  The blind candidate is
unscored and is not used for tuning; the SDK profile therefore makes no blind
generalization claim.
