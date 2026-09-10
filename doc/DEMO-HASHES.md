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
# Deterministic Demo Hashes - Pre-1.0 SDK

These hashes are release invariants verified by `compiler/verify_release.py`. Each demo is rebuilt from source, executed from the rebuilt C48B1, and required to produce the exact 6912-byte Spectrum screen hash below.

`argv` is executed with arguments `alpha beta gamma`; the runtime program token during verification is the deterministic basename `<demo>.c48b`.

| Demo | Source SHA-256 | C48B1 SHA-256 | Screen SHA-256 |
|---|---|---|---|
| `hello` | `bc22ea1b7f63cd89678402ed6f1089423dc4685e1195d6144fceeab3d99c1387` | `4dfbcdb0bc821a94054ef468f5ebe32e59e05e34e6e203284cce6ddceb842665` | `20e491b86cb68ca65eef144c760feaef80995242b258dc2421beda30a68a69f9` |
| `colors` | `abc01331d700471fbd4000f446c53dd49255d5c4f744e5edc05f14b5da023471` | `5e9411e2b3f818017373ba389039c169a5d757f913df045443e15410c7eefab4` | `82687c81ba0208c728b1a4643f03b67745b947a39cd252929f4b383d9fba6d55` |
| `graphics` | `866689771ea1df6ca718f759e49b013f76cf6a27bd184f646ac05276b3f4d09d` | `5d667ab8c3841d91cd97eb4ddd82389c98568dc23bbd979607af4fe7ce4c12ac` | `d2611838b3071ed7e658178d38a7bdd11a0d7fdf2aeffbb15bd65803a878053c` |
| `udg` | `38aafd04c42c1211868821b6678a8d0f3a8fbb46295a1d52812d73c70fc469cb` | `e6a33f15c8b0990d0c1dab06fddaa38ffdb431dff98f8cf05243dc7e124ffc23` | `297ef51aa92911f090027668d02bc5bd92eac82c72678a708cc9a1097b13081c` |
| `maze` | `46699d3d0a66843b40f0115eed046ac1e06c0e5df3e610ec77c84690b04cbd78` | `635375320159a6c44079d5066ad91d8f8c7f3189614271661e41cabf71389562` | `ca337377f9e1073e895d6ad9240072c37577e6dd16d8c3cd43620c0bec1c2335` |
| `argv` | `80bf3dd767d45cd70a5bc134075fd575b849e5fc3c317c6b1fb6819c6c9ced27` | `f9e33f5d72c69a637daf1c863f343095c36df239a3ad4c048f61b5af87f677ea` | `c5fdbdb1e1ee4eeca9df25cf07f2d8747ad9c622befaf9a176398329fa962898` |

Host Game API header SHA-256:

`7c4e883ecb6a2176b06c0dca86ea044142ebf9ea7a6dc9d9f0e93e7fb9861a82`

Default Tasword F4X8 SHA-256:

`90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339`

Alternate ZX-UX F4X8 SHA-256:

`90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339`

In this revision the two supplied F4X8 assets are byte-identical; they are kept under distinct names so either slot can evolve independently while `c48run --font PATH` remains stable.
