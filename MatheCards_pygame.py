"""
╔══════════════════════════════════════════════════════════════════╗
║        MatheCards: A Dueling Equation Card Game                  ║
║                   Pygame GUI Edition                             ║
╠══════════════════════════════════════════════════════════════════╣
║  HOW TO RUN:                                                     ║
║    pip install pygame                                            ║
║    python MatheCards_pygame.py server      ← host                ║
║    python MatheCards_pygame.py client      ← join                ║
║    python MatheCards_pygame.py             ← menu to choose      ║
║                                                                  ║
║  WHAT CHANGED vs the terminal version:                           ║
║    • Everything from Section O (display helpers) and             ║
║      ClientGame has been replaced with a Pygame GUI.             ║
║    • Sections A–N (config, math, power cards, network,           ║
║      server, game state) are IDENTICAL to the original.          ║
║                                                                  ║
║  GUI STRUCTURE (Sections added):                                 ║
║    Q. PYGAME CONSTANTS     — colors, fonts, card sizes           ║
║    R. UI PRIMITIVES        — draw_card, draw_button, textbox     ║
║    S. SCREENS              — one class per game screen           ║
║       S1. LandingScreen    — name entry + server/client choice   ║
║       S2. ConnectScreen    — enter server IP                     ║
║       S3. WaitScreen       — waiting for opponent                ║
║       S4. CoinTossScreen   — animated coin flip                  ║
║       S5. LobbyScreen      — challenger picks settings           ║
║       S6. PickScreen       — choose a card to send               ║
║       S7. DuelScreen       — solve received card + use powers    ║
║       S8. MinigameScreen   — obstacle card mini-challenge        ║
║       S9. RoundResultScreen— round winner display                ║
║       S10.GameOverScreen   — final result                        ║
║    T. PygameClient         — replaces ClientGame, runs the loop  ║
║    U. MAIN ENTRY POINT     — launch server or GUI client         ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ── STANDARD LIBRARY ─────────────────────────────────────────────
import sys, os, random, math, time, threading, socket, json, uuid, subprocess

# ── AUTO-INSTALL pygame ───────────────────────────────────────────
try:
    import pygame
except ImportError:
    print("Installing pygame…")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import pygame


# ════════════════════════════════════════════════════════════════
# SECTION A — CONFIGURATION
# (identical to original — edit here to change gameplay)
# ════════════════════════════════════════════════════════════════
SERVER_HOST          = "0.0.0.0"
SERVER_PORT          = 9999
PICK_TIMER_SECONDS   = 60
SOLVE_TIMERS         = {"easy": 300, "medium": 180, "hard": 60}
MATH_CARDS_PER_PLAYER  = 7
POWER_CARDS_PER_PLAYER = 3
TOTAL_MATH_CARDS       = MATH_CARDS_PER_PLAYER  * 2
TOTAL_POWER_CARDS      = POWER_CARDS_PER_PLAYER * 2


# ════════════════════════════════════════════════════════════════
# SECTION B — MATH PROBLEM GENERATOR
# (identical to original — add topics here)
# ════════════════════════════════════════════════════════════════
def rnd(a, b): return random.randint(a, b)

def generate_basic(difficulty):
    op = random.choice(["+", "-", "x", "/"])
    if difficulty == "easy":   a, b = rnd(1,20),  rnd(1,20)
    elif difficulty == "medium": a, b = rnd(10,100), rnd(10,50)
    else:                      a, b = rnd(50,999), rnd(10,99)
    if op == "+": return {"question": f"{a} + {b}", "answer": float(a+b), "topic": "basic"}
    if op == "-": b=rnd(1,a); return {"question": f"{a} - {b}", "answer": float(a-b), "topic": "basic"}
    if op == "x": lim=30 if difficulty=="hard" else 12; a,b=rnd(2,lim),rnd(2,lim); return {"question": f"{a} x {b}", "answer": float(a*b), "topic": "basic"}
    b=rnd(2,12); a=b*rnd(1,12); return {"question": f"{a} / {b}", "answer": float(a//b), "topic": "basic"}

def generate_algebra(difficulty):
    if difficulty == "easy":   a,x,b = rnd(1,5),  rnd(1,10),  rnd(0,10)
    elif difficulty == "medium": a,x,b = rnd(2,10), rnd(1,20),  rnd(1,20)
    else:                      a,x,b = rnd(3,15), rnd(-10,20), rnd(-20,20)
    c = a*x + b
    b_str = f"+ {b}" if b >= 0 else f"- {abs(b)}"
    return {"question": f"{a}x {b_str} = {c},  x=?", "answer": float(x), "topic": "algebra"}

def generate_trig(difficulty):
    angles = [(0,0.0,1.0,0.0),(30,0.5,0.87,0.58),(45,0.71,0.71,1.0),
              (60,0.87,0.5,1.73),(90,1.0,0.0,None),(120,0.87,-0.5,-1.73),(180,0.0,-1.0,0.0)]
    pool = angles[:4] if difficulty == "easy" else angles
    deg,sv,cv,tv = random.choice(pool)
    fns = [("sin",sv),("cos",cv)]
    if tv is not None: fns.append(("tan",tv))
    fn,ans = random.choice(fns)
    return {"question": f"{fn}({deg}deg) = ?  (2 dec)", "answer": float(ans), "topic": "trig"}

def generate_geometry(difficulty):
    w,h = rnd(2,20 if difficulty!="hard" else 40), rnd(2,20 if difficulty!="hard" else 40)
    r   = rnd(1, 8 if difficulty!="hard" else 15)
    base,ht = rnd(2,20), rnd(2,20)
    side = rnd(2,15 if difficulty!="hard" else 30)
    a,b,c = random.choice([(3,4,5),(5,12,13),(8,15,17),(7,24,25)])
    problems = [
        (f"Area rect {w}x{h}=?",        float(w*h)),
        (f"Area circle r={r} (pi=3.14)=?", round(3.14*r*r,2)),
        (f"Area triangle b={base} h={ht}=?", float(base*ht/2)),
        (f"Perim square s={side}=?",    float(side*4)),
        (f"Right tri a={a},b={b} c=?",  float(c)),
    ]
    q,ans = random.choice(problems)
    return {"question": q, "answer": ans, "topic": "geometry"}

MATH_GENERATORS = {"basic":generate_basic,"algebra":generate_algebra,
                   "trig":generate_trig,"geometry":generate_geometry}
TOPIC_NAMES = {"basic":"Basic Ops","algebra":"Algebra",
               "trig":"Trigonometry","geometry":"Geometry"}


# ════════════════════════════════════════════════════════════════
# SECTION C — POWER CARD DEFINITIONS  (identical to original)
# ════════════════════════════════════════════════════════════════
POWER_CARD_DEFS = [
    {"id":"hint_digit", "name":"Digit Hint",  "icon":"[D]","type":"aid",     "desc":"Reveals digit count of answer."},
    {"id":"hint_range", "name":"Range Hint",  "icon":"[R]","type":"aid",     "desc":"Above or below 50?"},
    {"id":"hint_sign",  "name":"Sign Hint",   "icon":"[+-]","type":"aid",    "desc":"Positive, negative, or zero?"},
    {"id":"extra_time", "name":"+10 Seconds", "icon":"[+T]","type":"aid",    "desc":"Adds 10s to timer."},
    {"id":"skip_card",  "name":"Skip Card",   "icon":"[SK]","type":"aid",    "desc":"Skip this duel (auto-win)."},
    {"id":"minigame",   "name":"Minigame!",   "icon":"[MG]","type":"obstacle","desc":"Opponent solves minigame."},
    {"id":"freeze",     "name":"Freeze",      "icon":"[FZ]","type":"obstacle","desc":"Freeze opponent timer 8s."},
    {"id":"scramble",   "name":"Scramble",    "icon":"[SC]","type":"obstacle","desc":"Scramble opponent input 5s."},
    {"id":"blind",      "name":"Blind",       "icon":"[BL]","type":"obstacle","desc":"Hide opponent question 5s."},
]


# ════════════════════════════════════════════════════════════════
# SECTION D — NETWORK LAYER  (identical to original)
# ════════════════════════════════════════════════════════════════
def send_msg(sock, msg_type, data=None):
    payload = json.dumps({"type": msg_type, "data": data or {}}) + "\n"
    try: sock.sendall(payload.encode("utf-8"))
    except (BrokenPipeError, OSError): pass

def recv_msg(sock):
    buf = b""
    try:
        while b"\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk: return None
            buf += chunk
        return json.loads(buf.split(b"\n")[0])
    except (json.JSONDecodeError, OSError): return None


# ════════════════════════════════════════════════════════════════
# SECTION D2 — NETWORK SERVER  (identical to original)
# ════════════════════════════════════════════════════════════════
class NetworkServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.players = {}
        self.player_ids = []
        self.game = None

    def start(self):
        self.sock.bind((SERVER_HOST, SERVER_PORT))
        self.sock.listen(2)
        print(f"Server started on port {SERVER_PORT}. Waiting for 2 players…")
        conn1, addr1 = self.sock.accept()
        p1_id = str(uuid.uuid4())[:8]
        self.players[p1_id] = {"conn":conn1,"name":"","hand":[],"powers":[]}
        self.player_ids.append(p1_id)
        send_msg(conn1, "assigned_id", {"id":p1_id,"role":"player1"})
        print(f"Player 1 connected from {addr1[0]}")
        conn2, addr2 = self.sock.accept()
        p2_id = str(uuid.uuid4())[:8]
        self.players[p2_id] = {"conn":conn2,"name":"","hand":[],"powers":[]}
        self.player_ids.append(p2_id)
        send_msg(conn2, "assigned_id", {"id":p2_id,"role":"player2"})
        print(f"Player 2 connected from {addr2[0]}")
        for pid in self.player_ids:
            threading.Thread(target=self._listen_player, args=(pid,), daemon=True).start()
        self.game = GameState(self)
        self.game.run()

    def _listen_player(self, pid):
        conn = self.players[pid]["conn"]
        while True:
            msg = recv_msg(conn)
            if msg is None: print(f"Player {pid} disconnected."); break
            self.game.on_message(pid, msg)

    def relay(self, from_pid, msg_type, data=None):
        for pid in self.player_ids:
            if pid != from_pid: send_msg(self.players[pid]["conn"], msg_type, data or {})

    def broadcast(self, msg_type, data=None):
        for pid in self.player_ids: send_msg(self.players[pid]["conn"], msg_type, data or {})

    def send_to(self, pid, msg_type, data=None):
        send_msg(self.players[pid]["conn"], msg_type, data or {})

    def other(self, pid):
        return self.player_ids[1] if pid == self.player_ids[0] else self.player_ids[0]


# ════════════════════════════════════════════════════════════════
# SECTION D3 — NETWORK CLIENT  (identical to original)
# ════════════════════════════════════════════════════════════════
class NetworkClient:
    def __init__(self, server_ip):
        self.server_ip = server_ip
        self.sock      = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_id     = None
        self.role      = None
        self.inbox     = []
        self._lock     = threading.Lock()

    def connect(self):
        self.sock.connect((self.server_ip, SERVER_PORT))
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        while True:
            msg = recv_msg(self.sock)
            if msg is None: break
            with self._lock: self.inbox.append(msg)

    def wait_for(self, msg_type, timeout=120):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                for i, m in enumerate(self.inbox):
                    if m["type"] == msg_type:
                        self.inbox.pop(i); return m
            time.sleep(0.05)
        return None

    def send(self, msg_type, data=None):
        send_msg(self.sock, msg_type, data or {})

    def peek(self, msg_type):
        """Non-blocking check — returns message without blocking if present."""
        with self._lock:
            for i, m in enumerate(self.inbox):
                if m["type"] == msg_type:
                    self.inbox.pop(i); return m
        return None


# ════════════════════════════════════════════════════════════════
# SECTION E — GAME STATE  (identical to original)
# ════════════════════════════════════════════════════════════════
class GameState:
    def __init__(self, server):
        self.server = server
        self.topic = "basic"; self.difficulty = "medium"; self.total_rounds = 5
        self.scores = {pid: 0 for pid in server.player_ids}
        self.current_round = 1
        self.picks = {}; self.solved = {}; self.hands = {}; self.powers = {}
        self._inbox = []; self._lock = threading.Lock()

    def on_message(self, pid, msg):
        with self._lock: self._inbox.append((pid, msg))

    def wait_for(self, msg_type, timeout=120):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                for i,(pid,msg) in enumerate(self._inbox):
                    if msg["type"] == msg_type: self._inbox.pop(i); return pid,msg
            time.sleep(0.05)
        return None

    def wait_for_both(self, msg_type, timeout=120):
        results = {}; deadline = time.time() + timeout
        while time.time() < deadline and len(results) < 2:
            with self._lock:
                for i in range(len(self._inbox)-1,-1,-1):
                    pid,msg = self._inbox[i]
                    if msg["type"] == msg_type and pid not in results:
                        results[pid] = msg["data"]; self._inbox.pop(i)
            time.sleep(0.05)
        return results if len(results) == 2 else None

    def run(self):
        self._collect_names(); self._coin_toss(); self._lobby()
        while self.current_round <= self.total_rounds:
            self._deal_round(); self._play_round()
            if self._check_game_over(): break
            self.current_round += 1
        self._game_over()

    def _collect_names(self):
        result = self.wait_for_both("set_name", timeout=120)
        if result:
            for pid,data in result.items(): self.server.players[pid]["name"] = data.get("name", f"P_{pid[:4]}")
        p1,p2 = self.server.player_ids
        self.server.send_to(p1,"opp_name",{"name":self.server.players[p2]["name"]})
        self.server.send_to(p2,"opp_name",{"name":self.server.players[p1]["name"]})

    def _coin_toss(self):
        result = random.choice(["heads","tails"])
        p1,p2  = self.server.player_ids
        self.challenger_id = p1 if result=="heads" else p2
        self.server.broadcast("coin_toss",{"result":result,"challenger":self.challenger_id,
                                            "challenger_name":self.server.players[self.challenger_id]["name"]})

    def _lobby(self):
        result = self.wait_for("lobby_settings", timeout=300)
        if result:
            pid,msg = result; d = msg["data"]
            self.topic = d.get("topic","basic"); self.difficulty = d.get("difficulty","medium")
            self.total_rounds = d.get("rounds",5)
        self.server.broadcast("game_starting",{"topic":self.topic,"difficulty":self.difficulty,"rounds":self.total_rounds})
        time.sleep(1)

    def _deal_round(self):
        all_math   = [{**MATH_GENERATORS[self.topic](self.difficulty),"uid":str(uuid.uuid4())[:8]} for _ in range(TOTAL_MATH_CARDS)]
        all_powers = [{**random.choice(POWER_CARD_DEFS),"uid":str(uuid.uuid4())[:8]} for _ in range(TOTAL_POWER_CARDS)]
        random.shuffle(all_math); random.shuffle(all_powers)
        p1,p2 = self.server.player_ids
        self.hands[p1]  = all_math[:MATH_CARDS_PER_PLAYER];  self.hands[p2]  = all_math[MATH_CARDS_PER_PLAYER:]
        self.powers[p1] = all_powers[:POWER_CARDS_PER_PLAYER]; self.powers[p2] = all_powers[POWER_CARDS_PER_PLAYER:]
        self.server.players[p1]["hand"] = self.hands[p1];  self.server.players[p2]["hand"] = self.hands[p2]
        self.server.players[p1]["powers"] = self.powers[p1]; self.server.players[p2]["powers"] = self.powers[p2]
        base = {"round":self.current_round,"total":self.total_rounds,
                "scores":{pid:self.scores[pid] for pid in self.server.player_ids},
                "names":{pid:self.server.players[pid]["name"] for pid in self.server.player_ids}}
        self.server.send_to(p1,"deal_hand",{**base,"math":self.hands[p1],"powers":self.powers[p1],"opp_count":MATH_CARDS_PER_PLAYER})
        self.server.send_to(p2,"deal_hand",{**base,"math":self.hands[p2],"powers":self.powers[p2],"opp_count":MATH_CARDS_PER_PLAYER})

    def _play_round(self):
        self.picks = {}; self.solved = {pid:False for pid in self.server.player_ids}
        while True:
            self.server.broadcast("pick_phase_start",{"timer":PICK_TIMER_SECONDS})
            picks_result = self.wait_for_both("card_picked", timeout=PICK_TIMER_SECONDS+5)
            p1,p2 = self.server.player_ids
            for pid in [p1,p2]:
                if picks_result and pid in picks_result:
                    uid = picks_result[pid].get("uid")
                    self.picks[pid] = next((c for c in self.hands[pid] if c["uid"]==uid), self.hands[pid][0])
                else:
                    self.picks[pid] = self.hands[pid][0]
            self.server.send_to(p1,"received_card",{"card":self.picks[p2]})
            self.server.send_to(p2,"received_card",{"card":self.picks[p1]})
            solve_time = SOLVE_TIMERS[self.difficulty]
            self.server.broadcast("duel_start",{"timer":solve_time})
            self.solved = {pid:False for pid in self.server.player_ids}
            # Both players get to submit until the timer runs out.
            # The loop only exits early if BOTH players have solved.
            # When the FIRST player solves, the remaining time is cut in half
            # to pressure the second player to answer quickly.
            deadline = time.time() + solve_time + 2
            first_solver = None
            while time.time() < deadline:
                result = self.wait_for("answer_submitted", timeout=0.2)
                if result:
                    pid, msg = result
                    if self.solved[pid]: continue
                    recv  = self.picks[self.server.other(pid)]
                    guess = float(msg["data"].get("answer", 999999))
                    ok    = abs(guess - recv["answer"]) <= 0.05
                    self.server.send_to(pid, "answer_result",
                        {"correct": ok, "answer": recv["answer"]})
                    if ok:
                        self.solved[pid] = True
                        if first_solver is None:
                            first_solver = pid
                            # ── CUT REMAINING TIME IN HALF ──
                            # Calculate how many seconds are left, halve them,
                            # and update the deadline so the loop ends sooner.
                            # Minimum 5 seconds so the opponent has a fair chance.
                            remaining = deadline - time.time()
                            halved    = max(5.0, remaining / 2)
                            deadline  = time.time() + halved
                            self.server.broadcast("duel_solved", {
                                "winner_id":    pid,
                                "winner_name":  self.server.players[pid]["name"],
                                "time_left":    int(halved),  # sent to clients
                            })
                        # Only stop when BOTH players have solved
                        if all(self.solved.values()):
                            break

            # Wait 3 seconds so both clients can see the duel outcome
            time.sleep(3)

            # Apply hand changes: remove sent card, keep received if unsolved
            for pid in self.server.player_ids:
                opp  = self.server.other(pid)
                recv = self.picks[opp]
                self.hands[pid] = [c for c in self.hands[pid]
                                   if c["uid"] != self.picks[pid]["uid"]]
                if not self.solved[pid]:
                    self.hands[pid].append(recv)
            for pid in self.server.player_ids:
                self.server.players[pid]["hand"] = self.hands[pid]

            self.server.broadcast("hand_update",
                {p1: len(self.hands[p1]), p2: len(self.hands[p2])})

            empty = [pid for pid in self.server.player_ids
                     if len(self.hands[pid]) == 0]
            if empty:
                winner = empty[0]
                self.scores[winner] += 1
                self.server.broadcast("round_over", {
                    "winner_id":   winner,
                    "winner_name": self.server.players[winner]["name"],
                    "scores":      {pid: self.scores[pid]
                                    for pid in self.server.player_ids}})
                time.sleep(3); return

            # Neither emptied — start next pick cycle
            self.picks = {}
            self.server.broadcast("next_pick", {
                "scores":     {pid: self.scores[pid] for pid in self.server.player_ids},
                "opp_counts": {p1: len(self.hands[p1]), p2: len(self.hands[p2])},
                "pick_timer": PICK_TIMER_SECONDS,
            })

    def _check_game_over(self):
        return any(self.scores[pid] >= math.ceil(self.total_rounds/2) for pid in self.server.player_ids)

    def _game_over(self):
        winner = max(self.scores, key=lambda p: self.scores[p])
        self.server.broadcast("game_over",{"winner_id":winner,"winner_name":self.server.players[winner]["name"],
                                            "scores":self.scores,"names":{pid:self.server.players[pid]["name"] for pid in self.server.player_ids}})


# ════════════════════════════════════════════════════════════════
# SECTION Q — PYGAME CONSTANTS
# Edit colors, sizes, and fonts here.
# ════════════════════════════════════════════════════════════════

W, H = 1100, 700          # window size — change to resize the game

# ── COLORS (R, G, B) ─────────────────────────────────────────────
# Edit these to restyle the entire game at once
BG         = (8,  11,  20)    # background (very dark blue)
SURFACE    = (16, 20,  31)    # card / panel background
SURFACE2   = (24, 29,  46)    # input field background
BORDER     = (40, 48,  70)    # default border
TEXT       = (232,230,244)    # main text
MUTED      = (107,110,138)    # secondary / dim text
ACCENT     = (91, 142,255)    # blue — primary accent
GOLD       = (240,180, 41)    # gold — challenger / winner
DANGER     = (255, 77,109)    # red — obstacles / wrong answers
SUCCESS    = (34, 197, 94)    # green — correct answers
WHITE      = (255,255,255)
BLACK      = (0,  0,   0)

# ── CARD COLORS [background, border, text] ────────────────────────
# TO RESTYLE A CARD TYPE: change its 3 values here
CARD_COLORS = {
    "basic":    ((13, 30, 58),  (26, 64,128), (133,183,235)),
    "algebra":  ((26, 13, 58),  (96, 48,160), (196,160,255)),
    "trig":     ((26, 40, 13),  (59,109, 17), (159,224, 96)),
    "geometry": ((58, 26, 13),  (160, 80,32), (255,192,128)),
    "aid":      ((13, 42, 26),  (21, 96, 58), ( 64,208,144)),
    "obstacle": ((42, 13, 26),  (128, 16,64), (255, 96,144)),
    "back":     ((16, 20, 31),  (40,  48,70), (107,110,138)),
}

# ── CARD SIZE ─────────────────────────────────────────────────────
CARD_W, CARD_H = 90, 126    # pixel size of each card

FPS = 60


# ════════════════════════════════════════════════════════════════
# SECTION R — UI PRIMITIVES
# Low-level drawing helpers used by all screens.
# ════════════════════════════════════════════════════════════════

def init_fonts():
    """
    Call once after pygame.init().
    Returns a dict of font objects keyed by size label.
    Edit the sizes here to change text scaling.
    """
    pygame.font.init()
    try:
        # Try to use a nice system font
        base = pygame.font.match_font("segoeui,helveticaneue,arial")
        mono = pygame.font.match_font("consolas,couriernew,monospace")
    except Exception:
        base = mono = None
    return {
        "title":  pygame.font.Font(base, 52),
        "h1":     pygame.font.Font(base, 32),
        "h2":     pygame.font.Font(base, 22),
        "body":   pygame.font.Font(base, 16),
        "small":  pygame.font.Font(base, 13),
        "mono":   pygame.font.Font(mono, 15),
        "mono_lg":pygame.font.Font(mono, 22),
    }


def draw_rect_border(surf, color, border_color, rect, radius=10, border=1):
    """Draw a rounded rectangle with a border."""
    pygame.draw.rect(surf, color,        rect, border_radius=radius)
    pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def draw_text(surf, fonts, text, size_key, color, cx, cy, anchor="center", max_width=None):
    """
    Draw text on `surf`.
    anchor: "center" | "topleft" | "topright"
    max_width: if set, wraps text to fit within pixel width (returns next y)
    """
    font = fonts[size_key]
    if max_width:
        # Word-wrap
        words = text.split()
        lines = []; line = ""
        for w in words:
            test = line + (" " if line else "") + w
            if font.size(test)[0] <= max_width: line = test
            else:
                if line: lines.append(line)
                line = w
        if line: lines.append(line)
        y = cy
        for l in lines:
            s = font.render(l, True, color)
            r = s.get_rect()
            if anchor == "center":  r.centerx = cx; r.top = y
            elif anchor == "topleft": r.left = cx; r.top = y
            surf.blit(s, r)
            y += r.height + 2
        return y
    else:
        s = font.render(text, True, color)
        r = s.get_rect()
        if   anchor == "center":   r.center   = (cx, cy)
        elif anchor == "topleft":  r.topleft  = (cx, cy)
        elif anchor == "topright": r.topright = (cx, cy)
        surf.blit(s, r)
        return r.bottom


def draw_card(surf, fonts, card, x, y, selected=False, face_down=False, small=False):
    """
    Draw one card at pixel position (x, y).
    Returns the pygame.Rect of the card (for click detection).

    To change card appearance: edit CARD_COLORS in Section Q.
    """
    cw = CARD_W if not small else 70
    ch = CARD_H if not small else 98
    rect = pygame.Rect(x, y, cw, ch)

    topic = card.get("topic", card.get("type", "back")) if not face_down else "back"
    bg, border, fg = CARD_COLORS.get(topic, CARD_COLORS["basic"])

    # Glow when selected
    if selected:
        glow = pygame.Rect(x-3, y-3, cw+6, ch+6)
        pygame.draw.rect(surf, GOLD, glow, border_radius=13)

    draw_rect_border(surf, bg, border, rect, radius=10)

    if face_down:
        # Hatched pattern on back
        for i in range(0, cw+ch, 12):
            pygame.draw.line(surf, BORDER, (x+max(0,i-ch), y+min(ch,i)),
                             (x+min(cw,i), y+max(0,i-cw)), 1)
        return rect

    # Topic label (top)
    topic_label = card.get("topic","").upper()[:6]
    draw_text(surf, fonts, topic_label, "small", (*fg[:3], 160) if len(fg)==3 else fg,
              x+cw//2, y+10, "center")

    if card.get("kind") == "power" or card.get("type") in ("aid","obstacle"):
        # Power card — show icon text + name
        draw_text(surf, fonts, card.get("icon","?"), "body", fg, x+cw//2, y+38, "center")
        draw_text(surf, fonts, card.get("name","?"), "small", fg, x+cw//2, y+58,
                  "center", max_width=cw-8)
    else:
        # Math card — show question (wrapped)
        q = card.get("question","?")
        draw_text(surf, fonts, q, "small", fg, x+cw//2, y+24, "center", max_width=cw-8)

    return rect


def draw_button(surf, fonts, text, rect, color=None, text_color=TEXT, hover=False, radius=8):
    """
    Draw a button and return its Rect.
    Pass hover=True to draw in lighter shade.
    """
    c = color or ACCENT
    if hover:
        c = tuple(min(255, v+30) for v in c)
    draw_rect_border(surf, c, c, rect, radius=radius)
    draw_text(surf, fonts, text, "body", text_color, rect.centerx, rect.centery, "center")
    return rect


def draw_input_box(surf, fonts, text, rect, active=False, placeholder=""):
    """Draw a text input box. active=True highlights the border."""
    border_c = ACCENT if active else BORDER
    draw_rect_border(surf, SURFACE2, border_c, rect, radius=8)
    display = text if text else placeholder
    color   = TEXT if text else MUTED
    # Clip text to box width
    font  = fonts["body"]
    clipped = display
    while font.size(clipped)[0] > rect.width - 16 and len(clipped) > 0:
        clipped = clipped[1:]
    draw_text(surf, fonts, clipped, "body", color, rect.x+10, rect.centery, "topleft")
    if active and time.time() % 1 < 0.5:  # blinking cursor
        cx = rect.x + 10 + font.size(clipped)[0] + 2
        pygame.draw.line(surf, ACCENT, (cx, rect.y+6), (cx, rect.bottom-6), 2)


def draw_timer_bar(surf, left, total, rect):
    """Draw a horizontal timer progress bar."""
    draw_rect_border(surf, SURFACE2, BORDER, rect, radius=4)
    if total > 0:
        pct = max(0, left/total)
        fill = pygame.Rect(rect.x+1, rect.y+1, int((rect.width-2)*pct), rect.height-2)
        color = DANGER if left <= 10 else ACCENT
        if fill.width > 0:
            pygame.draw.rect(surf, color, fill, border_radius=3)


def draw_panel(surf, rect, radius=12):
    """Draw a dark panel (card container background)."""
    draw_rect_border(surf, SURFACE, BORDER, rect, radius=radius)


def draw_hand_row(surf, fonts, cards, start_x, y, selected_uid=None,
                  locked=False, face_down=False, spacing=8):
    """
    Draw a row of cards. Returns list of (rect, card) tuples for hit-testing.
    """
    rects = []
    x = start_x
    for card in cards:
        sel = (not locked) and (card.get("uid") == selected_uid)
        r = draw_card(surf, fonts, card, x, y, selected=sel, face_down=face_down)
        rects.append((r, card))
        x += CARD_W + spacing
    return rects


def toast_surface(fonts, message, color=TEXT):
    """Create a small notification surface (blit near bottom of screen)."""
    font = fonts["body"]
    tw, th = font.size(message)
    s = pygame.Surface((tw+28, th+14), pygame.SRCALPHA)
    pygame.draw.rect(s, (*SURFACE, 230), s.get_rect(), border_radius=8)
    pygame.draw.rect(s, BORDER, s.get_rect(), 1, border_radius=8)
    font.render_to = None  # not using freetype
    ts = font.render(message, True, color)
    s.blit(ts, (14, 7))
    return s


# ════════════════════════════════════════════════════════════════
# SECTION S — SCREENS
# Each screen is a class with:
#   .draw(surf, fonts)   — render everything
#   .handle(event)       — handle pygame events, return next screen name or None
#   .update(dt)          — update timers / animations (dt = seconds since last frame)
# ════════════════════════════════════════════════════════════════

class LandingScreen:
    """S1 — Name entry + choose Server or Client."""

    def __init__(self):
        self.name_text   = ""
        self.ip_text     = ""
        self.active_box  = "name"   # "name" or "ip"
        self.error       = ""
        # Button rects (set in draw)
        self.btn_server  = pygame.Rect(0,0,0,0)
        self.btn_client  = pygame.Rect(0,0,0,0)
        self.box_name    = pygame.Rect(0,0,0,0)
        self.box_ip      = pygame.Rect(0,0,0,0)
        self.hover       = None

    def draw(self, surf, fonts):
        surf.fill(BG)
        cx = W // 2

        # Logo
        draw_text(surf, fonts, "Mathe", "title", TEXT, cx-60, 80, "center")
        draw_text(surf, fonts, "Cards", "title", ACCENT, cx+78, 80, "center")
        draw_text(surf, fonts, "a dueling equation card game", "small", MUTED, cx, 130, "center")

        # Name box
        draw_text(surf, fonts, "YOUR NAME", "small", MUTED, cx-160, 200, "topleft")
        self.box_name = pygame.Rect(cx-160, 218, 320, 40)
        draw_input_box(surf, fonts, self.name_text, self.box_name,
                       active=self.active_box=="name", placeholder="Enter display name")

        # Server IP box
        draw_text(surf, fonts, "SERVER IP  (for client only)", "small", MUTED, cx-160, 278, "topleft")
        self.box_ip = pygame.Rect(cx-160, 296, 320, 40)
        draw_input_box(surf, fonts, self.ip_text, self.box_ip,
                       active=self.active_box=="ip", placeholder="e.g.  192.168.1.5")

        # Buttons
        self.btn_server = pygame.Rect(cx-160, 370, 150, 44)
        self.btn_client = pygame.Rect(cx+10,  370, 150, 44)
        draw_button(surf, fonts, "Host Game",  self.btn_server, GOLD,  BLACK,
                    hover=self.hover=="server")
        draw_button(surf, fonts, "Join Game",  self.btn_client, ACCENT, WHITE,
                    hover=self.hover=="client")

        if self.error:
            draw_text(surf, fonts, self.error, "small", DANGER, cx, 430, "center")

        draw_text(surf, fonts, "Host runs the server. Both players open the game.", "small", MUTED, cx, 480, "center")

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if self.box_name.collidepoint(mx, my): self.active_box = "name"
            elif self.box_ip.collidepoint(mx, my): self.active_box = "ip"
            elif self.btn_server.collidepoint(mx, my):
                if not self.name_text.strip(): self.error = "Enter your name first!"; return None
                return ("server", self.name_text.strip())
            elif self.btn_client.collidepoint(mx, my):
                if not self.name_text.strip(): self.error = "Enter your name first!"; return None
                ip = self.ip_text.strip() or "127.0.0.1"
                return ("client", self.name_text.strip(), ip)
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if self.btn_server.collidepoint(mx, my): self.hover = "server"
            elif self.btn_client.collidepoint(mx, my): self.hover = "client"
            else: self.hover = None
        if event.type == pygame.KEYDOWN:
            box = self.active_box
            txt = self.name_text if box=="name" else self.ip_text
            if event.key == pygame.K_BACKSPACE: txt = txt[:-1]
            elif event.key == pygame.K_TAB:
                self.active_box = "ip" if box=="name" else "name"; return None
            elif event.unicode and len(txt) < 30: txt += event.unicode
            if box == "name": self.name_text = txt
            else:             self.ip_text   = txt
        return None

    def update(self, dt): pass


class WaitScreen:
    """S3 — Shown while waiting for opponent or connecting."""

    def __init__(self, message="Waiting…"):
        self.message = message
        self.angle   = 0.0   # spinner angle

    def draw(self, surf, fonts):
        surf.fill(BG)
        cx, cy = W//2, H//2
        draw_text(surf, fonts, "MatheCards", "h1", ACCENT, cx, cy-80, "center")
        draw_text(surf, fonts, self.message, "body", TEXT,  cx, cy-30, "center")
        # Spinner
        for i in range(8):
            a = self.angle + i * (360/8)
            rad = math.radians(a)
            px = int(cx + 28 * math.cos(rad))
            py = int(cy + 20 + 28 * math.sin(rad))
            alpha = int(255 * (i/8))
            pygame.draw.circle(surf, (*ACCENT[:3], alpha), (px, py), 4)

    def handle(self, event): return None
    def update(self, dt): self.angle = (self.angle + 180*dt) % 360


class CoinTossScreen:
    """S4 — Animated coin flip showing who is challenger."""

    def __init__(self, result, challenger_name, i_am_challenger):
        self.result          = result
        self.challenger_name = challenger_name
        self.i_am_challenger = i_am_challenger
        self.t               = 0.0    # time elapsed
        self.done            = False

    def draw(self, surf, fonts):
        surf.fill(BG)
        cx, cy = W//2, H//2
        draw_text(surf, fonts, "COIN TOSS", "h1", GOLD, cx, 100, "center")

        # Coin animation — squish to simulate flip
        if self.t < 1.5:
            scale = abs(math.cos(self.t * math.pi * 3))
            coin_w = int(100 * max(0.05, scale))
        else:
            scale  = 1.0
            coin_w = 100
            self.done = True

        coin_r = pygame.Rect(cx - coin_w//2, cy - 50, coin_w, 100)
        color  = GOLD if self.result == "heads" else ACCENT
        pygame.draw.ellipse(surf, color, coin_r)
        if coin_w > 30:
            sym = "H" if self.result == "heads" else "T"
            draw_text(surf, fonts, sym, "h1", BLACK, cx, cy, "center")

        if self.done:
            who = "YOU go first!" if self.i_am_challenger else f"{self.challenger_name} goes first!"
            draw_text(surf, fonts, who, "h2", TEXT,  cx, cy+100, "center")
            sub = "You set the rules." if self.i_am_challenger else "Waiting for settings…"
            draw_text(surf, fonts, sub, "body", MUTED, cx, cy+135, "center")

    def handle(self, event): return None
    def update(self, dt): self.t += dt


class LobbyScreen:
    """S5 — Challenger picks topic / difficulty / rounds."""

    def __init__(self, opp_name, i_am_challenger):
        self.opp_name        = opp_name
        self.i_am_challenger = i_am_challenger

        # Settings (challenger edits these)
        self.topics      = list(TOPIC_NAMES.keys())
        self.topic_idx   = 0
        self.diffs       = ["easy","medium","hard"]
        self.diff_idx    = 1
        self.rounds_opts = [3, 5, 7]
        self.rounds_idx  = 1

        self.btn_start   = pygame.Rect(0,0,0,0)
        self.btn_left    = {}   # arrow buttons
        self.btn_right   = {}
        self.hover       = None

    def _setting_row(self, surf, fonts, label, value, y, key):
        """Draw a setting row with ← value → arrows. Returns rects."""
        cx = W // 2
        draw_text(surf, fonts, label, "small", MUTED, cx-180, y, "topleft")
        lbtn = pygame.Rect(cx-20, y+20, 30, 30)
        rbtn = pygame.Rect(cx+100, y+20, 30, 30)
        draw_button(surf, fonts, "<", lbtn, SURFACE2, MUTED, hover=self.hover==f"{key}_l")
        draw_button(surf, fonts, ">", rbtn, SURFACE2, MUTED, hover=self.hover==f"{key}_r")
        draw_text(surf, fonts, value, "body", TEXT, cx+55, y+35, "center")
        return lbtn, rbtn

    def draw(self, surf, fonts):
        surf.fill(BG)
        cx = W // 2
        draw_text(surf, fonts, "LOBBY", "h1", ACCENT, cx, 60, "center")
        draw_text(surf, fonts, f"Opponent: {self.opp_name}", "body", MUTED, cx, 100, "center")

        if self.i_am_challenger:
            draw_text(surf, fonts, "You are the Challenger — set the rules:", "body", GOLD, cx, 140, "center")
            y = 180
            self.btn_left["topic"],  self.btn_right["topic"]  = self._setting_row(
                surf, fonts, "MATH TOPIC", TOPIC_NAMES[self.topics[self.topic_idx]], y, "topic")
            self.btn_left["diff"],   self.btn_right["diff"]   = self._setting_row(
                surf, fonts, "DIFFICULTY", self.diffs[self.diff_idx].upper(), y+80, "diff")
            self.btn_left["rounds"], self.btn_right["rounds"] = self._setting_row(
                surf, fonts, "ROUNDS",     f"Best of {self.rounds_opts[self.rounds_idx]}", y+160, "rounds")

            self.btn_start = pygame.Rect(cx-100, 430, 200, 46)
            draw_button(surf, fonts, "Start Game!", self.btn_start, GOLD, BLACK,
                        hover=self.hover=="start")
        else:
            draw_text(surf, fonts, "Waiting for challenger to set rules…", "h2", MUTED, cx, H//2-20, "center")
            # Spinner
            a = (time.time()*180) % 360
            for i in range(8):
                rad = math.radians(a + i*45)
                px = int(cx + 32*math.cos(rad)); py = int(H//2+50 + 32*math.sin(rad))
                pygame.draw.circle(surf, (*ACCENT, int(255*i/8)), (px,py), 4)

    def handle(self, event):
        if not self.i_am_challenger: return None
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx,my = event.pos
            for key, (lbtn, rbtn) in zip(
                    ["topic","diff","rounds"],
                    [(self.btn_left.get("topic",pygame.Rect(0,0,0,0)), self.btn_right.get("topic",pygame.Rect(0,0,0,0))),
                     (self.btn_left.get("diff", pygame.Rect(0,0,0,0)), self.btn_right.get("diff", pygame.Rect(0,0,0,0))),
                     (self.btn_left.get("rounds",pygame.Rect(0,0,0,0)),self.btn_right.get("rounds",pygame.Rect(0,0,0,0)))]):
                if lbtn.collidepoint(mx,my):
                    if key=="topic":  self.topic_idx  = (self.topic_idx -1) % len(self.topics)
                    if key=="diff":   self.diff_idx   = (self.diff_idx  -1) % len(self.diffs)
                    if key=="rounds": self.rounds_idx = (self.rounds_idx-1) % len(self.rounds_opts)
                if rbtn.collidepoint(mx,my):
                    if key=="topic":  self.topic_idx  = (self.topic_idx +1) % len(self.topics)
                    if key=="diff":   self.diff_idx   = (self.diff_idx  +1) % len(self.diffs)
                    if key=="rounds": self.rounds_idx = (self.rounds_idx+1) % len(self.rounds_opts)
            if self.btn_start.collidepoint(mx,my):
                return {
                    "topic":      self.topics[self.topic_idx],
                    "difficulty": self.diffs[self.diff_idx],
                    "rounds":     self.rounds_opts[self.rounds_idx],
                }
        if event.type == pygame.MOUSEMOTION:
            mx,my = event.pos
            self.hover = None
            if self.btn_start.collidepoint(mx,my): self.hover = "start"
            for k in ["topic","diff","rounds"]:
                if self.btn_left.get(k,pygame.Rect(0,0,0,0)).collidepoint(mx,my): self.hover=f"{k}_l"
                if self.btn_right.get(k,pygame.Rect(0,0,0,0)).collidepoint(mx,my): self.hover=f"{k}_r"
        return None

    def update(self, dt): pass


class PickScreen:
    """S6 — Player picks a card to send to opponent."""

    def __init__(self, hand, powers, opp_count, round_n, total_rounds,
                 my_score, opp_score, my_name, opp_name, timer_secs):
        self.hand         = hand
        self.powers       = powers
        self.opp_count    = opp_count
        self.round_n      = round_n
        self.total_rounds = total_rounds
        self.my_score     = my_score
        self.opp_score    = opp_score
        self.my_name      = my_name
        self.opp_name     = opp_name
        self.timer_left   = timer_secs
        self.selected_uid = None
        self.card_rects   = []   # [(rect, card), ...]
        self.btn_confirm  = pygame.Rect(0,0,0,0)
        self.hover_confirm = False
        self.toast_msg    = ""
        self.toast_t      = 0.0

    def draw(self, surf, fonts):
        surf.fill(BG)
        cx = W // 2

        # ── Score HUD ──
        draw_text(surf, fonts, self.my_name,   "h2",   TEXT,    cx-200, 20, "center")
        draw_text(surf, fonts, str(self.my_score), "title", GOLD, cx-200, 50, "center")
        draw_text(surf, fonts, self.opp_name,  "h2",   TEXT,    cx+200, 20, "center")
        draw_text(surf, fonts, str(self.opp_score),"title",GOLD, cx+200, 50, "center")
        draw_text(surf, fonts, f"Round {self.round_n} / {self.total_rounds}", "small", MUTED, cx, 50, "center")

        # ── Timer bar ──
        timer_rect = pygame.Rect(cx-200, 100, 400, 8)
        draw_timer_bar(surf, self.timer_left, PICK_TIMER_SECONDS, timer_rect)
        draw_text(surf, fonts, f"Pick a card to send — {int(self.timer_left)}s", "body", TEXT, cx, 120, "center")

        # ── Opponent hand (face-down) ──
        draw_text(surf, fonts, f"{self.opp_name}'s cards ({self.opp_count})", "small", MUTED, 40, 150, "topleft")
        ox = max(40, cx - (self.opp_count*(CARD_W+8))//2)
        for i in range(self.opp_count):
            draw_card(surf, fonts, {}, ox + i*(CARD_W+8), 170, face_down=True)

        # ── My hand ──
        draw_text(surf, fonts, "YOUR CARDS — click one to select, then confirm", "small", MUTED, 40, 315, "topleft")
        total_w = len(self.hand)*(CARD_W+8) - 8
        start_x = max(20, cx - total_w//2)
        self.card_rects = draw_hand_row(surf, fonts, self.hand, start_x, 335,
                                        selected_uid=self.selected_uid)

        # ── Power cards (read-only display during pick phase) ──
        draw_text(surf, fonts, "POWER CARDS (usable during duel phase)", "small", MUTED, 40, 480, "topleft")
        px = max(20, cx - (len(self.powers)*(80+8))//2)
        for i, p in enumerate(self.powers):
            draw_card(surf, fonts, p, px+i*88, 498, small=True)

        # ── Confirm button ──
        self.btn_confirm = pygame.Rect(cx-80, 630, 160, 42)
        col = GOLD if self.selected_uid else SURFACE2
        draw_button(surf, fonts, "Confirm Pick", self.btn_confirm, col, BLACK if self.selected_uid else MUTED,
                    hover=self.hover_confirm)

        # ── Toast ──
        if self.toast_msg and self.toast_t > 0:
            ts = toast_surface(fonts, self.toast_msg)
            surf.blit(ts, (cx - ts.get_width()//2, H-60))

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx,my = event.pos
            for rect, card in self.card_rects:
                if rect.collidepoint(mx,my):
                    self.selected_uid = card["uid"]
            if self.btn_confirm.collidepoint(mx,my) and self.selected_uid:
                return self.selected_uid   # signal pick confirmed
        if event.type == pygame.MOUSEMOTION:
            mx,my = event.pos
            self.hover_confirm = self.btn_confirm.collidepoint(mx,my)
        return None

    def update(self, dt):
        self.timer_left = max(0, self.timer_left - dt)
        if self.toast_t > 0: self.toast_t -= dt
        if self.timer_left <= 0 and not self.selected_uid:
            # Auto-pick first card
            if self.hand: self.selected_uid = self.hand[0]["uid"]

    def show_toast(self, msg):
        self.toast_msg = msg; self.toast_t = 3.0


class DuelScreen:
    """S7 — Solve the received card. Use power cards."""

    def __init__(self, recv_card, powers, opp_count, timer_secs,
                 my_name, opp_name, my_score, opp_score, round_n, total_rounds):
        self.recv_card    = recv_card
        self.powers       = list(powers)
        self.opp_count    = opp_count
        self.timer_total  = timer_secs
        self.timer_left   = float(timer_secs)
        self.my_name      = my_name
        self.opp_name     = opp_name
        self.my_score     = my_score
        self.opp_score    = opp_score
        self.round_n      = round_n
        self.total_rounds = total_rounds

        self.answer_text  = ""
        self.feedback     = ""
        self.feedback_col = TEXT
        self.active_input = True
        self.solved       = False
        self.frozen       = False
        self.blinded      = False
        self.scrambled    = False

        self.btn_submit   = pygame.Rect(0,0,0,0)
        self.power_rects  = []
        self.toast_msg    = ""; self.toast_t = 0.0
        self.hover_submit = False

    def draw(self, surf, fonts):
        surf.fill(BG)
        cx = W // 2

        # ── Score HUD ──
        draw_text(surf, fonts, self.my_name,      "h2",    TEXT, cx-220, 14, "center")
        draw_text(surf, fonts, str(self.my_score), "h1",   GOLD, cx-220, 40, "center")
        draw_text(surf, fonts, self.opp_name,      "h2",   TEXT, cx+220, 14, "center")
        draw_text(surf, fonts, str(self.opp_score),"h1",   GOLD, cx+220, 40, "center")
        draw_text(surf, fonts, f"Round {self.round_n}/{self.total_rounds}", "small", MUTED, cx, 35, "center")

        # ── Timer ──
        timer_rect = pygame.Rect(cx-240, 80, 480, 10)
        draw_timer_bar(surf, self.timer_left, self.timer_total, timer_rect)
        status = "FROZEN" if self.frozen else f"{int(self.timer_left)}s remaining"
        color  = ACCENT if self.frozen else (DANGER if self.timer_left<=10 else MUTED)
        draw_text(surf, fonts, status, "small", color, cx, 100, "center")

        # ── DUEL label ──
        draw_text(surf, fonts, "DUEL PHASE", "h2", DANGER, cx, 130, "center")

        # ── Received card (my challenge) ──
        panel = pygame.Rect(cx-380, 155, 340, 200)
        draw_panel(surf, panel)
        draw_text(surf, fonts, "YOUR CHALLENGE CARD", "small", MUTED, panel.centerx, panel.y+12, "center")
        q = "???" if self.blinded else self.recv_card.get("question","?")
        draw_text(surf, fonts, q, "mono_lg", GOLD, panel.centerx, panel.centery+10, "center", max_width=panel.width-20)

        # ── Opponent area ──
        opp_panel = pygame.Rect(cx+40, 155, 340, 200)
        draw_panel(surf, opp_panel)
        draw_text(surf, fonts, f"{self.opp_name} is solving…", "small", MUTED, opp_panel.centerx, opp_panel.y+12, "center")
        draw_card(surf, fonts, {}, opp_panel.centerx-CARD_W//2, opp_panel.y+40, face_down=True)

        # ── Solve input ──
        draw_text(surf, fonts, "Your answer:", "body", TEXT, cx-380, 375, "topleft")
        inp_rect = pygame.Rect(cx-380, 398, 280, 44)
        draw_input_box(surf, fonts, self.answer_text, inp_rect, active=self.active_input)

        self.btn_submit = pygame.Rect(cx-80, 398, 120, 44)
        draw_button(surf, fonts, "Submit", self.btn_submit, ACCENT, WHITE, hover=self.hover_submit)

        if self.feedback:
            draw_text(surf, fonts, self.feedback, "body", self.feedback_col, cx-240, 455, "center")

        # ── Power cards ──
        draw_text(surf, fonts, "POWER CARDS — click to use:", "small", MUTED, 40, 510, "topleft")
        self.power_rects = []
        px = 40
        for p in self.powers:
            r = draw_card(surf, fonts, p, px, 530, small=True)
            self.power_rects.append((r, p))
            px += 78

        # ── Toast ──
        if self.toast_msg and self.toast_t > 0:
            ts = toast_surface(fonts, self.toast_msg)
            surf.blit(ts, (cx - ts.get_width()//2, H-55))

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx,my = event.pos
            if self.btn_submit.collidepoint(mx,my): return ("submit", self.answer_text)
            for rect, card in self.power_rects:
                if rect.collidepoint(mx,my): return ("power", card)
        if event.type == pygame.MOUSEMOTION:
            self.hover_submit = self.btn_submit.collidepoint(*event.pos)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN: return ("submit", self.answer_text)
            elif event.key == pygame.K_BACKSPACE: self.answer_text = self.answer_text[:-1]
            elif event.unicode in "0123456789.-" and len(self.answer_text) < 12:
                self.answer_text += event.unicode
        return None

    def update(self, dt):
        if not self.frozen and not self.solved: self.timer_left = max(0, self.timer_left - dt)
        if self.toast_t > 0: self.toast_t -= dt

    def show_feedback(self, msg, correct):
        self.feedback     = msg
        self.feedback_col = SUCCESS if correct else DANGER

    def show_toast(self, msg):
        self.toast_msg = msg; self.toast_t = 3.5


class MinigameScreen:
    """S8 — Obstacle card mini-challenge (4-choice quick math)."""

    def __init__(self, from_name, topic, difficulty):
        a, b = rnd(1,10), rnd(1,10)
        self.correct = a + b
        self.question = f"{a} + {b} = ?"
        choices = [self.correct]
        while len(choices) < 4:
            w = self.correct + rnd(-5,5)
            if w not in choices: choices.append(w)
        random.shuffle(choices)
        self.choices    = choices
        self.from_name  = from_name
        self.timer_left = 10.0
        self.answered   = None
        self.btn_rects  = []
        self.result     = None   # "pass" or "fail"

    def draw(self, surf, fonts):
        surf.fill(BG)
        cx, cy = W//2, H//2
        # Dark overlay panel
        panel = pygame.Rect(cx-220, cy-200, 440, 400)
        pygame.draw.rect(surf, SURFACE, panel, border_radius=14)
        pygame.draw.rect(surf, DANGER,  panel, 2, border_radius=14)

        draw_text(surf, fonts, "OBSTACLE!", "h1",  DANGER, cx, cy-170, "center")
        draw_text(surf, fonts, f"{self.from_name} sent you a minigame!", "body", MUTED, cx, cy-130, "center")
        draw_text(surf, fonts, self.question, "title", GOLD, cx, cy-80, "center")

        # Timer bar
        draw_timer_bar(surf, self.timer_left, 10, pygame.Rect(cx-160, cy-30, 320, 8))
        draw_text(surf, fonts, f"{int(self.timer_left)}s", "small", MUTED, cx, cy-10, "center")

        # Choice buttons (2x2 grid)
        self.btn_rects = []
        positions = [(cx-170,cy+20),(cx+10,cy+20),(cx-170,cy+80),(cx+10,cy+80)]
        for i, (bx,by) in enumerate(positions):
            c = self.choices[i]
            rect = pygame.Rect(bx, by, 150, 48)
            if self.answered is not None:
                if c == self.correct: col = SUCCESS
                elif c == self.answered: col = DANGER
                else: col = SURFACE2
            else: col = SURFACE2
            draw_button(surf, fonts, str(c), rect, col, WHITE)
            self.btn_rects.append((rect, c))

        if self.result == "pass":
            draw_text(surf, fonts, "Correct! You earn a hint card.", "body", SUCCESS, cx, cy+150, "center")
        elif self.result == "fail":
            draw_text(surf, fonts, "Wrong! Penalty card added to your hand.", "body", DANGER, cx, cy+150, "center")

    def handle(self, event):
        if self.answered is not None: return None
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx,my = event.pos
            for rect, val in self.btn_rects:
                if rect.collidepoint(mx,my):
                    self.answered = val
                    self.result = "pass" if val == self.correct else "fail"
                    return self.result
        return None

    def update(self, dt):
        if self.answered is None:
            self.timer_left = max(0, self.timer_left - dt)
            if self.timer_left <= 0:
                self.answered = -1; self.result = "fail"
                return self.result
        return None


class RoundResultScreen:
    """S9 — Show who won the round."""

    def __init__(self, i_won, winner_name, my_score, opp_score, my_name, opp_name, next_label):
        self.i_won       = i_won
        self.winner_name = winner_name
        self.my_score    = my_score
        self.opp_score   = opp_score
        self.my_name     = my_name
        self.opp_name    = opp_name
        self.next_label  = next_label
        self.t           = 0.0

    def draw(self, surf, fonts):
        surf.fill(BG)
        cx, cy = W//2, H//2
        icon  = "YOU WON THE ROUND!" if self.i_won else f"{self.winner_name} won the round!"
        color = SUCCESS if self.i_won else DANGER
        draw_text(surf, fonts, "🏅" if self.i_won else "💔", "title", color, cx, cy-130, "center")
        draw_text(surf, fonts, icon, "h1", color, cx, cy-60, "center")
        draw_text(surf, fonts, f"{self.my_name}  {self.my_score}  —  {self.opp_score}  {self.opp_name}",
                  "h2", TEXT, cx, cy+20, "center")
        draw_text(surf, fonts, self.next_label, "small", MUTED, cx, cy+80, "center")

    def handle(self, event): return None
    def update(self, dt): self.t += dt


class GameOverScreen:
    """S10 — Final result."""

    def __init__(self, i_won, winner_name, my_score, opp_score, my_name, opp_name):
        self.i_won = i_won; self.winner_name = winner_name
        self.my_score = my_score; self.opp_score = opp_score
        self.my_name = my_name; self.opp_name = opp_name
        self.btn_menu = pygame.Rect(0,0,0,0)
        self.hover    = False

    def draw(self, surf, fonts):
        surf.fill(BG)
        cx, cy = W//2, H//2
        icon  = "VICTORY!" if self.i_won else "DEFEAT"
        color = GOLD if self.i_won else DANGER
        draw_text(surf, fonts, icon, "title", color, cx, cy-150, "center")
        sub = f"You beat {self.opp_name}!" if self.i_won else f"{self.winner_name} wins this time."
        draw_text(surf, fonts, sub, "h2", TEXT, cx, cy-80, "center")
        draw_text(surf, fonts, f"{self.my_name}  {self.my_score}  —  {self.opp_score}  {self.opp_name}",
                  "h2", MUTED, cx, cy, "center")
        self.btn_menu = pygame.Rect(cx-90, cy+80, 180, 46)
        draw_button(surf, fonts, "Main Menu", self.btn_menu, ACCENT, WHITE, hover=self.hover)

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.btn_menu.collidepoint(*event.pos): return "menu"
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.btn_menu.collidepoint(*event.pos)
        return None

    def update(self, dt): pass


# ════════════════════════════════════════════════════════════════
# SECTION T — PYGAME CLIENT
# Replaces the terminal-based ClientGame.
# Runs the Pygame event loop and coordinates with the network.
# ════════════════════════════════════════════════════════════════

class PygameClient:
    """
    Main Pygame client.
    Manages the window, the current screen, and the network connection.
    """

    def __init__(self):
        pygame.init()
        self.surf  = pygame.display.set_mode((W, H))
        pygame.display.set_caption("MatheCards")
        self.clock = pygame.time.Clock()
        self.fonts = init_fonts()
        self.net   = None   # NetworkClient, set after connecting

        # Player state
        self.my_id    = ""
        self.my_name  = ""
        self.opp_name = ""
        self.my_score = 0
        self.opp_score= 0
        self.difficulty    = "medium"
        self.topic         = "basic"
        self.total_rounds  = 5
        self.current_round = 1
        self.my_hand       = []
        self.my_powers     = []
        self.opp_count     = 0
        self.recv_card     = None
        self.is_challenger = False

        # Active screen
        self.screen = LandingScreen()

        # Pending minigame screen (shown over duel)
        self.minigame_screen = None

    def run(self):
        while True:
            try:
                dt = self.clock.tick(FPS) / 1000.0

                # ── Pygame events ──────────────────────────────────
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit(); sys.exit()
                    try:
                        result = self.screen.handle(event)
                        if result is not None:
                            self._on_screen_event(result)
                    except Exception as e:
                        print(f"[EVENT ERROR] {type(e).__name__}: {e}")
                        import traceback; traceback.print_exc()

                # ── Screen update ──────────────────────────────────
                try:
                    self.screen.update(dt)
                except Exception as e:
                    print(f"[UPDATE ERROR] {type(e).__name__}: {e}")

                # ── Network messages ───────────────────────────────
                if self.net:
                    try:
                        self._poll_network()
                    except Exception as e:
                        print(f"[NETWORK ERROR] {type(e).__name__}: {e}")

                # ── Draw ───────────────────────────────────────────
                try:
                    self.screen.draw(self.surf, self.fonts)
                except Exception as e:
                    print(f"[DRAW ERROR] {type(e).__name__}: {e}")
                    # Draw a fallback red error screen so window stays open
                    self.surf.fill((20, 5, 5))
                    font = self.fonts["body"]
                    s = font.render(f"Error: {e}", True, (255, 80, 80))
                    self.surf.blit(s, (20, 20))

                pygame.display.flip()

            except Exception as e:
                print(f"[LOOP ERROR] {type(e).__name__}: {e}")
                import traceback; traceback.print_exc()

    # ── SCREEN EVENT ROUTING ──────────────────────────────────────
    def _on_screen_event(self, result):
        """Called when a screen returns a non-None value from handle()."""

        # Landing screen → server or client
        if isinstance(result, tuple) and result[0] == "server":
            self.my_name = result[1]
            self.screen  = WaitScreen("Server mode — open this game on another machine as Client.")
            threading.Thread(target=self._run_server, daemon=True).start()

        elif isinstance(result, tuple) and result[0] == "client":
            self.my_name = result[1]
            ip           = result[2]
            self.screen  = WaitScreen(f"Connecting to {ip}…")
            threading.Thread(target=self._connect_client, args=(ip,), daemon=True).start()

        # Lobby → settings confirmed by challenger
        elif isinstance(result, dict) and "topic" in result:
            self.topic        = result["topic"]
            self.difficulty   = result["difficulty"]
            self.total_rounds = result["rounds"]
            self.net.send("lobby_settings", result)
            self.screen = WaitScreen("Settings sent! Waiting for cards to be dealt…")

        # Pick screen → card selected
        elif isinstance(result, str) and self.recv_card is None:
            # result is the uid of picked card
            self.net.send("card_picked", {"uid": result})
            self.screen = WaitScreen("Card sent! Waiting for opponent…")

        # Duel screen events
        elif isinstance(result, tuple) and result[0] == "submit":
            try:
                ans = float(result[1])
                self.net.send("answer_submitted", {"answer": ans})
            except ValueError:
                if isinstance(self.screen, DuelScreen):
                    self.screen.show_feedback("Enter a valid number!", False)

        elif isinstance(result, tuple) and result[0] == "power":
            self._use_power_card(result[1])

        # Minigame result
        elif result in ("pass", "fail"):
            self._on_minigame_result(result)

        # Game over screen → main menu
        elif result == "menu":
            self.screen = LandingScreen()
            self.net = None

    # ── SERVER THREAD ─────────────────────────────────────────────
    def _run_server(self):
        """Runs the server in a background thread. Also connects as client."""
        server = NetworkServer()
        # Start server in its own thread
        t = threading.Thread(target=server.start, daemon=True)
        t.start()
        time.sleep(0.4)
        # Also connect this machine as a client
        self._connect_client("127.0.0.1")

    # ── CLIENT CONNECT ────────────────────────────────────────────
    def _connect_client(self, ip):
        # This method always runs in a background thread (see _run_server and
        # the threading.Thread call in _on_screen_event). It is safe to call
        # wait_for() here because it does NOT block the main Pygame thread.
        try:
            self.net = NetworkClient(ip)
            self.net.connect()
            self.screen = WaitScreen("Connected! Waiting for opponent...")
            msg = self.net.wait_for("assigned_id", timeout=15)
            if msg:
                self.my_id    = msg["data"]["id"]
                self.net.role = msg["data"]["role"]
                self.net.send("set_name", {"name": self.my_name})
            # All further messages handled by _poll_network() via peek() on main thread
        except Exception as e:
            self.screen = LandingScreen()
            self.screen.error = f"Connection failed: {e}"

    # ── NETWORK POLLING ───────────────────────────────────────────
    def _poll_network(self):
        """Check inbox for new server messages and react to each."""
        for msg_type in ["opp_name","coin_toss","game_starting","deal_hand",
                         "pick_phase_start","received_card","duel_start",
                         "answer_result","duel_solved","hand_update",
                         "round_over","game_over","obstacle"]:
            msg = self.net.peek(msg_type)
            if msg: self._handle_server_msg(msg)

    def _handle_server_msg(self, msg):
        t = msg["type"]; d = msg.get("data", {})

        if t == "opp_name":
            self.opp_name = d["name"]
            self.screen   = WaitScreen(f"{self.opp_name} connected!")

        elif t == "coin_toss":
            self.is_challenger = (d["challenger"] == self.my_id)
            self.screen = CoinTossScreen(d["result"], d["challenger_name"], self.is_challenger)
            # After coin toss animation finishes, go straight to lobby
            def go_lobby():
                time.sleep(3.0)   # wait for coin animation
                self.screen = LobbyScreen(self.opp_name, self.is_challenger)
            threading.Thread(target=go_lobby, daemon=True).start()

        elif t == "game_starting":
            # Server confirms settings — store them and show a brief wait screen
            # then deal_hand will switch to the pick screen
            self.topic        = d["topic"]
            self.difficulty   = d["difficulty"]
            self.total_rounds = d["rounds"]
            self.screen = WaitScreen("Game starting! Cards being dealt…")

        elif t == "deal_hand":
            # Store hand data — do NOT call wait_for() here (blocks main thread).
            # pick_phase_start arrives moments later and will build the PickScreen.
            self.my_hand    = d["math"]
            self.my_powers  = d["powers"]
            self.opp_count  = d["opp_count"]
            self.current_round = d["round"]
            self.total_rounds  = d["total"]
            for sid,sc in d["scores"].items():
                if sid==self.my_id: self.my_score=sc
                else:               self.opp_score=sc
            for sid,nm in d["names"].items():
                if sid==self.my_id: self.my_name=nm
                else:               self.opp_name=nm
            self.recv_card = None
            self.screen = WaitScreen("Cards dealt! Get ready...")

        elif t == "pick_phase_start":
            # Arrives right after deal_hand — now safe to build PickScreen
            # because my_hand is already stored above. No blocking call needed.
            timer = d.get("timer", PICK_TIMER_SECONDS)
            self.screen = PickScreen(
                self.my_hand, self.my_powers, self.opp_count,
                self.current_round, self.total_rounds,
                self.my_score, self.opp_score,
                self.my_name, self.opp_name, timer)

        elif t == "received_card":
            self.recv_card = d["card"]

        elif t == "duel_start":
            if self.recv_card:
                self.screen = DuelScreen(
                    self.recv_card, self.my_powers, self.opp_count,
                    d["timer"], self.my_name, self.opp_name,
                    self.my_score, self.opp_score,
                    self.current_round, self.total_rounds)

        elif t == "answer_result":
            if isinstance(self.screen, DuelScreen):
                if d["correct"]:
                    self.screen.show_feedback("CORRECT!", True)
                    self.screen.solved = True
                else:
                    self.screen.show_feedback(f"Wrong. Answer: {d['answer']}", False)

        elif t == "duel_solved":
            # Opponent solved first — show it but keep the DuelScreen open.
            # The remaining timer is cut in half — update it on screen so the
            # player can see the urgency. Screen only switches on next_pick/round_over.
            if isinstance(self.screen, DuelScreen):
                if d.get("winner_id") != self.my_id:
                    halved = d.get("time_left", None)
                    if halved is not None:
                        # Snap the visual timer to the halved value
                        self.screen.timer_left  = float(halved)
                        self.screen.timer_total = float(halved)
                    self.screen.show_feedback(
                        f"{d['winner_name']} solved first! "
                        f"You have {int(self.screen.timer_left)}s left!", False)
                    self.screen.show_toast(
                        f"Timer halved! {int(self.screen.timer_left)}s remaining.")
                else:
                    # I solved first — confirm it visually
                    self.screen.show_feedback("CORRECT! You solved first!", True)
                    self.screen.solved = True

        elif t == "hand_update":
            # Just update card counts — never switch away from DuelScreen here.
            # next_pick or round_over will handle the screen transition.
            for sid, ct in d.items():
                if sid == self.my_id:
                    pass  # my hand is already tracked locally
                else:
                    self.opp_count = ct

        elif t == "obstacle":
            if isinstance(self.screen, DuelScreen):
                self._receive_obstacle(d)

        elif t == "next_pick":
            # Both players finished this duel cycle — go back to pick phase.
            # Wait 2 seconds so the player can see the duel result before switching.
            for sid, sc in d.get("scores", {}).items():
                if sid == self.my_id: self.my_score = sc
                else:                 self.opp_score = sc
            for sid, ct in d.get("opp_counts", {}).items():
                if sid != self.my_id: self.opp_count = ct
            timer = d.get("pick_timer", PICK_TIMER_SECONDS)
            def delayed_pick():
                time.sleep(2.0)
                self.screen = PickScreen(
                    self.my_hand, self.my_powers, self.opp_count,
                    self.current_round, self.total_rounds,
                    self.my_score, self.opp_score,
                    self.my_name, self.opp_name, timer)
            threading.Thread(target=delayed_pick, daemon=True).start()

        elif t == "round_over":
            for sid,sc in d["scores"].items():
                if sid==self.my_id: self.my_score=sc
                else:               self.opp_score=sc
            i_won  = d["winner_id"] == self.my_id
            wins_n = math.ceil(self.total_rounds/2)
            game_over = self.my_score >= wins_n or self.opp_score >= wins_n
            nxt = "Game ending…" if game_over else f"Round {self.current_round+1} starting…"
            self.screen = RoundResultScreen(i_won, d["winner_name"],
                                            self.my_score, self.opp_score,
                                            self.my_name, self.opp_name, nxt)

        elif t == "game_over":
            for sid,sc in d["scores"].items():
                if sid==self.my_id: self.my_score=sc
                else:               self.opp_score=sc
            i_won = d["winner_id"] == self.my_id
            self.screen = GameOverScreen(i_won, d["winner_name"],
                                         self.my_score, self.opp_score,
                                         self.my_name, self.opp_name)

    # ── POWER CARD EFFECTS (Section K) ───────────────────────────
    def _use_power_card(self, card):
        """Apply an aid card locally or send obstacle to server."""
        try:
            # Guard: card must have uid and type
            if not card or "uid" not in card or "type" not in card:
                print(f"[POWER] Skipped — card missing keys: {card}")
                return

            self.my_powers = [p for p in self.my_powers if p.get("uid") != card["uid"]]
            if isinstance(self.screen, DuelScreen):
                self.screen.powers = self.my_powers

            if card["type"] == "aid":
                self._apply_aid(card)
            else:
                if self.net:
                    self.net.send("use_power", {
                        "id":   card.get("id", ""),
                        "uid":  card.get("uid", ""),
                        "name": card.get("name", ""),
                    })
                if isinstance(self.screen, DuelScreen):
                    self.screen.show_toast(f"Sent {card.get('name','power')} to {self.opp_name}!")
        except Exception as e:
            print(f"[POWER ERROR] {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()

    def _apply_aid(self, card):
        try:
            if not isinstance(self.screen, DuelScreen): return
            # Safely get answer — default 0 if recv_card not ready yet
            ans = float(self.recv_card["answer"]) if self.recv_card else 0
            s   = self.screen
            cid = card.get("id", "")
            if cid == "hint_digit":
                digits = len(str(abs(int(round(ans)))))
                s.show_toast(f"Digit Hint: answer has {digits} digit(s).")
            elif cid == "hint_range":
                msg = "negative" if ans<0 else "zero" if ans==0 else "between 1-50" if ans<=50 else "greater than 50"
                s.show_toast(f"Range Hint: answer is {msg}.")
            elif cid == "hint_sign":
                sign = "negative" if ans<0 else "zero" if ans==0 else "positive"
                s.show_toast(f"Sign Hint: answer is {sign}.")
            elif cid == "extra_time":
                s.timer_left = min(s.timer_left + 10, s.timer_total)
                s.show_toast("+10 seconds added!")
            elif cid == "skip_card":
                s.solved = True
                if self.net:
                    self.net.send("answer_submitted", {"answer": ans})
                s.show_toast("Card skipped — auto-win!")
            else:
                s.show_toast(f"Used {card.get('name','card')}.")
        except Exception as e:
            print(f"[AID ERROR] {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()

    def _receive_obstacle(self, d):
        """Handle an obstacle card sent by opponent."""
        s = self.screen
        if not isinstance(s, DuelScreen): return
        cid = d.get("id","")
        frm = d.get("from", self.opp_name)
        if cid == "freeze":
            s.frozen = True
            s.show_toast(f"FROZEN by {frm} for 8s!")
            def unfreeze(): time.sleep(8); s.frozen = False
            threading.Thread(target=unfreeze, daemon=True).start()
        elif cid == "blind":
            s.blinded = True
            s.show_toast(f"BLINDED by {frm} for 5s!")
            def unblind(): time.sleep(5); s.blinded = False
            threading.Thread(target=unblind, daemon=True).start()
        elif cid == "scramble":
            s.answer_text = "".join(random.sample(s.answer_text, len(s.answer_text))) if s.answer_text else ""
            s.show_toast(f"SCRAMBLED by {frm}!")
        elif cid == "minigame":
            self.minigame_screen = MinigameScreen(frm, self.topic, self.difficulty)
            # Temporarily swap screen
            self._prev_duel = s
            self.screen = self.minigame_screen

    def _on_minigame_result(self, result):
        """Called when minigame screen returns pass/fail."""
        if result == "pass":
            reward = {**POWER_CARD_DEFS[2], "uid": str(uuid.uuid4())[:8]}
            self.my_powers.append(reward)
        else:
            penalty = {**MATH_GENERATORS[self.topic](self.difficulty), "uid": str(uuid.uuid4())[:8]}
            self.my_hand.append(penalty)
        # Return to duel screen
        if hasattr(self, "_prev_duel"):
            self.screen = self._prev_duel
            self.screen.powers = self.my_powers
            msg = "Minigame cleared! Got a Sign Hint." if result=="pass" else "Minigame failed! Penalty card added."
            self.screen.show_toast(msg)


# ════════════════════════════════════════════════════════════════
# SECTION U — MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════════

def main():
    args = sys.argv[1:]
    mode = args[0].lower() if args else ""

    if mode == "server":
        # Headless server only (no GUI window)
        print(f"Starting MatheCards server on port {SERVER_PORT}…")
        server = NetworkServer()
        server.start()
    else:
        # GUI client (handles both hosting and joining)
        client = PygameClient()
        client.run()


if __name__ == "__main__":
    main()
