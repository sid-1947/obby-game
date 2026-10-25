import { AVATARS, COURSE } from "./config.js";
import { AudioEngine } from "./audio.js";
import { Game } from "./game.js";
import { Renderer } from "./renderer.js";

const element = (id) => {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Required page element not found: #${id}`);
  return node;
};

const canvas = element("game-canvas");
const renderer = new Renderer(canvas);
const audio = new AudioEngine();
const toast = element("toast");
const overlayIds = ["start-overlay", "pause-overlay", "result-overlay"];
let selectedAvatar = AVATARS[0];
let unlockedAvatars = new Set([AVATARS[0].id]);
let lastFrame = performance.now();
let elapsed = 0;
let toastTimeout = 0;
let avatarPickerMode = false;

const game = new Game((type, detail) => {
  if (type === "pause") showOverlay("pause-overlay");
  if (type === "resume") hideOverlays();
  if (type === "jump" || type === "coin" || type === "checkpoint" || type === "hurt") audio.play(type);
  if (type === "won") audio.play("win");
  if (type === "coin") updateHud();
  if (type === "checkpoint") notify("Checkpoint reached!");
  if (type === "respawn") notify(detail);
  if (type === "hurt") {
    updateHud();
    if (game.health > 0) notify("Ouch! Back to the checkpoint.");
  }
  if (type === "won") finishRun(true);
  if (type === "lost") finishRun(false);
});

function showOverlay(id) {
  for (const overlayId of overlayIds) element(overlayId).classList.toggle("hidden", overlayId !== id);
}

function hideOverlays() {
  for (const id of overlayIds) element(id).classList.add("hidden");
}

function notify(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(toastTimeout);
  toastTimeout = window.setTimeout(() => toast.classList.remove("visible"), 1700);
}

function updateHud() {
  const platformNumber = Math.min(COURSE.platformCount, game.maxReached + 1);
  element("progress-value").innerHTML = `${platformNumber} <span>/ ${COURSE.platformCount}</span>`;
  element("progress-bar").style.width = `${platformNumber / COURSE.platformCount * 100}%`;
  element("coin-value").textContent = String(game.coins);
  element("health-value").textContent = `${"♥ ".repeat(game.health)}${"♡ ".repeat(COURSE.maxHealth - game.health)}`.trim();
  element("health-value").setAttribute("aria-label", `${game.health} of ${COURSE.maxHealth} hearts remaining`);
  element("pause-button").disabled = game.state !== "running" && game.state !== "paused";
}

function renderAvatarOptions() {
  const container = element("skin-options");
  container.replaceChildren();
  for (const avatar of AVATARS) {
    const button = document.createElement("button");
    const unlocked = unlockedAvatars.has(avatar.id);
    button.type = "button";
    button.className = `skin-option${unlocked ? "" : " locked"}`;
    button.style.backgroundColor = avatar.coat;
    button.textContent = avatar.mark;
    button.title = unlocked ? `${avatar.name} avatar` : `${avatar.name} avatar — ${avatar.price} stars`;
    button.setAttribute("aria-label", button.title);
    button.setAttribute("aria-pressed", String(selectedAvatar.id === avatar.id));
    button.addEventListener("click", () => {
      if (!unlockedAvatars.has(avatar.id)) {
        if (game.coins < avatar.price) {
          notify(`Collect ${avatar.price - game.coins} more stars to unlock ${avatar.name}.`);
          return;
        }
        game.coins -= avatar.price;
        unlockedAvatars.add(avatar.id);
        notify(`${avatar.name} avatar unlocked!`);
        updateHud();
      }
      selectedAvatar = avatar;
      audio.play("ui");
      renderAvatarOptions();
      updateAvatarChip();
    });
    container.append(button);
  }
}

function updateAvatarChip() {
  const chip = element("avatar-chip");
  chip.textContent = selectedAvatar.mark;
  chip.style.backgroundColor = selectedAvatar.coat;
}

async function beginRun() {
  const soundAvailable = await audio.enable();
  if (!soundAvailable) {
    audio.enabled = false;
    element("sound-toggle").disabled = true;
    element("sound-toggle").setAttribute("aria-pressed", "false");
    element("sound-toggle").setAttribute("aria-label", "Sound unavailable");
    element("sound-icon").textContent = "♪";
    element("sound-label").textContent = "Sound unavailable";
  }
  game.reset();
  game.start();
  elapsed = 0;
  hideOverlays();
  element("pause-button").disabled = false;
  canvas.focus({ preventScroll: true });
  updateHud();
  audio.play("ui");
}

function finishRun(won) {
  showOverlay("result-overlay");
  element("result-eyebrow").textContent = won ? "COURSE COMPLETE" : "RUN OVER";
  element("result-title").textContent = won ? "The sky is yours." : "Every great climb has a reset.";
  element("result-copy").textContent = won
    ? `You reached the skyline and collected ${game.coins} stars.`
    : `You collected ${game.coins} stars. Pick an avatar and give it another go.`;
  element("pause-button").disabled = true;
  updateHud();
}

function frame(now) {
  const delta = Math.min((now - lastFrame) / 1000, 0.05);
  lastFrame = now;
  elapsed += delta;
  game.update(delta, elapsed);
  renderer.draw(game, selectedAvatar, elapsed);
  if (game.state === "running") updateHud();
  window.requestAnimationFrame(frame);
}

element("start-button").addEventListener("click", () => {
  if (!avatarPickerMode) {
    void beginRun();
    return;
  }
  avatarPickerMode = false;
  element("start-title").innerHTML = "Make it to the <span>skyline.</span>";
  element("start-button").innerHTML = 'Start your run <span aria-hidden="true">→</span>';
  game.resume();
  hideOverlays();
});
element("resume-button").addEventListener("click", () => {
  game.resume();
  hideOverlays();
  canvas.focus({ preventScroll: true });
});
element("restart-button").addEventListener("click", beginRun);
element("play-again-button").addEventListener("click", beginRun);
element("pause-button").addEventListener("click", () => game.togglePause());
element("avatar-button").addEventListener("click", () => {
  avatarPickerMode = game.state === "running" || game.state === "paused";
  if (game.state === "running") game.pause();
  if (avatarPickerMode) {
    element("start-title").textContent = "Choose your look.";
    element("start-button").innerHTML = 'Save avatar & resume <span aria-hidden="true">→</span>';
  }
  showOverlay("start-overlay");
});
element("sound-toggle").addEventListener("click", () => {
  const enabled = audio.toggle();
  element("sound-toggle").setAttribute("aria-pressed", String(enabled));
  element("sound-toggle").setAttribute("aria-label", `Turn sound ${enabled ? "off" : "on"}`);
  element("sound-icon").textContent = enabled ? "♫" : "♪";
  element("sound-label").textContent = enabled ? "Sound on" : "Sound off";
  if (enabled) audio.enable();
});

for (const button of document.querySelectorAll("[data-touch-key]")) {
  const key = button.dataset.touchKey;
  button.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    game.keys.add(key);
    button.setPointerCapture(event.pointerId);
  });
  const release = (event) => {
    event.preventDefault();
    game.keys.delete(key);
  };
  button.addEventListener("pointerup", release);
  button.addEventListener("pointercancel", release);
  button.addEventListener("lostpointercapture", release);
}

element("touch-jump").addEventListener("pointerdown", (event) => {
  event.preventDefault();
  game.jump();
});

window.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  if (key === "escape") {
    event.preventDefault();
    game.togglePause();
    return;
  }
  if (key === " " || key.startsWith("arrow")) event.preventDefault();
  if (key === " " && !event.repeat) game.jump();
  game.keys.add(key);
});
window.addEventListener("keyup", (event) => game.keys.delete(event.key.toLowerCase()));
window.addEventListener("blur", () => {
  game.keys.clear();
  if (game.state === "running") game.pause();
});

renderAvatarOptions();
updateAvatarChip();
updateHud();
window.requestAnimationFrame(frame);
