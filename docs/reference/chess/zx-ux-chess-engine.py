#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
"""
ZX-UX Chess Reference Engine
============================

Purpose
-------
This file is a documented Python reference implementation accompanying the
ZX-UX Chess material in this SDK.  It is intended for study, validation,
experimentation, and comparison with the C48 chess program carried by the SDK
for ZX-UX development.  It is not the native ZX-UX program and it is not the
C48 source itself.  The Python version favors clarity and instrumentation over
the memory and execution constraints of a Sinclair ZX Spectrum 48K.

Engine architecture
-------------------
The engine is deliberately conventional and small:

* Board representation: a 10 x 12 mailbox board.  The playable 8 x 8 board is
  surrounded by OFF_BOARD sentinels, so sliding pieces can detect board edges
  without repeated file/rank boundary tests.
* Piece representation: the low three bits identify the piece type; bit 7 marks
  a black piece.  White therefore has colour value 0 and black has 0x80.
* Move generation: pseudo-legal moves are generated first.  A make/unmake test
  then rejects moves that leave the moving side's king in check.
* Rules implemented: castling, en passant, four promotion choices, check,
  checkmate, stalemate, the 50-move rule, and threefold repetition.
* Evaluation: material values plus optional midgame piece-square tables.
* Search: iterative deepening over a negamax alpha-beta search, with a
  transposition table, MVV-LVA capture ordering, killer moves, repetition
  detection, and an optional per-move time limit.
* Hashing: deterministic 64-bit Zobrist keys cover pieces, side to move,
  castling rights, and the en-passant file.
* Validation support: a perft mode is supplied for legal-move-tree counting.
* User interface: a simple terminal board, coordinate move entry, optional PGN
  output, and command-line controls for depth, side, timing, and evaluation.

Coordinate system
-----------------
The mailbox board uses rows 2..9 and columns 1..8 as the playable squares.
Display rank is therefore ``row - 1``.  White starts on mailbox rows 2 and 3;
black starts on rows 9 and 8.  UCI-like input such as ``e2e4`` is translated
into those mailbox coordinates.

Revision history
----------------
Revision 2:
  * Corrected board alignment and robust EOF / KeyboardInterrupt handling.
  * Hardened en-passant generation.
  * Replaced king centralisation bonus with a king midgame table.
  * Added standard midgame piece-square tables.
  * Added Zobrist hashing and a transposition table.
  * Added MVV-LVA move ordering and killer moves.
  * Added repetition and 50-move detection inside search.
  * Added a per-move time limit and mate-score TT adjustment.
  * Added --depth, --side, --perft, --pgn, and --no-pst options.
  * Added PGN export and perft test mode.

Revision 2.1:
  * Removed the unused ``board_before`` argument from format_pgn_move().
  * Added a legal-move fallback if an extremely small --time budget prevents
    find_best_move() from completing even one root move.

Documentation-only cleanup:
  * Standardised section headings.
  * Expanded comments throughout the board, move-generation, evaluation,
    search, rules, and command-line paths.
  * No executable chess-engine logic was intentionally changed.
"""

import sys
import time
import random
import argparse

# =============================================================================
# 1. CORE CONSTANTS AND BOARD GEOMETRY
# =============================================================================
# Piece codes are compact because the same integer travels through board
# storage, move records, evaluation, and hashing.  The low three bits hold the
# piece type; BLACK is a colour bit that can be ORed into a piece code.
OFF_BOARD  = 0xFF
EMPTY      = 0
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = 1, 2, 3, 4, 5, 6
BLACK      = 0x80
WHITE_SIDE = 0
BLACK_SIDE = 0x80

FLAG_EP        = 1
FLAG_CASTLE_K  = 2
FLAG_CASTLE_Q  = 4
FLAG_PROMOTION = 8

KNIGHT_OFFSETS = [(-2,-1),(-2,1),(-1,-2),(-1,2),
                  (1,-2),(1,2),(2,-1),(2,1)]
BISHOP_DIRS = [(-1,-1),(-1,1),(1,-1),(1,1)]
ROOK_DIRS   = [(-1,0),(1,0),(0,-1),(0,1)]
QUEEN_DIRS  = BISHOP_DIRS + ROOK_DIRS

PIECE_VALUES   = [0, 100, 320, 330, 500, 900, 20000]
MATE           = 100000
INF            = 1000000
MATE_THRESHOLD = MATE - 1000
MAX_DEPTH      = 4

PIECE_CHARS = " PNBRQK"

# =============================================================================
# 2. PIECE-SQUARE TABLES
# =============================================================================
# These midgame tables add positional preferences to the raw material score.
# They are written from White's point of view with rank 8 first.  Evaluation
# mirrors the mailbox row for White so both colours reuse the same tables.
# Standard midgame piece-square tables (centipawns, white's POV,
# rank 8 at index 0, rank 1 at index 63).
PST_PAWN = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]
PST_KNIGHT = [
   -50,-40,-30,-30,-30,-30,-40,-50,
   -40,-20,  0,  0,  0,  0,-20,-40,
   -30,  0, 10, 15, 15, 10,  0,-30,
   -30,  5, 15, 20, 20, 15,  5,-30,
   -30,  0, 15, 20, 20, 15,  0,-30,
   -30,  5, 10, 15, 15, 10,  5,-30,
   -40,-20,  0,  5,  5,  0,-20,-40,
   -50,-40,-30,-30,-30,-30,-40,-50,
]
PST_BISHOP = [
   -20,-10,-10,-10,-10,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5, 10, 10,  5,  0,-10,
   -10,  5,  5, 10, 10,  5,  5,-10,
   -10,  0, 10, 10, 10, 10,  0,-10,
   -10, 10, 10, 10, 10, 10, 10,-10,
   -10,  5,  0,  0,  0,  0,  5,-10,
   -20,-10,-10,-10,-10,-10,-10,-20,
]
PST_ROOK = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]
PST_QUEEN = [
   -20,-10,-10, -5, -5,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5,  5,  5,  5,  0,-10,
    -5,  0,  5,  5,  5,  5,  0, -5,
     0,  0,  5,  5,  5,  5,  0, -5,
   -10,  5,  5,  5,  5,  5,  0,-10,
   -10,  0,  5,  0,  0,  0,  0,-10,
   -20,-10,-10, -5, -5,-10,-10,-20,
]
PST_KING_MID = [
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -20,-30,-30,-40,-40,-30,-30,-20,
   -10,-20,-20,-20,-20,-20,-20,-10,
    20, 20,  0,  0,  0,  0, 20, 20,
    20, 30, 10,  0,  0, 10, 30, 20,
]
PST = [None, PST_PAWN, PST_KNIGHT, PST_BISHOP, PST_ROOK, PST_QUEEN, PST_KING_MID]

# =============================================================================
# 3. ZOBRIST HASHING
# =============================================================================
# Zobrist hashing gives each position a compact 64-bit identity.  A fixed RNG
# seed makes the table deterministic across runs, which is useful for debugging
# and repeatable reference tests.  The hash includes every state component that
# changes legal continuations: pieces, side, castling rights, and en-passant.
_rng = random.Random(0x16CE55)
Z_PIECE = [[[0] * 120 for _ in range(7)] for _ in range(2)]
for _c in range(2):
    for _p in range(7):
        for _s in range(120):
            Z_PIECE[_c][_p][_s] = _rng.getrandbits(64)
Z_SIDE    = _rng.getrandbits(64)
Z_CASTLE  = [_rng.getrandbits(64) for _ in range(4)]
Z_EP_FILE = [_rng.getrandbits(64) for _ in range(10)]

# =============================================================================
# 4. MOVE RECORD
# =============================================================================
# Move objects carry enough information for search ordering, execution,
# unexecution, display, and PGN formatting.  Coordinates stay in mailbox form
# so no conversion is required inside the engine's hot paths.
# A Move is treated as immutable in meaning after construction, although
# ``score`` is scratch storage used by move ordering.  ``captured`` stores the original piece
# code so unmake_move() can restore captures without consulting another board.
class Move:
    __slots__ = ('from_r', 'from_c', 'to_r', 'to_c',
                 'piece', 'captured', 'flags', 'promo', 'score')

    def __init__(self, fr, fc, tr, tc, piece, captured=0, flags=0, promo=None):
        self.from_r, self.from_c = fr, fc
        self.to_r,   self.to_c   = tr, tc
        self.piece    = piece
        self.captured = captured
        self.flags    = flags
        self.promo    = promo
        self.score    = 0

    def __repr__(self):
        return self.uci()

    def key(self):
        return (self.from_r, self.from_c, self.to_r, self.to_c, self.promo)

    def uci(self):
        files = "abcdefgh"
        s = (files[self.from_c - 1] + str(self.from_r - 1) +
             files[self.to_c   - 1] + str(self.to_r   - 1))
        if self.flags & FLAG_PROMOTION and self.promo:
            s += {QUEEN: 'q', ROOK: 'r', BISHOP: 'b', KNIGHT: 'n'}[self.promo]
        return s

    def is_capture(self):
        return self.captured != 0

# =============================================================================
# 5. BOARD STATE
# =============================================================================
# Board owns the complete reversible game state.  The 120-cell mailbox layout
# is the central simplifying device: playable squares live inside an OFF_BOARD
# border, letting leapers and sliders probe neighbors without separate edge
# tests for files a/h and ranks 1/8.
# Board state is deliberately explicit.  Search correctness depends on every
# state component being reversible and hash-visible where appropriate.
class Board:
    __slots__ = ('sq', 'side', 'ep_r', 'ep_c',
                 'castle', 'halfmove', 'fullmove', 'history')

    def __init__(self):
        self.sq       = [OFF_BOARD] * 120
        self.side     = WHITE_SIDE
        self.ep_r     = -1
        self.ep_c     = -1
        self.castle   = [True, True, True, True]
        self.halfmove = 0
        self.fullmove = 1
        self.history  = []

    def get(self, r, c):
        return self.sq[r * 10 + c]

    def set(self, r, c, v):
        self.sq[r * 10 + c] = v

    def hash(self):
        # XORing independent random keys makes the hash cheap to recompute and
        # naturally order-independent across occupied squares.  Recomputing
        # from board state is slower than incremental hashing but is clearer
        # for a compact reference implementation and harder to desynchronise.
        h = 0
        sq = self.sq
        for r in range(2, 10):
            base = r * 10
            for c in range(1, 9):
                p = sq[base + c]
                if p and p != OFF_BOARD:
                    h ^= Z_PIECE[(p >> 7) & 1][p & 7][base + c]
        # Position identity also depends on whose turn it is.
        if self.side == BLACK_SIDE:
            h ^= Z_SIDE
        # Four independent rights represent White/Black king- and queen-side
        # castling.  A position with different rights must hash differently
        # even when every piece occupies the same square.
        for i, b in enumerate(self.castle):
            if b:
                h ^= Z_CASTLE[i]
        # Only the en-passant file is needed because the target rank is implied
        # by the side that just advanced a pawn two squares.
        if self.ep_r >= 0:
            h ^= Z_EP_FILE[self.ep_c]
        return h

# =============================================================================
# 6. INITIAL POSITION
# =============================================================================
# Initialise both the mailbox sentinels and the standard chess starting
# position.  The first position hash is also seeded into history so repetition
# detection can reason about the complete game from move zero.
# Build the sentinel frame, clear the 64 playable cells, install both armies,
# restore initial rule state, and seed repetition history.
def init_board(board):
    # Start with a solid sentinel frame, then carve the 8 x 8 playable area
    # out of the middle of the mailbox.
    for i in range(120):
        board.sq[i] = OFF_BOARD
    for r in range(2, 10):
        base = r * 10
        for c in range(1, 9):
            board.sq[base + c] = EMPTY

    # Rows 2/3 are White ranks 1/2; rows 9/8 are Black ranks 8/7.
    back = [ROOK, KNIGHT, BISHOP, QUEEN, KING, BISHOP, KNIGHT, ROOK]
    for i, p in enumerate(back):
        c = i + 1
        board.set(2, c, p)
        board.set(3, c, PAWN)
        board.set(9, c, p | BLACK)
        board.set(8, c, PAWN | BLACK)

    board.side     = WHITE_SIDE
    board.ep_r     = -1
    board.ep_c     = -1
    board.castle   = [True, True, True, True]
    board.halfmove = 0
    board.fullmove = 1
    board.history  = [board.hash()]

# =============================================================================
# 7. ATTACK MAP AND CHECK DETECTION
# =============================================================================
# Attack detection is intentionally separate from legal move generation.
# Castling and king-safety tests need to ask whether a square is controlled
# even when constructing a full legal move list would be unnecessary.
# Return True when (r, c) is attacked by ``by_side``.  This routine reasons
# about attacks, not move legality; in particular it must work for castling-path
# tests and king safety without recursively generating legal moves.
def is_attacked(board, r, c, by_side):
    # Pawn attacks are directional and therefore handled before the symmetric
    # leaper and slider cases.
    if by_side == WHITE_SIDE:
        for dc in (-1, 1):
            p = board.get(r - 1, c + dc)
            if p != OFF_BOARD and p != EMPTY \
               and (p & 7) == PAWN and (p & BLACK) == 0:
                return True
    else:
        for dc in (-1, 1):
            p = board.get(r + 1, c + dc)
            if p != OFF_BOARD and p != EMPTY \
               and (p & 7) == PAWN and (p & BLACK) == BLACK:
                return True

    # Knights leap; kings attack the eight immediately adjacent squares.
    for dr, dc in KNIGHT_OFFSETS:
        p = board.get(r + dr, c + dc)
        if p != OFF_BOARD and p != EMPTY \
           and (p & 7) == KNIGHT and (p & BLACK) == by_side:
            return True
    for dr, dc in QUEEN_DIRS:
        p = board.get(r + dr, c + dc)
        if p != OFF_BOARD and p != EMPTY \
           and (p & 7) == KING and (p & BLACK) == by_side:
            return True

    # Bishops and queens attack along diagonals until the first blocker.
    for dr, dc in BISHOP_DIRS:
        nr, nc = r + dr, c + dc
        while True:
            p = board.get(nr, nc)
            if p == OFF_BOARD:
                break
            if p != EMPTY:
                if (p & BLACK) == by_side:
                    t = p & 7
                    if t == BISHOP or t == QUEEN:
                        return True
                break
            nr += dr; nc += dc

    # Rooks and queens use the same first-blocker rule on ranks/files.
    for dr, dc in ROOK_DIRS:
        nr, nc = r + dr, c + dc
        while True:
            p = board.get(nr, nc)
            if p == OFF_BOARD:
                break
            if p != EMPTY:
                if (p & BLACK) == by_side:
                    t = p & 7
                    if t == ROOK or t == QUEEN:
                        return True
                break
            nr += dr; nc += dc
    return False

# Locate one side's king by scanning the 64 playable mailbox cells.
def find_king(board, side):
    for r in range(2, 10):
        base = r * 10
        for c in range(1, 9):
            p = board.sq[base + c]
            if p != EMPTY and p != OFF_BOARD \
               and (p & 7) == KING and (p & BLACK) == side:
                return r, c
    return None

# A side is in check exactly when its king square is attacked by the opponent.
def in_check(board, side):
    kr = find_king(board, side)
    if kr is None:
        return False
    return is_attacked(board, kr[0], kr[1], side ^ BLACK)

# =============================================================================
# 8. MOVE GENERATION
# =============================================================================
# The generator is split into two layers:
#   1. pseudo-legal generation applies piece movement rules and special moves;
#   2. legal filtering makes each candidate and rejects it if the mover's king
#      remains or becomes attacked.
# This keeps individual piece generators simple and centralises king safety.
# Enumerate moves that obey piece movement and special-move rules.  King
# exposure is intentionally not filtered here; generate_legal_moves() performs
# that second-stage legality test.
def generate_pseudo_legal(board):
    moves = []
    side = board.side
    for r in range(2, 10):
        base = r * 10
        for c in range(1, 9):
            p = board.sq[base + c]
            if p == EMPTY or p == OFF_BOARD:
                continue
            if (p & BLACK) != side:
                continue
            t = p & 7
            if   t == PAWN:   _gen_pawn(board, r, c, side, moves)
            elif t == KNIGHT: _gen_knight(board, r, c, side, moves)
            elif t == BISHOP: _gen_slider(board, r, c, side, BISHOP_DIRS, moves)
            elif t == ROOK:   _gen_slider(board, r, c, side, ROOK_DIRS,   moves)
            elif t == QUEEN:  _gen_slider(board, r, c, side, QUEEN_DIRS,  moves)
            elif t == KING:   _gen_king(board, r, c, side, moves)
    return moves

# Pawn generation handles the asymmetric parts of chess movement: directional
# pushes, initial double pushes, diagonal captures, promotion fan-out, and
# en-passant captures.
def _gen_pawn(board, r, c, side, moves):
    p = board.get(r, c)
    if side == WHITE_SIDE:
        d, start, promo_row = 1, 3, 9
    else:
        d, start, promo_row = -1, 8, 2
    nr = r + d

    # A pawn may advance only into an empty square.  Promotion expands one
    # destination into four legal move records so search can compare each piece.
    if board.get(nr, c) == EMPTY:
        if nr == promo_row:
            for q in (QUEEN, ROOK, BISHOP, KNIGHT):
                moves.append(Move(r, c, nr, c, p, 0, FLAG_PROMOTION, q))
        else:
            moves.append(Move(r, c, nr, c, p))
            # The two-square opening push is legal only from the starting rank
            # and only when both traversed/destination squares are empty.
            if r == start and board.get(r + 2 * d, c) == EMPTY:
                moves.append(Move(r, c, r + 2 * d, c, p))

    # Normal captures and en-passant both move diagonally one file.  The enemy
    # colour is the current side with the colour bit toggled.
    enemy = side ^ BLACK
    for dc in (-1, 1):
        nc = c + dc
        t = board.get(nr, nc)
        if t != OFF_BOARD and t != EMPTY and (t & BLACK) != side:
            if nr == promo_row:
                for q in (QUEEN, ROOK, BISHOP, KNIGHT):
                    moves.append(Move(r, c, nr, nc, p, t, FLAG_PROMOTION, q))
            else:
                moves.append(Move(r, c, nr, nc, p, t))
        elif board.ep_r == nr and board.ep_c == nc:
            # En-passant is only valid if the adjacent square still contains
            # the enemy pawn that supposedly advanced two squares.
            captured = board.get(r, nc)
            if captured != OFF_BOARD and captured != EMPTY \
               and (captured & 7) == PAWN \
               and (captured & BLACK) == enemy:
                moves.append(Move(r, c, nr, nc, p, captured, FLAG_EP))

# Knights use fixed mailbox offsets.  The sentinel border turns off-board
# destinations into an ordinary value check.
def _gen_knight(board, r, c, side, moves):
    p = board.get(r, c)
    for dr, dc in KNIGHT_OFFSETS:
        nr, nc = r + dr, c + dc
        t = board.get(nr, nc)
        if t == OFF_BOARD:
            continue
        if t == EMPTY:
            moves.append(Move(r, c, nr, nc, p))
        elif (t & BLACK) != side:
            moves.append(Move(r, c, nr, nc, p, t))

# Bishops, rooks, and queens share ray tracing.  Empty squares extend a ray;
# the first occupied square either becomes one capture or blocks the ray.
def _gen_slider(board, r, c, side, dirs, moves):
    p = board.get(r, c)
    for dr, dc in dirs:
        nr, nc = r + dr, c + dc
        while True:
            t = board.get(nr, nc)
            if t == OFF_BOARD:
                break
            if t == EMPTY:
                moves.append(Move(r, c, nr, nc, p))
            else:
                if (t & BLACK) != side:
                    moves.append(Move(r, c, nr, nc, p, t))
                break
            nr += dr; nc += dc

# Generate one-square king moves plus castling.  Castling requires the expected
# king/rook placement, empty transit squares, retained castling rights, and no
# attack on the king's start, transit, or destination square.
def _gen_king(board, r, c, side, moves):
    p = board.get(r, c)
    for dr, dc in QUEEN_DIRS:
        nr, nc = r + dr, c + dc
        t = board.get(nr, nc)
        if t == OFF_BOARD:
            continue
        if t == EMPTY:
            moves.append(Move(r, c, nr, nc, p))
        elif (t & BLACK) != side:
            moves.append(Move(r, c, nr, nc, p, t))

    # Castling is generated only from the orthodox king square.  The castling
    # rights array uses [WK, WQ, BK, BQ].
    enemy = side ^ BLACK
    row = 2 if side == WHITE_SIDE else 9
    colour = side
    ks_index = 0 if side == WHITE_SIDE else 2
    qs_index = 1 if side == WHITE_SIDE else 3
    king_c   = 5

    if board.get(row, king_c) != (KING | colour):
        return

    if board.castle[ks_index] \
       and board.get(row, 6) == EMPTY \
       and board.get(row, 7) == EMPTY \
       and board.get(row, 8) == (ROOK | colour):
        if not is_attacked(board, row, 5, enemy) \
           and not is_attacked(board, row, 6, enemy) \
           and not is_attacked(board, row, 7, enemy):
            moves.append(Move(row, king_c, row, 7, p, 0, FLAG_CASTLE_K))

    if board.castle[qs_index] \
       and board.get(row, 4) == EMPTY \
       and board.get(row, 3) == EMPTY \
       and board.get(row, 2) == EMPTY \
       and board.get(row, 1) == (ROOK | colour):
        if not is_attacked(board, row, 5, enemy) \
           and not is_attacked(board, row, 4, enemy) \
           and not is_attacked(board, row, 3, enemy):
            moves.append(Move(row, king_c, row, 3, p, 0, FLAG_CASTLE_Q))

# Filter pseudo-legal candidates by making each move temporarily and checking
# the moving side's king.  The original board is restored after every probe.
def generate_legal_moves(board):
    legal = []
    side = board.side
    for m in generate_pseudo_legal(board):
        undo = make_move(board, m)
        if not in_check(board, side):
            legal.append(m)
        unmake_move(board, undo)
    return legal

# =============================================================================
# 9. MAKE / UNMAKE MOVE
# =============================================================================
# Search mutates one Board in place rather than allocating a new position for
# every node.  make_move() therefore captures all non-board state required to
# restore the position exactly; unmake_move() reverses the mutation.
# Apply one move and return an undo record.  Besides board squares, this updates
# castling rights, en-passant state, clocks, side to move, and repetition
# history—all state that can affect future legality or draw detection.
def make_move(board, move):
    # Save rule state that cannot be reconstructed from the destination board
    # alone.  Captured-piece data is already carried by the Move itself.
    undo = {
        'ep_r':     board.ep_r,
        'ep_c':     board.ep_c,
        'castle':   board.castle[:],
        'halfmove': board.halfmove,
        'fullmove': board.fullmove,
        'side':     board.side,
        'move':     move,
    }
    p      = move.piece
    colour = p & BLACK

    # Clear the origin first.  For en-passant the captured pawn is not on the
    # destination square, so its adjacent square must be cleared explicitly.
    board.set(move.from_r, move.from_c, EMPTY)

    if move.flags & FLAG_EP:
        board.set(move.from_r, move.to_c, EMPTY)

    # Promotion replaces the pawn with the selected piece while preserving
    # colour; otherwise the original piece simply occupies the destination.
    if move.flags & FLAG_PROMOTION and move.promo:
        board.set(move.to_r, move.to_c, move.promo | colour)
    else:
        board.set(move.to_r, move.to_c, p)

    # Castling is encoded as a king move, so make/unmake must also relocate the
    # rook on the same rank.
    if move.flags & FLAG_CASTLE_K:
        row = move.from_r
        board.set(row, 8, EMPTY)
        board.set(row, 6, ROOK | colour)
    elif move.flags & FLAG_CASTLE_Q:
        row = move.from_r
        board.set(row, 1, EMPTY)
        board.set(row, 4, ROOK | colour)

    # Moving a king permanently removes both rights for that colour.  Moving a
    # rook from its home square—or capturing a rook on that home square—removes
    # the corresponding individual right.
    t = p & 7
    if t == KING:
        if colour == 0:
            board.castle[0] = False
            board.castle[1] = False
        else:
            board.castle[2] = False
            board.castle[3] = False
    fr_fc = (move.from_r, move.from_c)
    tr_tc = (move.to_r,   move.to_c)
    if fr_fc == (2, 1) or tr_tc == (2, 1): board.castle[1] = False
    if fr_fc == (2, 8) or tr_tc == (2, 8): board.castle[0] = False
    if fr_fc == (9, 1) or tr_tc == (9, 1): board.castle[3] = False
    if fr_fc == (9, 8) or tr_tc == (9, 8): board.castle[2] = False

    # En-passant rights last for one reply only.  Clear the old target, then set
    # a new target if this move is a two-square pawn advance.
    board.ep_r = -1
    board.ep_c = -1
    if t == PAWN and abs(move.to_r - move.from_r) == 2:
        board.ep_r = (move.from_r + move.to_r) // 2
        board.ep_c = move.from_c

    # The FIDE halfmove clock resets on pawn moves and captures.  fullmove is
    # incremented after Black's move, before the side-to-move bit flips.
    if t == PAWN or move.captured != 0:
        board.halfmove = 0
    else:
        board.halfmove += 1
    if board.side == BLACK_SIDE:
        board.fullmove += 1

    board.side ^= BLACK
    # History stores the resulting position, including the new side to move.
    # Search and the game loop use it for repetition detection.
    board.history.append(board.hash())
    return undo

# Reverse make_move() exactly.  Search relies on byte-for-byte logical
# restoration of the position after every explored child.
def unmake_move(board, undo):
    move   = undo['move']
    p      = move.piece
    colour = p & BLACK

    # Remove the hash contributed by the move being undone before restoring
    # the previous rule state.
    board.history.pop()
    board.side = undo['side']

    # Restore the moving piece to its original square.  Promotion needs no
    # special reverse case because ``move.piece`` still stores the pawn.
    board.set(move.to_r,   move.to_c,   EMPTY)
    board.set(move.from_r, move.from_c, p)

    if move.flags & FLAG_EP:
        board.set(move.from_r, move.to_c, move.captured)
    elif move.captured:
        board.set(move.to_r, move.to_c, move.captured)

    if move.flags & FLAG_CASTLE_K:
        row = move.from_r
        board.set(row, 6, EMPTY)
        board.set(row, 8, ROOK | colour)
    elif move.flags & FLAG_CASTLE_Q:
        row = move.from_r
        board.set(row, 4, EMPTY)
        board.set(row, 1, ROOK | colour)

    board.ep_r     = undo['ep_r']
    board.ep_c     = undo['ep_c']
    board.castle   = undo['castle']
    board.halfmove = undo['halfmove']
    board.fullmove = undo['fullmove']

# =============================================================================
# 10. STATIC EVALUATION
# =============================================================================
# Scores are returned from the side-to-move perspective, which matches negamax.
# Material is always counted; piece-square terms can be disabled for comparison
# or debugging with --no-pst.
# Compute a centipawn-style static score.  Positive means good for the side to
# move because the final White-minus-Black total is flipped when Black moves.
def evaluate(board, use_pst=True):
    score = 0
    for r in range(2, 10):
        base = r * 10
        for c in range(1, 9):
            p = board.sq[base + c]
            if p == EMPTY or p == OFF_BOARD:
                continue
            t = p & 7
            # Start with material, then add the side-relative PST bonus.  White
            # indexes the table with its mailbox row mirrored; Black's mailbox
            # orientation already maps its home rank onto the table's rank 1.
            v = PIECE_VALUES[t]
            if use_pst:
                if p & BLACK:
                    v += PST[t][(r - 2) * 8 + (c - 1)]
                    score -= v
                else:
                    v += PST[t][(9 - r) * 8 + (c - 1)]
                    score += v
            else:
                score += -v if (p & BLACK) else v
    return score if board.side == WHITE_SIDE else -score

# =============================================================================
# 11. NEGAMAX ALPHA-BETA SEARCH
# =============================================================================
# The search is a compact negamax formulation: a child score is negated when
# returned to its parent, so one routine handles both colours.  Alpha-beta
# bounds prune branches that cannot change the current decision.  A
# transposition table, MVV-LVA ordering, killer moves, draw detection, and
# periodic deadline checks reduce work without changing legal semantics.
# Raised internally when a timed search reaches its deadline.  It is a control
# signal for iterative deepening, not a chess error.
class SearchTimeout(Exception):
    pass

EXACT, LOWER, UPPER = 0, 1, 2

# SearchCtx contains data shared by every node of one root search: deadline,
# node count, transposition table, killer table, and evaluation configuration.
class SearchCtx:
    __slots__ = ('deadline', 'nodes', 'tt', 'killers', 'use_pst')
    def __init__(self, deadline, use_pst=True):
        self.deadline = deadline
        self.nodes    = 0
        self.tt       = {}
        self.killers  = [[None, None] for _ in range(MAX_DEPTH + 4)]
        self.use_pst  = use_pst

# Compare move identity without relying on object identity or ordering score.
def _same_move(a, b):
    return a is not None and b is not None and a.key() == b.key()

# Order likely-good moves first so alpha-beta cutoffs happen earlier.  Priority
# is: TT move, profitable captures via MVV-LVA, then remembered killer moves.
def _order_moves(moves, tt_move, ctx, ply):
    for m in moves:
        s = 0
        if m.captured:
            s = 1000 + 10 * PIECE_VALUES[m.captured & 7] - PIECE_VALUES[m.piece & 7]
        if tt_move and m.key() == tt_move.key():
            s = 1_000_000
        elif not m.captured:
            if _same_move(m, ctx.killers[ply][0]):
                s = 900
            elif _same_move(m, ctx.killers[ply][1]):
                s = 800
        m.score = s
    moves.sort(key=lambda m: -m.score)

# Normalise mate scores before TT storage so the stored value remains valid
# when the same position is reached at a different ply.
def _score_to_tt(score, ply):
    if score >= MATE_THRESHOLD:
        return score + ply
    if score <= -MATE_THRESHOLD:
        return score - ply
    return score

# Convert a TT-normalised mate score back to the current search ply.
def _score_from_tt(score, ply):
    if score >= MATE_THRESHOLD:
        return score - ply
    if score <= -MATE_THRESHOLD:
        return score + ply
    return score

# Test whether the current hash has occurred twice earlier inside the reversible
# halfmove window; together with the current occurrence this is threefold.
def _is_repetition(board):
    h = board.history[-1]
    n = len(board.history) - 1
    lookback = min(board.halfmove, n)
    cnt = 0
    for i in range(n - 1, n - 1 - lookback, -1):
        if board.history[i] == h:
            cnt += 1
            if cnt >= 2:
                return True
    return False

# Recursive negamax alpha-beta search.  The routine first handles deadline and
# draw conditions, then probes the TT, evaluates leaves, orders moves, explores
# legal children, detects mate/stalemate, and finally stores a bounded TT entry.
def search(board, depth, alpha, beta, ply, ctx):
    # Deadline checks are amortised: querying the clock every node would add
    # avoidable overhead, so the search samples it once per 1024 nodes.
    ctx.nodes += 1
    if (ctx.nodes & 1023) == 0 and time.monotonic() > ctx.deadline:
        raise SearchTimeout

    # Draw nodes are neutral.  Repetition is skipped at ply 0 because the root
    # caller is choosing a move from the current game position, not adjudicating
    # that position as a recursive continuation.
    if ply > 0 and _is_repetition(board):
        return 0
    if board.halfmove >= 100:
        return 0

    # Probe the transposition table before expanding the node.  EXACT values can
    # return immediately; LOWER/UPPER bounds return only when they already prove
    # a beta cutoff or alpha fail-low for the current window.
    key = board.hash()
    entry = ctx.tt.get(key)
    tt_move = None
    if entry is not None:
        e_depth, e_score, e_flag, e_move = entry
        tt_move = e_move
        if e_depth >= depth:
            s = _score_from_tt(e_score, ply)
            if   e_flag == EXACT: return s
            elif e_flag == LOWER and s >= beta:  return s
            elif e_flag == UPPER and s <= alpha: return s

    # Depth zero is a static leaf.  There is no quiescence search in this small
    # reference engine.
    if depth <= 0:
        return evaluate(board, ctx.use_pst)

    moves = generate_pseudo_legal(board)
    _order_moves(moves, tt_move, ctx, ply)

    best_score = -INF
    best_move  = None
    legal      = 0
    orig_alpha = alpha
    side       = board.side

    # Pseudo-legal generation avoids repeated make/unmake work in the generator;
    # each candidate is legalised here by rejecting self-check.
    for m in moves:
        undo = make_move(board, m)
        if in_check(board, side):
            unmake_move(board, undo)
            continue
        legal += 1
        # Negamax swaps and negates the alpha-beta window because the child is
        # evaluated from the opponent's side-to-move perspective.
        score = -search(board, depth - 1, -beta, -alpha, ply + 1, ctx)
        unmake_move(board, undo)

        if score > best_score:
            best_score = score
            best_move  = m
        if score > alpha:
            alpha = score
        # A beta cutoff means later siblings cannot improve the parent's choice.
        # Quiet cutoff moves are remembered as killers for this ply.
        if alpha >= beta:
            if not m.captured:
                k = ctx.killers[ply]
                if not _same_move(m, k[0]):
                    k[1] = k[0]
                    k[0] = m
            break

    # No legal moves means mate if the side is checked, otherwise stalemate.
    # Adding ply prefers faster mates and delays unavoidable losses.
    if legal == 0:
        return -MATE + ply if in_check(board, side) else 0

    # Classify the result relative to the original search window before storing
    # it.  Future probes can then distinguish exact values from one-sided bounds.
    if best_score <= orig_alpha:
        flag = UPPER
    elif best_score >= beta:
        flag = LOWER
    else:
        flag = EXACT
    ctx.tt[key] = (depth, _score_to_tt(best_score, ply), flag, best_move)
    return best_score

# =============================================================================
# 12. ITERATIVE DEEPENING ROOT SEARCH
# =============================================================================
# Iterative deepening completes depth 1 before depth 2, and so on.  This yields
# a usable move if a time limit interrupts a deeper iteration and also gives the
# previous best move priority in the next iteration's ordering.
# Search the root repeatedly at increasing depth.  Only a fully completed
# iteration replaces ``best_move``; a timeout therefore preserves the best move
# from the last completed depth.
def find_best_move(board, max_depth, time_limit=None, use_pst=True):
    # A missing time limit becomes an infinite deadline.  One context—and thus
    # one TT and killer table—is reused across all iterative-deepening passes.
    deadline = time.monotonic() + time_limit if time_limit else float('inf')
    ctx = SearchCtx(deadline, use_pst)
    best_move = None

    # Each completed iteration produces a stable fallback move.  A later timeout
    # cannot erase that result because ``best_move`` is updated only after the
    # root loop for a depth has finished.
    for d in range(1, max_depth + 1):
        try:
            # Root move generation is fully legal rather than pseudo-legal,
            # simplifying the root loop and handling terminal positions early.
            moves = generate_legal_moves(board)
            if not moves:
                return None
            _order_moves(moves, best_move, ctx, 0)

            alpha      = -INF
            this_best  = None
            this_score = -INF
            side       = board.side

            for m in moves:
                undo = make_move(board, m)
                score = -search(board, d - 1, -INF, -alpha, 1, ctx)
                unmake_move(board, undo)
                if score > this_score:
                    this_score = score
                    this_best  = m
                if score > alpha:
                    alpha = score

            best_move = this_best
        except SearchTimeout:
            break
        if abs(this_score) > MATE_THRESHOLD:
            break

    return best_move

# =============================================================================
# 13. PERFT VALIDATION
# =============================================================================
# Perft counts legal leaf nodes at an exact depth.  It does not evaluate
# positions; its purpose is to expose move-generation, make/unmake, castling,
# promotion, and en-passant defects by comparing known node counts.
# Count legal move-tree leaves.  Because it uses the normal make/unmake and
# king-safety path, perft is an end-to-end move-generation integrity check.
def perft(board, depth):
    # Every reached position at depth zero contributes exactly one leaf.
    if depth == 0:
        return 1
    total = 0
    side = board.side
    for m in generate_pseudo_legal(board):
        undo = make_move(board, m)
        if not in_check(board, side):
            total += perft(board, depth - 1)
        unmake_move(board, undo)
    return total

# =============================================================================
# 14. TERMINAL BOARD DISPLAY
# =============================================================================
# Display converts mailbox rows back to chess ranks and uses upper-case pieces
# for White and lower-case pieces for Black.  It is deliberately independent of
# search so diagnostic and perft modes can remain lightweight.
# Render the current board from rank 8 down to rank 1.
def display_board(board):
    # The border width matches eight one-character cells plus seven spaces.
    sep = "  +" + "-" * 17 + "+"
    print(sep)
    for r in range(9, 1, -1):
        rank = r - 1
        row = []
        for c in range(1, 9):
            p = board.get(r, c)
            if p == EMPTY:
                row.append(".")
            else:
                t = p & 7
                ch = PIECE_CHARS[t] if 1 <= t <= 6 else "?"
                if p & BLACK:
                    ch = ch.lower()
                row.append(ch)
        print(f"{rank} | " + " ".join(row) + " |")
    print(sep)
    print("    A B C D E F G H")

# =============================================================================
# 15. INPUT PARSING
# =============================================================================
# Human input uses coordinate notation (for example e2e4 or e7e8q).  Parsing is
# intentionally forgiving about case, spaces, and an optional dash, while move
# legality is enforced later by matching against the generated legal list.
# Centralise terminal input so EOF and Ctrl-C produce a clean caller-visible
# sentinel instead of a traceback.
def _safe_input(prompt):
    # EOF and Ctrl-C both mean "leave the current interactive prompt cleanly".
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return None

# Parse coordinate notation into mailbox coordinates.  This function validates
# syntax and board range only; legal-move membership is checked by the game loop.
def parse_move(s):
    if not s:
        return None
    s = s.strip().upper().replace(" ", "").replace("-", "")
    if len(s) < 4:
        return None
    try:
        fc = ord(s[0]) - ord('A') + 1
        fr = int(s[1]) + 1
        tc = ord(s[2]) - ord('A') + 1
        tr = int(s[3]) + 1
    except (ValueError, IndexError):
        return None
    if not (1 <= fc <= 8 and 1 <= tc <= 8 and 2 <= fr <= 9 and 2 <= tr <= 9):
        return None
    promo = None
    if len(s) >= 5:
        # Only the four legal promotion pieces affect the parsed move; any
        # other fifth character leaves promotion unspecified.
        if s[4] == 'Q': promo = QUEEN
        elif s[4] == 'R': promo = ROOK
        elif s[4] == 'B': promo = BISHOP
        elif s[4] == 'N': promo = KNIGHT
    return (fr, fc, tr, tc, promo)

# =============================================================================
# 16. PGN-LIKE MOVE FORMATTING
# =============================================================================
# This formatter emits compact SAN-like tokens sufficient for the program's PGN
# transcript.  It handles castling, captures, promotion, check, and mate.  It
# does not attempt full SAN disambiguation between same-type pieces.
# Convert an executed move into the transcript's SAN-like token.  Board-before
# state is intentionally unnecessary for the subset emitted here.
def format_pgn_move(move, is_check, is_mate):
    # No board snapshot is required here.  The move itself contains the piece,
    # capture, promotion, and castling data needed by this formatter.
    piece = move.piece & 7
    if move.flags & FLAG_CASTLE_K:
        return "O-O" + ("#" if is_mate else ("+" if is_check else ""))
    if move.flags & FLAG_CASTLE_Q:
        return "O-O-O" + ("#" if is_mate else ("+" if is_check else ""))
    files = "abcdefgh"
    dest = files[move.to_c - 1] + str(move.to_r - 1)
    if piece == PAWN:
        prefix = ""
        if move.captured:
            prefix = files[move.from_c - 1] + "x"
        s = prefix + dest
        if move.flags & FLAG_PROMOTION and move.promo:
            s += "=" + {QUEEN:'Q', ROOK:'R', BISHOP:'B', KNIGHT:'N'}[move.promo]
    else:
        letter = PIECE_CHARS[piece]
        s = letter
        if move.captured:
            s += "x"
        s += dest
    if is_mate:
        s += "#"
    elif is_check:
        s += "+"
    return s

# =============================================================================
# 17. GAME-TERMINATION RULES
# =============================================================================
# Terminal-state detection is kept at game-loop level.  Search has its own draw
# checks because recursive nodes must recognise repetition and the 50-move rule
# before the user interface is involved.
# Return a human-readable terminal result, or None while play can continue.
def game_result(board):
    if not generate_legal_moves(board):
        if in_check(board, board.side):
            winner = "Black" if board.side == WHITE_SIDE else "White"
            return f"{winner} wins by checkmate"
        return "Stalemate — draw"
    if board.halfmove >= 100:
        return "Draw by 50-move rule"
    # 3-fold repetition in the real game
    if board.history:
        h = board.history[-1]
        if board.history.count(h) >= 3:
            return "Draw by threefold repetition"
    return None

# =============================================================================
# 18. COMMAND-LINE INTERFACE AND GAME LOOP
# =============================================================================
# main() wires together validation mode, player configuration, board display,
# human move selection, computer search, rule reporting, and optional PGN
# output.  Engine primitives above remain usable independently for tests.
# Parse CLI options, optionally run perft, then conduct an interactive game.
def main():
    # CLI options expose search/evaluation controls without entangling them with
    # the engine's reusable board and search functions.
    parser = argparse.ArgumentParser(description="16K Chess — Python port")
    parser.add_argument("--depth", type=int, default=None,
                        help=f"search depth 1..{MAX_DEPTH}")
    parser.add_argument("--side", choices=["W", "B"], default=None,
                        help="human side")
    parser.add_argument("--perft", type=int, default=None,
                        help="run perft to the given depth and exit")
    parser.add_argument("--pgn", metavar="FILE", default=None,
                        help="write the game as PGN to FILE")
    parser.add_argument("--no-pst", action="store_true",
                        help="disable piece-square tables (material only)")
    parser.add_argument("--time", type=float, default=None,
                        help="per-move time limit in seconds")
    args = parser.parse_args()

    use_pst = not args.no_pst

    # Perft bypasses all interactive setup and exists solely for engine
    # validation and regression checks.
    # ---- perft mode ----
    if args.perft is not None:
        board = Board()
        init_board(board)
        for d in range(1, args.perft + 1):
            t0 = time.monotonic()
            n = perft(board, d)
            dt = time.monotonic() - t0
            print(f"perft({d}) = {n}  ({dt:.3f}s)")
        return

    print("=" * 52)
    print("   ZX-UX CHESS")
    print("   Sinclair ZX Spectrum 48K Unix")
    print("   One Z80 @ 3.5 MHz vs a human")
    print("=" * 52)
    print()

    # Choose the human colour either from the command line or interactively.
    # ---- side ----
    if args.side is not None:
        human_side = WHITE_SIDE if args.side == 'W' else BLACK_SIDE
    else:
        human_side = None
        while human_side is None:
            a = _safe_input("PLAY WHITE OR BLACK? (W/B) ")
            if a is None:
                return
            a = a.strip().upper()
            if a in ('W', 'WHITE', '1'):
                human_side = WHITE_SIDE
            elif a in ('B', 'BLACK', '2'):
                human_side = BLACK_SIDE
            else:
                print("Please enter W or B.")

    # Search depth is clamped when supplied programmatically and validated when
    # entered interactively.
    # ---- level ----
    if args.depth is not None:
        level = max(1, min(MAX_DEPTH, args.depth))
    else:
        level = None
        while level is None:
            a = _safe_input(f"SELECT LOOK AHEAD (1-{MAX_DEPTH}): ")
            if a is None:
                return
            a = a.strip()
            if a.isdigit() and 1 <= int(a) <= MAX_DEPTH:
                level = int(a)
            else:
                print(f"Please enter a number 1..{MAX_DEPTH}.")

    board = Board()
    init_board(board)

    side_name = 'White' if human_side == WHITE_SIDE else 'Black'
    print(f"\nYou play {side_name}. Level {level}.")
    print("Enter moves as e2e4 (or 'e7e8q' to promote). 'quit' to exit.\n")

    pgn_moves = []

    # One loop iteration represents one side-to-move position: show it, test
    # termination, then obtain either a human move or a searched computer move.
    while True:
        display_board(board)

        res = game_result(board)
        if res:
            print(f"\n*** {res} ***")
            if pgn_moves:
                print("PGN: " + " ".join(pgn_moves))
                if args.pgn:
                    with open(args.pgn, "w") as f:
                        f.write("[Event \"16K Chess\"]\n")
                        f.write(f"[White \"{'Human' if human_side == WHITE_SIDE else 'Computer'}\"]\n")
                        f.write(f"[Black \"{'Human' if human_side == BLACK_SIDE else 'Computer'}\"]\n")
                        f.write(f"[Result \"*\"]\n\n")
                        # wrap PGN at ~80 chars
                        line, lines = "", []
                        for i, tok in enumerate(pgn_moves):
                            if i % 2 == 0:
                                line += f"{i//2 + 1}. "
                            line += tok + " "
                            if len(line) > 72:
                                lines.append(line.rstrip())
                                line = ""
                        if line:
                            lines.append(line.rstrip())
                        f.write("\n".join(lines) + "\n")
                    print(f"(PGN written to {args.pgn})")
            _safe_input("\nPress Enter to exit...")
            return

        if board.side == human_side:
            # Human text is parsed first, then matched against the generated
            # legal list.  Promotion defaults to queen when the suffix is absent.
            while True:
                s = _safe_input("YOUR MOVE: ")
                if s is None:
                    return
                if s.strip().lower() in ('quit', 'exit', 'q'):
                    print("Goodbye.")
                    return
                parsed = parse_move(s)
                if parsed is None:
                    print("Invalid format. Try e2e4 or e7e8q.")
                    continue
                fr, fc, tr, tc, promo = parsed
                legal  = generate_legal_moves(board)
                chosen = None
                for m in legal:
                    if m.from_r == fr and m.from_c == fc \
                       and m.to_r == tr and m.to_c == tc:
                        if m.flags & FLAG_PROMOTION:
                            if promo and m.promo == promo:
                                chosen = m
                                break
                            if promo is None and m.promo == QUEEN:
                                chosen = m
                                break
                        else:
                            chosen = m
                            break
                if chosen is None:
                    print("Illegal move. Try again.")
                    continue

                # Format after execution so the caller can append check/mate
                # suffixes determined from the resulting position.
                make_move(board, chosen)
                is_check = in_check(board, board.side)
                is_mate  = is_check and not generate_legal_moves(board)
                pgn_moves.append(format_pgn_move(chosen, is_check, is_mate))

                print()
                if is_check and not is_mate:
                    print("  (CHECK!)")
                elif is_mate:
                    print("  (CHECKMATE!)")
                break
        else:
            # Computer turns use the configured iterative-deepening search.
            print("Thinking...")
            t0 = time.monotonic()
            best = find_best_move(board, level,
                                  time_limit=args.time, use_pst=use_pst)
            dt = time.monotonic() - t0

            # An extremely small time budget can expire before one root move
            # completes.  Fall back to a legal move rather than misreporting a
            # non-terminal position as having no move.
            if best is None:
                legal = generate_legal_moves(board)
                if not legal:
                    print("No legal move.")
                    return
                best = legal[0]

            make_move(board, best)
            is_check = in_check(board, board.side)
            is_mate  = is_check and not generate_legal_moves(board)
            pgn_moves.append(format_pgn_move(best, is_check, is_mate))

            print(f"I MOVE: {best.uci()}  ({dt:.2f}s)\n")
            if is_check and not is_mate:
                print("  (CHECK!)")
            elif is_mate:
                print("  (CHECKMATE!)")


if __name__ == "__main__":
    sys.setrecursionlimit(2000)
    main()
