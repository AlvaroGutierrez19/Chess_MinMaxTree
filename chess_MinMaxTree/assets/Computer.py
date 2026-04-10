from ChessPiece import ChessPiece

INF = float('inf')


def get_all_moves(board, color):
    """Return list of (piece, x, y) for every legal move of the given color."""
    moves = []
    pieces = board.whites if color == "white" else board.blacks
    for piece in list(pieces):
        # Skip ghost pieces: captured in this search branch but not yet removed
        # from the list (keep_history=True doesn't remove from whites/blacks).
        if board[piece.x][piece.y] is not piece:
            continue
        for move in piece.filter_moves(piece.get_moves(board), board):
            moves.append((piece, move[0], move[1]))
    return moves


def minimax(board, depth, alpha, beta, maximizing):
    """
    Minimax with alpha-beta pruning.
    The board.evaluate() score is always from the perspective of the AI player
    (positive = good for AI, negative = bad).
    maximizing=True  → AI's turn (tries to maximise score)
    maximizing=False → human's turn (tries to minimise score)
    """
    if depth == 0 or board.is_terminal():
        return board.evaluate(), None

    ai_color    = "black" if board.game_mode == 0 else "white"
    human_color = "white" if board.game_mode == 0 else "black"
    color = ai_color if maximizing else human_color

    best_move = None

    if maximizing:
        best_score = -INF
        for piece, x, y in get_all_moves(board, color):
            board.make_move(piece, x, y, keep_history=True)
            score, _ = minimax(board, depth - 1, alpha, beta, False)
            board.unmake_move(piece)
            if score > best_score:
                best_score = score
                best_move = (piece, x, y)
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
        return best_score, best_move
    else:
        best_score = INF
        for piece, x, y in get_all_moves(board, color):
            board.make_move(piece, x, y, keep_history=True)
            score, _ = minimax(board, depth - 1, alpha, beta, True)
            board.unmake_move(piece)
            if score < best_score:
                best_score = score
                best_move = (piece, x, y)
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return best_score, best_move


def get_best_move(board):
    """Return (piece, x, y) for the best AI move without making it, or None."""
    _, best = minimax(board, board.depth, -INF, INF, maximizing=True)
    return best


def get_ai_move(board):
    """Legacy: make AI move permanently. Use get_best_move for new code."""
    best = get_best_move(board)
    if best:
        piece, x, y = best
        board.make_move(piece, x, y)
