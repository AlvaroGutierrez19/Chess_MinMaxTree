from ChessPiece import *
from copy import deepcopy

class Board:
    whites = []
    blacks = []
    def __init__(self, game_mode, ai = False, depth = 3, log=False):
        self.board = []
        self.game_mode = game_mode
        self.depth = depth
        self.ai = ai
        self.log = log
        self.en_passant_target = None
        self.en_passant_target_history = []
        self.en_passant_capture_history = []
        self.castling_rook_history = []
        self.promotion_history = []
        self.game_history = []  # pieces moved in the real game (for undo)

    def initialize_board(self):
        for i in range(8):
            self.board.append(['empty_block' for _ in range(8)])
    
    def place_pieces(self):
        self.board.clear()
        self.whites.clear()
        self.blacks.clear()
        self.en_passant_target = None
        self.en_passant_target_history.clear()
        self.en_passant_capture_history.clear()
        self.castling_rook_history.clear()
        self.promotion_history.clear()
        self.game_history.clear()
        self.initialize_board()
        self.whiteKing = King("white", 0, 4,'\u265A')
        self.blackKing = King("black", 7, 4,'\u2654')
        for p in range(8):
            self[1][p] = Pawn("white", 1, p, '\u265F')
            self[6][p] = Pawn("black", 6, p, '\u2659')
        self[0][0] = Rook("white", 0, 0, '\u265C')
        self[0][7] = Rook("white", 0, 7, '\u265C')
        self[7][0] = Rook("black", 7, 0, '\u2656') 
        self[7][7] = Rook("black", 7, 7, '\u2656')
        self[0][1] = Knight("white", 0, 1, '\u265E')
        self[0][6] = Knight("white", 0, 6, '\u265E')
        self[7][1] = Knight("black", 7, 1, '\u2658')
        self[7][6] = Knight("black", 7, 6, '\u2658')
        self[0][2] = Bishop("white", 0, 2, '\u265D')
        self[0][5] = Bishop("white", 0, 5, '\u265D')
        self[7][2] = Bishop("black", 7, 2, '\u2657')
        self[7][5] = Bishop("black", 7, 5, '\u2657')
        self[0][3] = Queen("white", 0, 3, '\u265B')
        self[7][3] = Queen("black", 7, 3, '\u2655')
        self[0][4] = self.whiteKing
        self[7][4] = self.blackKing
        self.whites = [self[0][i] for i in range(8)] + [self[1][i] for i in range(8)]
        self.blacks = [self[7][i] for i in range(8)] + [self[6][i] for i in range(8)]

        if self.game_mode != 0:
            self.reverse()
        
    def reverse(self):
        self.board = self.board[::-1]
        for i in range(8):
            for j in range(8):
                if isinstance(self.board[i][j], ChessPiece):
                    piece = self.board[i][j]
                    piece.x = i
                    piece.y = j

    def make_move(self, piece, x, y, keep_history=False):  # keep_history is for ai look-ahead
        old_x = piece.x
        old_y = piece.y

        is_en_passant = (
            isinstance(piece, Pawn) and
            old_y != y and
            self.board[x][y] == 'empty_block'
        )
        is_castling = isinstance(piece, King) and abs(old_y - y) == 2

        if keep_history:
            self.en_passant_target_history.append(self.en_passant_target)

            if is_en_passant:
                captured = self.board[old_x][y]
                self.board[old_x][y] = 'empty_block'
                piece.set_last_eaten('empty_block')  # placeholder; real captured piece in ep stack
                self.en_passant_capture_history.append((captured, old_x, y))
            else:
                piece.set_last_eaten(self.board[x][y])
                self.en_passant_capture_history.append(None)

            if is_castling:
                rook_col = 7 if y > old_y else 0
                new_rook_col = 5 if y > old_y else 3
                rook = self.board[old_x][rook_col]
                self.board[old_x][new_rook_col] = rook
                self.board[old_x][rook_col] = 'empty_block'
                rook.set_position(old_x, new_rook_col, keep_history=True)
                self.castling_rook_history.append((rook, old_x, rook_col, old_x, new_rook_col))
            else:
                self.castling_rook_history.append(None)
        else:
            if is_en_passant:
                captured = self.board[old_x][y]
                self.board[old_x][y] = 'empty_block'
                (self.whites if captured.color == "white" else self.blacks).remove(captured)
            elif isinstance(self.board[x][y], ChessPiece):
                target = self.board[x][y]
                (self.whites if target.color == "white" else self.blacks).remove(target)

            if is_castling:
                rook_col = 7 if y > old_y else 0
                new_rook_col = 5 if y > old_y else 3
                rook = self.board[old_x][rook_col]
                self.board[old_x][new_rook_col] = rook
                self.board[old_x][rook_col] = 'empty_block'
                rook.set_position(old_x, new_rook_col, keep_history=False)

        self.board[x][y] = self.board[old_x][old_y]
        self.board[old_x][old_y] = 'empty_block'
        self.board[x][y].set_position(x, y, keep_history)

        # Pawn promotion — auto-queen
        promotion_row = 7 if (
            (self.game_mode == 0 and piece.color == "white") or
            (self.game_mode == 1 and piece.color == "black")
        ) else 0
        if isinstance(piece, Pawn) and x == promotion_row:
            unicode_char = '\u265B' if piece.color == "white" else '\u2655'
            queen = Queen(piece.color, x, y, unicode_char)
            self.board[x][y] = queen
            if keep_history:
                self.promotion_history.append((piece, queen))
            else:
                pieces = self.whites if piece.color == "white" else self.blacks
                pieces.remove(piece)
                pieces.append(queen)
        elif keep_history:
            self.promotion_history.append(None)

        # Update en passant target for next move
        if isinstance(piece, Pawn) and abs(old_x - x) == 2:
            self.en_passant_target = ((old_x + x) // 2, y)
        else:
            self.en_passant_target = None
    
    def unmake_move(self, piece):
        x = piece.x
        y = piece.y

        # Undo promotion: swap queen back to pawn before restoring position
        promo = self.promotion_history.pop() if self.promotion_history else None
        if promo:
            pawn, _ = promo
            self.board[x][y] = pawn

        self.board[x][y].set_old_position()
        old_x = piece.x
        old_y = piece.y

        # Undo castling rook
        castle = self.castling_rook_history.pop() if self.castling_rook_history else None
        if castle:
            rook, orig_rx, orig_ry, new_rx, new_ry = castle
            rook.set_old_position()
            self.board[orig_rx][orig_ry] = rook
            self.board[new_rx][new_ry] = 'empty_block'

        self.board[old_x][old_y] = self.board[x][y]

        # Undo en passant or normal capture
        ep_cap = self.en_passant_capture_history.pop() if self.en_passant_capture_history else None
        if ep_cap:
            captured, sq_x, sq_y = ep_cap
            self.board[sq_x][sq_y] = captured  # restore pawn to its actual square
            self.board[x][y] = 'empty_block'   # destination was empty
            piece.get_last_eaten()              # consume placeholder
        else:
            self.board[x][y] = piece.get_last_eaten() or 'empty_block'

        # Restore en passant target
        if self.en_passant_target_history:
            self.en_passant_target = self.en_passant_target_history.pop()
    
    def sync_piece_lists(self):
        """Rebuild whites/blacks from the actual board state (needed after keep_history moves)."""
        self.whites = []
        self.blacks = []
        for row in self.board:
            for sq in row:
                if isinstance(sq, ChessPiece):
                    (self.whites if sq.color == "white" else self.blacks).append(sq)

    def __getitem__(self, item):
        return self.board[item]

    def has_opponent(self, piece, x, y):
        if not self.is_valid_move(x,y):
            return False
        if isinstance(self.board[x][y], ChessPiece):
            return piece.color != self[x][y].color
        return False
    
    def has_friend(self, piece, x, y):
        if not self.is_valid_move(x,y):
            return False
        if isinstance(self.board[x][y], ChessPiece):
            return piece.color == self[x][y].color
        return False
    
    @staticmethod
    def is_valid_move(x, y):
        return 0 <= x < 8 and 0 <= y < 8
    
    def has_empty_block(self, x, y):
        if not self.is_valid_move(x,y):
            return False
        return not isinstance(self[x][y], ChessPiece)
    
    def get_player_color(self):
        return "white" if self.game_mode == 0 else "black"
    
    def king_is_threatened(self, color, move=None):
        if color == "white":
            king = self.whiteKing
            enemies = self.blacks
        else:
            king = self.blackKing
            enemies = self.whites
        threats = []
        for enemy in enemies:
            # Skip ghost pieces captured in the current search branch
            if self.board[enemy.x][enemy.y] is not enemy:
                continue
            moves = enemy.get_moves(self)
            if (king.x, king.y) in moves:
                threats.append(enemy)
        if move and len(threats) == 1 and threats[0].x == move[0] and threats[0].y == move[1]:
            return False
        return True if len(threats) > 0 else False

    def square_is_attacked(self, color, x, y):
        """Check if square (x,y) is attacked by any enemy, by temporarily placing the king there."""
        king = self.whiteKing if color == "white" else self.blackKing
        old_x, old_y = king.x, king.y
        king.x, king.y = x, y
        attacked = self.king_is_threatened(color)
        king.x, king.y = old_x, old_y
        return attacked

    def is_terminal(self):
        terminal1 = self.white_won()
        terminal2 = self.black_won()
        terminal3 = self.draw()
        return terminal1 or terminal2 or terminal3

    def draw(self):
        if not self.king_is_threatened("white") and not self.has_moves("white"):
            return True
        if not self.king_is_threatened("black") and not self.has_moves("black"):
            return True
        if self.insufficient_material():
            return True
        return False

    def white_won(self):
        return self.king_is_threatened("black") and not self.has_moves("black")

    def black_won(self):
        return self.king_is_threatened("white") and not self.has_moves("white")

    def has_moves(self, color):
        for i in range(8):
            for j in range(8):
                if isinstance(self[i][j], ChessPiece) and self[i][j].color == color:
                    piece = self[i][j]
                    if len(piece.filter_moves(piece.get_moves(self), self)) > 0:
                        return True
        return False

    def insufficient_material(self):
        total_white_knights = 0
        total_black_knights = 0
        total_white_bishops = 0
        total_black_bishops = 0
        total_other_white_pieces = 0
        total_other_black_pieces = 0

        for piece in self.whites:
            if piece.type == 'knight':
                total_white_knights += 1
            elif piece.type == 'bishop':
                total_white_bishops += 1
            elif piece.type != 'king':
                total_other_white_pieces += 1

        for piece in self.blacks:
            if piece.type == 'knight':
                total_black_knights += 1
            elif piece.type == 'bishop':
                total_black_bishops += 1
            elif piece.type != 'king':
                total_other_black_pieces += 1

        weak_white_pieces = total_white_bishops + total_white_knights
        weak_black_pieces = total_black_bishops + total_black_knights

        if self.whiteKing and self.blackKing:
            if weak_white_pieces + total_other_white_pieces + weak_black_pieces + total_other_black_pieces == 0:
                return True
            if weak_white_pieces + total_other_white_pieces == 0 and weak_black_pieces == 1:
                return True
            if weak_black_pieces + total_other_black_pieces == 0 and weak_white_pieces == 1:
                return True
        return False

    def evaluate(self):
        white_points = 0
        black_points = 0
        for i in range(8):
            for j in range(8):
                if isinstance(self[i][j], ChessPiece):
                    piece = self[i][j]
                    if piece.color == "white":
                        white_points += piece.get_score()
                    else:
                        black_points += piece.get_score()
        if self.game_mode == 0:
            return black_points - white_points
        return white_points - black_points

    def __str__(self):
        return str(self[::-1]).replace('], ', ']\n')

    def __repr__(self):
        return "Board"

    def unicode_array_rep(self):
        data = deepcopy(self.board)
        for idx, row in enumerate(self):
            for i, p in enumerate(row):
                if isinstance(p, ChessPiece):
                    un = p.unicode
                else:
                    un = '\u25AF'
                data[idx][i] = un
        return data[::-1]

    def get_king(self, piece):
        if piece.color == "white":
            return self.whiteKing
        else:
            return self.blackKing
