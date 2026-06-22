"""
GobanAI
"""

import tkinter as tk
from tkinter import messagebox
import math
import time
from enum import Enum


class Player(Enum):
    EMPTY = 0
    BLACK = 1
    WHITE = 2


class GameMode(Enum):
    PVP = "双人对战"
    PVE = "人机对战"


class Board:
    """棋盘逻辑"""

    def __init__(self, size=15):
        self.size = size
        self.grid = [[Player.EMPTY for _ in range(size)] for _ in range(size)]
        self.last_move = None
        self.move_history = []

    def get(self, row, col):
        if self._in_bounds(row, col):
            return self.grid[row][col]
        return Player.EMPTY

    def set(self, row, col, player):
        if self._in_bounds(row, col) and self.grid[row][col] == Player.EMPTY:
            self.grid[row][col] = player
            self.last_move = (row, col)
            self.move_history.append((row, col, player))
            return True
        return False

    def _in_bounds(self, row, col):
        return 0 <= row < self.size and 0 <= col < self.size

    def get_empty_positions(self):
        return [(r, c) for r in range(self.size) for c in range(self.size)
                if self.grid[r][c] == Player.EMPTY]

    def is_full(self):
        return len(self.get_empty_positions()) == 0

    def get_candidate_positions(self, radius=2):
        candidates = set()
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] != Player.EMPTY:
                    for dr in range(-radius, radius + 1):
                        for dc in range(-radius, radius + 1):
                            nr, nc = r + dr, c + dc
                            if self._in_bounds(nr, nc) and self.grid[nr][nc] == Player.EMPTY:
                                candidates.add((nr, nc))
        return list(candidates) if candidates else self.get_empty_positions()

    def check_win(self, player):
        if self.last_move is None:
            return False
        row, col = self.last_move
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]

        for dr, dc in directions:
            count = 1
            for i in range(1, 5):
                r, c = row + dr * i, col + dc * i
                if not self._in_bounds(r, c) or self.grid[r][c] != player:
                    break
                count += 1
            for i in range(1, 5):
                r, c = row - dr * i, col - dc * i
                if not self._in_bounds(r, c) or self.grid[r][c] != player:
                    break
                count += 1
            if count >= 5:
                return True
        return False

    def copy(self):
        new_board = Board(self.size)
        new_board.grid = [row[:] for row in self.grid]
        new_board.last_move = self.last_move
        new_board.move_history = self.move_history[:]
        return new_board


class Evaluator:
    """增强版评估器"""

    def __init__(self):
        self.SCORES = {
            'FIVE': 1000000,
            'LIVE_FOUR': 100000,
            'RUSH_FOUR': 10000,
            'LIVE_THREE': 8000,
            'SLEEP_THREE': 1000,
            'LIVE_TWO': 500,
            'SLEEP_TWO': 100,
            'JUMP_THREE': 6000,
            'JUMP_FOUR': 9000,
        }

    def evaluate(self, board, player):
        opponent = Player.BLACK if player == Player.WHITE else Player.WHITE
        player_score = self._evaluate_player(board, player)
        opponent_score = self._evaluate_player(board, opponent)
        return player_score - opponent_score * 1.2

    def _evaluate_player(self, board, player):
        total_score = 0
        size = board.size
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]

        for r in range(size):
            for c in range(size):
                if board.grid[r][c] == player:
                    for dr, dc in directions:
                        total_score += self._evaluate_sequence(board, r, c, dr, dc, player)
                        total_score += self._evaluate_jump_pattern(board, r, c, dr, dc, player)
        return total_score

    def _evaluate_sequence(self, board, r, c, dr, dc, player):
        r_prev, c_prev = r - dr, c - dc
        if board._in_bounds(r_prev, c_prev) and board.grid[r_prev][c_prev] == player:
            return 0

        count = 0
        block_left = False
        block_right = False

        for i in range(5):
            nr, nc = r + dr * i, c + dc * i
            if not board._in_bounds(nr, nc) or board.grid[nr][nc] != player:
                break
            count += 1

        if count >= 5:
            return self.SCORES['FIVE']

        r_left, c_left = r - dr, c - dc
        if not board._in_bounds(r_left, c_left) or board.grid[r_left][c_left] != Player.EMPTY:
            block_left = True

        r_right, c_right = r + dr * count, c + dc * count
        if not board._in_bounds(r_right, c_right) or board.grid[r_right][c_right] != Player.EMPTY:
            block_right = True

        if count == 4:
            if not block_left and not block_right:
                return self.SCORES['LIVE_FOUR'] * 2
            elif not block_left or not block_right:
                return self.SCORES['RUSH_FOUR']
        elif count == 3:
            if not block_left and not block_right:
                return self.SCORES['LIVE_THREE']
            elif not block_left or not block_right:
                return self.SCORES['SLEEP_THREE']
        elif count == 2:
            if not block_left and not block_right:
                return self.SCORES['LIVE_TWO']
            elif not block_left or not block_right:
                return self.SCORES['SLEEP_TWO']

        return 0

    def _evaluate_jump_pattern(self, board, r, c, dr, dc, player):
        score = 0
        for gap in [1, 2]:
            count = 1
            pos = 1
            while pos <= 4:
                nr, nc = r + dr * pos, c + dc * pos
                if not board._in_bounds(nr, nc):
                    break
                if board.grid[nr][nc] == player:
                    count += 1
                elif board.grid[nr][nc] == Player.EMPTY and pos <= 2:
                    pass
                else:
                    break
                pos += 1

            if count >= 4:
                score += self.SCORES['JUMP_FOUR']
            elif count >= 3:
                r_start, c_start = r - dr, c - dc
                r_end, c_end = r + dr * pos, c + dc * pos
                open_start = board._in_bounds(r_start, c_start) and board.grid[r_start][c_start] == Player.EMPTY
                open_end = board._in_bounds(r_end, c_end) and board.grid[r_end][c_end] == Player.EMPTY
                if open_start and open_end:
                    score += self.SCORES['LIVE_THREE'] * 1.5
        return score


class AIEngine:
    """增强版AI引擎"""

    def __init__(self, board_size=15, max_depth=4):
        self.board_size = board_size
        self.max_depth = max_depth
        self.evaluator = Evaluator()
        self.nodes_explored = 0

    def get_best_move(self, board, player, time_limit=2.0):
        self.nodes_explored = 0
        candidates = board.get_candidate_positions(radius=1)

        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        opponent = Player.BLACK if player == Player.WHITE else Player.WHITE

        # 必杀检测
        for move in candidates:
            test_board = board.copy()
            test_board.set(move[0], move[1], player)
            if test_board.check_win(player):
                return move

        # 必防检测
        must_defend = []
        for move in candidates:
            test_board = board.copy()
            test_board.set(move[0], move[1], opponent)
            if test_board.check_win(opponent):
                must_defend.append(move)

        if must_defend:
            return self._choose_best_defense(board, must_defend, player, opponent)

        # 双威胁检测
        for move in candidates:
            test_board = board.copy()
            test_board.set(move[0], move[1], player)
            if self._check_double_threat(test_board, player):
                return move

        for move in candidates:
            test_board = board.copy()
            test_board.set(move[0], move[1], opponent)
            if self._check_double_threat(test_board, opponent):
                return move

        # 正常搜索
        start_time = time.time()
        best_score = -math.inf
        best_move = candidates[0]

        sorted_candidates = self._order_moves(board, candidates, player, opponent)

        for depth in range(1, self.max_depth + 1):
            if time.time() - start_time > time_limit:
                break

            for move in sorted_candidates[:min(20, len(sorted_candidates))]:
                board_copy = board.copy()
                board_copy.set(move[0], move[1], player)

                score = self._minimax(board_copy, depth - 1, -math.inf, math.inf,
                                      False, player, opponent)

                if score > best_score:
                    best_score = score
                    best_move = move

        return best_move

    def _choose_best_defense(self, board, defend_moves, player, opponent):
        best_score = -math.inf
        best_move = defend_moves[0]

        for move in defend_moves:
            board_copy = board.copy()
            board_copy.set(move[0], move[1], player)
            score = self.evaluator.evaluate(board_copy, player)
            attack_potential = self._count_potential(board_copy, player, move)
            total_score = score + attack_potential * 100

            if total_score > best_score:
                best_score = total_score
                best_move = move

        return best_move

    def _check_double_threat(self, board, player):
        threats = 0
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]

        for dr, dc in directions:
            for r in range(board.size):
                for c in range(board.size):
                    if board.grid[r][c] == player:
                        if self._is_threat(board, r, c, dr, dc, player):
                            threats += 1
                            if threats >= 2:
                                return True
        return False

    def _is_threat(self, board, r, c, dr, dc, player):
        count = 0
        block_left = False
        block_right = False

        for i in range(5):
            nr, nc = r + dr * i, c + dc * i
            if not board._in_bounds(nr, nc) or board.grid[nr][nc] != player:
                break
            count += 1

        if count < 3:
            return False

        r_left, c_left = r - dr, c - dc
        if not board._in_bounds(r_left, c_left) or board.grid[r_left][c_left] != Player.EMPTY:
            block_left = True

        r_right, c_right = r + dr * count, c + dc * count
        if not board._in_bounds(r_right, c_right) or board.grid[r_right][c_right] != Player.EMPTY:
            block_right = True

        if count >= 3 and not block_left and not block_right:
            return True
        if count == 4 and (not block_left or not block_right):
            return True

        return False

    def _count_potential(self, board, player, move):
        r, c = move
        potential = 0
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]

        for dr, dc in directions:
            count = 1
            for i in range(1, 5):
                nr, nc = r + dr * i, c + dc * i
                if not board._in_bounds(nr, nc) or board.grid[nr][nc] != player:
                    break
                count += 1
            for i in range(1, 5):
                nr, nc = r - dr * i, c - dc * i
                if not board._in_bounds(nr, nc) or board.grid[nr][nc] != player:
                    break
                count += 1
            potential = max(potential, count)

        return potential

    def _minimax(self, board, depth, alpha, beta, is_maximizing, ai_player, current_player):
        self.nodes_explored += 1

        opponent = Player.BLACK if ai_player == Player.WHITE else Player.WHITE

        if board.check_win(ai_player):
            return 100000 + depth
        if board.check_win(opponent):
            return -100000 - depth

        if depth == 0 or board.is_full():
            return self.evaluator.evaluate(board, ai_player)

        candidates = board.get_candidate_positions(radius=1)
        if not candidates:
            return self.evaluator.evaluate(board, ai_player)

        sorted_candidates = self._order_moves(board, candidates, current_player, opponent)
        sorted_candidates = sorted_candidates[:min(15, len(sorted_candidates))]

        if is_maximizing:
            max_eval = -math.inf
            for move in sorted_candidates:
                board_copy = board.copy()
                board_copy.set(move[0], move[1], current_player)
                eval_score = self._minimax(board_copy, depth - 1, alpha, beta,
                                           False, ai_player,
                                           Player.BLACK if current_player == Player.WHITE else Player.WHITE)
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = math.inf
            for move in sorted_candidates:
                board_copy = board.copy()
                board_copy.set(move[0], move[1], current_player)
                eval_score = self._minimax(board_copy, depth - 1, alpha, beta,
                                           True, ai_player,
                                           Player.BLACK if current_player == Player.WHITE else Player.WHITE)
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval

    def _order_moves(self, board, moves, player, opponent):
        scored = []
        for r, c in moves:
            score = 0
            # 进攻价值
            for dr, dc in [(1, 0), (0, 1), (1, 1), (1, -1)]:
                count = 1
                for i in range(1, 5):
                    nr, nc = r + dr * i, c + dc * i
                    if board._in_bounds(nr, nc) and board.grid[nr][nc] == player:
                        count += 1
                    elif board._in_bounds(nr, nc) and board.grid[nr][nc] == Player.EMPTY:
                        pass
                    else:
                        break
                score += count * count * 10

            # 防守价值
            for dr, dc in [(1, 0), (0, 1), (1, 1), (1, -1)]:
                count = 1
                for i in range(1, 5):
                    nr, nc = r + dr * i, c + dc * i
                    if board._in_bounds(nr, nc) and board.grid[nr][nc] == opponent:
                        count += 1
                    elif board._in_bounds(nr, nc) and board.grid[nr][nc] == Player.EMPTY:
                        pass
                    else:
                        break
                score += count * count * 12

            center = board.size // 2
            distance = abs(r - center) + abs(c - center)
            score += 10 / (distance + 1)

            scored.append((score, r, c))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [(r, c) for _, r, c in scored]


class GobanUI:
    """五子棋图形界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("GobanAI - 五子棋")
        self.root.geometry("750x620")
        self.root.resizable(False, False)

        # 游戏状态
        self.board = Board(15)
        self.game_mode = GameMode.PVE
        self.current_player = Player.BLACK
        self.ai_player = Player.WHITE
        self.human_player = Player.BLACK
        self.ai_engine = AIEngine(15, max_depth=4)
        self.game_over = False

        # 界面参数
        self.cell_size = 35
        self.margin = 30
        self.board_pixel_size = self.cell_size * (self.board.size - 1)

        self.colors = {
            'bg': '#DEB887',
            'line': '#000000',
            'black': '#000000',
            'white': '#FFFFFF',
            'last_move': '#FF0000'
        }

        self._create_widgets()
        self._draw_board()
        self.canvas.bind("<Button-1>", self.on_click)

    def _create_widgets(self):
        """创建界面"""
        main_frame = tk.Frame(self.root)
        main_frame.pack(pady=15)

        # 棋盘
        canvas_width = self.margin * 2 + self.board_pixel_size
        canvas_height = self.margin * 2 + self.board_pixel_size
        self.canvas = tk.Canvas(main_frame, width=canvas_width, height=canvas_height,
                                bg=self.colors['bg'], highlightthickness=1)
        self.canvas.pack(side=tk.LEFT, padx=10)

        # 右侧控制面板
        control_frame = tk.Frame(main_frame, width=180, height=canvas_height)
        control_frame.pack(side=tk.RIGHT, padx=10, fill=tk.Y)
        control_frame.pack_propagate(False)

        # 标题
        tk.Label(control_frame, text="GobanAI", font=('Arial', 22, 'bold')).pack(pady=8)

        # 游戏模式
        mode_frame = tk.LabelFrame(control_frame, text="游戏模式", padx=10, pady=5)
        mode_frame.pack(pady=8, fill=tk.X)

        self.mode_var = tk.StringVar(value="人机对战")
        for mode in [GameMode.PVE, GameMode.PVP]:
            rb = tk.Radiobutton(mode_frame, text=mode.value, variable=self.mode_var,
                                value=mode.value, command=self.change_mode)
            rb.pack(anchor=tk.W)

        # AI难度
        difficulty_frame = tk.LabelFrame(control_frame, text="AI难度", padx=10, pady=5)
        difficulty_frame.pack(pady=8, fill=tk.X)

        self.difficulty_var = tk.IntVar(value=3)
        difficulty_scale = tk.Scale(difficulty_frame, from_=1, to=5, orient=tk.HORIZONTAL,
                                    variable=self.difficulty_var, command=self.change_difficulty,
                                    length=130)
        difficulty_scale.pack(fill=tk.X)

        tk.Label(difficulty_frame, text="1简单 3中等 5困难", font=('Arial', 8)).pack()

        # 状态显示
        self.status_var = tk.StringVar(value="黑棋走")
        status_label = tk.Label(control_frame, textvariable=self.status_var,
                                font=('Arial', 16, 'bold'), fg='#1565C0')
        status_label.pack(pady=12)

        # 按钮
        btn_frame = tk.Frame(control_frame)
        btn_frame.pack(pady=8, fill=tk.X)

        tk.Button(btn_frame, text="新游戏", command=self.new_game,
                  bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'),
                  width=14, height=1).pack(pady=4)

        tk.Button(btn_frame, text="悔棋", command=self.undo_move,
                  bg='#FF9800', fg='white', font=('Arial', 12, 'bold'),
                  width=14, height=1).pack(pady=4)


    def _draw_board(self):
        """绘制棋盘"""
        self.canvas.delete("all")

        # 网格线
        for i in range(self.board.size):
            start = self.margin + i * self.cell_size
            self.canvas.create_line(self.margin, start,
                                    self.margin + self.board_pixel_size, start,
                                    fill=self.colors['line'], width=1)
            self.canvas.create_line(start, self.margin,
                                    start, self.margin + self.board_pixel_size,
                                    fill=self.colors['line'], width=1)

        # 星标
        star_points = [(7, 7)] if self.board.size == 15 else [(3, 3), (3, 11), (11, 3), (11, 11)]
        for r, c in star_points:
            x = self.margin + c * self.cell_size
            y = self.margin + r * self.cell_size
            self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4,
                                    fill=self.colors['line'], outline=self.colors['line'])

        # 棋子
        for r in range(self.board.size):
            for c in range(self.board.size):
                player = self.board.grid[r][c]
                if player != Player.EMPTY:
                    x = self.margin + c * self.cell_size
                    y = self.margin + r * self.cell_size
                    color = self.colors['black'] if player == Player.BLACK else self.colors['white']
                    outline = '#666' if player == Player.WHITE else '#000'
                    self.canvas.create_oval(x - 14, y - 14, x + 14, y + 14,
                                            fill=color, outline=outline, width=1)

        # 最后落子标记
        if self.board.last_move:
            r, c = self.board.last_move
            x = self.margin + c * self.cell_size
            y = self.margin + r * self.cell_size
            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5,
                                    fill=self.colors['last_move'], outline='')

        # 坐标
        for i in range(self.board.size):
            self.canvas.create_text(self.margin + i * self.cell_size,
                                    self.margin + self.board_pixel_size + 15,
                                    text=chr(ord('A') + i), font=('Arial', 8))
            self.canvas.create_text(self.margin - 15,
                                    self.margin + i * self.cell_size,
                                    text=str(i + 1), font=('Arial', 8))

    def on_click(self, event):
        """鼠标点击"""
        if self.game_over:
            return

        if self.game_mode == GameMode.PVE and self.current_player != self.human_player:
            return

        col = round((event.x - self.margin) / self.cell_size)
        row = round((event.y - self.margin) / self.cell_size)

        if not self.board._in_bounds(row, col) or self.board.grid[row][col] != Player.EMPTY:
            return

        self._make_move(row, col)

    def _make_move(self, row, col):
        """执行落子"""
        if not self.board.set(row, col, self.current_player):
            return

        self._draw_board()
        self._update_status()

        if self.board.check_win(self.current_player):
            winner = "黑棋" if self.current_player == Player.BLACK else "白棋"
            self.game_over = True
            self.status_var.set(f"{winner}获胜！🎉")
            messagebox.showinfo("游戏结束", f"{winner}获胜！")
            return

        if self.board.is_full():
            self.game_over = True
            self.status_var.set("平局！")
            messagebox.showinfo("游戏结束", "平局！")
            return

        self.current_player = Player.BLACK if self.current_player == Player.WHITE else Player.WHITE
        self._update_status()

        if (self.game_mode == GameMode.PVE and
                self.current_player == self.ai_player and
                not self.game_over):
            self.root.after(300, self.ai_move)

    def ai_move(self):
        """AI走一步"""
        if self.game_over or self.current_player != self.ai_player:
            return

        self.status_var.set("AI思考中...")
        self.root.update()

        move = self.ai_engine.get_best_move(self.board, self.ai_player, time_limit=2.0)

        if move is None:
            return

        row, col = move
        self._make_move(row, col)

    def _update_status(self):
        """更新状态"""
        if self.game_over:
            return

        if self.game_mode == GameMode.PVE:
            if self.current_player == self.human_player:
                self.status_var.set("你的回合 ●")
            else:
                self.status_var.set("AI思考中...")
        else:
            player_name = "黑棋 ●" if self.current_player == Player.BLACK else "白棋 ○"
            self.status_var.set(f"{player_name}走")

    def change_mode(self):
        mode_str = self.mode_var.get()
        self.game_mode = GameMode.PVE if mode_str == "人机对战" else GameMode.PVP
        self.new_game()

    def change_difficulty(self, val):
        level = int(val)
        depth_map = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6}
        self.ai_engine.max_depth = depth_map.get(level, 4)

    def new_game(self):
        self.board = Board(15)
        self.current_player = Player.BLACK
        self.game_over = False

        if self.game_mode == GameMode.PVE:
            self.human_player = Player.BLACK
            self.ai_player = Player.WHITE
        else:
            self.human_player = Player.BLACK
            self.ai_player = Player.WHITE

        self._draw_board()
        self._update_status()

    def undo_move(self):
        if self.game_over:
            return

        if len(self.board.move_history) < 2:
            messagebox.showinfo("提示", "没有可以悔的棋")
            return

        if self.game_mode == GameMode.PVE:
            for _ in range(2):
                if self.board.move_history:
                    r, c, _ = self.board.move_history.pop()
                    self.board.grid[r][c] = Player.EMPTY
            self.board.last_move = self.board.move_history[-1][:2] if self.board.move_history else None
            self.current_player = self.human_player
        else:
            r, c, _ = self.board.move_history.pop()
            self.board.grid[r][c] = Player.EMPTY
            self.board.last_move = self.board.move_history[-1][:2] if self.board.move_history else None
            self.current_player = Player.BLACK if self.current_player == Player.WHITE else Player.WHITE

        self.game_over = False
        self._draw_board()
        self._update_status()


def main():
    root = tk.Tk()
    app = GobanUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()