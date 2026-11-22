#!/usr/bin/env python3
"""Firma Puente al estilo de las placas del Boletin Oficial:
linea dorada + estrella | monograma P | PUENTE TRIBUTARIO Y ADUANERO / ESTUDIO CONTABLE | estrella + linea
y debajo telefono y web. Uso: from firma import firma; firma(ancho)  -> RGBA"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = (222, 184, 92); GOLD_D = (176, 132, 46); CREAM = (236, 228, 210); GREY = (190, 182, 166)
PORTADA = os.path.join(HERE, 'Portada_Reel.png')
SYM = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def font(name, w, s): return ImageFont.truetype(os.path.join(HERE, 'fonts', f'{name}-latin-{w}-normal.ttf'), s)


def monograma(h):
    src = Image.open(PORTADA).convert('RGB').crop((380, 485, 700, 800))
    a = np.asarray(src).astype(float)
    alpha = np.clip((a.max(2) - 30) / 150, 0, 1)
    col = np.clip(a / np.maximum(alpha, 1e-3)[..., None], 0, 255)
    im = Image.fromarray(np.dstack([col, alpha * 255]).astype(np.uint8), 'RGBA')
    im = im.crop(im.getbbox())
    return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)


def tracked(txt, f, fill, tr):
    d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    ws = [d.textlength(c, font=f) for c in txt]
    a, ds = f.getmetrics()
    im = Image.new('RGBA', (int(sum(ws) + tr * len(txt)) + 10, a + ds + 10), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im); x = 5
    for c, w in zip(txt, ws): dr.text((x, 5), c, font=f, fill=fill); x += w + tr
    return im.crop(im.getbbox())


def text(txt, f, fill):
    d = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    a, ds = f.getmetrics()
    im = Image.new('RGBA', (int(d.textlength(txt, font=f)) + 10, a + ds + 10), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((5, 5), txt, font=f, fill=fill)
    return im.crop(im.getbbox())


def estrella(d, cx, cy, r):
    k = r * .22
    d.polygon([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k), (cx, cy + r), (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)], fill=(*GOLD, 255))


def firma(W=1000, s=1.0, contacto=True):
    S = lambda v: int(round(v * s))
    mono = monograma(S(104))
    nombre = text('Puente Tributario y Aduanero', font('cinzel', 500, S(36)), CREAM)
    est = tracked('ESTUDIO CONTABLE', font('cinzel', 500, S(21)), GREY, S(7))
    tw = max(nombre.width, est.width)
    gap = S(22)
    bw = mono.width + gap + tw
    bh = max(mono.height, nombre.height + S(18) + est.height + S(14))
    H1 = bh
    rows = [H1]
    if contacto:
        cf = font('montserrat', 500, S(26)); sf = ImageFont.truetype(SYM, S(28))
        tel = text('+54 9 381 276-8888', cf, CREAM); web = text('www.puentetributario.com.ar', cf, CREAM)
        ic1 = text('☎', sf, GOLD); ic2 = text('✉', sf, GOLD)
        cw = ic1.width + S(12) + tel.width + S(50) + ic2.width + S(12) + web.width
        rows.append(max(tel.height, ic1.height))
    H = H1 + (S(30) + rows[1] if contacto else 0) + S(20)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x0 = (W - bw) // 2
    im.alpha_composite(mono, (x0, (H1 - mono.height) // 2))
    tx = x0 + mono.width + gap
    ty = (H1 - (nombre.height + S(18) + est.height)) // 2
    im.alpha_composite(nombre, (tx + (tw - nombre.width) // 2, ty))
    ly = ty + nombre.height + S(9)
    d.line((tx + S(10), ly, tx + tw - S(10), ly), fill=(*GOLD, 150), width=max(1, S(2)))
    im.alpha_composite(est, (tx + (tw - est.width) // 2, ty + nombre.height + S(18)))
    cy = H1 // 2
    for side in (-1, 1):
        edge = x0 - S(40) if side < 0 else x0 + bw + S(40)
        sx = edge
        estrella(d, sx, cy, S(16))
        a, b = (S(10), sx - S(28)) if side < 0 else (sx + S(28), W - S(10))
        n = 60
        for i in range(n):  # linea que se desvanece hacia afuera
            u0, u1 = a + (b - a) * i / n, a + (b - a) * (i + 1) / n
            f = (i / n) if side < 0 else (1 - i / n)
            d.line((u0, cy, u1, cy), fill=(*GOLD, int(220 * f ** 1.3)), width=max(1, S(2)))
    if contacto:
        y = H1 + S(30); x = (W - cw) // 2
        for el, after in ((ic1, S(12)), (tel, S(50)), (ic2, S(12)), (web, 0)):
            im.alpha_composite(el, (x, y + (rows[1] - el.height) // 2)); x += el.width + after
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * .8)))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 4)); out.alpha_composite(im)
    return out


if __name__ == '__main__':
    f = firma()
    bg = Image.new('RGBA', f.size, (12, 12, 11, 255)); bg.alpha_composite(f)
    bg.save(sys.argv[1] if len(sys.argv) > 1 else 'firma_prueba.png')
