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
# Deterministic Demo and Security-Fixture Hashes - 1.0.0 Host SDK

These hashes are release invariants verified by `compiler/verify_release.py`. Each ordinary demo is rebuilt from source, executed from the rebuilt C48B1, and required to produce the exact 6912-byte Spectrum screen hash below. Security fixtures are also rebuilt byte-for-byte; their runtime mitigation behavior is asserted by `compiler/tests/test_security.py`.

`argv` is executed with arguments `alpha beta gamma`; the runtime program token during verification is the deterministic basename `<demo>.c48b`.

| Demo | Source SHA-256 | C48B1 SHA-256 | Screen SHA-256 |
|---|---|---|---|
| `hello` | `314c973f97449348fcafe02d27b8df3f91ecdd41665a2cf2d7baffcb4c5ba7e3` | `529d3d85c8558511057f92d07137db800fa69fb0b357434a83cd36b28637fabe` | `20e491b86cb68ca65eef144c760feaef80995242b258dc2421beda30a68a69f9` |
| `colors` | `de7525ddfda166c060884b949cb022d346ffc3f04fd031b6122523c2a9c12262` | `a1e42b6aca33881a0d2daf3fc2920049081bf3c70d63bfe5ecabfcda48a666d0` | `9852ec86a5fa7a35b1761295933078dcb5b8a3d7f81c1e45a75f1d4aa39f3b25` |
| `graphics` | `1981324b45387acd98e9be80e6800d97e8ccd9937f6af31715b370da0fc4c3e7` | `f28447b9592a260ee06beb6b47ef823e527874ffcbae1521c6608f75ac312fde` | `d2611838b3071ed7e658178d38a7bdd11a0d7fdf2aeffbb15bd65803a878053c` |
| `udg` | `dd15548be86d79b48ca8c5d9d0d87a1425236ccff7e548ef32952eaa031ffeff` | `2fe398f3a58ea4ccfe43533beada9b925526901f43c7e706d8a2d0390836558f` | `297ef51aa92911f090027668d02bc5bd92eac82c72678a708cc9a1097b13081c` |
| `maze` | `982ef55dc51dbaf3566efb5f9af98f98729138c53df8a837b7d435f0b0016ddb` | `21a8b006f0ce6a02fd1bbbef2b8a6499507af54188cccd9a5f3cc870da956a90` | `ca337377f9e1073e895d6ad9240072c37577e6dd16d8c3cd43620c0bec1c2335` |
| `argv` | `3f5a39220fb2ef64c3957a166bbd3c7e7de8930029433d00c90f64bdd59e3aee` | `12323dbcd9f664dfacc1597517ba295d34e61c4d5a1a22d49a64f631e5177cef` | `8e6dc907df2046e99dd165662459f469f0ee6f1d5f100c55f75b3ec627b9776a` |

## Security fixture binaries

These C48 programs visibly announce the attempted attack and expected mitigation on the emulated 64-column Spectrum screen before exercising the guard. `seckern.c` is intentionally compile-negative and therefore has no C48B1 binary.

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

`tune.c` exercises the architecture-frozen synchronous `beep(float duration,
float pitch)` API, including a fractional pitch. `compiler/verify_beep.py`
proves ROM-derived waveform frequency/duration and blocking wall time.

| Fixture | Source SHA-256 | C48B1 SHA-256 |
|---|---|---|
| `tune` | `fb8d7f320ef1421c6eb895ed77dc935d35b5edbfccf4ea2e562aabcacea03f51` | `88bb88069d5efa0d357f114ad30ccc67f52c21aefd03f0a81dab74cf54b73211` |

Host Game API header SHA-256:

`04bf2a02afd7b022e63d92ebadab08527821eb8148e2a82cd43cd616efd20114`

Default Tasword F4X8 SHA-256:

`90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339`

Alternate ZX-UX F4X8 SHA-256:

`90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339`

In this revision the two supplied F4X8 assets are byte-identical; they are kept under distinct names so either slot can evolve independently while `c48run --font PATH` remains stable.
