import { COURSE } from "./config.js";

const clamp = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));

export class Game {
  constructor(onEvent = () => {}) {
    this.onEvent = onEvent;
    this.keys = new Set();
    this.reset();
  }

  reset() {
    this.player = { x: 0, y: 0, z: 0, vy: 0, grounded: true };
    this.coins = 0;
    this.health = COURSE.maxHealth;
    this.maxReached = 0;
    this.checkpoint = 0;
    this.collected = new Set();
    this.keys.clear();
    this.state = "ready";
    this.platforms = Array.from({ length: COURSE.platformCount }, (_, index) => ({
      index,
      z: index * COURSE.spacing,
      x: 0,
      moving: index > 0 && index % 8 === 5,
      hazard: index > 0 && index % 7 === 4,
    }));
  }

  start() {
    this.state = "running";
  }

  pause() {
    if (this.state !== "running") return;
    this.state = "paused";
    this.onEvent("pause");
  }

  resume() {
    if (this.state !== "paused") return;
    this.state = "running";
    this.onEvent("resume");
  }

  togglePause() {
    if (this.state === "running") this.pause();
    else if (this.state === "paused") this.resume();
  }

  jump() {
    if (this.state !== "running" || !this.player.grounded) return;
    this.player.vy = COURSE.jumpSpeed;
    this.player.grounded = false;
    this.onEvent("jump");
  }

  update(deltaTime, elapsedTime) {
    if (this.state !== "running") return;
    const dt = Math.min(deltaTime, 0.04);
    const p = this.player;
    const oldY = p.y;

    for (const platform of this.platforms) {
      if (platform.moving) platform.x = Math.sin(elapsedTime * 1.1 + platform.index) * 2.1;
    }

    const forward = Number(this.keys.has("w") || this.keys.has("arrowup"))
      - Number(this.keys.has("s") || this.keys.has("arrowdown"));
    const side = Number(this.keys.has("d") || this.keys.has("arrowright"))
      - Number(this.keys.has("a") || this.keys.has("arrowleft"));
    const diagonalScale = forward !== 0 && side !== 0 ? Math.SQRT1_2 : 1;
    p.x = clamp(p.x + side * COURSE.moveSpeed * diagonalScale * dt, -5.2, 5.2);
    p.z += forward * COURSE.moveSpeed * diagonalScale * dt;
    p.vy -= COURSE.gravity * dt;
    p.y += p.vy * dt;
    p.grounded = false;

    for (const platform of this.platforms) {
      const supported = Math.abs(p.x - platform.x) <= COURSE.platformWidth / 2
        && Math.abs(p.z - platform.z) <= COURSE.platformLength / 2;
      if (supported && p.vy <= 0 && oldY >= 0 && p.y <= 0) {
        p.y = 0;
        p.vy = 0;
        p.grounded = true;
        this.#reachPlatform(platform.index);
        break;
      }
    }

    const currentPlatform = this.#platformAt(p.z);
    if (currentPlatform && currentPlatform.hazard && p.y < 1.25
      && Math.abs(p.z - currentPlatform.z) < 1.15
      && Math.abs(p.x - currentPlatform.x) < 1.25) {
      this.#takeDamage();
    }

    if (p.y < -9) this.#respawn("Fell! Back to your last checkpoint.");
    this.#collectStar();
  }

  #platformAt(z) {
    return this.platforms.find((platform) =>
      Math.abs(z - platform.z) <= COURSE.platformLength / 2
      && Math.abs(this.player.x - platform.x) <= COURSE.platformWidth / 2);
  }

  #reachPlatform(index) {
    if (index <= this.maxReached) return;
    this.maxReached = index;
    if ((index + 1) % COURSE.checkpointInterval === 0) {
      this.checkpoint = index;
      this.onEvent("checkpoint");
    }
    if (index === COURSE.platformCount - 1) {
      this.state = "won";
      this.onEvent("won");
    }
  }

  #collectStar() {
    const platform = this.#platformAt(this.player.z);
    if (!platform || this.player.y > 2.8 || this.collected.has(platform.index)) return;
    const starX = platform.x + (platform.index % 2 === 0 ? -1.5 : 1.5);
    if (Math.abs(this.player.x - starX) > 1.25) return;
    this.collected.add(platform.index);
    this.coins += 1;
    this.onEvent("coin");
  }

  #takeDamage() {
    const platform = this.#platformAt(this.player.z);
    if (platform) platform.hazard = false;
    this.health -= 1;
    this.onEvent("hurt");
    if (this.health <= 0) {
      this.state = "lost";
      this.onEvent("lost");
      return;
    }
    this.#respawn("Ouch! Watch for the glowing hazards.");
  }

  #respawn(message) {
    const platform = this.platforms[this.checkpoint];
    this.player = { x: platform.x, y: 0, z: platform.z, vy: 0, grounded: true };
    this.onEvent("respawn", message);
  }
}
