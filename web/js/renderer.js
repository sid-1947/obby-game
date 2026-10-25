import { COLORS, COURSE } from "./config.js";

const clamp = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));

export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d", { alpha: false });
    this.width = 0;
    this.height = 0;
    this.pixelRatio = 1;
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas);
    this.resize();
  }

  resize() {
    const bounds = this.canvas.getBoundingClientRect();
    this.width = Math.max(1, bounds.width);
    this.height = Math.max(1, bounds.height);
    this.pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    this.canvas.width = Math.round(this.width * this.pixelRatio);
    this.canvas.height = Math.round(this.height * this.pixelRatio);
    this.context.setTransform(this.pixelRatio, 0, 0, this.pixelRatio, 0, 0);
  }

  draw(game, avatar, elapsedTime) {
    const ctx = this.context;
    const { width, height } = this;
    this.camera = {
      x: game.player.x * 0.35,
      y: game.player.y + 3.3,
      z: game.player.z - 7.5,
      pitch: 0.26,
      focal: Math.min(width, height) * 0.92,
    };
    this.#drawSky(ctx, width, height, elapsedTime);

    const visible = game.platforms
      .filter((platform) => Math.abs(platform.z - game.player.z) < 72)
      .sort((a, b) => b.z - a.z);
    for (const platform of visible) this.#drawPlatform(ctx, platform);
    for (const platform of visible) {
      if (platform.hazard) this.#drawHazard(ctx, platform, elapsedTime);
      if (!game.collected.has(platform.index)) this.#drawStar(ctx, platform, elapsedTime);
    }
    this.#drawAvatar(ctx, game.player, avatar, elapsedTime);
  }

  #project(x, y, z) {
    const camera = this.camera;
    const dx = x - camera.x;
    const dy = y - camera.y;
    const dz = z - camera.z;
    const depth = dz * Math.cos(camera.pitch) - dy * Math.sin(camera.pitch);
    if (depth <= 0.35) return null;
    const vertical = dy * Math.cos(camera.pitch) + dz * Math.sin(camera.pitch);
    return {
      x: this.width / 2 + camera.focal * dx / depth,
      y: this.height * 0.45 - camera.focal * vertical / depth,
      depth,
    };
  }

  #polygon(ctx, points, fill, stroke = fill) {
    const projected = points.map(([x, y, z]) => this.#project(x, y, z));
    if (projected.some((point) => point === null)) return;
    ctx.beginPath();
    ctx.moveTo(projected[0].x, projected[0].y);
    for (let index = 1; index < projected.length; index += 1) {
      ctx.lineTo(projected[index].x, projected[index].y);
    }
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }

  #drawSky(ctx, width, height, time) {
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, COLORS.skyTop);
    gradient.addColorStop(1, COLORS.skyBottom);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    ctx.globalAlpha = 0.66;
    ctx.fillStyle = "#f7fdff";
    for (let index = 0; index < 5; index += 1) {
      const x = ((index * 257 + time * (5 + index)) % (width + 180)) - 90;
      const y = 86 + (index % 3) * 54;
      this.#cloud(ctx, x, y, 0.65 + (index % 2) * 0.25);
    }
    ctx.globalAlpha = 1;
    ctx.fillStyle = COLORS.mountainFar;
    ctx.beginPath();
    ctx.moveTo(0, height * 0.62);
    for (let x = 0; x <= width + 80; x += 80) {
      const y = height * (0.46 + 0.08 * Math.sin(x * 0.012) + 0.03 * Math.sin(x * 0.027 + 1));
      ctx.lineTo(x, y);
    }
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = COLORS.mountainNear;
    ctx.beginPath();
    ctx.moveTo(0, height * 0.73);
    for (let x = 0; x <= width + 90; x += 90) {
      ctx.lineTo(x, height * (0.63 + 0.06 * Math.sin(x * 0.009 + 1.8)));
    }
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();
    ctx.fill();
  }

  #cloud(ctx, x, y, scale) {
    ctx.beginPath();
    ctx.ellipse(x, y, 34 * scale, 12 * scale, 0, 0, Math.PI * 2);
    ctx.ellipse(x - 16 * scale, y + 1, 15 * scale, 11 * scale, 0, 0, Math.PI * 2);
    ctx.ellipse(x + 15 * scale, y + 1, 17 * scale, 13 * scale, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  #drawPlatform(ctx, platform) {
    const halfWidth = COURSE.platformWidth / 2;
    const halfLength = COURSE.platformLength / 2;
    const x0 = platform.x - halfWidth;
    const x1 = platform.x + halfWidth;
    const z0 = platform.z - halfLength;
    const z1 = platform.z + halfLength;
    const base = -0.42;
    const top = platform.index % COURSE.checkpointInterval === COURSE.checkpointInterval - 1
      ? COLORS.checkpoint
      : platform.moving ? COLORS.moving : COLORS.platform;
    this.#polygon(ctx, [[x0, base, z1], [x1, base, z1], [x1, 0, z1], [x0, 0, z1]], "#287f82", "#4a999b");
    this.#polygon(ctx, [[x1, base, z0], [x1, base, z1], [x1, 0, z1], [x1, 0, z0]], "#349795", "#54aaa5");
    this.#polygon(ctx, [[x0, 0, z0], [x1, 0, z0], [x1, 0, z1], [x0, 0, z1]], top, "#f2fff8");

    if (platform.index % COURSE.checkpointInterval === COURSE.checkpointInterval - 1) {
      const beacon = this.#project(platform.x, 0.35, platform.z);
      if (beacon) {
        const size = clamp(40 / beacon.depth, 2, 10);
        ctx.fillStyle = "rgba(255, 255, 255, 0.75)";
        ctx.beginPath();
        ctx.arc(beacon.x, beacon.y, size, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  #drawHazard(ctx, platform, time) {
    const point = this.#project(platform.x, 0, platform.z);
    if (!point) return;
    const size = clamp(150 / point.depth, 3, 20);
    const pulse = 0.55 + Math.sin(time * 5 + platform.index) * 0.18;
    ctx.save();
    ctx.globalAlpha = pulse;
    ctx.shadowColor = "#ff5274";
    ctx.shadowBlur = size;
    ctx.fillStyle = "#e84865";
    ctx.beginPath();
    ctx.moveTo(point.x, point.y - size * 1.8);
    ctx.lineTo(point.x + size, point.y + size * 0.7);
    ctx.lineTo(point.x - size, point.y + size * 0.7);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  #drawStar(ctx, platform, time) {
    const x = platform.x + (platform.index % 2 === 0 ? -1.5 : 1.5);
    const point = this.#project(x, 1.15 + Math.sin(time * 3 + platform.index) * 0.12, platform.z);
    if (!point) return;
    const radius = clamp(105 / point.depth, 3, 13);
    ctx.save();
    ctx.translate(point.x, point.y);
    ctx.rotate(time * 0.8);
    ctx.shadowColor = "#ffe58a";
    ctx.shadowBlur = radius * 1.8;
    ctx.fillStyle = "#ffe18a";
    ctx.strokeStyle = "#fff6cf";
    ctx.lineWidth = Math.max(1, radius * 0.14);
    ctx.beginPath();
    for (let index = 0; index < 10; index += 1) {
      const angle = -Math.PI / 2 + index * Math.PI / 5;
      const length = index % 2 === 0 ? radius : radius * 0.48;
      const px = Math.cos(angle) * length;
      const py = Math.sin(angle) * length;
      if (index === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }

  #drawAvatar(ctx, player, avatar, time) {
    const feet = this.#project(player.x, player.y, player.z);
    const head = this.#project(player.x, player.y + 1.85, player.z);
    if (!feet || !head) return;
    const scale = clamp(350 / feet.depth, 0.38, 1.45);
    const height = (feet.y - head.y) * 1.03;
    const width = height * 0.64;
    const x = feet.x;
    const bob = player.grounded ? Math.sin(time * 10) * scale * 1.6 : 0;
    const top = feet.y - height + bob;
    const headRadius = width * 0.29;
    const headY = top + headRadius + 2 * scale;
    const torsoTop = headY + headRadius * 0.7;
    const torsoBottom = feet.y - height * 0.32;
    const stride = player.grounded ? Math.sin(time * 13) * scale * 3 : -scale * 2;

    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "rgba(29, 49, 72, 0.24)";
    ctx.lineWidth = width * 0.28;
    ctx.beginPath();
    ctx.ellipse(x, feet.y + 2, width * 0.46, width * 0.13, 0, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = "#263451";
    ctx.lineWidth = width * 0.2;
    ctx.beginPath();
    ctx.moveTo(x - width * 0.16, torsoBottom);
    ctx.lineTo(x - width * 0.18 + stride, feet.y - 2);
    ctx.moveTo(x + width * 0.16, torsoBottom);
    ctx.lineTo(x + width * 0.18 - stride, feet.y - 2);
    ctx.stroke();
    ctx.strokeStyle = "#f4f5ff";
    ctx.lineWidth = width * 0.23;
    ctx.beginPath();
    ctx.moveTo(x - width * 0.18 + stride, feet.y - 2);
    ctx.lineTo(x - width * 0.3 + stride, feet.y - 1);
    ctx.moveTo(x + width * 0.18 - stride, feet.y - 2);
    ctx.lineTo(x + width * 0.3 - stride, feet.y - 1);
    ctx.stroke();

    ctx.fillStyle = avatar.coat;
    this.#roundedRect(ctx, x - width * 0.34, torsoTop, width * 0.68, torsoBottom - torsoTop, width * 0.15);
    ctx.fill();
    ctx.fillStyle = avatar.trim;
    ctx.fillRect(x - width * 0.035, torsoTop + width * 0.08, width * 0.07, torsoBottom - torsoTop - width * 0.1);

    ctx.strokeStyle = avatar.coat;
    ctx.lineWidth = width * 0.16;
    ctx.beginPath();
    ctx.moveTo(x - width * 0.31, torsoTop + width * 0.07);
    ctx.lineTo(x - width * 0.48, torsoBottom - width * 0.04 + stride * 0.35);
    ctx.moveTo(x + width * 0.31, torsoTop + width * 0.07);
    ctx.lineTo(x + width * 0.48, torsoBottom - width * 0.04 - stride * 0.35);
    ctx.stroke();
    ctx.fillStyle = avatar.skin;
    ctx.beginPath();
    ctx.arc(x - width * 0.48, torsoBottom - width * 0.04 + stride * 0.35, width * 0.09, 0, Math.PI * 2);
    ctx.arc(x + width * 0.48, torsoBottom - width * 0.04 - stride * 0.35, width * 0.09, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = avatar.skin;
    ctx.beginPath();
    ctx.arc(x, headY, headRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = avatar.hair;
    ctx.beginPath();
    ctx.ellipse(x, headY - headRadius * 0.45, headRadius * 1.02, headRadius * 0.63, 0, Math.PI, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#25344e";
    ctx.beginPath();
    ctx.arc(x - headRadius * 0.32, headY + headRadius * 0.08, Math.max(1, headRadius * 0.075), 0, Math.PI * 2);
    ctx.arc(x + headRadius * 0.32, headY + headRadius * 0.08, Math.max(1, headRadius * 0.075), 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = avatar.trim;
    ctx.beginPath();
    ctx.arc(x, headY - headRadius * 1.02, headRadius * 0.32, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  #roundedRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.roundRect(x, y, width, height, radius);
  }
}
