import pygame
from ChessPiece import ChessPiece, Pawn, King
from Computer import get_best_move
from pathlib import Path

# ── Layout constants ──────────────────────────────────────────────────────────
BOARD_SIZE = 600
CELL_SIZE  = 75
PANEL_W    = 300
WIN_W      = BOARD_SIZE + PANEL_W   # 900
WIN_H      = BOARD_SIZE + 50        # 650
STATUS_H   = WIN_H - BOARD_SIZE     # 50

ASSETS_DIR = Path(__file__).parent
IMG_DIR    = ASSETS_DIR / 'JohnPablok Cburnett Chess set' / '128px'

# Populated in initialize()
IMAGES     = {}
screen     = None
font       = None        # large  (status / game-over text)
small_font = None        # medium (panel labels)
mono_font  = None        # monospace (move notation)

# Undo button rect (absolute screen coords)
UNDO_BTN = pygame.Rect(BOARD_SIZE + 20, WIN_H - 52, PANEL_W - 40, 36)


# ── Init ──────────────────────────────────────────────────────────────────────
def initialize():
    global screen, font, small_font, mono_font, IMAGES
    pygame.init()
    pygame.font.init()
    pygame.display.set_caption('Chess!')
    pygame.display.set_icon(pygame.image.load(ASSETS_DIR / 'icon.png'))
    screen = pygame.display.set_mode((WIN_W, WIN_H))

    font       = pygame.font.SysFont('Comic Sans MS', 30)
    small_font = pygame.font.SysFont('Arial', 14)
    mono_font  = pygame.font.SysFont('Courier New', 15)

    def load(name):
        return pygame.transform.scale(
            pygame.image.load(IMG_DIR / name), (CELL_SIZE, CELL_SIZE))

    IMAGES['dark_block']  = load('square brown dark_png_shadow_128px.png')
    IMAGES['light_block'] = load('square brown light_png_shadow_128px.png')
    IMAGES['highlight']   = load('highlight_128px.png')

    for color, prefix in (('white', 'w'), ('black', 'b')):
        for piece, name in (('Pawn',   'pawn'),   ('Rook',   'rook'),
                             ('Bishop', 'bishop'), ('Knight', 'knight'),
                             ('King',   'king'),   ('Queen',  'queen')):
            IMAGES[f'{color}{piece}'] = load(f'{prefix}_{name}_png_shadow_128px.png')


# ── Coordinate helpers ────────────────────────────────────────────────────────
def _sq_pixel(row, col):
    """Top-left pixel of board square (row, col)."""
    return col * CELL_SIZE, BOARD_SIZE - (row + 1) * CELL_SIZE


def _click_to_sq(mx, my):
    """Convert screen pixel to board (row, col)."""
    return 7 - my // CELL_SIZE, mx // CELL_SIZE


# ── Drawing ───────────────────────────────────────────────────────────────────
def draw_board(board):
    """Draw tiles then pieces."""
    for row in range(8):
        for col in range(8):
            tile = 'light_block' if (row + col) % 2 == 1 else 'dark_block'
            screen.blit(IMAGES[tile], _sq_pixel(row, col))

    for row in range(8):
        for col in range(8):
            sq = board[row][col]
            if isinstance(sq, ChessPiece):
                key = f'{sq.color}{sq.type[0].upper()}{sq.type[1:]}'
                screen.blit(IMAGES[key], _sq_pixel(row, col))


def draw_panel(notation_log, can_undo):
    """Right-side panel: move history + undo button."""
    # Background + border
    pygame.draw.rect(screen, (28, 28, 28), (BOARD_SIZE, 0, PANEL_W, WIN_H))
    pygame.draw.line(screen, (65, 65, 65), (BOARD_SIZE, 0), (BOARD_SIZE, WIN_H), 2)

    # Title
    title = small_font.render('M O V E S', True, (170, 170, 170))
    screen.blit(title, (BOARD_SIZE + PANEL_W // 2 - title.get_width() // 2, 8))
    pygame.draw.line(screen, (50, 50, 50), (BOARD_SIZE + 8, 26), (WIN_W - 8, 26))

    # Move list
    line_h   = 20
    area_top = 32
    area_bot = UNDO_BTN.top - 10
    max_vis  = (area_bot - area_top) // line_h

    # Group flat log into (move_num, white_note, black_note) pairs
    pairs = []
    for i in range(0, len(notation_log), 2):
        pairs.append((
            i // 2 + 1,
            notation_log[i],
            notation_log[i + 1] if i + 1 < len(notation_log) else '',
        ))

    visible = pairs[-max_vis:] if len(pairs) > max_vis else pairs
    for idx, (num, w_n, b_n) in enumerate(visible):
        y    = area_top + idx * line_h
        n_s  = mono_font.render(f'{num}.', True, (110, 110, 110))
        w_s  = mono_font.render(w_n,       True, (225, 225, 225))
        b_s  = mono_font.render(b_n,       True, (160, 165, 180))
        screen.blit(n_s, (BOARD_SIZE + 6,   y))
        screen.blit(w_s, (BOARD_SIZE + 40,  y))
        screen.blit(b_s, (BOARD_SIZE + 152, y))

    # Undo button
    btn_col = (55, 85, 55)   if can_undo else (38, 38, 38)
    brd_col = (100, 140, 100) if can_undo else (55, 55, 55)
    txt_col = (185, 230, 185) if can_undo else (75, 75, 75)
    pygame.draw.rect(screen, btn_col, UNDO_BTN, border_radius=6)
    pygame.draw.rect(screen, brd_col, UNDO_BTN, 1, border_radius=6)
    lbl = small_font.render('UNDO  (Ctrl+Z)', True, txt_col)
    screen.blit(lbl, (UNDO_BTN.centerx - lbl.get_width() // 2,
                      UNDO_BTN.centery - lbl.get_height() // 2))


def draw_status(text):
    """Status bar below the board."""
    pygame.draw.rect(screen, (0, 0, 0), (0, BOARD_SIZE, BOARD_SIZE, STATUS_H))
    surf = font.render(text, False, (237, 237, 237))
    screen.blit(surf, (BOARD_SIZE // 2 - surf.get_width() // 2, BOARD_SIZE + 8))


# ── Notation ─────────────────────────────────────────────────────────────────
def _build_notation(board, piece, x, y):
    """
    Build algebraic notation string for piece moving to (x, y).
    Must be called BEFORE make_move so we can read the board state.
    """
    _, old_y = piece.x, piece.y
    target   = board[x][y]
    is_cap   = isinstance(target, ChessPiece)
    is_ep    = isinstance(piece, Pawn) and old_y != y and not is_cap
    is_cks   = isinstance(piece, King) and y - old_y == 2
    is_cqs   = isinstance(piece, King) and old_y - y == 2
    prow     = 7 if ((board.game_mode == 0 and piece.color == "white") or
                     (board.game_mode == 1 and piece.color == "black")) else 0
    is_promo = isinstance(piece, Pawn) and x == prow

    if is_cks: return 'O-O'
    if is_cqs: return 'O-O-O'

    # File/rank in standard (white-perspective) notation
    from_file = chr(ord('a') + old_y)
    to_file   = chr(ord('a') + y)
    to_rank   = str(x + 1) if board.game_mode == 0 else str(8 - x)

    LETTERS = {'pawn': '', 'rook': 'R', 'knight': 'N',
               'bishop': 'B', 'queen': 'Q', 'king': 'K'}
    note = LETTERS.get(piece.type, '')
    if piece.type == 'pawn' and (is_cap or is_ep):
        note += from_file
    if is_cap or is_ep:
        note += 'x'
    note += to_file + to_rank
    if is_promo:
        note += '=Q'
    return note


def _make_real_move(board, piece, x, y, notation_log):
    """
    Execute a real game move (with history so it can be undone),
    sync piece lists, record piece in game_history, append notation.
    """
    note = _build_notation(board, piece, x, y)
    board.make_move(piece, x, y, keep_history=True)
    board.sync_piece_lists()
    board.game_history.append(piece)
    notation_log.append(note)


def _ai_move(board, notation_log):
    """Ask the AI for the best move, execute it, log notation. Returns True if a move was made."""
    best = get_best_move(board)
    if not best:
        return False
    piece, x, y = best
    _make_real_move(board, piece, x, y, notation_log)
    return True


# ── Main loop ─────────────────────────────────────────────────────────────────
def start(board):
    notation_log   = []
    possible_moves = []   # list of (row, col) for highlighted squares
    selected       = None # currently selected piece
    game_over      = False
    game_over_txt  = ''
    running        = True

    # ── helpers ──
    def refresh():
        draw_board(board)
        for (r, c) in possible_moves:
            screen.blit(IMAGES['highlight'], _sq_pixel(r, c))
        draw_panel(notation_log, bool(board.game_history))
        if game_over:
            draw_status(game_over_txt)
        pygame.display.update()

    def check_game_over():
        nonlocal game_over, game_over_txt
        if   board.white_won(): game_over, game_over_txt = True, 'WHITE WINS!'
        elif board.black_won(): game_over, game_over_txt = True, 'BLACK WINS!'
        elif board.draw():      game_over, game_over_txt = True, 'DRAW!'

    def do_undo():
        nonlocal game_over, game_over_txt, selected, possible_moves
        if not board.game_history:
            return
        # Undo 2 plies (human + AI) or 1 if fewer moves were made
        n = min(2 if board.ai else 1, len(board.game_history))
        for _ in range(n):
            p = board.game_history.pop()
            board.unmake_move(p)
            board.sync_piece_lists()
            if notation_log:
                notation_log.pop()
        game_over, game_over_txt = False, ''
        selected, possible_moves = None, []

    # AI goes first in game_mode 1 (AI plays white)
    if board.game_mode == 1 and board.ai:
        _ai_move(board, notation_log)

    while running:
        refresh()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Restart after game over
            if game_over and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                return True

            # Ctrl+Z undo
            if (event.type == pygame.KEYDOWN
                    and event.key == pygame.K_z
                    and (pygame.key.get_mods() & pygame.KMOD_CTRL)
                    and not game_over):
                do_undo()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()

                # ── Panel click ──────────────────────────────────────────────
                if mx >= BOARD_SIZE:
                    if UNDO_BTN.collidepoint(mx, my) and not game_over:
                        do_undo()
                    continue

                if game_over:
                    continue

                # ── Board click ──────────────────────────────────────────────
                row, col = _click_to_sq(mx, my)
                if not (0 <= row < 8 and 0 <= col < 8):
                    continue

                sq           = board[row][col]
                player_color = board.get_player_color()

                # Select a piece
                if (isinstance(sq, ChessPiece)
                        and (not board.ai or sq.color == player_color)
                        and (row, col) not in possible_moves):
                    selected       = sq
                    possible_moves = selected.filter_moves(selected.get_moves(board), board)

                # Execute move on a highlighted square
                elif selected and (row, col) in possible_moves:
                    _make_real_move(board, selected, row, col, notation_log)
                    selected, possible_moves = None, []
                    check_game_over()

                    if board.ai and not game_over:
                        _ai_move(board, notation_log)
                        check_game_over()

                # Click elsewhere — deselect
                else:
                    selected, possible_moves = None, []

    return False
