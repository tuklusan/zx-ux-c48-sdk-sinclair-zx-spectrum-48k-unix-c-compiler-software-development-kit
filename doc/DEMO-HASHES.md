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
# Deterministic Example and Security-Fixture Hashes - 1.0.0 Host SDK

These hashes are release invariants verified by `compiler/verify_release.py`.
The six ordinary examples live under `usr/src/examples/` with matching
`usr/bin/examples/` binaries. Each is rebuilt, executed from the rebuilt
C48B1, and required to produce the exact 6912-byte Spectrum screen hash below.
Security fixtures are rebuilt from `usr/src/security/` and checked against
`usr/bin/security/`; their mitigation behavior is asserted by the security tests.

`argv` is executed with arguments `alpha beta gamma`; the runtime program token
during verification is the deterministic basename `<example>.c48b`.

| Example | Source SHA-256 | C48B1 SHA-256 | Screen SHA-256 |
|---|---|---|---|
| `hello` | `6f94a735f230dadf5928993f9a071f3f47e98b63d18230eef102f6ae7b63e4b2` | `529d3d85c8558511057f92d07137db800fa69fb0b357434a83cd36b28637fabe` | `20e491b86cb68ca65eef144c760feaef80995242b258dc2421beda30a68a69f9` |
| `colors` | `79a7f14328bb40faef5d6b19569f58445a0e36eadc2ab3cf0d39b2465c529078` | `a1e42b6aca33881a0d2daf3fc2920049081bf3c70d63bfe5ecabfcda48a666d0` | `9852ec86a5fa7a35b1761295933078dcb5b8a3d7f81c1e45a75f1d4aa39f3b25` |
| `graphics` | `e287a917c92494641e2ff1a24129c91ef10603af6d44f8d813a2527c466139c8` | `f28447b9592a260ee06beb6b47ef823e527874ffcbae1521c6608f75ac312fde` | `d2611838b3071ed7e658178d38a7bdd11a0d7fdf2aeffbb15bd65803a878053c` |
| `udg` | `2df322a65cea578d494c810b3ab35f7213cffc35eff1606b48b8540f197fc7ee` | `2fe398f3a58ea4ccfe43533beada9b925526901f43c7e706d8a2d0390836558f` | `297ef51aa92911f090027668d02bc5bd92eac82c72678a708cc9a1097b13081c` |
| `maze` | `87306248074f554b71ac5a388875102ac1a152013eb2367e1af2a33e3660e7ba` | `21a8b006f0ce6a02fd1bbbef2b8a6499507af54188cccd9a5f3cc870da956a90` | `ca337377f9e1073e895d6ad9240072c37577e6dd16d8c3cd43620c0bec1c2335` |
| `argv` | `36060049da34bb1fdf91dcee325091ee9a54b6eddde3d1cf8ae4260a56af9ffb` | `12323dbcd9f664dfacc1597517ba295d34e61c4d5a1a22d49a64f631e5177cef` | `8e6dc907df2046e99dd165662459f469f0ee6f1d5f100c55f75b3ec627b9776a` |

## Security fixture binaries

The runnable fixtures announce the attempted attack and expected mitigation on the
emulated 64-column screen before exercising the guard. `seckern.c` is intentionally
compile-negative and therefore has no C48B1 binary.

| Fixture | C48B1 SHA-256 |
|---|---|
| `secguard` | `d6f03422dc9051ff3b8303a3211b3997bfb3ef63bb24e468061f51fbff2af3ae` |
| `secoob` | `1dcb4de8ea4c6421a2880df1677d46876ebf45808077a4c4fc2e465d1ddfa8c6` |
| `secuaf` | `0920a9767130d4367fd0c973e686e15fb1a4a2a0dafa4cb3b92a2faf4019b9f5` |
| `secfree` | `ebca254c7996b4cb101b4773d771b36df0409798a6275ae19ee6937ffac33a93` |
| `secdbl` | `37b006603de8ee2d72ed1186f08d8991973cb047f86a3abe645bb1d25ebe25bd` |
| `secloop` | `407ab56ecd3bb55b6421258ee2b6937ff3c17df4b7b3c0c8e06ea103676db1ed` |
| `secrecur` | `fb2f1e310a002c030cc16f581f116646b193990d2505fa155f95a802402cc27e` |
| `secforge` | `047d406771432b34adb30291a10b35a46c451ba9a741cddc20df4152809e24a0` |

## Sound fixture

`usr/src/sound/tune.c` exercises the architecture-frozen synchronous
`beep(float duration, float pitch)` API, including a fractional pitch. The
BEEP verifier proves ROM-derived waveform frequency/duration and blocking time.

| Fixture | Source SHA-256 | C48B1 SHA-256 |
|---|---|---|
| `tune` | `62273f41c03991658f34cdf7bfce7bda92f53a0d563a6d0951e7c501f4cd920c` | `bc3f178d1ae8210319b55b65ea47bb4007ed029cb3ebc544937a819d9736e333` |

## API header hashes

- shared `c48host.h`: `04bf2a02afd7b022e63d92ebadab08527821eb8148e2a82cd43cd616efd20114`
- examples `exapi.h`: `2fa0edc593832d3ab57bc105233f41fd81a02b1f3ea022cefc42da01a6084bb8`
- security `secapi.h`: `af17410d683bdf197cbd487aa87fa27833767523790bedf5bc50d1b2ee2a9f6b`
- sound `sndapi.h`: `4ba62701a6a454df5dc1c8cac44eced983eadada384fe71732c2ac3fb14f397d`

Default Tasword F4X8 SHA-256:

`90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339`

Alternate ZX-UX F4X8 SHA-256:

`90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339`

The two supplied F4X8 assets are currently byte-identical; distinct names keep
the runtime selection interface stable if either asset diverges later.
