import math
import random
import threading
import time
import tkinter as tk
from tkinter import simpledialog

try:
    import winsound  # Windows
except ImportError:
    winsound = None

# ----------------------------- Settings -----------------------------

GRAVITY = 24.0
JUMP_SPEED = 16.0
MOVE_SPEED = 10.0

FOCAL_LENGTH = 520.0
NEAR_PLANE = 0.5
EYE_HEIGHT = 1.5
CAMERA_DISTANCE = 6.0
CAMERA_HEIGHT = 3.0

SHOT_COOLDOWN = 0.35
GRENADE_FUSE = 1.5
GRENADE_RADIUS = 7.0
LASER_CLEARANCE = 2.4

WIDTH, HEIGHT = 1000, 700
LEVEL_COUNT = 10
PLATFORMS_PER_LEVEL = 5
PLATFORM_COUNT = LEVEL_COUNT * PLATFORMS_PER_LEVEL
PLATFORM_SPACING = 8.0
PLATFORM_LENGTH = 5.4
PLATFORM_WIDTH = 8.0

AVATAR_COLORS = {
    "Blue": "#4388ff",
    "Red": "#ef5350",
    "Green": "#52c878",
    "Purple": "#ae72e8",
    "Gold": "#f3c84b",
}

AVATAR_STYLES = {
    "Blue": {"skin": "#f0c49b", "hair": "#4a3028", "accent": "#ffd166"},
    "Red": {"skin": "#e7ae8e", "hair": "#34263c", "accent": "#ffe2c2"},
    "Green": {"skin": "#c98f78", "hair": "#302b28", "accent": "#e8f5b8"},
    "Purple": {"skin": "#f1c6a7", "hair": "#322744", "accent": "#f6dcff"},
    "Gold": {"skin": "#e2aa82", "hair": "#65402a", "accent": "#fff1b0"},
}

SNIPER_COOLDOWN = 0.1
BOSS_SPAWN_INTERVAL = 20.0
BOSS_HEALTH = 5
BOSS_DAMAGE = 50
BOSS_SPEED = 1.0  # Normal monsters move at 2.4
FULLSCREEN = True


def play_sound(root, sound="shot"):
    """Play a short sound without blocking the Tkinter event loop."""
    sounds = {
        "shot": (1000, 70),
        "boss_spawn": (180, 500),
        "boss_hit": (300, 180),
        "boss_die": (850, 350),
        "damage": (120, 250),
        "explosion": (100, 300),
    }
    frequency, duration = sounds[sound]

    if winsound is not None:
        threading.Thread(
            target=winsound.Beep,
            args=(frequency, duration),
            daemon=True,
        ).start()
        return

    root.bell()


def clamp(value, low, high):
    return max(low, min(high, value))


class ObbyGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Tkinter 3D Obby")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root, width=WIDTH, height=HEIGHT,
            bg="#87c9ee", highlightthickness=0
        )
        self.canvas.pack()
        self.canvas.focus_set()

        self.keys = set()
        self.yaw = 0.0
        self.pitch = 0.0
        self.first_person = False

        self.coins = 0
        self.owned_avatars = {"Blue"}
        self.avatar_name = "Blue"
        self.avatar_color = AVATAR_COLORS["Blue"]

        self.jetpack_owned = False
        self.jetpack_fuel = 0.0
        self.jetpack_until = 0.0

        self.hp = 100
        self.last_monster_hit = 0.0

        self.last_shot = 0.0
        self.pistol_recoil = 0.0
        self.muzzle_flash_until = 0.0

        self.grenades = []
        self.explosions = []

        self.message = ""
        self.message_until = 0.0
        self.last_time = time.monotonic()

        self.player = {
            "x": 0.0, "y": 0.0, "z": 0.0,
            "vy": 0.0, "grounded": True,
        }

        self.checkpoint = 0
        self.max_reached = 0
        self.platforms = []
        self.moving_platforms = {}
        self.monsters = []

        self._make_world()
        self._bind_events()
        self.root.after(16, self._tick)

        # Sniper
        self.sniper_mode = False
        self.sniper_ammo = float("inf")
        self.last_sniper_shot = 0.0
        self.sniper_recoil = 0.0

        # Mega boss
        self.boss = None
        self.boss_hits = 0
        self.next_boss_spawn = time.monotonic() + BOSS_SPAWN_INTERVAL

        # Fullscreen
        self.fullscreen = FULLSCREEN
        self.root.attributes("-fullscreen", self.fullscreen)

        self._draw_boss()

    # ----------------------------- World -----------------------------

    def _make_world(self):
        for i in range(PLATFORM_COUNT):
            platform = {
                "index": i,
                "x": 0.0,
                "z": i * PLATFORM_SPACING,
                "width": PLATFORM_WIDTH,
                "length": PLATFORM_LENGTH,
                "moving": i > 0 and i % 9 == 6,
            }
            self.platforms.append(platform)

            if platform["moving"]:
                self.moving_platforms[i] = platform

            if i > 0 and i % 3 == 0:
                self.monsters.append({
                    "x": random.choice([-2.0, 2.0]),
                    "y": 0.0,
                    "z": platform["z"],
                    "alive": True,
                })

    def _bind_events(self):
        self.root.bind("<KeyPress>", self._key_down)
        self.root.bind("<KeyRelease>", self._key_up)
        self.canvas.bind("<Motion>", self._mouse_move)
        self.canvas.bind("<Button-1>", self._shoot)
        self.canvas.bind("<Button-3>", self._throw_grenade)
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._exit_fullscreen)

    # ----------------------------- Input -----------------------------

    def _key_down(self, event):
        key = event.keysym.lower()
        self.keys.add(key)

        if key == "space":
            self._jump()
        elif key == "v":
            self.first_person = not self.first_person
        elif key == "g":
            self._throw_grenade()
        elif key == "r":
            self._return_to_checkpoint()
        elif key == "j":
            self._activate_jetpack()
        elif key == "b":
            self._open_avatar_shop()
        elif key == "n":
            self._open_gadget_shop()
        elif key == "t":
            self.sniper_mode = not self.sniper_mode
            self._notice(
                "SNIPER MODE ON — infinite ammo"
                if self.sniper_mode else "Sniper mode off"
            )

    def _key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def _mouse_move(self, event):
        self.yaw = clamp((event.x - WIDTH / 2) / 240.0, -1.2, 1.2)
        self.pitch = clamp(-(event.y - HEIGHT / 2) / 260.0, -0.55, 0.55)

    def _forward_vector(self):
        return math.sin(self.yaw), math.cos(self.yaw)

    def _jump(self):
        if self.player["grounded"]:
            self.player["vy"] = JUMP_SPEED
            self.player["grounded"] = False
            self.coins += 1
            self._notice("+1 coin")

    # ----------------------------- Shops and actions -----------------------------

    def _open_avatar_shop(self):
        options = list(AVATAR_COLORS)
        choice = simpledialog.askstring(
            "Avatar shop",
            "Outfits cost 5 coins each.\nEnter: " + ", ".join(options),
            parent=self.root,
        )
        if not choice:
            return

        color_name = next(
            (name for name in options if name.lower() == choice.strip().lower()),
            None
        )
        if color_name is None:
            self._notice("Unknown color")
            return

        if color_name not in self.owned_avatars:
            if self.coins < 5:
                self._notice("Need 5 coins")
                return
            self.coins -= 5
            self.owned_avatars.add(color_name)

        self.avatar_name = color_name
        self.avatar_color = AVATAR_COLORS[color_name]
        self._notice(f"{color_name} equipped")

    def _open_gadget_shop(self):
        choice = simpledialog.askstring(
            "Gadget shop",
            "Enter 'jetpack' (10 coins) or 'fuel' (10 coins):",
            parent=self.root,
        )
        if not choice:
            return

        choice = choice.strip().lower()
        if choice not in ("jetpack", "fuel"):
            self._notice("Choose jetpack or fuel")
        elif self.coins < 10:
            self._notice("Need 10 coins")
        elif choice == "jetpack":
            self.coins -= 10
            self.jetpack_owned = True
            self.jetpack_fuel += 10.0
            self._notice("Jetpack purchased: 10 seconds of fuel")
        elif not self.jetpack_owned:
            self._notice("Buy a jetpack first")
        else:
            self.coins -= 10
            self.jetpack_fuel += 10.0
            self._notice("10 seconds of fuel added")

    def _activate_jetpack(self):
        if not self.jetpack_owned:
            self._notice("Buy a jetpack in the gadget shop (N)")
        elif self.jetpack_fuel <= 0:
            self._notice("No jetpack fuel")
        else:
            duration = min(10.0, self.jetpack_fuel)
            self.jetpack_until = time.monotonic() + duration
            self._notice("Jetpack on")

    def _shoot(self, event=None):
        if self.sniper_mode:
            self._shoot_sniper(event)
            return
        
        now = time.monotonic()
        if now - self.last_shot < SHOT_COOLDOWN:
            return

        self.last_shot = now
        self.pistol_recoil = 1.0
        self.muzzle_flash_until = now + 0.07

        px, pz = self.player["x"], self.player["z"]
        fx, fz = self._forward_vector()
        target = None
        best_distance = 22.0

        for monster in self.monsters:
            if not monster["alive"]:
                continue

            dx = monster["x"] - px
            dz = monster["z"] - pz
            distance = math.hypot(dx, dz)
            if distance > best_distance:
                continue

            dot = (dx * fx + dz * fz) / max(distance, 0.001)
            side = abs(dx * fz - dz * fx)
            if dot > 0.75 and side < 2.0:
                target = monster
                best_distance = distance

        if target:
            target["alive"] = False
            self._notice("Monster eliminated")
        else:
            self._notice("Miss")

    def _throw_grenade(self, event=None):
        fx, fz = self._forward_vector()
        p = self.player
        now = time.monotonic()

        self.grenades.append({
            "x": p["x"] + fx * 1.5,
            "y": p["y"] + 1.0,
            "z": p["z"] + fz * 1.5,
            "vx": fx * 9.0,
            "vy": 5.0,
            "vz": fz * 9.0,
            "created_at": now,
            "explode_at": now + GRENADE_FUSE,
        })
        self._notice("Grenade thrown")

    def _return_to_checkpoint(self):
        platform = self.platforms[self.checkpoint]
        self.player.update(
            x=platform["x"],
            y=0.0,
            z=platform["z"],
            vy=0.0,
            grounded=True,
        )

    def _notice(self, text):
        self.message = text
        self.message_until = time.monotonic() + 1.8

    # ----------------------------- Simulation -----------------------------

    def _tick(self):
        now = time.monotonic()
        dt = min(now - self.last_time, 0.04)
        self.last_time = now

        self._update(dt, now)
        self._draw()
        self.root.after(16, self._tick)

    def _update(self, dt, now):
        p = self.player

        # Spawn a new boss every 10 seconds.
        if now >= self.next_boss_spawn:
            self._spawn_boss(now)
            self.next_boss_spawn = now + BOSS_SPAWN_INTERVAL

        # Moving platforms slide sideways.
        for index, platform in self.moving_platforms.items():
            platform["x"] = math.sin(now * 1.3 + index) * 2.2

        fx, fz = self._forward_vector()
        rx, rz = math.cos(self.yaw), -math.sin(self.yaw)

        forward = (
            int("w" in self.keys or "up" in self.keys)
            - int("s" in self.keys or "down" in self.keys)
        )
        sideways = (
            int("d" in self.keys or "right" in self.keys)
            - int("a" in self.keys or "left" in self.keys)
        )

        p["x"] += (fx * forward + rx * sideways) * MOVE_SPEED * dt
        p["z"] += (fz * forward + rz * sideways) * MOVE_SPEED * dt

        jet_active = now < self.jetpack_until
        if jet_active:
            self.jetpack_fuel = max(0.0, self.jetpack_fuel - dt)
            p["vy"] = max(p["vy"], 5.0)
        else:
            p["vy"] -= GRAVITY * dt

        old_y = p["y"]
        p["y"] += p["vy"] * dt
        p["grounded"] = False

        # Platform landing and support.
        for platform in self.platforms:
            on_platform = (
                abs(p["x"] - platform["x"]) <= platform["width"] / 2
                and abs(p["z"] - platform["z"]) <= platform["length"] / 2
            )
            if on_platform and p["vy"] <= 0 and old_y >= 0 and p["y"] <= 0:
                p["y"] = 0
                p["vy"] = 0
                p["grounded"] = True
                self.max_reached = max(self.max_reached, platform["index"])

                if (platform["index"] + 1) % PLATFORMS_PER_LEVEL == 0:
                    self.checkpoint = platform["index"]
                break

        if p["y"] < -12:
            self._return_to_checkpoint()
            self._notice("You fell — checkpoint restored")

        # Lasers every 20 platforms. Jump or fly above the beam.
        for i in range(20, PLATFORM_COUNT, 20):
            laser_z = self.platforms[i]["z"]
            if abs(p["z"] - laser_z) < 0.8 and abs(p["x"]) < 3.4:
                if p["y"] < LASER_CLEARANCE:
                    self._return_to_checkpoint()
                    self._notice("Laser hit! Use J to fly over it")
                    break

        # Monsters chase the player and attack at close range.
        for monster in self.monsters:
            if not monster["alive"]:
                continue

            dx = p["x"] - monster["x"]
            dz = p["z"] - monster["z"]
            distance = math.hypot(dx, dz)

            # Keep the monster's movement on its platform level.
            if distance > 1.15:
                monster["x"] += (dx / max(distance, 0.001)) * 2.4 * dt
                monster["z"] += (dz / max(distance, 0.001)) * 2.4 * dt

            if distance < 1.35 and now - self.last_monster_hit >= 0.8:
                self.hp = max(0, self.hp - 10)
                self.last_monster_hit = now
                self._notice("Monster hit! -10 HP")

                if self.hp <= 0:
                    self._return_to_checkpoint()
                    self.hp = 100
                    self._notice("You were defeated — respawned at checkpoint")

        # Grenade flight, explosions, and monster damage.
        remaining = []
        for grenade in self.grenades:
            grenade["x"] += grenade["vx"] * dt
            grenade["y"] += grenade["vy"] * dt
            grenade["z"] += grenade["vz"] * dt
            grenade["vy"] -= GRAVITY * dt

            if now >= grenade["explode_at"]:
                self.explosions.append({
                    "x": grenade["x"],
                    "y": grenade["y"],
                    "z": grenade["z"],
                    "started": now,
                })
                for monster in self.monsters:
                    distance = math.dist(
                        (monster["x"], monster["z"]),
                        (grenade["x"], grenade["z"]),
                    )
                    if monster["alive"] and distance <= GRENADE_RADIUS:
                        monster["alive"] = False
                continue

            remaining.append(grenade)

        self.grenades = remaining
        self.explosions = [
            effect for effect in self.explosions
            if now - effect["started"] < 0.55
        ]
        self.pistol_recoil = max(0.0, self.pistol_recoil - dt * 7.0)


        if self.boss and self.boss["alive"]:
            boss = self.boss

            dx = p["x"] - boss["x"]
            dz = p["z"] - boss["z"]
            distance = math.hypot(dx, dz)

            # Half the normal monster's speed: 1.2 instead of 2.4.
            if distance > 1.5:
                boss["x"] += dx / max(distance, 0.001) * BOSS_SPEED * dt
                boss["z"] += dz / max(distance, 0.001) * BOSS_SPEED * dt

            # Each hit deals 50 HP, so two hits defeat the player.
            if distance < 1.8 and now - boss["last_attack"] >= 1.0:
                self.hp = max(0, self.hp - BOSS_DAMAGE)
                boss["last_attack"] = now

                play_sound(self.root, "damage")
                self._notice(f"MEGA BOSS HIT! -{BOSS_DAMAGE} HP")

                if self.hp <= 0:
                    self._return_to_checkpoint()
                    self.hp = 100
                    self._notice("Boss defeated you — checkpoint respawn!")

    # ----------------------------- Projection -----------------------------

    def _camera(self):
        p = self.player
        fx, fz = self._forward_vector()

        if self.first_person:
            return (p["x"], p["y"] + EYE_HEIGHT, p["z"]), (fx, fz)

        return (
            p["x"] - fx * CAMERA_DISTANCE,
            p["y"] + CAMERA_HEIGHT,
            p["z"] - fz * CAMERA_DISTANCE,
        ), (fx, fz)

    def _project(self, point):
        (cx, cy, cz), (fx, fz) = self._camera()
        x, y, z = point
        dx, dy, dz = x - cx, y - cy, z - cz

        right_x, right_z = fz, -fx
        cam_x = dx * right_x + dz * right_z
        cam_forward = dx * fx + dz * fz

        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        depth = cam_forward * cp + dy * sp
        vertical = dy * cp - cam_forward * sp

        if depth <= NEAR_PLANE:
            return None

        sx = WIDTH / 2 + FOCAL_LENGTH * cam_x / depth
        sy = HEIGHT / 2 - FOCAL_LENGTH * vertical / depth
        return sx, sy, depth

    def _poly(self, points, fill, outline=None):
        projected = [self._project(point) for point in points]
        if any(point is None for point in projected):
            return

        coords = []
        for sx, sy, _ in projected:
            coords.extend((sx, sy))

        self.canvas.create_polygon(
            *coords, fill=fill, outline=outline or fill, width=1
        )

    def _box(self, x, y, z, width, height, length, color, shadow=False):
        x0, x1 = x - width / 2, x + width / 2
        z0, z1 = z - length / 2, z + length / 2
        y0, y1 = y, y + height

        if shadow:
            self._poly([
                (x0, 0.03, z0), (x1, 0.03, z0),
                (x1, 0.03, z1), (x0, 0.03, z1),
            ], "#59666e")

        self._poly([
            (x0, y1, z0), (x1, y1, z0),
            (x1, y1, z1), (x0, y1, z1),
        ], color)
        self._poly([
            (x0, y0, z0), (x1, y0, z0),
            (x1, y1, z0), (x0, y1, z0),
        ], "#4f5964")
        self._poly([
            (x1, y0, z0), (x1, y0, z1),
            (x1, y1, z1), (x1, y1, z0),
        ], "#697582")

    # ----------------------------- Drawing -----------------------------

    def _draw_platform(self, platform):
        i = platform["index"]
        color = "#49a8ff" if i % PLATFORMS_PER_LEVEL == 0 else "#55c76a"
        if platform["moving"]:
            color = "#edaa38"

        self._box(
            platform["x"], -0.35, platform["z"],
            platform["width"], 0.7, platform["length"],
            color, shadow=True,
        )

    def _draw_laser(self, index):
        z = self.platforms[index]["z"]

        for x in (-3.5, 3.5):
            self._box(x, 0, z, 0.22, 3.2, 0.22, "#bd293e")

        a = self._project((-3.5, LASER_CLEARANCE, z))
        b = self._project((3.5, LASER_CLEARANCE, z))
        if a and b:
            self.canvas.create_line(
                a[0], a[1], b[0], b[1], fill="#ff244e", width=5
            )

    def _draw_monster(self, monster):
        if not monster["alive"]:
            return

        head = self._project((monster["x"], 1.35, monster["z"]))
        body = self._project((monster["x"], 0.75, monster["z"]))
        if not head or not body:
            return

        radius = clamp(180 / head[2], 3, 24)
        self.canvas.create_oval(
            head[0] - radius, head[1] - radius,
            head[0] + radius, head[1] + radius,
            fill="#6f3f86", outline="#321e3e", width=2,
        )
        self.canvas.create_rectangle(
            body[0] - radius * 0.7, body[1] - radius * 0.2,
            body[0] + radius * 0.7, body[1] + radius * 2.2,
            fill="#783d8f", outline="#321e3e", width=2,
        )

        eye_radius = max(1, radius * 0.13)
        for offset in (-0.45, 0.45):
            ex = head[0] + radius * offset
            self.canvas.create_oval(
                ex - eye_radius, head[1] - eye_radius,
                ex + eye_radius, head[1] + eye_radius,
                fill="white",
            )

    def _draw_2d_avatar(self):
        """Draw the third-person player as a screen-facing 2D character."""
        p = self.player
        style = AVATAR_STYLES[self.avatar_name]
        point = self._project((p["x"], p["y"] + 1.1, p["z"]))
        feet = self._project((p["x"], p["y"], p["z"]))
        if point is None or feet is None:
            return

        sx, sy, depth = point
        _, feet_y, _ = feet
        scale = clamp(300 / depth, 0.25, 1.5)
        body_h = 70 * scale
        body_w = 26 * scale
        head_r = 11 * scale

        # Legs and shoes.
        leg_color = "#303c59"
        self.canvas.create_line(
            sx - 5 * scale, feet_y - 28 * scale,
            sx - 7 * scale, feet_y,
            fill=leg_color, width=max(2, int(8 * scale)),
        )
        self.canvas.create_line(
            sx + 5 * scale, feet_y - 28 * scale,
            sx + 7 * scale, feet_y,
            fill=leg_color, width=max(2, int(8 * scale)),
        )
        self.canvas.create_line(
            sx - 7 * scale, feet_y,
            sx - 13 * scale, feet_y,
            fill="#202530", width=max(2, int(7 * scale)),
        )
        self.canvas.create_line(
            sx + 7 * scale, feet_y,
            sx + 13 * scale, feet_y,
            fill="#202530", width=max(2, int(7 * scale)),
        )
        self.canvas.create_line(
            sx - 10 * scale, feet_y - 2 * scale,
            sx - 13 * scale, feet_y - 2 * scale,
            fill="#f4f5ff", width=max(1, int(2 * scale)),
        )
        self.canvas.create_line(
            sx + 10 * scale, feet_y - 2 * scale,
            sx + 13 * scale, feet_y - 2 * scale,
            fill="#f4f5ff", width=max(1, int(2 * scale)),
        )

        # Torso, arms, and head.
        torso_top = feet_y - body_h
        self.canvas.create_rectangle(
            sx - body_w / 2, torso_top + 18 * scale,
            sx + body_w / 2, feet_y - 25 * scale,
            fill=self.avatar_color, outline="#202530",
            width=max(1, int(2 * scale)),
        )
        self.canvas.create_rectangle(
            sx - body_w / 2 + scale, torso_top + 20 * scale,
            sx + body_w / 2 - scale, torso_top + 25 * scale,
            fill=style["accent"], outline="",
        )
        self.canvas.create_line(
            sx, torso_top + 27 * scale,
            sx, feet_y - 28 * scale,
            fill=style["accent"], width=max(1, int(3 * scale)),
        )
        self.canvas.create_oval(
            sx - 2 * scale, torso_top + 30 * scale,
            sx + 2 * scale, torso_top + 34 * scale,
            fill="#fff4d4", outline="",
        )
        self.canvas.create_line(
            sx - body_w / 2, torso_top + 23 * scale,
            sx - 21 * scale, feet_y - 35 * scale,
            fill=style["skin"], width=max(3, int(7 * scale)),
        )
        self.canvas.create_line(
            sx + body_w / 2, torso_top + 23 * scale,
            sx + 21 * scale, feet_y - 35 * scale,
            fill=style["skin"], width=max(3, int(7 * scale)),
        )
        head_y = torso_top + 6 * scale
        self.canvas.create_oval(
            sx - head_r, head_y - head_r,
            sx + head_r, head_y + head_r,
            fill=style["skin"], outline="#523c32",
            width=max(1, int(scale)),
        )
        self.canvas.create_arc(
            sx - head_r, head_y - head_r,
            sx + head_r, head_y + head_r,
            start=0, extent=180, fill=style["hair"], outline=style["hair"],
        )
        eye_radius = max(1, scale * 1.2)
        for offset in (-0.38, 0.38):
            eye_x = sx + head_r * offset
            eye_y = head_y + head_r * 0.08
            self.canvas.create_oval(
                eye_x - eye_radius, eye_y - eye_radius,
                eye_x + eye_radius, eye_y + eye_radius,
                fill="#28334a", outline="",
            )
        self.canvas.create_arc(
            sx - head_r * 0.25, head_y + head_r * 0.22,
            sx + head_r * 0.25, head_y + head_r * 0.58,
            start=205, extent=130, style="arc",
            outline="#9c5548", width=max(1, int(scale)),
        )

    def _draw_cuboid_hand(self, x, y, width, height, color, outline):
        """Draw a small pseudo-3D cuboid using canvas polygons."""
        depth = max(3, width * 0.22)

        # Top face.
        self.canvas.create_polygon(
            x, y,
            x + depth, y - depth,
            x + width + depth, y - depth,
            x + width, y,
            fill="#ffd7b3", outline=outline,
        )
        # Side face.
        self.canvas.create_polygon(
            x + width, y,
            x + width + depth, y - depth,
            x + width + depth, y + height - depth,
            x + width, y + height,
            fill="#c99572", outline=outline,
        )
        # Front face.
        self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill=color, outline=outline, width=2,
        )

    def _draw_first_person_assets(self):
        recoil = self.pistol_recoil * 18

        # Forearms/hands as cuboids.
        self._draw_cuboid_hand(
            WIDTH * 0.32, HEIGHT * 0.83 + recoil,
            48, 90, "#e7b48f", "#744e3e",
        )
        self._draw_cuboid_hand(
            WIDTH * 0.63, HEIGHT * 0.83 + recoil,
            48, 90, "#e7b48f", "#744e3e",
        )

        # Pistol, raised slightly during recoil.
        self.canvas.create_rectangle(
            WIDTH * 0.52, HEIGHT * 0.76 + recoil,
            WIDTH * 0.58, HEIGHT * 0.84 + recoil,
            fill="#353b43", outline="#15191e", width=2,
        )
        self.canvas.create_rectangle(
            WIDTH * 0.535, HEIGHT * 0.72 + recoil,
            WIDTH * 0.565, HEIGHT * 0.78 + recoil,
            fill="#59616a", outline="#15191e", width=2,
        )

        if time.monotonic() < self.muzzle_flash_until:
            self.canvas.create_polygon(
                WIDTH * 0.535, HEIGHT * 0.715 + recoil,
                WIDTH * 0.565, HEIGHT * 0.715 + recoil,
                WIDTH * 0.58, HEIGHT * 0.67 + recoil,
                WIDTH * 0.55, HEIGHT * 0.69 + recoil,
                WIDTH * 0.52, HEIGHT * 0.67 + recoil,
                fill="#ffe36e", outline="#ff8b35",
            )

        cx, cy = WIDTH / 2, HEIGHT / 2
        self.canvas.create_line(cx - 9, cy, cx - 3, cy, fill="white", width=2)
        self.canvas.create_line(cx + 3, cy, cx + 9, cy, fill="white", width=2)
        self.canvas.create_line(cx, cy - 9, cx, cy - 3, fill="white", width=2)
        self.canvas.create_line(cx, cy + 3, cx, cy + 9, fill="white", width=2)

    def _draw_grenades_and_explosions(self):
        now = time.monotonic()

        for grenade in self.grenades:
            point = self._project(
                (grenade["x"], grenade["y"], grenade["z"])
            )
            if point is None:
                continue

            sx, sy, depth = point
            radius = clamp(150 / depth, 3, 13)
            spin = math.sin((now - grenade["created_at"]) * 24) * radius * 0.65

            self.canvas.create_oval(
                sx - radius, sy - radius,
                sx + radius, sy + radius,
                fill="#426c3e", outline="#172b18", width=2,
            )
            self.canvas.create_line(
                sx - spin, sy, sx + spin, sy,
                fill="#a8d779", width=2,
            )
            self.canvas.create_oval(
                sx - radius * 0.25, sy - radius * 0.25,
                sx + radius * 0.25, sy + radius * 0.25,
                fill="#b6d989", outline="",
            )

        for effect in self.explosions:
            age = now - effect["started"]
            progress = clamp(age / 0.55, 0.0, 1.0)
            point = self._project(
                (effect["x"], effect["y"] + 0.8, effect["z"])
            )
            if point is None:
                continue

            sx, sy, depth = point
            radius = clamp((25 + progress * 125) / depth * 12, 5, 90)
            color = "#ffdd55" if progress < 0.35 else "#ff782e"

            self.canvas.create_oval(
                sx - radius, sy - radius,
                sx + radius, sy + radius,
                outline=color, width=max(1, int(5 * (1 - progress))),
            )
            self.canvas.create_oval(
                sx - radius * 0.45, sy - radius * 0.45,
                sx + radius * 0.45, sy + radius * 0.45,
                fill="#ffb532", outline="#fff07a", width=2,
            )

    def _draw_health_bar(self):
        x, y = 14, 69
        bar_width, bar_height = 180, 16
        self.canvas.create_rectangle(
            x, y, x + bar_width, y + bar_height,
            fill="#401d24", outline="white",
        )
        fill_width = bar_width * self.hp / 100
        color = "#49d16d" if self.hp > 40 else "#eea936"
        if self.hp <= 20:
            color = "#ed4141"
        self.canvas.create_rectangle(
            x, y, x + fill_width, y + bar_height,
            fill=color, outline="",
        )
        self.canvas.create_text(
            x + bar_width + 8, y + bar_height / 2,
            text=f"{self.hp}/100 HP", fill="white",
            anchor="w", font=("TkDefaultFont", 10, "bold"),
        )

    def _draw(self):
        self.canvas.delete("all")
        player_z = self.player["z"]

        visible = sorted(
            (p for p in self.platforms if abs(p["z"] - player_z) < 85),
            key=lambda p: p["z"],
            reverse=True,
        )
        for platform in visible:
            self._draw_platform(platform)

        for i in range(20, PLATFORM_COUNT, 20):
            if abs(self.platforms[i]["z"] - player_z) < 85:
                self._draw_laser(i)

        for monster in self.monsters:
            if abs(monster["z"] - player_z) < 65:
                self._draw_monster(monster)

        self._draw_grenades_and_explosions()

        if self.first_person:
            self._draw_first_person_assets()
        else:
            self._draw_2d_avatar()

        level = min(
            LEVEL_COUNT,
            self.max_reached // PLATFORMS_PER_LEVEL + 1,
        )
        view = "First person" if self.first_person else "Third person"
        jet_left = max(0.0, self.jetpack_until - time.monotonic())

        hud = (
            f"Level {level}/{LEVEL_COUNT}   "
            f"Platform {self.max_reached + 1}/{PLATFORM_COUNT}   "
            f"Coins: {self.coins}   Checkpoint: {self.checkpoint + 1}\n"
            f"{view} (V)   Jetpack fuel: {self.jetpack_fuel:.1f}s"
        )
        if jet_left:
            hud += f"   Flying: {jet_left:.1f}s"

        self.canvas.create_text(
            14, 14, anchor="nw", text=hud,
            fill="white", font=("TkDefaultFont", 12, "bold"),
        )
        self._draw_health_bar()
        self._draw_boss()

        controls = (
            "W/↑ forward  S/↓ backward  A/D steer  Space jump  "
            "Mouse aim/fire  T sniper  G grenade  J jetpack  R checkpoint\n"
            "B avatar shop  N gadget shop  V switch view  F11 fullscreen  Esc exit"
        )
        self.canvas.create_text(
            WIDTH / 2, HEIGHT - 14, anchor="s",
            text=controls, fill="white",
            font=("TkDefaultFont", 10, "bold"),
        )

        if time.monotonic() < self.message_until:
            self.canvas.create_text(
                WIDTH / 2, 105, text=self.message,
                fill="#fff49a", font=("TkDefaultFont", 15, "bold"),
            )

        if self.sniper_mode:
            self._draw_sniper_scope()

    def _toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def _exit_fullscreen(self, event=None):
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)

    def _shoot_sniper(self, event=None):
        now = time.monotonic()

        if now - self.last_sniper_shot < SNIPER_COOLDOWN:
            return

        self.last_sniper_shot = now
        self.sniper_recoil = 1.0
        play_sound(self.root, "shot")

        px = self.player["x"]
        pz = self.player["z"]
        fx, fz = self._forward_vector()

        # Boss requires exactly five sniper hits.
        if self.boss and self.boss["alive"]:
            dx = self.boss["x"] - px
            dz = self.boss["z"] - pz
            distance = math.hypot(dx, dz)

            dot = (dx * fx + dz * fz) / max(distance, 0.001)
            side = abs(dx * fz - dz * fx)

            if distance <= 80 and dot > 0.96 and side < 1.8:
                self.boss["hp"] -= 1
                play_sound(self.root, "boss_hit")

                if self.boss["hp"] <= 0:
                    self.boss["alive"] = False
                    play_sound(self.root, "boss_die")
                    self._notice("MEGA BOSS DEFEATED!")
                else:
                    self._notice(
                        f"BOSS HIT! {self.boss['hp']} sniper hits remaining"
                    )
                return

        # Sniper also eliminates ordinary monsters in one shot.
        target = None
        best_distance = 80.0

        for monster in self.monsters:
            if not monster["alive"]:
                continue

            dx = monster["x"] - px
            dz = monster["z"] - pz
            distance = math.hypot(dx, dz)

            if distance >= best_distance:
                continue

            dot = (dx * fx + dz * fz) / max(distance, 0.001)
            side = abs(dx * fz - dz * fx)

            if dot > 0.96 and side < 1.8:
                target = monster
                best_distance = distance

        if target:
            target["alive"] = False
            self._notice("SNIPER HIT — monster eliminated")
        else:
            self._notice("SNIPER MISS — unlimited ammo")

    def _spawn_boss(self, now):
        # Only one living boss at a time.
        if self.boss and self.boss["alive"]:
            return

        # Spawn ahead of the player so it can approach.
        spawn_z = self.player["z"] + 30.0

        self.boss = {
            "x": random.choice([-2.0, 2.0]),
            "y": 0.0,
            "z": spawn_z,
            "hp": BOSS_HEALTH,
            "alive": True,
            "last_attack": 0.0,
        }

        play_sound(self.root, "boss_spawn")
        self._notice("⚠ MEGA BOSS HAS SPAWNED!")

    def _draw_boss(self):
        boss = self.boss

        if not boss or not boss["alive"]:
            return

        head = self._project((boss["x"], 2.8, boss["z"]))
        body = self._project((boss["x"], 1.4, boss["z"]))

        if head is None or body is None:
            return

        sx, sy, depth = head
        bx, by, _ = body

        radius = clamp(500 / depth, 10, 55)

        # Large boss head.
        self.canvas.create_oval(
            sx - radius, sy - radius,
            sx + radius, sy + radius,
            fill="#b51f35", outline="#4a0711", width=4,
        )

        # Body.
        self.canvas.create_rectangle(
            bx - radius * 0.85, by,
            bx + radius * 0.85, by + radius * 2.1,
            fill="#711526", outline="#33050c", width=3,
        )

        # Glowing eyes.
        eye_r = max(2, radius * 0.14)

        for offset in (-0.4, 0.4):
            ex = sx + radius * offset
            self.canvas.create_oval(
                ex - eye_r, sy - eye_r,
                ex + eye_r, sy + eye_r,
                fill="#fff35b", outline="white",
            )

        # Boss health indicator.
        bar_w = radius * 2.4
        bar_y = sy - radius - 15
        self.canvas.create_rectangle(
            sx - bar_w / 2, bar_y,
            sx + bar_w / 2, bar_y + 7,
            fill="#3a1018", outline="white",
        )
        self.canvas.create_rectangle(
            sx - bar_w / 2, bar_y,
            sx - bar_w / 2 + bar_w * boss["hp"] / BOSS_HEALTH,
            bar_y + 7,
            fill="#ff344e", outline="",
        )


    def _draw_sniper_scope(self):
        cx, cy = WIDTH / 2, HEIGHT / 2

        # Scope crosshairs.
        self.canvas.create_oval(
            cx - 75, cy - 75,      # Changed from 150
            cx + 75, cy + 75,       # Changed from 150
            outline="#151a1d", width=3,
        )
        self.canvas.create_line(
            cx - 125, cy, cx + 125, cy,  # Changed from 250
            fill="#161a1d", width=2,
        )
        self.canvas.create_line(
            cx, cy - 125, cx, cy + 125,  # Changed from 250
            fill="#161a1d", width=2,
        )

        # Center aiming point.
        self.canvas.create_oval(
            cx - 3, cy - 3, cx + 3, cy + 3,
            fill="#ff3030", outline="white",
        )

        self.canvas.create_text(
            WIDTH - 20, 25,
            text="SNIPER  |  AMMO: INF",
            fill="#ff4545",
            anchor="ne",
            font=("TkDefaultFont", 14, "bold"),
        )

if __name__ == "__main__":
    root = tk.Tk()
    game = ObbyGame(root)
    root.mainloop()
