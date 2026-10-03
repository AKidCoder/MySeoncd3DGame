import pyray as pr
import math
import random

# Screen Setup
SCREEN_WIDTH = 1100
SCREEN_HEIGHT = 650
pr.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Roof Rumble: Arcade Sumo")
pr.set_target_fps(60)

# Colors
CYAN = pr.Color(0, 255, 255, 255)
NEON_RED = pr.Color(255, 50, 50, 255)
GOLD = pr.Color(255, 215, 0, 255)
PURPLE = pr.Color(180, 50, 255, 255)
ROOF_COLOR = pr.Color(45, 52, 72, 255)
EDGE_RING = pr.Color(255, 200, 0, 255)

ARENA_RADIUS = 20.0
screen_shake = 0.0

# -------------------------------------------------------------
# PERSISTENT SHOP & INVENTORY DATA
# -------------------------------------------------------------
player_shards = 15

SKINS = [
    {"name": "Cyber Cyan", "color": CYAN, "cost": 0, "owned": True},
    {"name": "Inferno Red", "color": NEON_RED, "cost": 6, "owned": False},
    {"name": "Void Purple", "color": PURPLE, "cost": 10, "owned": False},
    {"name": "Pure Gold", "color": GOLD, "cost": 16, "owned": False},
]
equipped_skin_idx = 0

ABILITIES = [
    {"name": "Standard Engine", "cost": 0, "owned": True, "badge": "STD", "desc": "Clean, reliable handling"},
    {"name": "Nitro Dash", "cost": 8, "owned": False, "badge": "BOOST", "desc": "Rocket forward surge"},
    {"name": "Shockwave", "cost": 12, "owned": False, "badge": "BURST", "desc": "Light stun & defensive disrupt"},
    {"name": "Titan Heavy", "cost": 15, "owned": False, "badge": "ARMOR", "desc": "2.5x mass bonus for 3s"},
]
equipped_ability_idx = 0

selected_tab = "SKINS"
shop_cursor = 0

game_state = "TITLE"
match_kills = 0
match_shards_earned = 0
match_won = False

# -------------------------------------------------------------
# BUMPER CAR CLASS
# -------------------------------------------------------------
class BumperCar:
    def __init__(self, x, z, angle, color, is_player=False, ability="Standard Engine"):
        self.x = x
        self.z = z
        self.y = 0.5
        self.angle = angle
        self.vx = 0.0
        self.vz = 0.0
        self.color = color
        self.is_player = is_player
        self.radius = 1.3
        self.base_mass = 1.45 if is_player else 1.0
        self.mass = self.base_mass
        self.is_alive = True
        self.fall_speed = 0.0
        self.spin_speed = 0.0
        self.stun_timer = 0.0
        
        self.ability = ability
        self.ability_cooldown = 0.0
        self.titan_timer = 0.0
        self.shockwave_timer = 0.0

    def trigger_ability(self, other_cars):
        global screen_shake
        if self.ability_cooldown > 0.0 or not self.is_alive:
            return

        if self.ability == "Nitro Dash":
            self.ability_cooldown = 3.5
            fwd_x = math.cos(self.angle)
            fwd_z = math.sin(self.angle)
            self.vx += fwd_x * 85.0
            self.vz += fwd_z * 85.0
            if self.is_player:
                screen_shake = 0.55

        elif self.ability == "Shockwave":
            self.ability_cooldown = 5.0
            self.shockwave_timer = 0.30
            if self.is_player:
                screen_shake = 0.70
            for other in other_cars:
                if other is not self and other.is_alive:
                    dx = other.x - self.x
                    dz = other.z - self.z
                    dist = math.hypot(dx, dz)
                    if 0.1 < dist < 7.5:
                        nx = dx / dist
                        nz = dz / dist
                        push = (7.5 - dist) * 2.8
                        other.vx += nx * push
                        other.vz += nz * push
                        other.stun_timer = 0.40

        elif self.ability == "Titan Heavy":
            self.ability_cooldown = 7.0
            self.titan_timer = 3.0
            self.mass = self.base_mass * 2.5

    def update_physics(self, dt, is_driving=False):
        if not self.is_alive:
            self.fall_speed += 36.0 * dt
            self.y -= self.fall_speed * dt
            self.angle += self.spin_speed * dt
            return

        if self.stun_timer > 0.0:
            self.stun_timer -= dt
            self.vx *= 0.95
            self.vz *= 0.95
        elif not is_driving:
            self.vx *= 0.85
            self.vz *= 0.85

        if self.ability_cooldown > 0.0:
            self.ability_cooldown -= dt
        if self.shockwave_timer > 0.0:
            self.shockwave_timer -= dt
        if self.titan_timer > 0.0:
            self.titan_timer -= dt
            if self.titan_timer <= 0.0:
                self.mass = self.base_mass

        self.x += self.vx * dt
        self.z += self.vz * dt

        if math.hypot(self.x, self.z) > ARENA_RADIUS:
            self.is_alive = False
            self.fall_speed = 3.0
            self.spin_speed = random.uniform(-6.0, 6.0)

    def draw(self):
        car_pos = pr.Vector3(self.x, self.y, self.z)
        
        draw_color = self.color
        if self.titan_timer > 0.0:
            draw_color = pr.WHITE
        elif self.stun_timer > 0.0 and int(pr.get_time() * 20) % 2 == 0:
            draw_color = pr.LIGHTGRAY

        pr.draw_cube(car_pos, 2.0, 0.8, 1.6, draw_color)
        pr.draw_cube_wires(car_pos, 2.0, 0.8, 1.6, pr.WHITE if self.is_player else pr.BLACK)

        cabin_pos = pr.Vector3(self.x, self.y + 0.55, self.z)
        pr.draw_cube(cabin_pos, 1.1, 0.5, 1.1, pr.LIGHTGRAY if self.is_player else pr.DARKGRAY)

        nose_x = self.x + math.cos(self.angle) * 0.95
        nose_z = self.z + math.sin(self.angle) * 0.95
        pr.draw_sphere(pr.Vector3(nose_x, self.y + 0.1, nose_z), 0.3, GOLD)

        if self.shockwave_timer > 0.0:
            ring_rad = (0.30 - self.shockwave_timer) * 25.0
            pr.draw_circle_3d(pr.Vector3(self.x, 0.2, self.z), ring_rad, pr.Vector3(1, 0, 0), 90.0, CYAN)

# -------------------------------------------------------------
# COLLISION LOGIC (BASE=2.0, MULTIPLIER=1.0)
# -------------------------------------------------------------
def resolve_car_collision(c1, c2):
    global screen_shake
    if not (c1.is_alive and c2.is_alive):
        return

    dx = c2.x - c1.x
    dz = c2.z - c1.z
    dist = math.hypot(dx, dz)
    min_dist = c1.radius + c2.radius

    if 0.001 < dist < min_dist:
        nx = dx / dist
        nz = dz / dist

        overlap = 0.5 * (min_dist - dist)
        c1.x -= nx * overlap
        c1.z -= nz * overlap
        c2.x += nx * overlap
        c2.z += nz * overlap

        rel_v = (c1.vx - c2.vx) * nx + (c1.vz - c2.vz) * nz

        BASE_FORCE = 2.0
        SPEED_MULT = 1.0

        if abs(rel_v) > 0.01:
            total_force = (abs(rel_v) * SPEED_MULT) + BASE_FORCE

            if rel_v > 0:
                attacker, victim = c1, c2
                dir_sign = 1.0
            else:
                attacker, victim = c2, c1
                dir_sign = -1.0

            mass_ratio_victim = attacker.mass / (attacker.mass + victim.mass)
            victim.vx += (nx * dir_sign) * (total_force * mass_ratio_victim) * 3.5
            victim.vz += (nz * dir_sign) * (total_force * mass_ratio_victim) * 3.5
            victim.stun_timer = 0.45

            recoil_factor = min(0.12, 0.08 * (victim.mass / (attacker.mass + victim.mass)))
            attacker.vx -= (nx * dir_sign) * (total_force * recoil_factor)
            attacker.vz -= (nz * dir_sign) * (total_force * recoil_factor)

            if attacker.is_player and not victim.is_player:
                victim.last_hit_by_player = True

            # Robust screen shake impulse on impact
            if c1.is_player or c2.is_player:
                screen_shake = min(0.85, screen_shake + 0.45)

# -------------------------------------------------------------
# SPEEDOMETER HUD DRAWING FUNCTION
# -------------------------------------------------------------
def draw_speedometer(cx, cy, radius, current_speed, max_displayed_speed=50.0):
    pr.draw_circle(cx, cy, radius + 4, pr.Color(16, 20, 32, 230))
    pr.draw_circle(cx, cy, radius, pr.Color(26, 32, 48, 255))
    pr.draw_circle_lines(cx, cy, radius, pr.Color(60, 75, 110, 255))

    num_ticks = 9
    start_deg = 135.0
    end_deg = 405.0
    for i in range(num_ticks):
        fraction = i / (num_ticks - 1)
        tick_angle = math.radians(start_deg + fraction * (end_deg - start_deg))
        t_cos = math.cos(tick_angle)
        t_sin = math.sin(tick_angle)
        p_inner = pr.Vector2(cx + t_cos * (radius - 10), cy + t_sin * (radius - 10))
        p_outer = pr.Vector2(cx + t_cos * (radius - 3), cy + t_sin * (radius - 3))
        tick_color = NEON_RED if fraction >= 0.75 else (GOLD if fraction >= 0.45 else CYAN)
        pr.draw_line_ex(p_inner, p_outer, 2.0, tick_color)

    speed_ratio = max(0.0, min(1.0, current_speed / max_displayed_speed))
    needle_deg = start_deg + speed_ratio * (end_deg - start_deg)
    needle_rad = math.radians(needle_deg)

    needle_len = radius - 8
    tip_x = cx + math.cos(needle_rad) * needle_len
    tip_y = cy + math.sin(needle_rad) * needle_len

    needle_color = NEON_RED if speed_ratio > 0.75 else (GOLD if speed_ratio > 0.45 else CYAN)
    pr.draw_line_ex(pr.Vector2(cx, cy), pr.Vector2(tip_x, tip_y), 3.0, needle_color)

    pr.draw_circle(cx, cy, 7, pr.Color(12, 14, 22, 255))
    pr.draw_circle(cx, cy, 4, needle_color)

    speed_val_str = f"{int(round(current_speed))}"
    unit_str = "VEL"
    val_w = pr.measure_text(speed_val_str, 16)
    pr.draw_text(speed_val_str, cx - val_w // 2, cy + 18, 16, pr.WHITE)
    unit_w = pr.measure_text(unit_str, 10)
    pr.draw_text(unit_str, cx - unit_w // 2, cy + 34, 10, pr.GRAY)

# -------------------------------------------------------------
# MATCH CONTROLLER
# -------------------------------------------------------------
def start_new_match():
    global player, ai_bots, match_kills, match_shards_earned, match_won, game_state
    match_kills = 0
    match_shards_earned = 0
    match_won = False

    player_color = SKINS[equipped_skin_idx]["color"]
    player_ability = ABILITIES[equipped_ability_idx]["name"]
    player = BumperCar(0.0, 11.0, -math.pi / 2, player_color, is_player=True, ability=player_ability)

    ai_colors = [NEON_RED, pr.ORANGE, PURPLE, pr.GREEN]
    ai_abilities = ["Nitro Dash", "Shockwave", "Titan Heavy", "Standard Engine"]
    ai_bots = []

    spawn_coords = [
        (0.0, -11.0),
        (-11.0, 0.0),
        (11.0, 0.0),
        (-7.5, -7.5),
    ]

    for i, (sx, sz) in enumerate(spawn_coords):
        heading = math.atan2(-sz, -sx)
        bot_ability = random.choice(ai_abilities)
        bot = BumperCar(sx, sz, heading, ai_colors[i], ability=bot_ability)
        bot.last_hit_by_player = False
        ai_bots.append(bot)

    game_state = "PLAYING"

player, ai_bots = None, []

# Cameras
camera = pr.Camera3D(
    pr.Vector3(0.0, 22.0, 28.0),
    pr.Vector3(0.0, 0.0, 0.0),
    pr.Vector3(0.0, 1.0, 0.0),
    45.0,
    pr.CAMERA_PERSPECTIVE
)

shop_camera = pr.Camera3D(
    pr.Vector3(4.5, 3.8, 4.8),
    pr.Vector3(0.0, 0.2, 0.0),
    pr.Vector3(0.0, 1.0, 0.0),
    45.0,
    pr.CAMERA_PERSPECTIVE
)

# -------------------------------------------------------------
# MAIN GAME LOOP
# -------------------------------------------------------------
while not pr.window_should_close():
    dt = pr.get_frame_time()

    # ======================== TITLE SCREEN ========================
    if game_state == "TITLE":
        if pr.is_key_pressed(pr.KEY_ENTER) or pr.is_key_pressed(pr.KEY_SPACE):
            start_new_match()
        elif pr.is_key_pressed(pr.KEY_S):
            game_state = "SHOP"

        pr.begin_drawing()
        pr.clear_background(pr.Color(12, 14, 22, 255))

        pr.draw_text("ROOF RUMBLE", SCREEN_WIDTH // 2 - pr.measure_text("ROOF RUMBLE", 48) // 2, 160, 48, CYAN)
        pr.draw_text("3D BUMPER ARENA", SCREEN_WIDTH // 2 - pr.measure_text("3D BUMPER ARENA", 16) // 2, 218, 16, pr.GRAY)

        shard_badge = f"{player_shards} SHARDS"
        b_w = pr.measure_text(shard_badge, 18) + 40
        pr.draw_rectangle_rounded(pr.Rectangle(SCREEN_WIDTH // 2 - b_w // 2, 255, b_w, 32), 0.5, 4, pr.Color(22, 26, 40, 255))
        pr.draw_circle(SCREEN_WIDTH // 2 - b_w // 2 + 16, 271, 5, GOLD)
        pr.draw_text(shard_badge, SCREEN_WIDTH // 2 - b_w // 2 + 28, 263, 18, GOLD)

        btn_w, btn_h = 260, 48
        pr.draw_rectangle_rounded(pr.Rectangle(SCREEN_WIDTH // 2 - btn_w // 2, 330, btn_w, btn_h), 0.25, 4, CYAN)
        pr.draw_text("PLAY  [ENTER]", SCREEN_WIDTH // 2 - pr.measure_text("PLAY  [ENTER]", 18) // 2, 345, 18, pr.BLACK)

        pr.draw_rectangle_rounded_lines(pr.Rectangle(SCREEN_WIDTH // 2 - btn_w // 2, 395, btn_w, btn_h), 0.25, 4, pr.WHITE)
        pr.draw_text("GARAGE & SHOP  [S]", SCREEN_WIDTH // 2 - pr.measure_text("GARAGE & SHOP  [S]", 16) // 2, 411, 16, pr.WHITE)

        pr.draw_text("WASD to Drive   |   SPACE for Special Ability", SCREEN_WIDTH // 2 - 160, 560, 14, pr.DARKGRAY)
        pr.end_drawing()
        continue

    # ======================== SHOP SCREEN ========================
    elif game_state == "SHOP":
        if pr.is_key_pressed(pr.KEY_ESCAPE) or pr.is_key_pressed(pr.KEY_B):
            game_state = "TITLE"

        if pr.is_key_pressed(pr.KEY_TAB):
            selected_tab = "ABILITIES" if selected_tab == "SKINS" else "SKINS"
            shop_cursor = 0

        active_list = SKINS if selected_tab == "SKINS" else ABILITIES
        if pr.is_key_pressed(pr.KEY_UP) or pr.is_key_pressed(pr.KEY_W):
            shop_cursor = (shop_cursor - 1) % len(active_list)
        if pr.is_key_pressed(pr.KEY_DOWN) or pr.is_key_pressed(pr.KEY_S):
            shop_cursor = (shop_cursor + 1) % len(active_list)

        if pr.is_key_pressed(pr.KEY_ENTER) or pr.is_key_pressed(pr.KEY_SPACE):
            target = active_list[shop_cursor]
            if target["owned"]:
                if selected_tab == "SKINS":
                    equipped_skin_idx = shop_cursor
                else:
                    equipped_ability_idx = shop_cursor
            elif player_shards >= target["cost"]:
                player_shards -= target["cost"]
                target["owned"] = True
                if selected_tab == "SKINS":
                    equipped_skin_idx = shop_cursor
                else:
                    equipped_ability_idx = shop_cursor

        pr.begin_drawing()
        pr.clear_background(pr.Color(16, 18, 28, 255))

        pr.draw_text("THE GARAGE", 50, 30, 26, pr.WHITE)
        pr.draw_text(f"SHARDS: {player_shards}", SCREEN_WIDTH - 220, 35, 20, GOLD)

        tab_skin_col = CYAN if selected_tab == "SKINS" else pr.GRAY
        tab_ab_col = CYAN if selected_tab == "ABILITIES" else pr.GRAY
        pr.draw_text("[TAB] CHASSIS SKINS", 50, 75, 16, tab_skin_col)
        pr.draw_text("ABILITIES", 260, 75, 16, tab_ab_col)

        for i, itm in enumerate(active_list):
            y_pos = 110 + i * 75
            is_cur = (i == shop_cursor)
            is_eq = (equipped_skin_idx == i if selected_tab == "SKINS" else equipped_ability_idx == i)

            card_col = pr.Color(32, 40, 60, 255) if is_cur else pr.Color(22, 25, 38, 255)
            pr.draw_rectangle_rounded(pr.Rectangle(50, y_pos, 460, 65), 0.2, 4, card_col)
            
            if is_cur:
                pr.draw_rectangle_rounded_lines(pr.Rectangle(50, y_pos, 460, 65), 0.2, 4, CYAN)

            pic_rect = pr.Rectangle(60, y_pos + 12, 40, 40)
            pr.draw_rectangle_rounded(pic_rect, 0.2, 4, pr.Color(12, 14, 20, 255))
            pr.draw_rectangle_rounded_lines(pic_rect, 0.2, 4, pr.Color(45, 55, 75, 255))
            
            if selected_tab == "SKINS":
                car_col = itm["color"]
                pr.draw_rectangle(66, y_pos + 26, 28, 14, car_col)
                pr.draw_rectangle(71, y_pos + 20, 18, 8, pr.SKYBLUE)
                pr.draw_rectangle_lines(71, y_pos + 20, 18, 8, pr.WHITE)
                pr.draw_rectangle(64, y_pos + 38, 8, 4, pr.BLACK)
                pr.draw_rectangle(88, y_pos + 38, 8, 4, pr.BLACK)
                pr.draw_circle(94, y_pos + 33, 2, GOLD)
            else:
                pr.draw_rectangle_rounded_lines(pic_rect, 0.2, 4, GOLD)
                if itm["badge"] == "BOOST":
                    pr.draw_triangle(pr.Vector2(68, y_pos + 22), pr.Vector2(68, y_pos + 42), pr.Vector2(82, y_pos + 32), GOLD)
                    pr.draw_triangle(pr.Vector2(76, y_pos + 22), pr.Vector2(76, y_pos + 42), pr.Vector2(90, y_pos + 32), CYAN)
                elif itm["badge"] == "BURST":
                    pr.draw_circle_lines(80, y_pos + 32, 6, CYAN)
                    pr.draw_circle_lines(80, y_pos + 32, 12, GOLD)
                elif itm["badge"] == "ARMOR":
                    pr.draw_rectangle_lines(68, y_pos + 20, 24, 24, pr.WHITE)
                    pr.draw_rectangle(72, y_pos + 24, 16, 16, pr.GRAY)
                else:
                    pr.draw_line_ex(pr.Vector2(66, y_pos + 32), pr.Vector2(94, y_pos + 32), 2, pr.GRAY)

            pr.draw_text(itm["name"], 115, y_pos + 15, 18, pr.WHITE)
            desc_str = itm.get("desc", "")
            pr.draw_text(desc_str, 115, y_pos + 38, 14, pr.LIGHTGRAY)

            if is_eq:
                stat_str, stat_c = "EQUIPPED", pr.GREEN
            elif itm["owned"]:
                stat_str, stat_c = "OWNED", CYAN
            else:
                stat_str, stat_c = f"{itm['cost']} SHARDS", GOLD
            
            pr.draw_text(stat_str, 490 - pr.measure_text(stat_str, 14), y_pos + 25, 14, stat_c)

        # 3D Turntable Showcase
        preview_box = pr.Rectangle(560, 110, 480, 360)
        pr.draw_rectangle_rounded(preview_box, 0.1, 4, pr.Color(10, 12, 18, 255))
        pr.draw_text("3D LIVE INSPECTION", 560 + 240 - pr.measure_text("3D LIVE INSPECTION", 14)//2, 125, 14, pr.DARKGRAY)

        pr.begin_scissor_mode(560, 110, 480, 360)
        pr.begin_mode_3d(shop_camera)
        
        spin_ang = pr.get_time() * 1.5
        showcase_color = SKINS[shop_cursor]["color"] if selected_tab == "SKINS" else SKINS[equipped_skin_idx]["color"]

        pr.draw_cylinder(pr.Vector3(0, 0, 0), 2.2, 2.2, 0.15, 24, pr.Color(25, 30, 45, 255))
        pr.draw_cylinder_wires(pr.Vector3(0, 0, 0), 2.2, 2.2, 0.15, 24, CYAN)

        pr.draw_cube(pr.Vector3(0, 0.55, 0), 2.0, 0.8, 1.6, showcase_color)
        pr.draw_cube_wires(pr.Vector3(0, 0.55, 0), 2.0, 0.8, 1.6, pr.WHITE)
        pr.draw_cube(pr.Vector3(0, 1.1, 0), 1.1, 0.5, 1.1, pr.LIGHTGRAY)
        
        nose_off_x = math.cos(spin_ang) * 0.95
        nose_off_z = math.sin(spin_ang) * 0.95
        pr.draw_sphere(pr.Vector3(nose_off_x, 0.65, nose_off_z), 0.3, GOLD)
        
        pr.end_mode_3d()
        pr.end_scissor_mode()

        pr.draw_rectangle_rounded_lines(preview_box, 0.1, 4, pr.Color(40, 50, 75, 255))

        pr.draw_text("[UP/DOWN] Move   |   [ENTER] Buy / Equip   |   [B/ESC] Return", 50, 580, 15, pr.LIGHTGRAY)
        pr.end_drawing()
        continue

    # ======================== ARENA LOOP ========================
    all_cars = [player] + ai_bots

    # Controlled Player Movement
    is_driving = False
    if player.is_alive and player.stun_timer <= 0.0:
        dir_x, dir_z = 0.0, 0.0
        if pr.is_key_down(pr.KEY_W) or pr.is_key_down(pr.KEY_UP):    dir_z -= 1.0
        if pr.is_key_down(pr.KEY_S) or pr.is_key_down(pr.KEY_DOWN):  dir_z += 1.0
        if pr.is_key_down(pr.KEY_A) or pr.is_key_down(pr.KEY_LEFT):  dir_x -= 1.0
        if pr.is_key_down(pr.KEY_D) or pr.is_key_down(pr.KEY_RIGHT): dir_x += 1.0

        TARGET_SPEED = 24.0

        if dir_x != 0.0 or dir_z != 0.0:
            is_driving = True
            length = math.hypot(dir_x, dir_z)
            dir_x /= length
            dir_z /= length
            player.angle = math.atan2(dir_z, dir_x)

            player.vx += (dir_x * TARGET_SPEED - player.vx) * 12.0 * dt
            player.vz += (dir_z * TARGET_SPEED - player.vz) * 12.0 * dt
        else:
            player.vx += (0.0 - player.vx) * 14.0 * dt
            player.vz += (0.0 - player.vz) * 14.0 * dt

        if pr.is_key_pressed(pr.KEY_SPACE):
            player.trigger_ability(all_cars)

    player.update_physics(dt, is_driving=is_driving)

    # NPCs
    alive_targets = [c for c in all_cars if c.is_alive]

    for bot in ai_bots:
        if not bot.is_alive:
            bot.update_physics(dt)
            continue

        dist_center = math.hypot(bot.x, bot.z)

        if dist_center > (ARENA_RADIUS - 5.5):
            target_angle = math.atan2(-bot.z, -bot.x)
            diff = (target_angle - bot.angle + math.pi) % (2 * math.pi) - math.pi
            bot.angle += max(-7.5 * dt, min(7.5 * dt, diff * 8.0))
            if abs(diff) > math.pi / 3:
                bot.vx *= 0.88
                bot.vz *= 0.88
            elif bot.stun_timer <= 0.0:
                bot.vx = math.cos(bot.angle) * 20.0
                bot.vz = math.sin(bot.angle) * 20.0
        else:
            nearest = None
            min_d = 999.0
            for other in alive_targets:
                if other is bot: continue
                d = math.hypot(other.x - bot.x, other.z - bot.z)
                if d < min_d:
                    min_d = d
                    nearest = other

            if nearest:
                target_angle = math.atan2(nearest.z - bot.z, nearest.x - bot.x)
                if min_d < 6.5 and bot.ability_cooldown <= 0.0:
                    bot.trigger_ability(all_cars)
            else:
                target_angle = bot.angle

            diff = (target_angle - bot.angle + math.pi) % (2 * math.pi) - math.pi
            bot.angle += max(-5.5 * dt, min(5.5 * dt, diff * 6.0))

            if bot.stun_timer <= 0.0:
                bot.vx = math.cos(bot.angle) * 18.0
                bot.vz = math.sin(bot.angle) * 18.0

        bot.update_physics(dt, is_driving=(bot.stun_timer <= 0.0))

    # Collisions
    for i in range(len(all_cars)):
        for j in range(i + 1, len(all_cars)):
            resolve_car_collision(all_cars[i], all_cars[j])

    # Kills
    for bot in ai_bots:
        if not bot.is_alive and getattr(bot, "last_hit_by_player", False):
            match_kills += 1
            bot.last_hit_by_player = False

    enemies_left = sum(1 for b in ai_bots if b.is_alive)

    # Round Over
    if (not player.is_alive or enemies_left == 0) and game_state == "PLAYING":
        game_state = "GAMEOVER"
        match_won = (enemies_left == 0)
        if match_kills >= 3 or match_won:
            match_shards_earned = 5
        elif match_kills == 2:
            match_shards_earned = 4
        else:
            match_shards_earned = 3
        player_shards += match_shards_earned

    # -------------------------------------------------------------
    # CAMERA SHAKE CALCULATION & APPLICATION
    # -------------------------------------------------------------
    if screen_shake > 0.0:
        screen_shake = max(0.0, screen_shake - dt * 2.0)

    # Screen-space jitter magnitude
    shake_magnitude = screen_shake * 3.5
    offset_x = random.uniform(-shake_magnitude, shake_magnitude)
    offset_y = random.uniform(-shake_magnitude, shake_magnitude)

    base_cam_pos = pr.Vector3(0.0, 22.0, 28.0)
    base_target = pr.Vector3(player.x * 0.35, 0.0, player.z * 0.35)

    # Apply shake to BOTH eye and target positions
    camera.position = pr.Vector3(base_cam_pos.x + offset_x, base_cam_pos.y + offset_y, base_cam_pos.z)
    camera.target = pr.Vector3(base_target.x + offset_x, base_target.y + offset_y, base_target.z)

    # ======================== RENDER 3D ========================
    pr.begin_drawing()
    pr.clear_background(pr.Color(20, 24, 38, 255))

    pr.begin_mode_3d(camera)

    num_segments = 48
    for i in range(num_segments):
        a1 = (i / num_segments) * 2 * math.pi
        a2 = ((i + 1) / num_segments) * 2 * math.pi
        p_center = pr.Vector3(0.0, 0.0, 0.0)
        p1 = pr.Vector3(math.cos(a1) * ARENA_RADIUS, 0.0, math.sin(a1) * ARENA_RADIUS)
        p2 = pr.Vector3(math.cos(a2) * ARENA_RADIUS, 0.0, math.sin(a2) * ARENA_RADIUS)
        pr.draw_triangle_3d(p_center, p1, p2, ROOF_COLOR)
        pr.draw_line_3d(p1, p2, EDGE_RING)

    pr.draw_grid(30, 2.0)

    for car in all_cars:
        car.draw()

    pr.end_mode_3d()

    # Top-Left HUD
    pr.draw_text(f"KILLS: {match_kills}", 25, 20, 22, CYAN)
    pr.draw_text(f"ENEMIES: {enemies_left}", 25, 48, 16, pr.WHITE)
    pr.draw_text(f"SHARDS: {player_shards}", SCREEN_WIDTH - 160, 20, 22, GOLD)

    # Ability Cooldown Bar
    pr.draw_text(f"ABILITY: {player.ability.upper()}", 25, 78, 15, GOLD)
    if player.ability != "Standard Engine":
        cd_ratio = max(0.0, 1.0 - (player.ability_cooldown / 4.0))
        pr.draw_rectangle(25, 100, 110, 10, pr.DARKGRAY)
        pr.draw_rectangle(25, 100, int(110 * cd_ratio), 10, CYAN if cd_ratio >= 1.0 else pr.GRAY)
        pr.draw_rectangle_lines(25, 100, 110, 10, pr.WHITE)

    # Radial Speedometer HUD (Bottom-Right)
    if player.is_alive and game_state == "PLAYING":
        current_speed = math.hypot(player.vx, player.vz)
        draw_speedometer(
            cx=SCREEN_WIDTH - 90,
            cy=SCREEN_HEIGHT - 90,
            radius=55,
            current_speed=current_speed,
            max_displayed_speed=40.0
        )

    # Game Over Screen
    if game_state == "GAMEOVER":
        pr.draw_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, pr.Color(10, 12, 20, 210))
        title = "VICTORY!" if match_won else "KNOCKED OUT!"
        col = GOLD if match_won else NEON_RED
        pr.draw_text(title, SCREEN_WIDTH // 2 - pr.measure_text(title, 36) // 2, 200, 36, col)

        pr.draw_text(f"Eliminations: {match_kills}", SCREEN_WIDTH // 2 - 60, 260, 18, pr.WHITE)
        pr.draw_text(f"+{match_shards_earned} Shards Earned", SCREEN_WIDTH // 2 - 75, 290, 20, GOLD)

        pr.draw_rectangle_rounded(pr.Rectangle(SCREEN_WIDTH // 2 - 130, 350, 260, 42), 0.25, 4, CYAN)
        pr.draw_text("PLAY AGAIN [ENTER]", SCREEN_WIDTH // 2 - pr.measure_text("PLAY AGAIN [ENTER]", 16) // 2, 363, 16, pr.BLACK)

        pr.draw_rectangle_rounded_lines(pr.Rectangle(SCREEN_WIDTH // 2 - 130, 405, 260, 42), 0.25, 4, pr.WHITE)
        pr.draw_text("GARAGE [S]", SCREEN_WIDTH // 2 - pr.measure_text("GARAGE [S]", 16) // 2, 418, 16, pr.WHITE)

        if pr.is_key_pressed(pr.KEY_ENTER):
            start_new_match()
        elif pr.is_key_pressed(pr.KEY_S):
            game_state = "SHOP"

    pr.end_drawing()

pr.close_window()