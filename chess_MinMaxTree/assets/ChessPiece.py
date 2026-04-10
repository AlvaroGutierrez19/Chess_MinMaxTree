class ChessPiece:
    # History of moves and captures for this piece setted for each piece, to be used in the MinMaxTree for move generation and evaluation

    
    def __init__(self, color, x, y, unicode):
        self.eaten_pieces_history = []
        self.has_moved_history = []
        self.position_history = []
        self.moved = False
        self.color = color
        self.x = x
        self.y = y
        self.unicode = unicode
        self.type = self.__class__.__name__.lower()

    def filter_moves(self, moves, board):
        final_moves = moves[:]
        for move in moves:
            board.make_move(self, move[0], move[1], keep_history=True)
            if board.king_is_threatened(self.color, move):
                final_moves.remove(move)
            board.unmake_move(self)
        return final_moves
    
    def get_moves(self, board):
        pass

    def get_last_eaten(self):
        if self.eaten_pieces_history:
            return self.eaten_pieces_history.pop()
        return None
    
    def set_last_eaten(self, piece):
        self.eaten_pieces_history.append(piece)
    
    def set_position(self, x, y, keep_history=True):
        if keep_history:
            self.position_history.append(self.x)
            self.position_history.append(self.y)
            self.has_moved_history.append(self.moved)
        self.x = x
        self.y = y
        self.moved = True
    
    def set_old_position(self):
        if self.position_history:
            self.y = self.position_history.pop()
            self.x = self.position_history.pop()
        if self.has_moved_history:
            self.moved = self.has_moved_history.pop()

    def get_score(self):
        return 0
    
    def __repr__(self):
        return '{}: {}|{},{}'.format(self.type, self.color, self.x, self.y)

class Pawn(ChessPiece):
    def get_moves(self, board):
        moves= []
        if board.game_mode == 0 and self.color == "white" or board.game_mode == 1 and self.color=="black":
            direction = 1
        else:
            direction = -1
        x = self.x + direction
        if board.has_empty_block(x, self.y):
            moves.append((x, self.y))
            if not self.moved and board.has_empty_block(x + direction, self.y):
                moves.append((x + direction, self.y))
        if board.is_valid_move(x, self.y - 1) and board.has_opponent(self, x, self.y - 1):
            moves.append((x, self.y - 1))
        if board.is_valid_move(x, self.y + 1) and board.has_opponent(self, x, self.y + 1):
            moves.append((x, self.y + 1))
        # En passant
        if board.en_passant_target:
            ep_x, ep_y = board.en_passant_target
            if ep_x == x and abs(ep_y - self.y) == 1:
                moves.append((ep_x, ep_y))
        return moves
    def get_score(self):
        return 10
    
class Rook(ChessPiece):
    def get_moves(self, board):
        moves = []
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            for i in range(1, 8):
                nx, ny = self.x + dx*i, self.y + dy*i
                if not board.is_valid_move(nx, ny):
                    break
                if board.has_empty_block(nx, ny):
                    moves.append((nx, ny))
                elif board.has_opponent(self, nx, ny):
                    moves.append((nx, ny))
                    break
                else:
                    break
        return moves

    def get_score(self):
        return 30


class Knight(ChessPiece):
    def get_moves(self, board):
        moves = []
        for dx, dy in [(2,1), (2,-1), (-2,1), (-2,-1), (1,2), (1,-2), (-1,2), (-1,-2)]:
            nx, ny = self.x + dx, self.y + dy
            if board.is_valid_move(nx, ny) and not board.has_friend(self, nx, ny):
                moves.append((nx, ny))
        return moves

    def get_score(self):
        return 20
    
class Bishop(ChessPiece):
    def get_moves(self, board):
        moves = []
        for dx, dy in [(1,1), (1,-1), (-1,1), (-1,-1)]:
            for i in range(1, 8):
                nx, ny = self.x + dx*i, self.y + dy*i
                if not board.is_valid_move(nx, ny):
                    break
                if board.has_empty_block(nx, ny):
                    moves.append((nx, ny))
                elif board.has_opponent(self, nx, ny):
                    moves.append((nx, ny))
                    break
                else:
                    break
        return moves

    def get_score(self):
        return 30

class Queen(ChessPiece):
    # i could have inherited from Rook and Bishop but i prefer to keep it simple and just copy the code, since it's not that much
    def get_moves(self, board):
        moves = []
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1), (1,1), (1,-1), (-1,1), (-1,-1)]:
            for i in range(1, 8):
                nx, ny = self.x + dx*i, self.y + dy*i
                if not board.is_valid_move(nx, ny):
                    break
                if board.has_empty_block(nx, ny):
                    moves.append((nx, ny))
                elif board.has_opponent(self, nx, ny):
                    moves.append((nx, ny))
                    break
                else:
                    break
        return moves

    def get_score(self):
        return 90
class King(ChessPiece):
    _checking_castling = False  # class-level guard to prevent infinite recursion

    def get_moves(self, board):
        moves = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = self.x + dx, self.y + dy
                if board.is_valid_move(nx, ny) and not board.has_friend(self, nx, ny):
                    moves.append((nx, ny))
        # Castling — skip if recursing through king_is_threatened
        if not self.moved and not King._checking_castling:
            King._checking_castling = True
            try:
                if not board.king_is_threatened(self.color):
                    # Kingside (short castling)
                    rook = board[self.x][7]
                    if isinstance(rook, Rook) and not rook.moved:
                        if board.has_empty_block(self.x, 5) and board.has_empty_block(self.x, 6):
                            if not board.square_is_attacked(self.color, self.x, 5):
                                moves.append((self.x, 6))
                    # Queenside (long castling)
                    rook = board[self.x][0]
                    if isinstance(rook, Rook) and not rook.moved:
                        if (board.has_empty_block(self.x, 1) and
                                board.has_empty_block(self.x, 2) and
                                board.has_empty_block(self.x, 3)):
                            if not board.square_is_attacked(self.color, self.x, 3):
                                moves.append((self.x, 2))
            finally:
                King._checking_castling = False
        return moves

    def get_score(self):
        return 900
