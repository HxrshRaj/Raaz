/** Procedural audio (no sample files): looping rain, a low drone, rare distant thunder, and UI sounds.
 *  Everything is synthesised with WebAudio, so there are no licensing concerns and nothing to download. */

type Ctx = AudioContext;

class Soundscape {
  private ctx: Ctx | null = null;
  private master: GainNode | null = null;
  private rainGain: GainNode | null = null;
  private running = false;
  private thunderTimer: number | undefined;
  volume = 0.5;
  muted = false;
  sfx = true;

  private ensure(): Ctx | null {
    if (this.ctx) return this.ctx;
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return null;
    this.ctx = new AC();
    this.master = this.ctx.createGain();
    this.master.gain.value = this.muted ? 0 : this.volume;
    this.master.connect(this.ctx.destination);
    return this.ctx;
  }

  private noiseBuffer(ctx: Ctx, seconds = 4): AudioBuffer {
    const buf = ctx.createBuffer(1, ctx.sampleRate * seconds, ctx.sampleRate);
    const d = buf.getChannelData(0);
    let b0 = 0, b1 = 0, b2 = 0;
    for (let i = 0; i < d.length; i++) {
      const w = Math.random() * 2 - 1;
      b0 = 0.99765 * b0 + w * 0.099046; b1 = 0.963 * b1 + w * 0.2965164; b2 = 0.57 * b2 + w * 1.0526913;
      d[i] = (b0 + b1 + b2 + w * 0.1848) * 0.2;
    }
    return buf;
  }

  start() {
    const ctx = this.ensure();
    if (!ctx || !this.master || this.running) return;
    void ctx.resume();
    this.running = true;
    const src = ctx.createBufferSource();
    src.buffer = this.noiseBuffer(ctx);
    src.loop = true;
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass"; lp.frequency.value = 3800;
    const hp = ctx.createBiquadFilter();
    hp.type = "highpass"; hp.frequency.value = 400;
    this.rainGain = ctx.createGain();
    this.rainGain.gain.value = 0.28;
    src.connect(hp).connect(lp).connect(this.rainGain).connect(this.master);
    src.start();
    // a faint low drone, like a distant locomotive
    const g = ctx.createGain(); g.gain.value = 0.035;
    for (const f of [55, 55.4, 82.5]) {
      const o = ctx.createOscillator(); o.type = "sine"; o.frequency.value = f; o.connect(g); o.start();
    }
    g.connect(this.master);
    this.scheduleThunder();
  }

  private scheduleThunder() {
    window.clearTimeout(this.thunderTimer);
    this.thunderTimer = window.setTimeout(() => {
      if (this.running && !this.muted) this.thunder();
      this.scheduleThunder();
    }, 25000 + Math.random() * 40000);
  }

  private thunder() {
    const ctx = this.ctx; if (!ctx || !this.master) return;
    const s = ctx.createBufferSource(); s.buffer = this.noiseBuffer(ctx, 3);
    const lp = ctx.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 180;
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.9, ctx.currentTime + 0.4);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 3);
    s.connect(lp).connect(g).connect(this.master); s.start();
  }

  stop() {
    this.running = false;
    window.clearTimeout(this.thunderTimer);
    void this.ctx?.close();
    this.ctx = null; this.master = null; this.rainGain = null;
  }

  apply() {
    if (this.master && this.ctx) this.master.gain.setTargetAtTime(this.muted ? 0 : this.volume, this.ctx.currentTime, 0.05);
  }

  private blip(freq: number, dur: number, type: OscillatorType = "triangle", vol = 0.12) {
    if (!this.sfx || this.muted) return;
    const ctx = this.ensure(); if (!ctx || !this.master) return;
    void ctx.resume();
    const o = ctx.createOscillator(); const g = ctx.createGain();
    o.type = type; o.frequency.value = freq;
    g.gain.setValueAtTime(vol, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
    o.connect(g).connect(this.master); o.start(); o.stop(ctx.currentTime + dur);
  }

  click() { this.blip(520, 0.07, "square", 0.05); }
  discover() { this.blip(392, 0.16); setTimeout(() => this.blip(587, 0.22), 110); }
  paper() { this.blip(180, 0.09, "sawtooth", 0.04); }
  alert() { this.blip(220, 0.25, "sawtooth", 0.08); setTimeout(() => this.blip(165, 0.35, "sawtooth", 0.08), 160); }
}

export const sound = new Soundscape();
