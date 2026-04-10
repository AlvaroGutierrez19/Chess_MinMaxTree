import sys
from Board import Board
import graphics

def main():
    """
    game_mode 0 → white is human (plays from bottom), black is AI
    game_mode 1 → black is human (plays from bottom), white is AI
    ai=True     → enable AI opponent
    depth       → minimax search depth (3 is fast, 4-5 is stronger but slower)
    """
    game_mode = 0
    ai = True
    depth = 3

    graphics.initialize()
    board = Board(game_mode=game_mode, ai=ai, depth=depth)
    board.place_pieces()
    graphics.draw_board(board)

    while True:
        restart = graphics.start(board)
        if not restart:
            break
        board.place_pieces()
        graphics.draw_board(board)

if __name__ == '__main__':
    main()
