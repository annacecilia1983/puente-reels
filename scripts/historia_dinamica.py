#!/usr/bin/env python3
"""Historias dinamicas Puente (formato nuevo, 22/11/2026). 1080x1920, 30 fps, 20,48 s, tema Puente v20.
Negro y dorado, Cinzel + Montserrat, texto *entre asteriscos* en dorado.
Estructura en la grilla del tema (BEAT 0,64 s):
  0-10,24 s  pregunta palabra por palabra + opciones + cuenta regresiva 3-2-1
  10,24 s    revelacion: destello, golpe de zoom, respuesta grande
  15,36 s    cierre: CTA WhatsApp + firma del estudio (entra con el motivo del tema)
Fondo: si existe bg/<tema>.mp4 (clip de Buzzy) se usa oscurecido; si no, fondo animado propio.
Uso: python3 historia_dinamica.py <id> salida.mp4 [--stills]"""
import math, os, re, subprocess, sys, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from firma import firma
from historias_specs import SPECS

W, H, FPS = 1080, 1920, 30
DUR = 20.48
T_REV, T_CLOSE = 10.24, 15.36
HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = (222, 184, 92); GOLD_D = (176, 132, 46); GOLD_L = (246, 214, 128)
WHITE = (244, 240, 232); GREY = (168, 160, 146); BG = (10, 10, 9)


def sans(s, w=700): return ImageFont.truetype(f'{HERE}/fonts/montserrat-latin-{w}-normal.ttf', s)
def serif(s, w=800): return ImageFont.truetype(f'{HERE}/fonts/cinzel-latin-{w}-normal.ttf', s)
def ease(u): u = min(max(u, 0), 1); return 1 - (1 - u) ** 3
def back(u, k=1.7): u = min(max(u, 0), 1); u -= 1; return 1 + u * u * ((k + 1) * u + k)


def gold_grad(mask):
    w, h = mask.size
    g = np.linspace(0, 1, h)[:, None]
    col = (np.array(GOLD_L) * (1 - g) + np.array(GOLD_D) * g)[:, None, :].repeat(w, 1).reshape(h, w, 3)
    return Image.fromarray(np.dstack([col, np.asarray(mask)]).astype(np.uint8), 'RGBA')


def shadowed(layer, blur=10, off=6, k=.85):
    sh = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    sh.putalpha(layer.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * k)))
    out = Image.new('RGBA', layer.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, off)); out.alpha_composite(layer)
    return out


def word_img(w, font, gold, base=WHITE):
    d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    a, ds = font.getmetrics(); pad = 24
    im = Image.new('RGBA', (int(d.textlength(w, font=font)) + 2 * pad, a + ds + 2 * pad), (0, 0, 0, 0))
    if gold:
        m = Image.new('L', im.size, 0); ImageDraw.Draw(m).text((pad, pad), w, font=font, fill=255); im = gold_grad(m)
    else:
        ImageDraw.Draw(im).text((pad, pad), w, font=font, fill=base)
    return shadowed(im, 8, 5), pad


def layout(text, font, maxw, lh, cy, base=WHITE):
    """Devuelve [(img, x, y)] palabra por palabra, centrado en cy. '|' fuerza salto."""
    toks = []
    for i, seg in enumerate(re.split(r'\*', text)):
        for w_ in seg.replace('|', ' | ').split(' '):
            if w_: toks.append((w_, i % 2 == 1))
    d = ImageDraw.Draw(Image.new('RGBA', (1, 1))); sp = d.textlength(' ', font=font)
    lines, cur, cw = [], [], 0
    for w_, g in toks:
        if w_ == '|': lines.append(cur); cur, cw = [], 0; continue
        tw = d.textlength(w_, font=font)
        if cur and cw + sp + tw > maxw: lines.append(cur); cur, cw = [], 0
        cw += (sp if cur else 0) + tw; cur.append((w_, g, tw))
    if cur: lines.append(cur)
    out = []; y0 = cy - lh * len(lines) / 2
    asc = font.getmetrics()[0]
    for li, line in enumerate(lines):
        lw = sum(t for _, _, t in line) + sp * (len(line) - 1); x = W / 2 - lw / 2
        for w_, g, tw in line:
            im, pad = word_img(w_, font, g, base)
            out.append((im, x - pad, y0 + li * lh - pad + (lh - asc) / 2 - 8)); x += tw + sp
    return out, lh * len(lines)


def alpha_mul(im, a):
    if a >= .999: return im
    im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * a))); return im


def put(fr, im, cx, cy, a=1., s=1.):
    if a <= .01: return
    if abs(s - 1) > .005: im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    fr.alpha_composite(alpha_mul(im, a), (int(cx - im.width / 2), int(cy - im.height / 2)))


def draw_words(fr, words, t, t0, stagger=.07, a_out=1.):
    for i, (im, x, y) in enumerate(words):
        u = (t - t0 - i * stagger) / .32
        if u <= 0: continue
        s = 1.35 - .35 * back(u, 2.2) if u < 1 else 1
        a = ease(u) * a_out
        cx, cy = x + im.width / 2, y + im.height / 2 + 26 * (1 - ease(u))
        put(fr, im, cx, cy, a, s)


# ---------- piezas ----------
def pill(label):
    f = sans(34, 800); d = ImageDraw.Draw(Image.new('RGBA', (1, 1))); tr = 6
    tw = int(sum(d.textlength(c, font=f) for c in label) + tr * (len(label) - 1))
    im = Image.new('RGBA', (tw + 90, 84), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    dr.rounded_rectangle((2, 2, tw + 88, 82), 41, fill=(20, 19, 16, 230), outline=(*GOLD, 255), width=3)
    x = 45
    for c in label: dr.text((x, 20), c, font=f, fill=GOLD); x += d.textlength(c, font=f) + tr
    return im


def option_card(letter, txt, state='idle', w=900):
    f = sans(44 if len(txt) < 30 else 38, 700)
    d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    words, lines, cur = txt.split(), [], ''
    for w_ in words:
        nxt = (cur + ' ' + w_).strip()
        if d.textlength(nxt, font=f) > w - 200 and cur: lines.append(cur); cur = w_
        else: cur = nxt
    lines.append(cur)
    h = 70 + 54 * len(lines)
    im = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    if state == 'ok':
        dr.rounded_rectangle((20, 20, 20 + w, 20 + h), 30, fill=(*GOLD, 255))
        tc, cc, lc = BG, BG, GOLD
    else:
        dr.rounded_rectangle((20, 20, 20 + w, 20 + h), 30, fill=(20, 19, 16, 215), outline=(*GOLD, 170), width=3)
        tc, cc, lc = WHITE, GOLD, BG
    cy = 20 + h / 2
    dr.ellipse((50, cy - 34, 118, cy + 34), fill=(*cc, 255))
    lf = sans(38, 800); lw = d.textlength(letter, font=lf)
    dr.text((84 - lw / 2, cy - 25), letter, font=lf, fill=lc)
    for i, ln in enumerate(lines):
        dr.text((150, cy - 27 * len(lines) + i * 54 - 2), ln, font=f, fill=tc)
    if state == 'ok':
        # tilde
        x0 = 20 + w - 80
        dr.line((x0, cy, x0 + 18, cy + 20, x0 + 50, cy - 22), fill=BG, width=9, joint='curve')
        return im
    return shadowed(im, 12, 6, .7)


def ring(num, p):
    im = Image.new('RGBA', (240, 240), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((20, 20, 220, 220), outline=(*GOLD, 70), width=8)
    d.arc((20, 20, 220, 220), -90, -90 + 360 * p, fill=(*GOLD, 255), width=8)
    f = serif(110, 800); m = Image.new('L', im.size, 0); dm = ImageDraw.Draw(m)
    tw = dm.textlength(num, font=f); dm.text((120 - tw / 2, 48), num, font=f, fill=255)
    im.alpha_composite(gold_grad(m))
    return im


def big_answer(txt, size):
    f = serif(size, 900); d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    lines = txt.split('|'); lh = int(size * 1.08)
    wmax = int(max(d.textlength(l, font=f) for l in lines)) + 60
    m = Image.new('L', (wmax, lh * len(lines) + 60), 0); dm = ImageDraw.Draw(m)
    for i, l in enumerate(lines): dm.text(((wmax - dm.textlength(l, font=f)) / 2, 20 + i * lh), l, font=f, fill=255)
    g = gold_grad(m.crop(m.getbbox()))
    glow = Image.new('RGBA', (g.width + 120, g.height + 120), (0, 0, 0, 0))
    gl = Image.new('RGBA', glow.size, (*GOLD, 0)); a = Image.new('L', glow.size, 0); a.paste(g.split()[3], (60, 60))
    gl.putalpha(a.filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * .55)))
    glow.alpha_composite(gl); glow.alpha_composite(shadowed(g, 10, 6), (60, 60))
    return glow


def bubble():
    b = Image.new('RGBA', (220, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(b)
    d.rounded_rectangle((10, 10, 210, 150), 40, outline=(*GOLD, 255), width=8)
    d.polygon([(50, 145), (40, 192), (100, 148)], fill=(*GOLD, 255))
    for x in (65, 110, 155): d.ellipse((x - 12, 68, x + 12, 92), fill=(*GOLD, 255))
    return b


# ---------- iconos de linea (fondo) ----------
def icon(kind, size=860):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = (*GOLD, 255); w = 6; s = size / 100
    P = lambda *xy: [(x * s, y * s) for x, y in zip(xy[::2], xy[1::2])]
    if kind == 'arca':  # documento con sello
        d.line(P(22, 8, 64, 8, 80, 24, 80, 92, 22, 92, 22, 8), fill=c, width=w, joint='curve')
        d.line(P(64, 8, 64, 24, 80, 24), fill=c, width=w)
        for y in (36, 46, 56): d.line(P(32, y, 70, y), fill=(*GOLD, 160), width=w - 2)
        d.ellipse(P(48, 64, 74, 90), outline=c, width=w)
        d.line(P(54, 77, 60, 83, 69, 71), fill=c, width=w)
    elif kind == 'comex':  # contenedores apilados + grua
        for x0, y0 in ((10, 66), (42, 66), (26, 46)):
            d.rectangle(P(x0, y0, x0 + 30, y0 + 18), outline=c, width=w)
            for k in range(1, 5): d.line(P(x0 + 6 * k, y0 + 3, x0 + 6 * k, y0 + 15), fill=(*GOLD, 150), width=3)
        d.line(P(82, 92, 82, 10, 40, 10), fill=c, width=w); d.line(P(82, 22, 94, 10, 82, 10), fill=c, width=w)
        d.line(P(54, 10, 54, 34), fill=(*GOLD, 180), width=3); d.line(P(4, 92, 96, 92), fill=c, width=w)
    elif kind == 'sueldos':  # recibo + barras
        d.line(P(14, 10, 56, 10, 56, 90, 50, 85, 44, 90, 38, 85, 32, 90, 26, 85, 20, 90, 14, 85, 14, 10), fill=c, width=w, joint='curve')
        for y in (24, 34, 44, 54): d.line(P(22, y, 48, y), fill=(*GOLD, 160), width=w - 2)
        for i, hgt in enumerate((22, 36, 52, 70)):
            x = 64 + i * 8.5; d.rectangle(P(x, 88 - hgt, x + 5, 88), outline=c, width=4)
    else:  # pregunta: arco del puente
        pts = [(s * (8 + 84 * u), s * (70 - 46 * math.sin(math.pi * u))) for u in np.linspace(0, 1, 120)]
        d.line(pts, fill=c, width=w, joint='curve'); d.line(P(4, 70, 96, 70), fill=c, width=w)
        for k in range(1, 8):
            u = .1 + .8 * k / 8; d.line(P(8 + 84 * u, 70, 8 + 84 * u, 70 - 46 * math.sin(math.pi * u)), fill=(*GOLD, 150), width=3)
    return im


class Background:
    def __init__(self, tema, seed=3):
        self.clip = None
        path = f'{HERE}/bg/{tema}.mp4'
        if os.path.exists(path):  # clip de Buzzy
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}',
                                  '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
            self.clip = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
        y, x = np.mgrid[0:H, 0:W]
        self.base = np.clip(np.array(BG, float)[None, None] + np.random.default_rng(7).normal(0, 1.6, (H, W, 3)), 0, 255).astype(np.uint8)
        g = np.clip(1 - np.sqrt(((x[::2, ::2] - W / 2) / (W * .6)) ** 2 + ((y[::2, ::2] - H / 2) / (H * .42)) ** 2), 0, 1) ** 2.2
        gl = (g[..., None] * np.array([44, 38, 20])[None, None]).astype(np.uint8)
        self.glow = Image.fromarray(gl).resize((W, H), Image.BILINEAR)
        self.icon = icon(tema)
        band = np.zeros((H * 2, 260), np.float32); band += np.exp(-((np.arange(260) - 130) / 55.0) ** 2)[None]
        b = Image.fromarray((band * 38).astype(np.uint8)).rotate(-28, expand=True, resample=Image.BILINEAR)
        self.sweep = b
        r = random.Random(seed)
        self.p = [(r.uniform(0, W), r.uniform(0, H), r.uniform(2, 6), r.uniform(30, 90), r.uniform(0, 6.28), r.uniform(.2, .6)) for _ in range(90)]

    def frame(self, t, boost=0.):
        if self.clip is not None:
            n = len(self.clip); k = int(t * FPS) % (2 * n - 2); k = k if k < n else 2 * n - 2 - k  # ida y vuelta
            arr = (self.clip[k].astype(np.float32) * .42).astype(np.uint8)
            fr = Image.fromarray(arr).convert('RGBA')
            dark = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(dark).rectangle((0, 0, W, H), fill=(0, 0, 0, 60))
            fr.alpha_composite(dark)
        else:
            fr = Image.fromarray(self.base).convert('RGBA')
            gx = int(70 * math.sin(t * .5)); gy = int(120 * math.sin(t * .33))
            g = Image.new('RGBA', (W, H), (0, 0, 0, 0)); g.paste(self.glow.convert('RGBA'), (gx, gy))
            arr = np.asarray(fr).astype(np.int16); arr[..., :3] += np.asarray(g)[..., :3]
            fr = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
            # icono gigante que respira y gira apenas
            s = 1.05 + .05 * math.sin(t * .6) + .04 * boost
            ic = self.icon.rotate(4 * math.sin(t * .3), resample=Image.BILINEAR)
            put(fr, ic, W / 2 + 30 * math.sin(t * .4), H * .52, .10 + .08 * boost, s)
        # barrido de luz cada ~5 s
        ph = (t % 5.12) / 5.12
        sx = int(-900 + ph * (W + 1800))
        sw = Image.new('RGBA', self.sweep.size, (*GOLD_L, 0)); sw.putalpha(self.sweep)
        fr.alpha_composite(sw, (sx, -H // 2))
        d = ImageDraw.Draw(fr)
        for x, y, s, v, ph, a in self.p:
            yy = (y - v * t * (1 + boost)) % H; xx = x + 16 * math.sin(t * .7 + ph)
            al = int(255 * a * (.55 + .45 * math.sin(t * 2.1 + ph)))
            d.ellipse((xx - s / 2, yy - s / 2, xx + s / 2, yy + s / 2), fill=(*GOLD, al))
        return fr


def build(spec):
    L = {}
    L['pill'] = pill(spec['label'])
    qs = spec.get('qsize', 74)
    L['q'], qh = layout(spec['q'], sans(qs, 800), 920, int(qs * 1.2), 0)
    opts = spec.get('opts', [])
    letters = 'ABC'
    L['opts'] = [option_card(letters[i], o) for i, o in enumerate(opts)]
    L['opts_ok'] = [option_card(letters[i], o, 'ok') for i, o in enumerate(opts)]
    L['qh'] = qh
    L['big'] = big_answer(spec['big'], spec.get('bsize', 190))
    L['body'], L['bh'] = layout(spec['body'], sans(54, 700), 900, 72, 0)
    L['note'], L['nh'] = layout(spec['note'], sans(38, 500), 880, 50, 0, base=GREY) if spec.get('note') else ([], 0)
    L['bubble'] = bubble()
    L['c1'], _ = layout('Respondé esta historia|con la palabra', sans(58, 800), 900, 72, 0)
    kwsz = 200 if len(spec['kw']) <= 6 else int(200 * 5.8 / len(spec['kw']))
    L['kw'] = big_answer(spec['kw'], kwsz)
    L['c2'], _ = layout('o escribinos por WhatsApp al|*381 276-8888*', sans(42, 600), 900, 56, 0, base=GREY)
    L['firma'] = firma(1000)
    return L


def shift(words, dy): return [(im, x, y + dy) for im, x, y in words]


def render_frame(spec, L, bgc, t):
    kind = spec['kind']
    boost = max(0, 1 - abs(t - T_REV) / .6)
    fr = bgc.frame(t, boost)
    # ---- fase A: pregunta ----
    if t < T_REV + .35:
        aout = 1 - ease((t - T_REV) / .3) if t > T_REV else 1
        pu = ease(t / .35)
        put(fr, L['pill'], W / 2 - (1 - pu) * 600, 300, aout * pu)
        nopt = len(L['opts'])
        qcy = 640 if nopt == 0 else max(560, 430 + L['qh'] / 2)
        draw_words(fr, shift(L['q'], qcy), t, .25, .075, aout)
        nw = len(L['q']); t_opts = .25 + nw * .075 + .5
        y = qcy + L['qh'] / 2 + 70
        for i, oc in enumerate(L['opts']):
            u = ease((t - t_opts - i * .22) / .45)
            if u <= 0: y += oc.height + 6; continue
            dx = (1 - u) * (W if i % 2 == 0 else -W)
            put(fr, oc, W / 2 + dx, y + oc.height / 2, aout)
            y += oc.height + 6
        if kind in ('vf', 'quiz', 'poll'):
            # cuenta regresiva en la grilla: 6,40 / 7,68 / 8,96
            for k, t0 in enumerate((T_REV - 3.84, T_REV - 2.56, T_REV - 1.28)):
                if t0 <= t < t0 + 1.28:
                    u = (t - t0) / 1.28
                    s = 1.25 - .25 * back(min(1, u / .25))
                    put(fr, ring(str(3 - k), u), W / 2, 1640, aout * (1 if u < .85 else 1 - (u - .85) / .15), s)
            if t < T_REV - 3.84:
                hint = spec.get('hint', '¿Qué pensás? Respondé antes del 3-2-1')
                if 'hint_im' not in L: L['hint_im'] = layout(hint, sans(36, 600), 900, 44, 1640, base=GREY)[0]
                draw_words(fr, L['hint_im'], t, t_opts + .6, .03)
    # ---- fase B: respuesta ----
    if T_REV <= t < T_CLOSE + .35:
        aout = 1 - ease((t - T_CLOSE) / .3) if t > T_CLOSE else 1
        u = (t - T_REV) / .5
        s = 1.7 - .7 * back(u, 1.4) if u < 1 else 1
        put(fr, L['big'], W / 2, 540, aout * ease(u * 1.5), s)
        top = 540 + L['big'].height / 2 + 30
        if kind in ('quiz', 'poll') and spec.get('show_ok') is not None:
            oc = L['opts_ok'][spec['show_ok']]
            uu = ease((t - T_REV - .35) / .4)
            put(fr, oc, W / 2, top + oc.height / 2, aout * uu, .9 + .1 * uu); top += oc.height + 30
        draw_words(fr, shift(L['body'], top + L['bh'] / 2 + 10), t, T_REV + .55, .06, aout)
        if L['note']:
            draw_words(fr, shift(L['note'], top + L['bh'] + 60 + L['nh'] / 2), t, T_REV + 1.6, .035, aout)
    # ---- fase C: cierre ----
    if t >= T_CLOSE:
        u = t - T_CLOSE
        put(fr, L['bubble'], W / 2, 400, ease(u / .4), .6 + .4 * back(u / .45))
        draw_words(fr, shift(L['c1'], 630), t, T_CLOSE + .15, .06)
        uk = (u - .9) / .5
        if uk > 0:
            pulse = 1 + .03 * math.sin(max(0, u - 1.4) * 5)
            put(fr, L['kw'], W / 2, 830, ease(uk * 1.5), (1.6 - .6 * back(uk, 1.4) if uk < 1 else 1) * pulse)
        draw_words(fr, shift(L['c2'], 1040), t, T_CLOSE + 1.6, .04)
        put(fr, L['firma'], W / 2, 1400 + 20 * (1 - ease((u - 1.9) / .5)), ease((u - 1.9) / .5))
    # destello y golpe de zoom en la revelacion
    if T_REV <= t < T_REV + .4:
        a = 1 - (t - T_REV) / .4
        fl = Image.new('RGBA', (W, H), (255, 236, 190, int(200 * a ** 2))); fr.alpha_composite(fl)
    zs = 1 + .045 * max(0, 1 - (t - T_REV) / .5) if t >= T_REV else 1 + .012 * t / T_REV
    if zs > 1.001:
        sh = int(10 * max(0, 1 - (t - T_REV) / .3) * math.sin(t * 90)) if t >= T_REV else 0
        z = fr.resize((int(W * zs), int(H * zs)), Image.BILINEAR)
        ox, oy = (z.width - W) // 2 + sh, (z.height - H) // 2
        fr = z.crop((ox, oy, ox + W, oy + H))
    # salida a negro
    if t > DUR - .4:
        fr.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * ease((t - DUR + .4) / .4)))))
    return fr.convert('RGB')


def main():
    global T_REV, T_CLOSE, DUR
    sid, out = sys.argv[1], sys.argv[2]
    spec = SPECS[sid]
    ex = spec.get('extra', 0)  # tiempos extra (en la grilla) para preguntas con opciones leidas
    T_REV, T_CLOSE, DUR = T_REV + ex, T_CLOSE + ex, DUR + ex
    L = build(spec); bgc = Background(spec['tema'])
    if '--stills' in sys.argv:
        os.makedirs(out, exist_ok=True)
        for t in (1.5, 5.5, T_REV - 3, T_REV + .2, T_REV + 2.3, T_CLOSE + 2.5):
            render_frame(spec, L, bgc, t).save(f'{out}/{sid}_t{t:05.2f}.png')
        return
    tmp = out + '.v.mp4'
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        p.stdin.write(render_frame(spec, L, bgc, i / FPS).tobytes())
    p.stdin.close(); p.wait()
    os.replace(tmp, out)  # la musica y la voz se agregan en mezcla_voz.py


if __name__ == '__main__':
    main()
