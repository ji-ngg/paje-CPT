import os
import sys
import random
from PIL import Image, ImageOps
import shutil
import math

possible_room_paths = [
    "/mnt/data/Screenshot 2025-12-05 at 9.37.14 pm.png",
    "/mnt/data/Screenshot 2025-12-05 at 9.47.52 pm.png",
    "/mnt/data/room.png",
    "room.png"
]
possible_door_paths = [
    "/mnt/data/Screenshot 2025-12-05 at 9.48.13 pm.png",
    "/mnt/data/Screenshot 2025-12-05 at 9.48.13 pm.png",
    "/mnt/data/door.png",
    "door.png"
]

player_icon = "(*-*)"
mr_clark_icon = "(-_-)"
lollipop_total = 5

player = {"x": None, "y": None, "lollipops": 0, "hp": 20}
mr_clark = {"hp": 20}
game_state = {
    "first_scene_shown": False,
    "got_key": False,
    "met_mr_clark": False,
    "escaped": False
}

def find_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None

room_path = find_existing(possible_room_paths)
door_path = find_existing(possible_door_paths)

def get_terminal_size():
    try:
        cols, rows = shutil.get_terminal_size((120, 40))
    except:
        cols, rows = (120, 40)
    return cols, rows

def image_to_ascii_lines(path, max_width=None, scale=0.45):
    """
    path: image file path
    max_width: maximum ascii width in characters (None -> terminal width - padding)
    scale: vertical scale factor (height scaling)
    returns: ascii_lines, brightness_grid (2d list matching ascii chars)
    """
    if not path or not os.path.exists(path):
        return None, None
    cols, rows = get_terminal_size()
    if max_width is None:
        max_width = min(120, max(40, cols - 4))
    img = Image.open(path)
    img = ImageOps.grayscale(img)
    w, h = img.size
    new_w = max_width
    new_h = max(10, int((h / w) * new_w * scale))
    img = img.resize((new_w, new_h))
    pixels = list(img.getdata())
    pixels_2d = [pixels[i * new_w:(i + 1) * new_w] for i in range(new_h)]
    chars = "@%#*+=-:. "  
    ascii_lines = []
    brightness_grid = []
    for row in pixels_2d:
        line = "".join(chars[pixel * (len(chars)-1) // 255] for pixel in row)
        ascii_lines.append(line)
        brightness_grid.append(row)
    return ascii_lines, brightness_grid

room_ascii, room_bright = image_to_ascii_lines(room_path)
door_ascii, door_bright = image_to_ascii_lines(door_path)

if room_ascii is None:
    room_ascii = [
        "+---------------------------------------------+",
        "|  [T1]      [T2]      [T3]       window      |",
        "|                                             |",
        "|  [T4]      [T5]      [T6]                   |",
        "|                                             |",
        "|      teacher desk (staff-only door)         |",
        "|                    _______                  |",
        "|                   |staff |  main door -->   |",
        "+---------------------------------------------+"
    ]
    room_bright = [[255 if c == " " else 0 for c in line] for line in room_ascii]

if door_ascii is None:
    door_ascii = [
        "  ________________________",
        " |  ____                 |",
        " | |    |   []           |",
        " | |    |   -()          |",
        " | |____|                |",
        " |_______________________|",
        " /                       \\",
        "/_________________________\\"
    ]
    door_bright = [[255 if c == " " else 0 for c in line] for line in door_ascii]

map_h = len(room_ascii)
map_w = max(len(line) for line in room_ascii)
door_h = len(door_ascii)
door_w = max(len(line) for line in door_ascii)

def pad_lines(lines, width):
    return [line + " " * (width - len(line)) for line in lines]

room_ascii = pad_lines(room_ascii, map_w)
if room_bright:
    room_bright = [row + [255] * (map_w - len(row)) for row in room_bright]

door_ascii = pad_lines(door_ascii, door_w)
if door_bright:
    door_bright = [row + [255] * (door_w - len(row)) for row in door_bright]

walkable = [[False] * map_w for _ in range(map_h)]

if room_bright and all(isinstance(r, list) for r in room_bright):
    for y in range(map_h):
        for x in range(map_w):
            try:
                b = room_bright[y][x]
            except:
                b = 255
            walkable[y][x] = (b > 160)
else:
    for y, line in enumerate(room_ascii):
        for x, ch in enumerate(line):
            walkable[y][x] = (ch == " " or ch == "." or ch == ":")

spawn_found = False
for dy in range(map_h):
    y = map_h // 2 + (dy if dy % 2 == 0 else -dy)
    for x in range(map_w):
        if walkable[y][x]:
            player["x"], player["y"] = x, y
            spawn_found = True
            break
    if spawn_found:
        break

if player["x"] is None:
    player["x"], player["y"] = map_w // 2, map_h // 2  

table_positions = []
for tlabel in ["T1","T2","T3","T4","T5","T6"]:
    found = False
    for y, line in enumerate(room_ascii):
        idx = line.find(tlabel)
        if idx != -1:            tx = idx + len(tlabel)//2
            ty = y
            table_positions.append((tx, ty))
            found = True
            break
    if not found:
        pass

if len(table_positions) < 6:
    walk_cells = [(x,y) for y in range(map_h) for x in range(map_w) if walkable[y][x]]
    random.shuffle(walk_cells)
    picks = walk_cells[:6]
    table_positions = picks

lollipops_on_table = {i+1: 0 for i in range(6)}
for _ in range(lollipop_total):
    t = random.randint(1,6)
    lollipops_on_table[t] += 1

coord_to_table = {}
for i, (tx, ty) in enumerate(table_positions, 1):
    coord_to_table[(tx, ty)] = i

def render_room_with_player():
    canvas = [list(line) for line in room_ascii]
    px, py = player["x"], player["y"]
    icon = player_icon
    half = len(icon) // 2
    startx = max(0, px - half)
    for i, ch in enumerate(icon):
        x = startx + i
        if 0 <= x < map_w and 0 <= py < map_h and walkable[py][x]:
            canvas[py][x] = ch
        else:
            if 0 <= px < map_w and 0 <= py < map_h:
                canvas[py][px] = "*"
    return ["".join(row) for row in canvas]

def print_room():
    lines = render_room_with_player()
    for line in lines:
        print(line)

def print_door():
    for line in door_ascii:
        print(line)

def wait_for_space():
    while True:
        s = input("(press space then enter to continue) ")
        if s == " ":
            break
        else:
            print("press the spacebar then enter like it asks.")

def slow_print_lines(lines):
    for line in lines:
        print(line)
        wait_for_space()

def show_first_scene():
    if game_state["first_scene_shown"]:
        return
    lines = [
        "you wake up in a classroom, alone and confused.",
        "you look around the classroom and feel a sense of unease.",
        "after a look around, you realise that you’re in k13.",
        "a wave of memories fills your mind.",
        "the website task.",
        "scratch.",
        "unity.",
        "(client task)",
        "a wave of disgust rolls over you and you shudder.",
        "you notice the number of things scattered over the desks.",
        "notes, and… lollipops?",
        "what am i doing in k13 again?",
        "why am i willingly staying longer than i have to be in k13??",
        "you stagger up to walk to the door, intending to leave.",
        "you flick the lock on the door from locked to unlocked as you would for any normal classroom door at fort street.",
        "you pull on the handle.",
        "the door does not open.",
        "you shake the door handle aggressively, but the door still doesn’t open.",
        "how am i locked inside the classroom?",
        "you turn around, eyes fixing on the closest of the three windows.",
        "jumping off the second story of kilgour was not a good idea…",
        "but what other choice was there?",
        "and then there was the staff only door behind the teacher’s desk.",
        "maybe there’s something there?",
        "(find your way out)"
    ]
    slow_print_lines(lines)
    game_state["first_scene_shown"] = True

def in_bounds(x,y):
    return 0 <= x < map_w and 0 <= y < map_h

def can_walk(x,y):
    if not in_bounds(x,y):
        return False
    return walkable[y][x]

def move(dx, dy):
    nx = player["x"] + dx
    ny = player["y"] + dy
    if can_walk(nx, ny):
        player["x"], player["y"] = nx, ny
        print_room()
    else:
        print("you can't move there. there's something blocking you.")

def find_nearby_table():
    px, py = player["x"], player["y"]
    for (tx, ty), idx in coord_to_table.items():
        if abs(px - tx) <= 2 and abs(py - ty) <= 1:
            return idx
    return None

def interact_current():
    px, py = player["x"], player["y"]
    near_door = (px >= map_w - 8) 
    near_teacher = (py >= map_h - 6 and px < map_w // 3)
    table_idx = find_nearby_table()
    if table_idx:
        found = lollipops_on_table.get(table_idx, 0)
        print(f"you rummage table {table_idx}.")
        if found > 0:
            print(f"you found {found} lollipop{'s' if found>1 else ''}!")
            player["lollipops"] += found
            lollipops_on_table[table_idx] = 0
        else:
            print("there's nothing here.")
        return
    if near_teacher:
        print("you approach the teacher's desk and the staff-only door.")
        interact_staff_door()
        return
    if near_door:
        print_door()
        if game_state["got_key"]:
            print("you use the key and the main door opens. you escaped k13.")
            game_state["escaped"] = True
        else:
            print("the door is still locked. stop trying to force it open and find clues.")
        return
    print("there's nothing obvious to interact with here.")

player_attack_phrases_pool = [
    "you answer confidently with a neat code solution.",
    "you bluff about a clever optimisation you once read.",
    "you tie it back to an example in a game engine.",
    "you rant about datasets and pipelines for a moment.",
    "you recall a graph theory trick about bridges.",
    "you explain a tiny prime-check function in python."
]

def mr_clark_prompts():
    pool = [
        "mr clark: explain how simulations can model emergent behaviour.",
        "mr clark: describe why game loops are important.",
        "mr clark: code a simple python function that returns true if a number is prime.",
        "mr clark: what's the map-reduce idea used in big data?",
        "mr clark: talk about the seven bridges problem and why it's important.",
        "mr clark: why is computational thinking important in games?",
        "mr clark: outline how you'd optimise a physics update loop."
    ]
    return random.sample(pool, 4)

def player_damage_by_lollipops(n):
    mapping = {0:2, 1:3, 2:4, 3:5, 4:7, 5:8}
    return mapping.get(n, 2)

def mr_clark_bossfight():
    print("mr clark stares at you. battle begins.")
    player["hp"] = 20
    mr_clark["hp"] = 20
    prompts = mr_clark_prompts()
    idx = 0
    round_no = 1
    while player["hp"] > 0 and mr_clark["hp"] > 0:
        print(f"\n--- round {round_no} ---")
        # mr clark's turn
        pr = prompts[idx % len(prompts)]
        idx += 1
        print(mr_clark_icon, pr)
        dmg_to_player = 4
        player["hp"] = max(0, player["hp"] - dmg_to_player)
        print(f"mr clark hits you -{dmg_to_player}. your hp: {player['hp']}/20")
        if player["hp"] <= 0:
            break
        # player's turn
        choices = random.sample(player_attack_phrases_pool, 2)
        print("your options:")
        for i,ch in enumerate(choices,1):
            print(f"  {i}. {ch}")
        while True:
            choice = input("choose 1 or 2: ").strip()
            if choice in ("1","2"):
                break
            print("type 1 or 2")
        dmg = player_damage_by_lollipops(player["lollipops"])
        mr_clark["hp"] = max(0, mr_clark["hp"] - dmg)
        print(f"you: {choices[int(choice)-1]}")
        print(f"you deal -{dmg} to mr clark. mr clark hp: {mr_clark['hp']}/20")
        round_no += 1
    if mr_clark["hp"] <= 0:
        slow_print_lines = [
            "\"okay fine here's the key.\"",
            "he tosses you a small key."
        ]
        for line in slow_print_lines:
            print(line)
            # don't require space here to keep flow
        game_state["got_key"] = True
    else:
        for line in ["\"go do your homework. you don't know enough about cpt.\"", "mr clark leaves."]:
            print(line)

def interact_staff_door():
    if not game_state["met_mr_clark"]:
        print("\"what are you doing here?\"")
        print("uh oh, it's mr clark.")
        print("\"where did you appear from??\"")
        game_state["met_mr_clark"] = True
        mr_clark_bossfight()
    else:
        mr_clark_bossfight()

# ---------- commands & main loop ----------
def show_help():
    print("commands:")
    print("  w/a/s/d  -> move up/left/down/right")
    print("  move w/a/s/d -> same")
    print("  look -> describe surroundings")
    print("  interact -> interact with a nearby object/table/door")
    print("  map -> redraw ascii room")
    print("  inventory -> show lollipops/hp/key")
    print("  quit -> exit")

def show_inventory():
    print(f"lollipops: {player['lollipops']}")
    print(f"hp: {player['hp']}/20")
    print(f"key: {'yes' if game_state['got_key'] else 'no'}")

def main():
    print("move with w/a/s/d. interact when near tables/teacher/door.")
    if not game_state["first_scene_shown"]:
        show_first_scene()
    print_room()
    show_help()
    while True:
        if game_state["escaped"]:
            print("congrats. you escaped k13. game over.")
            break
        cmd = input("> ").strip().lower()
        if cmd in ("q","quit","exit"):
            print("bye.")
            break
        if cmd in ("help","h"):
            show_help()
            continue
        if cmd in ("map","m"):
            print_room()
            continue
        if cmd in ("look",):
            print("you see desks, a teacher desk with a staff-only door, and the main door. try to move near items to interact.")
            continue
        if cmd in ("inventory","i"):
            show_inventory()
            continue
        if cmd.startswith("move "):
            c = cmd.split()[1]
            cmd = c
        if cmd in ("w","up"):
            move(0, -1)
            continue
        if cmd in ("s","down"):
            move(0, 1)
            continue
        if cmd in ("a","left"):
            move(-1, 0)
            continue
        if cmd in ("d","right"):
            move(1, 0)
            continue
        if cmd in ("interact","e"):
            interact_current()
            continue
        print("unknown command. type help")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nexiting")
        sys.exit(0)
