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
# Adversarial security review test results

This ledger operationalizes, in source order, all 84 numbered attacks under
**Additional attacks I would run before rev-1.0** in
`ZX-UX C48 SDK Adversarial Security Review.docx`.

The executable implementation is `compiler/tests/test_security_review.py`.
Methods `test_001_...` through `test_084_...` preserve this exact sequence.
Runtime cases execute C48 programs; compiler cases compile hostile C48 source
bytes; C48B1 cases mutate canonical compiler output and recompute its digest.

A PASS means the attack reached its intended boundary and either completed
with the expected safe result or was rejected by a controlled C48 diagnostic
or resource limit. A Python traceback, assertion leak, hang, source corruption,
or uncontrolled host-resource path is a failure.

## Summary

- Review attacks incorporated: **84 / 84**.
- Security-review incorporation baseline: **291 tests** (207 prior + 84 new).
- Current 1.0.0 full unittest corpus: **338 tests**.
- Local full unittest corpus: **PASS, 338 tests**.
- Game build/play/human-I/O verifier: **PASS, 14 games**.
- Graphics-demo static verifier: **PASS, 21 demos**.
- Release-valid status additionally requires the repository CI matrix on
  Ubuntu x64, Windows x64, macOS arm64 and macOS Intel under Python 3.10 and
  Python 3.13 to pass on the containing commit.

The new corpus exposed real missing defenses in forged-C48B1 semantic
cross-checking/width limits and quoted-include symlink/reparse handling. Those
compiler defects were fixed before the rows below were marked PASS.

## Memory/provenance suite

| ID | Review attack | Regression | Result |
| --- | --- | --- | --- |
| MEM-01 | Pointer subtraction across distinct objects. | `test_001_mem_01_cross_object_pointer_subtraction` | PASS - runtime rejected subtraction across unrelated object provenance. |
| MEM-02 | Pointer comparisons across incompatible/different objects. | `test_002_mem_02_cross_object_and_incompatible_pointer_comparisons` | PASS - unrelated ordering trapped; incompatible typed equality was compile-rejected. |
| MEM-03 | Form a one-past pointer, decrement back, then dereference. | `test_003_mem_03_one_past_decrement_then_dereference` | PASS - one-past pointer moved back in-range and dereferenced correctly. |
| MEM-04 | Save pointer bytes through memcpy, free source allocation, reload copied pointer, dereference. | `test_004_mem_04_copied_pointer_bytes_stay_stale_after_free` | PASS - copied pointer provenance became stale after free and dereference trapped. |
| MEM-05 | Overwrite one byte of a stored pointer and ensure pointer shadow is invalidated. | `test_005_mem_05_byte_write_invalidates_pointer_shadow` | PASS - byte write invalidated pointer shadow; dereference could not regain provenance. |
| MEM-06 | Copy a pointer using partially overlapping memmove. | `test_006_mem_06_overlapping_memmove_preserves_pointer_provenance` | PASS - overlapping memmove preserved legitimate pointer provenance. |
| MEM-07 | Store pointer through char * byte writes and ensure provenance cannot be forged. | `test_007_mem_07_char_byte_writes_cannot_forge_provenance` | PASS - raw byte writes could not manufacture pointer provenance. |
| MEM-08 | Reallocate freed address, then dereference a stale pointer whose numeric address now matches the new object. | `test_008_mem_08_stale_pointer_traps_after_same_address_reuse` | PASS - stale pointer remained invalid after same-address reallocation. |
| MEM-09 | Verify allocation-ID generation prevents ABA-style stale-pointer resurrection. | `test_009_mem_09_allocation_ids_prevent_aba_resurrection` | PASS - new allocation ID prevented ABA stale-pointer resurrection. |
| MEM-10 | Heap exhaustion/reuse loops. | `test_010_mem_10_heap_exhaustion_and_reuse_loop` | PASS - repeated reuse stayed stable; exhaustion returned null; freed capacity was reusable. |
| MEM-11 | Zero-length memcpy, memmove, memset, memchr with null, one-past, dead, and invalid pointers. | `test_011_mem_11_zero_length_memory_builtins_touch_no_pointer` | PASS - zero-length memory builtins performed no access for null/one-past/dead/invalid pointers. |
| MEM-12 | strcpy destination exactly one byte short. | `test_012_mem_12_strcpy_destination_one_byte_short` | PASS - strcpy rejected the one-byte-short destination. |
| MEM-13 | strncpy source exactly at object end with n=0, n=1, and large n. | `test_013_mem_13_strncpy_at_source_end_n_zero_one_large` | PASS - n=0 touched no source; positive counts rejected a one-past source. |
| MEM-14 | Unterminated source strings in every string builtin. | `test_014_mem_14_unterminated_source_in_every_string_builtin` | PASS - all C48 string-reading builtins rejected unterminated object storage. |
| MEM-15 | Read-only string-literal aliases passed to write-capable memory builtins. | `test_015_mem_15_readonly_literal_aliases_reject_writes` | PASS - strcpy/strncpy/memcpy/memmove/memset rejected writes through literal aliases. |
| MEM-16 | Misaligned pointers formed through char-level address movement where the language permits it. | `test_016_mem_16_misaligned_pointer_from_char_level_movement` | PASS - misaligned int access formed through char-level movement trapped. |
| MEM-17 | Maximum 0xFFFF pointer arithmetic/wrap boundaries. | `test_017_mem_17_pointer_arithmetic_cannot_wrap_at_ffff` | PASS - 0xFFFF-scale pointer arithmetic was range-checked before wrap. |
| MEM-18 | Screen-adjacent addresses 0x5AFF/0x5B00 and user-space boundaries 0x5FFF/0x6000/0xDFFF/0xE000. | `test_018_mem_18_screen_and_user_boundary_addresses_are_isolated` | PASS - screen/user boundary probes preserved the C object/provenance boundary. |
| MEM-19 | Objects whose final byte is exactly at USER_HI-1. | `test_019_mem_19_object_can_end_exactly_at_user_hi_minus_one` | PASS - an object ending exactly at 0xDFFF read/wrote its last legal byte. |
| MEM-20 | 16-bit two-byte load/store where the first byte is legal but second crosses the allocation boundary. | `test_020_mem_20_two_byte_access_cannot_cross_allocation_end` | PASS - two-byte loads and stores rejected a one-byte remaining allocation. |

## Forged C48B1 suite

| ID | Review attack | Regression | Result |
| --- | --- | --- | --- |
| B1-01 | Wrong expression ctype attached to otherwise valid node. | `test_021_b1_01_wrong_expression_ctype` | PASS - forged literal ctype was rejected by C48B1 semantic cross-checking. |
| B1-02 | Identifier metadata disagreeing with symbol-table type. | `test_022_b1_02_identifier_metadata_disagrees_with_symbol_table` | PASS - forged identifier type/entity metadata was rejected with lexical-scope awareness. |
| B1-03 | Function call result type disagreeing with function declaration. | `test_023_b1_03_call_result_type_disagrees_with_function` | PASS - forged call-result ctype was rejected against the function return type. |
| B1-04 | Pointer arithmetic node whose result type is intentionally forged. | `test_024_b1_04_pointer_arithmetic_result_type_is_forged` | PASS - forged pointer-arithmetic result ctype was rejected. |
| B1-05 | Array bound/type length mismatch. | `test_025_b1_05_array_declaration_and_type_length_mismatch` | PASS - forged array length disagreed with the canonical symbol type and was rejected. |
| B1-06 | sizeof_value inconsistent with type. | `test_026_b1_06_sizeof_value_mismatch` | PASS - forged sizeof_value was recomputed and rejected. |
| B1-07 | String SID collisions. | `test_027_b1_07_string_sid_collision` | PASS - one SID could not alias different literal byte sequences. |
| B1-08 | Duplicate symbol names with conflicting manifest metadata. | `test_028_b1_08_duplicate_symbol_identity_conflict` | PASS - conflicting top-level symbol/declaration identity was rejected. |
| B1-09 | Block declaration with file-scope-only metadata. | `test_029_b1_09_block_declaration_cannot_carry_file_metadata` | PASS - file-scope-only metadata on a block declaration was rejected. |
| B1-10 | Huge integer values in fields whose schema checks only Python int. | `test_030_b1_10_huge_integer_field_is_rejected` | PASS - absurd Python-sized integer metadata was rejected by C48 range validation. |
| B1-11 | Negative/absurd source-derived counters. | `test_031_b1_11_negative_source_derived_counter_is_rejected` | PASS - negative source-derived SID metadata was rejected. |
| B1-12 | Thousands of symbols/functions. | `test_032_b1_12_thousands_of_symbols_hit_explicit_budget` | PASS - a 5,000-entry forged symbol table hit the explicit symbol budget. |
| B1-13 | Deeply nested compounds/expressions. | `test_033_b1_13_deep_ast_nesting_hits_budget` | PASS - deep forged AST nesting hit the structural resource budget. |
| B1-14 | Very wide items, declarations, statements, args, or initializer arrays. | `test_034_b1_14_wide_structural_lists_hit_budget` | PASS - a 4,097-wide structural sequence hit the 4,096-item width budget. |
| B1-15 | Multi-megabyte string literal byte arrays. | `test_035_b1_15_multimegabyte_string_byte_array_is_bounded` | PASS - a 700,000-byte literal vector was rejected by C48B1 resource limits. |
| B1-16 | JSON duplicate keys. | `test_036_b1_16_duplicate_json_keys_are_rejected` | PASS - duplicate JSON keys were rejected despite a recomputed valid digest. |
| B1-17 | Noncanonical whitespace/order. | `test_037_b1_17_noncanonical_whitespace_or_order_is_rejected` | PASS - rehashed noncanonical JSON whitespace/order was rejected. |
| B1-18 | Valid digest but trailing garbage. | `test_038_b1_18_valid_digest_with_trailing_garbage_is_rejected` | PASS - rehashed trailing payload garbage was rejected. |
| B1-19 | Truncated digest/payload. | `test_039_b1_19_truncated_digest_and_payload_are_rejected` | PASS - truncated digest/payload forms produced controlled diagnostics. |
| B1-20 | NUL/non-ASCII bytes. | `test_040_b1_20_nul_and_nonascii_payload_bytes_are_rejected` | PASS - rehashed NUL and non-ASCII payload bytes were rejected cleanly. |
| B1-21 | Gigabyte-scale declared input file. | `test_041_b1_21_gigabyte_sparse_file_rejected_before_read` | PASS - a 1 GiB sparse C48B1 was rejected by the pre-read size gate. |
| B1-22 | Exponential-looking AST shapes with repeated nested subtrees. | `test_042_b1_22_repeated_ast_subtrees_hit_node_budget` | PASS - repeated forged AST growth was bounded by structural/node budgets. |

## Compiler lexical/preprocessor suite

| ID | Review attack | Regression | Result |
| --- | --- | --- | --- |
| LEX-01 | Every byte 0x00-0xFF at every sensitive lexical position. | `test_043_lex_01_all_byte_values_at_sensitive_positions` | PASS - all 256 byte values were injected at seven lexical contexts with only controlled outcomes. |
| LEX-02 | BOMs, UTF-8 lead bytes, DEL, VT, FF, CR-only, mixed CRLF/LF. | `test_044_lex_02_bom_utf8_del_controls_and_newline_forms` | PASS - BOM/UTF-8/control/newline variants were rejected or normalized as specified. |
| LEX-03 | Unterminated strings/chars/comments at EOF and before LF. | `test_045_lex_03_unterminated_literals_and_comments` | PASS - unterminated string/char/comment forms produced controlled lexical errors. |
| LEX-04 | Extremely long source line. | `test_046_lex_04_extremely_long_physical_line_is_bounded` | PASS - overlong physical line hit the line-byte ceiling. |
| LEX-05 | Extremely many empty lines. | `test_047_lex_05_extremely_many_empty_lines_are_bounded` | PASS - empty-line flood hit source/line resource accounting. |
| LEX-06 | Extremely many comments. | `test_048_lex_06_extremely_many_comments_are_bounded` | PASS - comment flood remained resource-bounded. |
| LEX-07 | Long runs of /, *, quotes, backslashes, #, and operator prefixes. | `test_049_lex_07_long_runs_of_sensitive_punctuation_are_bounded` | PASS - sensitive punctuation runs remained lexically/resource controlled. |
| LEX-08 | Numeric strings one character either side of every valid grammar. | `test_050_lex_08_numeric_grammar_neighbors_are_controlled` | PASS - near-grammar numeric corpus produced only controlled compiler outcomes. |
| LEX-09 | Very long decimal/octal/hex values. | `test_051_lex_09_very_long_integer_literals_are_controlled` | PASS - huge decimal/octal/hex spellings were bounded without host integer leakage. |
| LEX-10 | Very long float mantissas and exponents. | `test_052_lex_10_very_long_float_mantissas_and_exponents_controlled` | PASS - huge float mantissa/exponent spellings were bounded cleanly. |
| LEX-11 | Repeated maximal-munch ambiguous operators. | `test_053_lex_11_repeated_maximal_munch_operators_controlled` | PASS - repeated ambiguous operators remained deterministic and bounded. |
| LEX-12 | 15-character identifiers everywhere; 16-character identifiers everywhere. | `test_054_lex_12_identifier_visible_length_boundary` | PASS - 15-character identifiers were accepted and 16-character identifiers rejected. |
| LEX-13 | Tens of thousands of unique identifiers. | `test_055_lex_13_tens_of_thousands_unique_identifiers_prebounded` | PASS - tens-of-thousands unique-identifier source was prebounded. |
| LEX-14 | Tens of thousands of repeated declarations. | `test_056_lex_14_tens_of_thousands_repeated_declarations_prebounded` | PASS - tens-of-thousands repeated declarations were prebounded. |
| LEX-15 | Macro doubling, tripling, and wide fan-out. | `test_057_lex_15_macro_doubling_tripling_and_wide_fanout_bounded` | PASS - doubling/tripling/fan-out macro growth hit expansion budgets. |
| LEX-16 | Macro chains containing parenthesized constants. | `test_058_lex_16_parenthesized_macro_chain_is_controlled` | PASS - parenthesized macro chains hit controlled nesting/resource limits. |
| LEX-17 | Macro expansion to huge string constants. | `test_059_lex_17_macro_expansion_to_huge_string_is_bounded` | PASS - huge string-producing macro expansion was bounded. |
| LEX-18 | Many identical macro redefinitions. | `test_060_lex_18_many_identical_macro_redefinitions_remain_bounded` | PASS - many identical macro redefinitions remained deterministic and bounded. |
| LEX-19 | Includes targeting every legal/illegal basename length and suffix. | `test_061_lex_19_include_basename_and_suffix_boundaries` | PASS - legal/illegal include basename lengths and suffixes matched the portable rule. |
| LEX-20 | Case-collision sibling files on Windows. | `test_062_lex_20_include_case_collision_is_exact_case_only` | PASS - exact-case include lookup prevented case-fold substitution; Windows CI covers host semantics. |
| LEX-21 | Symlink/reparse-point include behavior on hosts that support it. | `test_063_lex_21_symlink_or_reparse_include_cannot_escape_sibling_rule` | PASS - symlink/reparse include objects were explicitly rejected on hosts supporting the fixture. |
| LEX-22 | Source/output path aliases via .., junctions, hardlinks, and case folding. | `test_064_lex_22_source_output_aliases_do_not_destroy_source` | PASS - .., directory link/junction, hardlink, and Windows case-fold output aliases did not corrupt source. |

## Parser/semantic suite

| ID | Review attack | Regression | Result |
| --- | --- | --- | --- |
| PAR-01 | Deep parentheses. | `test_065_par_01_deep_parentheses_bounded` | PASS - deep parentheses hit explicit parser nesting before Python recursion. |
| PAR-02 | Deep blocks. | `test_066_par_02_deep_blocks_bounded` | PASS - deep compound blocks hit explicit statement nesting. |
| PAR-03 | Deep unary chains (!, ~, + with separators preventing token fusion). | `test_067_par_03_deep_unary_chains_bounded` | PASS - deep !, ~, and separated + unary chains were resource-bounded. |
| PAR-04 | Deep pointer types. | `test_068_par_04_deep_pointer_types_bounded` | PASS - excessive pointer indirection hit the explicit type/declarator depth ceiling. |
| PAR-05 | Long left-associative binary chains. | `test_069_par_05_long_left_associative_binary_chain_bounded` | PASS - long left-associative binary chain was resource-bounded. |
| PAR-06 | Long right-recursive or parenthesized constant trees. | `test_070_par_06_long_right_parenthesized_constant_tree_bounded` | PASS - right-nested constant tree was rejected before host recursion overflow. |
| PAR-07 | Huge initializer lists. | `test_071_par_07_huge_initializer_list_is_prebounded` | PASS - 20,000-element initializer source was rejected by frozen host resource ceilings. |
| PAR-08 | Huge parameter lists. | `test_072_par_08_huge_parameter_list_is_prebounded` | PASS - 5,000-parameter declaration was prebounded. |
| PAR-09 | Huge argument lists. | `test_073_par_09_huge_argument_list_is_prebounded` | PASS - 5,000-argument call was prebounded. |
| PAR-10 | Long declaration lists separated by commas. | `test_074_par_10_long_comma_declaration_list_is_prebounded` | PASS - 5,000-declarator comma list was prebounded. |
| PAR-11 | Long chains of nested if/else. | `test_075_par_11_deep_if_else_chain_bounded` | PASS - deep if/else nesting hit the statement budget. |
| PAR-12 | Long nested loops. | `test_076_par_12_deep_loop_chain_bounded` | PASS - deep loop nesting hit the statement budget. |
| PAR-13 | Long chained indexing. | `test_077_par_13_chained_indexing_respects_pointer_depth_ceiling` | PASS - chained indexing respected parser/type-depth ceilings. |
| PAR-14 | Maximum call graph width/depth. | `test_078_par_14_call_graph_width_and_runtime_depth_are_bounded` | PASS - wide call graph remained controlled and hostile recursive depth hit VM call-depth limit. |
| PAR-15 | Mutually recursive declarations/calls within the source-order rules. | `test_079_par_15_mutual_recursion_with_prototypes_is_controlled` | PASS - mutual recursion with valid prototypes compiled; VM depth limit terminated hostile execution. |
| PAR-16 | Extremely large symbol tables with many shadowing scopes. | `test_080_par_16_large_symbol_table_and_shadowing_scopes_controlled` | PASS - large symbols were bounded and repeated lexical shadow scopes preserved semantics. |
| PAR-17 | Pathological combinations of sizeof, casts, and pointer types. | `test_081_par_17_sizeof_cast_pointer_type_pathologies_controlled` | PASS - pathological legal sizeof/cast/pointer types executed; unsupported continuation rejected cleanly. |
| PAR-18 | Constant-expression division/remainder/shift boundary vectors. | `test_082_par_18_constant_division_remainder_shift_boundaries` | PASS - division/remainder/shift boundary vectors matched C48 rules; constant divide-by-zero rejected. |
| PAR-19 | Float literals close to representational underflow/overflow. | `test_083_par_19_float_underflow_overflow_literals_are_controlled` | PASS - underflow/overflow-adjacent float literals produced only controlled outcomes. |
| PAR-20 | Error-position stress at very large line/column numbers. | `test_084_par_20_large_error_line_and_column_positions_remain_exact` | PASS - diagnostics retained exact large line/column positions without traceback. |

## Compiler hardening required by the corpus

1. **Forged C48B1 semantic metadata and width.** The decoder now enforces
   bounded sequence widths and symbol counts; scalar/SID ranges; literal
   result types; lexical-scope-aware identifier metadata; function return
   metadata; pointer-arithmetic result metadata; `sizeof_value`; string SID
   uniqueness; and top-level declaration/symbol consistency before VM use.
2. **Quoted-include host redirection.** Exact-case sibling includes now reject
   symlink and Windows reparse-point file objects before reading them.

These are host-safety defenses. They do not broaden the C48 language or alter
the documented target ABI.

## Release evidence

`compiler/verify_release.py` requires both this ledger and the 84-test
module. The 291-test figure above is the historical incorporation baseline for
that review; `compiler/release_expectations.json` now freezes the complete
1.0.0 unittest count at 338. The release workflow runs the complete verifier
on Ubuntu x64, Windows x64, macOS arm64 and macOS Intel under Python 3.10 and
Python 3.13, thereby making this abuse corpus a cross-platform CI gate rather
than a one-off review exercise.
