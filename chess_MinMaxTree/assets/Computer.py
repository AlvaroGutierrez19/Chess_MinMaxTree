from ChessPiece import ChessPiece

INF = float('inf')

# Set to True to print AI thought process each move
DEBUG = True

# Piece values used for MVV-LVA move ordering
_PIECE_VALUES = {
    'pawn': 100, 'knight': 300, 'bishop': 300,
    'rook': 500, 'queen': 900, 'king': 20000,
}


def _move_order_score(piece, x, y, board):
    """Higher score = try this move first. Captures ordered by MVV-LVA."""
    target = board[x][y]
    if isinstance(target, ChessPiece):
        # Prefer capturing high-value pieces with low-value pieces
        return 10000 + _PIECE_VALUES.get(target.type, 0) - _PIECE_VALUES.get(piece.type, 0)
    return 0


def get_all_moves(board, color):
    """Return list of (piece, x, y) for every legal move, captures ordered first."""
    moves = []
    pieces = board.whites if color == "white" else board.blacks
    for piece in list(pieces):
        if board[piece.x][piece.y] is not piece:
            continue
        for x, y in piece.filter_moves(piece.get_moves(board), board):
            moves.append((_move_order_score(piece, x, y, board), piece, x, y))
    moves.sort(key=lambda m: -m[0])
    return [(p, x, y) for _, p, x, y in moves]


def _board_key(board):
    """Compact board key: piece type/color/moved per square + en-passant target."""
    return (
        tuple(
            (sq.type, sq.color, sq.moved) if isinstance(sq, ChessPiece) else None
            for row in board.board for sq in row
        ),
        board.en_passant_target,
    )


def _move_label(piece, from_y, to_x, to_y, captured):
    """Build a readable label for a move given from/to squares and capture flag."""
    LETTERS = {'pawn': '', 'rook': 'R', 'knight': 'N',
               'bishop': 'B', 'queen': 'Q', 'king': 'K'}
    is_castle_k = piece.type == 'king' and to_y - from_y == 2
    is_castle_q = piece.type == 'king' and from_y - to_y == 2
    if is_castle_k: return 'O-O'
    if is_castle_q: return 'O-O-O'
    note = LETTERS.get(piece.type, '?')
    if piece.type == 'pawn' and captured:
        note += chr(ord('a') + from_y)
    if captured:
        note += 'x'
    note += chr(ord('a') + to_y) + str(to_x + 1)
    return note


def minimax(board, depth, initial_depth, alpha, beta, maximizing, seen, tt):
    """
    Returns (score, pv) where pv is a list of (piece, from_x, from_y, to_x, to_y, captured).
    - depth:         plies remaining
    - initial_depth: total search depth (used to prefer faster mates)
    - seen:          dict {board_key: count} for repetition detection on the current path
    - tt:            transposition table shared across the whole search
    """
    key = _board_key(board)
    if seen.get(key, 0) >= 2:
        return 0, []

    if depth == 0 or board.is_terminal():
        score = board.evaluate()
        if score > 9000:
            score -= (initial_depth - depth)
        elif score < -9000:
            score += (initial_depth - depth)
        return score, []

    # Transposition table lookup
    orig_alpha = alpha
    if key in tt:
        tt_depth, tt_score, tt_flag = tt[key]
        if tt_depth >= depth:
            if tt_flag == 'exact':
                return tt_score, []
            elif tt_flag == 'lower':
                alpha = max(alpha, tt_score)
            elif tt_flag == 'upper':
                beta = min(beta, tt_score)
            if alpha >= beta:
                return tt_score, []

    ai_color    = "black" if board.game_mode == 0 else "white"
    human_color = "white" if board.game_mode == 0 else "black"
    color = ai_color if maximizing else human_color

    seen[key] = seen.get(key, 0) + 1
    best_pv    = []

    if maximizing:
        best_score = -INF
        for piece, x, y in get_all_moves(board, color):
            from_x, from_y = piece.x, piece.y
            captured = isinstance(board[x][y], ChessPiece)
            board.make_move(piece, x, y, keep_history=True)
            score, rest_pv = minimax(board, depth - 1, initial_depth, alpha, beta, False, seen, tt)
            board.unmake_move(piece)
            if score > best_score:
                best_score = score
                best_pv    = [(piece, from_x, from_y, x, y, captured)] + rest_pv
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
    else:
        best_score = INF
        for piece, x, y in get_all_moves(board, color):
            from_x, from_y = piece.x, piece.y
            captured = isinstance(board[x][y], ChessPiece)
            board.make_move(piece, x, y, keep_history=True)
            score, rest_pv = minimax(board, depth - 1, initial_depth, alpha, beta, True, seen, tt)
            board.unmake_move(piece)
            if score < best_score:
                best_score = score
                best_pv    = [(piece, from_x, from_y, x, y, captured)] + rest_pv
            beta = min(beta, best_score)
            if beta <= alpha:
                break

    seen[key] -= 1

    # Store result in transposition table
    if best_score <= orig_alpha:
        tt[key] = (depth, best_score, 'upper')
    elif best_score >= beta:
        tt[key] = (depth, best_score, 'lower')
    else:
        tt[key] = (depth, best_score, 'exact')

    return best_score, best_pv


def _print_debug(board, root_scores):
    """Print the top candidate moves and the principal variation."""
    ai_color = "black" if board.game_mode == 0 else "white"
    print(f"\n{'='*50}")
    print(f"AI ({ai_color}) thinking at depth {board.depth}:")

    # Top moves sorted by score descending
    root_scores.sort(key=lambda t: t[0], reverse=True)
    print(f"\n  Top candidates:")
    for score, piece, _, from_y, to_x, to_y, captured, pv in root_scores[:5]:
        label = _move_label(piece, from_y, to_x, to_y, captured)
        pv_str = ' '.join(
            _move_label(p, fy, tx, ty, cap)
            for p, _fx, fy, tx, ty, cap in pv[1:]  # skip the root move itself
        )
        print(f"    {label:10s} score={score:+.0f}  line: {pv_str}")

    if root_scores:
        best = root_scores[0]
        chosen = _move_label(best[1], best[3], best[4], best[5], best[6])
        print(f"\n  Chosen: {chosen}  (score={best[0]:+.0f})")
    print('='*50)


def get_best_move(board):
    """
    Return (piece, x, y) for the best AI move.
    If DEBUG is True, print all candidate moves with scores and the full PV.
    """
    tt = {}  # transposition table, shared across the entire search
    ai_color = "black" if board.game_mode == 0 else "white"

    if not DEBUG:
        _, pv = minimax(board, board.depth, board.depth, -INF, INF, True, {}, tt)
        if not pv:
            return None
        _, _, _, tx, ty, _ = pv[0]
        return pv[0][0], tx, ty

    # Debug: evaluate every root move individually to get per-move scores.
    # The TT is shared so later root moves benefit from nodes computed earlier.
    root_scores = []
    for piece, x, y in get_all_moves(board, ai_color):
        from_x, from_y = piece.x, piece.y
        captured = isinstance(board[x][y], ChessPiece)
        board.make_move(piece, x, y, keep_history=True)
        score, rest_pv = minimax(board, board.depth - 1, board.depth, -INF, INF, False, {}, tt)
        board.unmake_move(piece)
        full_pv = [(piece, from_x, from_y, x, y, captured)] + rest_pv
        root_scores.append((score, piece, from_x, from_y, x, y, captured, full_pv))

    _print_debug(board, root_scores)

    if not root_scores:
        return None
    root_scores.sort(key=lambda t: t[0], reverse=True)
    best = root_scores[0]
    return best[1], best[4], best[5]


def get_ai_move(board):
    best = get_best_move(board)
    if best:
        piece, x, y = best
        board.make_move(piece, x, y)
