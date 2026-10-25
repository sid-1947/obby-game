const SOUNDS = Object.freeze({
  jump: { frequency: 340, endFrequency: 640, duration: 0.12, type: "triangle", volume: 0.12 },
  coin: { frequency: 740, endFrequency: 1180, duration: 0.16, type: "sine", volume: 0.15 },
  checkpoint: { frequency: 420, endFrequency: 920, duration: 0.32, type: "sine", volume: 0.14 },
  hurt: { frequency: 210, endFrequency: 95, duration: 0.22, type: "sawtooth", volume: 0.1 },
  land: { frequency: 150, endFrequency: 90, duration: 0.07, type: "triangle", volume: 0.07 },
  win: { frequency: 480, endFrequency: 1080, duration: 0.5, type: "sine", volume: 0.14 },
  ui: { frequency: 520, endFrequency: 660, duration: 0.07, type: "sine", volume: 0.07 },
});

export class AudioEngine {
  constructor() {
    this.context = null;
    this.enabled = true;
  }

  async enable() {
    if (!("AudioContext" in window)) return false;
    if (!this.context) this.context = new AudioContext();
    if (this.context.state === "suspended") await this.context.resume();
    return true;
  }

  toggle() {
    this.enabled = !this.enabled;
    return this.enabled;
  }

  play(name) {
    const sound = SOUNDS[name];
    if (!sound) throw new RangeError(`Unknown sound: ${name}`);
    if (!this.enabled || !this.context || this.context.state !== "running") return;

    const oscillator = this.context.createOscillator();
    const gain = this.context.createGain();
    const now = this.context.currentTime;
    oscillator.type = sound.type;
    oscillator.frequency.setValueAtTime(sound.frequency, now);
    oscillator.frequency.exponentialRampToValueAtTime(sound.endFrequency, now + sound.duration);
    gain.gain.setValueAtTime(sound.volume, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + sound.duration);
    oscillator.connect(gain);
    gain.connect(this.context.destination);
    oscillator.start(now);
    oscillator.stop(now + sound.duration);
  }
}
