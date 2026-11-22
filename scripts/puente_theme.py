#!/usr/bin/env python3
"""Tema Puente: identidad sonora original. Todo se sintetiza aqui, sin samples.
93.75 BPM: 50 tiempos = 32.00 s exactos; los cortes del reel caen en la grilla."""
import sys, os
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR = 44100
BEAT = 0.64
rng = np.random.default_rng(1921)


def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def lp(x, fc, o=2): return sosfilt(butter(o, fc, 'low', fs=SR, output='sos'), x)
def hp(x, fc, o=2): return sosfilt(butter(o, fc, 'high', fs=SR, output='sos'), x)
def bp(x, a, b, o=2): return sosfilt(butter(o, [a, b], 'band', fs=SR, output='sos'), x)


_cache = {}


def epiano(m, dur, vel):
    key = ('ep', m, round(dur, 2), round(vel, 2))
    if key in _cache: return _cache[key]
    rel = 1.6
    t = np.arange(int((dur + rel) * SR)) / SR
    f = hz(m)
    out = []
    for det in (-1.3, 1.3):
        ff = f * 2 ** (det / 1200)
        I = (0.8 + 1.5 * vel) * np.exp(-t * 6.5) + 0.2
        x = np.sin(2 * np.pi * ff * t + I * np.sin(2 * np.pi * ff * t))
        x += 0.05 * vel * np.sin(2 * np.pi * min(ff * 7, 8000) * t) * np.exp(-t * 24)
        out.append(x)
    x = np.stack(out, 1)
    env = np.exp(-t * (0.8 + f / 1100)) * np.minimum(t / 0.004, 1)
    gate = np.clip((dur + 0.5 - t) / 0.5, 0, 1) ** 2
    x *= (env * gate * vel)[:, None]
    x = np.stack([lp(x[:, 0], 7500), lp(x[:, 1], 7500)], 1)
    _cache[key] = x
    return x


def bell(m, vel):
    t = np.arange(int(3.5 * SR)) / SR
    f = hz(m)
    x = np.sin(2 * np.pi * f * t + 0.8 * np.exp(-t * 4) * np.sin(2 * np.pi * f * 3.0 * t))
    x += 0.22 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 2.2)
    x *= np.exp(-t * 1.5) * np.minimum(t / 0.003, 1) * vel
    return np.stack([x * 0.92, np.roll(x, 40)], 1)


def pad(notes, dur, level, bright=0.42):
    a, r = min(1.1, dur * 0.45), 1.8
    t = np.arange(int((dur + r) * SR)) / SR
    env = np.minimum(t / a, 1) ** 1.5 * np.clip((dur + r - t) / r, 0, 1) ** 1.6
    L, R = np.zeros(len(t)), np.zeros(len(t))
    for idx, m in enumerate(notes):
        f = hz(m)
        for n in range(1, 8):
            amp = bright ** (n - 1) / n
            if f * n > 7000: continue
            for det, side in ((-3.5, 0.72), (3.5, 0.28)):
                ph = rng.uniform(0, 2 * np.pi)
                lfo = 1 + 0.12 * np.sin(2 * np.pi * (0.13 + 0.03 * n) * t + ph)
                s = amp * lfo * np.sin(2 * np.pi * f * n * 2 ** (det / 1200) * t + ph)
                L += s * side
                R += s * (1 - side)
    x = np.stack([L, R], 1) * env[:, None] * level / max(1, len(notes))
    return x


def bass(m, dur, vel):
    t = np.arange(int((dur + 0.35) * SR)) / SR
    f = hz(m)
    x = np.sin(2 * np.pi * f * t) + 0.42 * np.sin(4 * np.pi * f * t) + 0.16 * np.sin(6 * np.pi * f * t)
    env = np.minimum(t / 0.018, 1) * np.exp(-t * 0.6) * np.clip((dur + 0.35 - t) / 0.35, 0, 1)
    x = np.tanh(1.5 * x * env) * vel
    return np.stack([x, x], 1)


def kick(vel):
    t = np.arange(int(0.42 * SR)) / SR
    f = 46 + 42 * np.exp(-t * 22)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8.5) * np.minimum(t / 0.002, 1) * vel
    x = np.tanh(1.5 * x)
    return np.stack([x, x], 1)


def shaker(vel):
    t = np.arange(int(0.09 * SR)) / SR
    n = bp(rng.standard_normal(len(t)), 5500, 12000) * np.exp(-t * 55) * vel
    return np.stack([n, np.roll(n, 25)], 1)


def snap(vel):
    t = np.arange(int(0.2 * SR)) / SR
    n = bp(rng.standard_normal(len(t)), 1300, 5200) * np.exp(-t * 34)
    n += 0.4 * np.sin(2 * np.pi * 210 * t) * np.exp(-t * 45)
    return np.stack([n, n], 1) * vel


def tick(vel):
    t = np.arange(int(0.05 * SR)) / SR
    x = (np.sin(2 * np.pi * 2300 * t) + 0.5 * bp(rng.standard_normal(len(t)), 2500, 7000)) * np.exp(-t * 170) * vel
    return np.stack([x, x], 1)


def riser(dur, vel):
    n = int(dur * SR)
    w = rng.standard_normal((n, 2))
    r = np.linspace(0, 1, n)
    dark = np.stack([bp(w[:, c], 300, 1800) for c in range(2)], 1)
    br = np.stack([bp(w[:, c], 1800, 9000) for c in range(2)], 1)
    return (dark * ((1 - r) * r ** 2 * 3)[:, None] + br * (r ** 3)[:, None]) * vel


MOTIF = [(0, 62), (.5, 69), (1, 76), (1.5, 69), (2, 62)]
ARCH = {'D': [62, 69, 76, 69], 'Bm': [59, 66, 73, 66], 'G': [55, 62, 69, 62],
        'A': [57, 64, 71, 64], 'F#': [54, 62, 69, 62]}
PAD = {'D5': [50, 57, 62, 69], 'D': [50, 57, 64, 66, 69], 'Bm': [47, 54, 57, 62, 66],
       'G': [43, 50, 54, 59, 66], 'Dfs': [42, 50, 57, 62, 66], 'Asus': [45, 52, 57, 62, 64],
       'A': [45, 52, 57, 61, 64]}
BASS = {'D5': 38, 'D': 38, 'Bm': 35, 'G': 31, 'Dfs': 30, 'Asus': 33, 'A': 33}
ARPKEY = {'D5': 'D', 'D': 'D', 'Bm': 'Bm', 'G': 'G', 'Dfs': 'F#', 'Asus': 'A', 'A': 'A'}


def S(chord, beats, **k):
    d = dict(chord=chord, beats=beats, pad=.6, bright=.42, arp=0, kick=0, shk=0, snap=0, tick=0,
             bass=0, motif=0, bloom=0, lead=None, rise=0)
    d.update(k)
    return d


HOOK = lambda b=6: S('D5', b, pad=.48, bright=.36, tick=.1, bass=.28, rise=.07)
LOGO = lambda b=6: S('D', b, pad=.72, motif=.8, bloom=1, bass=.34, rise=.03)
CONT = lambda b=8: S('Bm', b, arp=.68, kick=.42, shk=.045, bass=.44, rise=.03)
ADUA = lambda b=8: S('G', b, bright=.5, arp=.72, kick=.5, shk=.06, snap=.08, bass=.48, rise=.04)
CLOS = lambda b=8: S('D', b, pad=.8, bright=.46, motif=.85, bloom=1.15, bass=.34)

VERSIONS = {
    # historias dinamicas: 32 tiempos = 20,48 s (arranca con pulso, cierra con el motivo)
    'v20': [CONT(), ADUA(), S('A', 8, bright=.5, arp=.72, kick=.5, shk=.06, snap=.08, bass=.48, rise=.06), CLOS(8)],
    # 40 tiempos = 25,6 s: un compas de pulso mas antes de la cuenta regresiva
    'v25': [S('D', 8, pad=.6, arp=.6, kick=.38, shk=.04, bass=.4), CONT(), ADUA(), S('A', 8, bright=.5, arp=.72, kick=.5, shk=.06, snap=.08, bass=.48, rise=.06), CLOS(8)],
}


def make_ir():
    n = int(3.0 * SR)
    t = np.arange(n) / SR
    out = []
    for _ in range(2):
        w = rng.standard_normal(n)
        ir = lp(w, 6500) * np.exp(-t * 4.6) * 0.45 + lp(w, 1800) * np.exp(-t * 2.5)
        pre = int(.022 * SR)
        ir = np.concatenate([np.zeros(pre), ir])[:n]
        out.append(ir)
    ir = np.stack(out, 1)
    return ir / np.sqrt((ir ** 2).sum(0).mean())


IR = make_ir()


def render(sections, humanize=True):
    beats = sum(s['beats'] for s in sections)
    dur = beats * BEAT
    n = int((dur + 6) * SR)
    dry, wet, pads = np.zeros((n, 2)), np.zeros((n, 2)), np.zeros((n, 2))
    kicks = []

    def add(bus, x, at, pan=0.0):
        i = int(max(at, 0) * SR)
        if i >= n: return
        x = x[:n - i]
        l, r = np.cos((pan + 1) * np.pi / 4) * 1.414, np.sin((pan + 1) * np.pi / 4) * 1.414
        bus[i:i + len(x), 0] += x[:, 0] * l
        bus[i:i + len(x), 1] += x[:, 1] * r

    def human(): return rng.normal(0, 0.005) if humanize else 0.0

    b0 = 0.0
    for s in sections:
        t0, B = b0 * BEAT, s['beats']
        c = s['chord']
        sb = B * BEAT
        add(pads, pad(PAD[c], sb, s['pad'], s['bright']), t0)
        if s['bass']:
            add(dry, bass(BASS[c], sb * .96, s['bass']), t0)
        if s['arp']:
            nt = ARCH[ARPKEY[c]]
            for i in range(int(B * 2)):
                m = nt[i % 4]
                v = s['arp'] * (1.0 if i % 4 == 0 else .72 if i % 2 == 0 else .58) * (rng.uniform(.92, 1.06) if humanize else 1.0)
                x = epiano(m, BEAT * 1.1, v)
                at = t0 + i * BEAT / 2 + human()
                add(dry, x * .85, at, -.18 + .36 * ((i % 4) / 3))
                add(wet, x * .28, at)
        if s['kick']:
            for b in np.arange(0, B, 2):
                add(dry, kick(s['kick']), t0 + b * BEAT); kicks.append(t0 + b * BEAT)
                if (b + 1.5) < B and int(b) % 4 == 2:
                    add(dry, kick(s['kick'] * .6), t0 + (b + 1.5) * BEAT); kicks.append(t0 + (b + 1.5) * BEAT)
        if s['shk']:
            for i in range(int(B * 2)):
                add(dry, shaker(s['shk'] * (1 if i % 2 else .55)), t0 + i * BEAT / 2 + human(), .25)
        if s['snap']:
            for b in np.arange(1, B, 2):
                x = snap(s['snap'])
                add(dry, x, t0 + b * BEAT); add(wet, x * .9, t0 + b * BEAT)
        if s['tick']:
            for b in range(int(B)):
                x = tick(s['tick'])
                add(dry, x, t0 + b * BEAT); add(wet, x * 1.3, t0 + b * BEAT)
        if s['motif']:
            for off, m in MOTIF:
                v = s['motif'] * (1.0 if m == 76 else .78)
                x = epiano(m, BEAT * 2.4, v) + epiano(m + 12, BEAT * 2.4, v * .17)
                at = t0 + off * BEAT + human() * .4
                add(dry, x, at); add(wet, x * .55, at)
        if s['bloom']:
            at = t0 + 2 * BEAT
            for m, v in ((38, .3), (50, .36), (57, .3), (66, .3), (69, .28), (76, .24)):
                x = epiano(m, BEAT * 3, v * s['bloom'])
                add(dry, x, at); add(wet, x * .5, at)
            b = bell(88, .1 * s['bloom']) + bell(93, .05 * s['bloom'])
            add(dry, b * .6, at, .15); add(wet, b * 1.5, at)
            add(dry, kick(.38 * s['bloom']), t0)
        if s['lead']:
            for off, m, d in s['lead']:
                x = epiano(m, d * BEAT, .46) + epiano(m + 12, d * BEAT, .07)
                add(dry, x, t0 + off * BEAT); add(wet, x * .75, t0 + off * BEAT)
        if s['rise']:
            r = min(sb, 3 * BEAT)
            add(dry, riser(r, s['rise']), t0 + sb - r)
            add(wet, riser(r, s['rise'] * .8), t0 + sb - r)
        b0 += B

    g = np.ones(n)
    tt = np.arange(n) / SR
    for k in kicks:
        i = int(k * SR); e = min(n, i + int(.5 * SR))
        g[i:e] = np.minimum(g[i:e], 1 - .17 * np.exp(-(tt[i:e] - k) / .16))
    pads *= g[:, None]
    wet = wet + pads * .3
    rev = np.stack([fftconvolve(wet[:, c], IR[:, c])[:n] for c in range(2)], 1) * .5
    mix = dry * .8 + pads * .78 + rev
    mix = np.stack([hp(mix[:, c], 30, 2) + .4 * hp(mix[:, c], 2600, 1) for c in range(2)], 1)
    pk = np.abs(mix).max()
    mix = np.tanh(mix / pk * 1.1) / np.tanh(1.1)
    return mix, dur


def finish(mix, dur, fade):
    x = mix[:int(round(dur * SR))].copy()
    if fade:
        k = int(fade * SR)
        x[-k:] *= (np.cos(np.linspace(0, np.pi / 2, k)) ** 2)[:, None]
    x[:64] *= np.linspace(0, 1, 64)[:, None]
    return x


def write(path, x):
    wavfile.write(path, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))


if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for name, sec in VERSIONS.items():
        mix, dur = render(sec)
        write(f'{out}/{name}.wav', finish(mix, dur, 1.0))
        print(name, round(dur, 3))
