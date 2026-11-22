#!/usr/bin/env python3
"""Reels dinamicos Puente · Serie 3 (22/11/2026). 1080x1920, 30 fps. Negro y dorado, Cinzel + Montserrat.
Cada escena dura lo que dura su frase de Andrea (voz3/<id>.mp3, acelerada 8 %).
Escenas: hook | big | text | point | cta. Marca de agua (monograma + @usuario) que cambia de esquina cada 7 s.
Musica: tema Puente armado a la medida (pulso + cierre con el motivo), -14 LUFS, baja bajo la voz.
Uso: python3 reel_dinamico.py <id> salida.mp4 [--stills]"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy.io import wavfile
import historia_dinamica as hd
from historia_dinamica import (W, H, FPS, GOLD, GREY, WHITE, sans, serif, ease, back, put, layout, shift,
                               draw_words, pill, big_answer, bubble, Background, gold_grad)
from firma import firma, monograma
from mezcla_voz import load, tempo, SR
from reels_serie3 import REELS

HERE = os.path.dirname(os.path.abspath(__file__))
GAP, TAIL = .38, 2.6


def timeline(spec):
    t = .35; out = []
    for sc in spec['scenes']:
        x = tempo(load(f'{HERE}/voz3/{sc["v"]}.mp3'), 1.08)
        d = len(x) / SR
        out.append((t, t + d, x)); t += d + GAP
    return out, out[-1][1] + TAIL


def watermark():
    m = monograma(70)
    tx = hd.word_img('@puentetributarioyaduanero', sans(24, 600), False, base=WHITE)[0]
    im = Image.new('RGBA', (m.width + 12 + tx.width, max(m.height, tx.height)), (0, 0, 0, 0))
    im.alpha_composite(m, (0, (im.height - m.height) // 2)); im.alpha_composite(tx, (m.width + 2, (im.height - tx.height) // 2))
    return hd.alpha_mul(im, .55)


def build(spec):
    L = []
    for sc in spec['scenes']:
        k = sc['k']; d = {}
        if k == 'hook':
            d['pill'] = pill(sc['label'])
            d['w'], d['h'] = layout(sc['t'], sans(sc.get('size', 86), 800), 940, int(sc.get('size', 86) * 1.18), 0)
        elif k == 'big':
            d['big'] = big_answer(sc['big'], sc.get('bs', 200))
            d['w'], d['h'] = layout(sc['t'], sans(56, 700), 920, 72, 0)
            if sc.get('n'): d['n'], d['nh'] = layout(sc['n'], sans(36, 500), 880, 46, 0, base=GREY)
        elif k == 'text':
            d['w'], d['h'] = layout(sc['t'], sans(sc.get('size', 68), 800), 940, int(sc.get('size', 68) * 1.22), 0)
            if sc.get('n'): d['n'], d['nh'] = layout(sc['n'], sans(36, 500), 880, 46, 0, base=GREY)
        elif k == 'point':
            c = Image.new('RGBA', (230, 230), (0, 0, 0, 0)); dr = ImageDraw.Draw(c)
            dr.ellipse((10, 10, 220, 220), outline=(*GOLD, 255), width=8)
            m = Image.new('L', c.size, 0); dm = ImageDraw.Draw(m); f = serif(130, 900)
            tw = dm.textlength(sc['num'], font=f); dm.text((115 - tw / 2, 28), sc['num'], font=f, fill=255)
            c.alpha_composite(gold_grad(m)); d['num'] = c
            d['w'], d['h'] = layout(sc['t'], sans(62, 800), 920, 78, 0)
        elif k == 'cta':
            d['bub'] = bubble()
            d['pre'], _ = layout('Comentá', sans(72, 800), 900, 90, 0)
            kw = sc['kw']; d['kw'] = big_answer(kw, 210 if len(kw) <= 6 else int(210 * 5.8 / len(kw)))
            d['w'], d['h'] = layout(sc['t'], sans(48, 600), 900, 62, 0, base=GREY)
            d['wa'], _ = layout('WhatsApp *381 276-8888*', sans(44, 700), 900, 56, 0)
            d['firma'] = firma(1000)
        L.append(d)
    return L


def render_frame(spec, L, TL, total, bgc, wm, t):
    idx = max([i for i, (a, b, _) in enumerate(TL) if t >= a - .05] or [0])
    t0 = TL[idx][0]
    boost = max(0, 1 - (t - t0) / .5)
    fr = bgc.frame(t, boost * .7)
    # escena saliente (barrido a la izquierda)
    if idx > 0 and t - t0 < .3:
        draw_scene(fr, spec['scenes'][idx - 1], L[idx - 1], TL[idx - 1][0], t, out=(t - t0) / .3)
    draw_scene(fr, spec['scenes'][idx], L[idx], t0, t)
    # barra de progreso
    d = ImageDraw.Draw(fr)
    d.rectangle((0, 0, int(W * min(1, t / total)), 7), fill=(*GOLD, 230))
    # marca de agua: cambia de esquina cada 7 s
    k = int(t // 7) % 4
    pos = [(40, 120), (W - wm.width - 40, 120), (W - wm.width - 40, H - 260), (40, H - 260)][k]
    if spec['scenes'][idx]['k'] != 'cta': fr.alpha_composite(wm, pos)
    # destello al cambiar de escena
    if t - t0 < .22 and idx > 0:
        a = 1 - (t - t0) / .22
        fr.alpha_composite(Image.new('RGBA', (W, H), (255, 236, 190, int(110 * a * a))))
    zs = 1 + .03 * boost
    if zs > 1.001:
        z = fr.resize((int(W * zs), int(H * zs)), Image.BILINEAR)
        ox, oy = (z.width - W) // 2, (z.height - H) // 2; fr = z.crop((ox, oy, ox + W, oy + H))
    if t < .3: fr.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - t / .3)))))
    if t > total - .5: fr.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * ease((t - total + .5) / .5)))))
    return fr.convert('RGB')


def draw_scene(fr, sc, d, t0, t, out=0.):
    k = sc['k']; a_out = 1 - out
    if out:
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); tgt = layer
    else:
        tgt = fr
    if k == 'hook':
        put(tgt, d['pill'], W / 2, 700, ease((t - t0) / .3))
        draw_words(tgt, shift(d['w'], 1000), t, t0 + .08, .06)
    elif k == 'big':
        u = (t - t0) / .45
        put(tgt, d['big'], W / 2, 780, ease(u * 1.6), 1.6 - .6 * back(u, 1.4) if u < 1 else 1)
        top = 780 + d['big'].height / 2 + 40
        draw_words(tgt, shift(d['w'], top + d['h'] / 2), t, t0 + .35, .05)
        if 'n' in d: draw_words(tgt, shift(d['n'], top + d['h'] + 50 + d['nh'] / 2), t, t0 + 1.2, .03)
    elif k == 'text':
        draw_words(tgt, shift(d['w'], 960), t, t0 + .05, .06)
        if 'n' in d: draw_words(tgt, shift(d['n'], 960 + d['h'] / 2 + 70 + d['nh'] / 2), t, t0 + 1.0, .03)
    elif k == 'point':
        u = (t - t0) / .4
        put(tgt, d['num'], W / 2, 720, ease(u * 1.5), 1.5 - .5 * back(u, 1.6) if u < 1 else 1)
        draw_words(tgt, shift(d['w'], 1000 + d['h'] / 2 - 40), t, t0 + .25, .05)
    elif k == 'cta':
        u = t - t0
        put(tgt, d['bub'], W / 2, 470, ease(u / .35), .6 + .4 * back(u / .4))
        draw_words(tgt, shift(d['pre'], 670), t, t0 + .1, .06)
        uk = (u - .35) / .45
        if uk > 0:
            put(tgt, d['kw'], W / 2, 850, ease(uk * 1.5), (1.6 - .6 * back(uk, 1.4) if uk < 1 else 1) * (1 + .025 * math.sin(max(0, u - 1) * 5)))
        draw_words(tgt, shift(d['w'], 1040), t, t0 + .9, .04)
        draw_words(tgt, shift(d['wa'], 1170), t, t0 + 1.4, .05)
        put(tgt, d['firma'], W / 2, 1480 + 20 * (1 - ease((u - 1.8) / .5)), ease((u - 1.8) / .5))
    if out:
        fr.alpha_composite(hd.alpha_mul(layer, a_out), (int(-260 * ease(out)), 0))


def music(total, path):
    import puente_theme as pt
    beats = int(math.ceil(total / pt.BEAT)) + 1
    body = []; cyc = [pt.CONT, pt.ADUA, lambda b=8: pt.S('A', b, bright=.5, arp=.72, kick=.5, shk=.06, snap=.08, bass=.48, rise=.05)]
    n = 0
    while sum(s['beats'] for s in body) + 8 < beats:
        rem = beats - 8 - sum(s['beats'] for s in body)
        body.append(cyc[n % 3](min(8, rem))); n += 1
    body.append(pt.CLOS(8))
    mix, dur = pt.render(body)
    x = pt.finish(mix, min(dur, total), .8)
    pt.write(path, x)


def main():
    rid, out = sys.argv[1], sys.argv[2]
    spec = REELS[rid]
    TL, total = timeline(spec)
    L = build(spec); bgc = Background(spec['tema']); wm = watermark()
    if '--stills' in sys.argv:
        os.makedirs(out, exist_ok=True)
        for i, (a, b, _) in enumerate(TL):
            render_frame(spec, L, TL, total, bgc, wm, min(b, a + 2.2)).save(f'{out}/{rid}_{i}.png')
        print(rid, round(total, 2)); return
    # audio
    voice = np.zeros(int((total + .5) * SR), np.float32)
    for a, b, x in TL:
        i = int(a * SR); voice[i:i + len(x)] += x[:len(voice) - i]
    wavfile.write(f'/tmp/{rid}_voz.wav', SR, voice)
    music(total, f'/tmp/{rid}_mus.wav')
    tmp = f'/tmp/{rid}_v.mp4'
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    for i in range(int(total * FPS)):
        p.stdin.write(render_frame(spec, L, TL, total, bgc, wm, i / FPS).tobytes())
    p.stdin.close(); p.wait()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-i', f'/tmp/{rid}_mus.wav', '-i', f'/tmp/{rid}_voz.wav', '-filter_complex',
                    '[2:a]aformat=channel_layouts=stereo,volume=1.6,asplit=2[v1][v2];'
                    '[1:a]volume=0.5[m];[m][v1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[md];'
                    '[md][v2]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]',
                    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-shortest',
                    '-movflags', '+faststart', out], check=True)
    print(rid, round(total, 2))


if __name__ == '__main__':
    main()
