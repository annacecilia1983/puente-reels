#!/usr/bin/env python3
"""Voz de Andrea sobre las historias dinamicas: A (pregunta) 0,25 s, B (respuesta) 10,35 s, cierre 16,0 s.
Recorta silencios, acelera 8 % (hasta 25 % si hace falta para entrar en la ventana), baja la musica bajo la voz, -14 LUFS.
Uso: python3 mezcla_voz.py <id> video_sin_voz.mp4 salida.mp4"""
import subprocess, sys, os
import numpy as np
from scipy.io import wavfile

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))



def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    env = np.convolve(np.abs(x), np.ones(441) / 441, 'same')
    on = np.where(env > .004)[0]
    y = x[max(0, on[0] - 600):min(len(x), on[-1] + int(.30 * SR))].copy()  # 0,30 s de cola: no cortar la s final
    k = int(.08 * SR); y[-k:] *= np.linspace(1, 0, k)
    return y


def tempo(x, f):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', '-af', f'atempo={f:.4f}', '-f', 'f32le', '-'],
                       input=x.astype(np.float32).tobytes(), capture_output=True)
    return np.frombuffer(p.stdout, np.float32)


def main(sid, vin, out):
    sys.path.insert(0, HERE); from historias_specs import SPECS
    ex = SPECS[sid].get('extra', 0); dur = 20.48 + ex
    tr, tc = 10.24 + ex, 15.36 + ex
    SLOTS = [('A', .25, tr - 3.7), ('B', tr + .11, tc + .3), ('cta', tc + .5, dur - .35)]
    music = f'{HERE}/audio/{"v25" if ex else "v20"}_n.wav'
    pre = sid.split('_')[0]
    voice = np.zeros(int(dur * SR), np.float32)
    end = 0
    for tag, t0, t1 in SLOTS:
        t0 = max(t0, end + .2)
        x = load(f'{HERE}/voz/{pre}_{tag}.mp3')
        win = t1 - t0
        f = min(1.18, max(1.08, len(x) / SR / win))
        y = tempo(x, f)
        end = t0 + len(y) / SR  # si no entra, se extiende sobre la cuenta regresiva o empuja el cierre
        i = int(t0 * SR); voice[i:i + len(y)] += y[:len(voice) - i]
        print(sid, tag, f'x{f:.2f}', round(len(y) / SR, 2), 'de', round(win, 2))
    wavfile.write('/tmp/voz.wav', SR, voice)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', vin, '-i', music, '-i', '/tmp/voz.wav', '-filter_complex',
                    '[2:a]aformat=channel_layouts=stereo,volume=1.6,asplit=2[v1][v2];'
                    '[1:a]volume=0.55[m];[m][v1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[md];'
                    '[md][v2]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]',
                    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-movflags', '+faststart', out], check=True)


if __name__ == '__main__':
    main(*sys.argv[1:4])
