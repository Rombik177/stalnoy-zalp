"""Всё, что игра рисует кодом: кляксы гуашью, крестик и точка как в бумажном морском бое,
белый флаг — и заглушки вместо картинок, которых ещё нет. Цвета приглушённые, под гуашь."""
import math
import os
import random

import pygame

from game import nastroyki as N

M = 2                       # рисуем вдвое крупнее и сглаживаем уменьшением
CHERNILA = N.CVET_CHERNILA
_kesh = {}


def temnee(c, k):
    return tuple(max(0, int(v * k)) for v in c[:3])


def svetlee(c, k):
    return tuple(min(255, int(v + (255 - v) * k)) for v in c[:3])


def smesh(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _kontur(rng, cx, cy, r, rvanost, tochek=64):
    """Рваный край: окружность, искажённая суммой гармоник со случайными фазами."""
    garm = [(rvanost * rng.uniform(0.35, 1.0) / (1 + j * 0.6), k, rng.uniform(0, math.tau))
            for j, k in enumerate((2, 3, 5, 7, 11, 17))]
    pts = []
    for i in range(tochek):
        a = math.tau * i / tochek
        m = 1 + sum(amp * math.sin(k * a + f) for amp, k, f in garm) + rng.uniform(-0.04, 0.04)
        pts.append((cx + math.cos(a) * r * m, cy + math.sin(a) * r * m))
    return pts


def klyaksa(radius, cvet, nomer=0):
    """Клякса гуаши: тёмный рваный край, основной тон, светлые мазки кисти,
    капли с хвостиками вокруг. Поверхность 4,2·radius, центр — центр пятна."""
    cvet = tuple(cvet[:3])
    kl = ("k", radius, cvet, nomer % 16)
    s = _kesh.get(kl)
    if s is not None:
        return s
    rng = random.Random(radius * 7919 + cvet[0] * 65599 + cvet[1] * 257 + cvet[2] + (nomer % 16) * 104729)
    r = radius * M
    razm = int(r * 4.2)
    c = razm / 2
    pov = pygame.Surface((razm, razm), pygame.SRCALPHA)
    temn = temnee(cvet, 0.76)
    svet = svetlee(cvet, 0.2)
    blik = svetlee(cvet, 0.38)
    for _ in range(rng.randint(5, 9)):
        a = rng.uniform(0, math.tau)
        d = r * rng.uniform(1.08, 1.8)
        rk = r * rng.uniform(0.05, 0.15)
        x, y = c + math.cos(a) * d, c + math.sin(a) * d
        if rng.random() < 0.45:
            x0, y0 = c + math.cos(a) * r * 0.85, c + math.sin(a) * r * 0.85
            pygame.draw.line(pov, temn, (x0, y0), (x, y), max(2, int(rk * 0.9)))
        pygame.draw.circle(pov, temn, (x, y), rk)
    pygame.draw.polygon(pov, temn, _kontur(rng, c, c, r, 0.26))
    pygame.draw.polygon(pov, cvet, _kontur(rng, c - r * 0.05, c - r * 0.06, r * 0.82, 0.2))
    for _ in range(rng.randint(3, 5)):
        a = rng.uniform(0, math.tau)
        d = r * rng.uniform(0.05, 0.45)
        x, y = c + math.cos(a) * d - r * 0.08, c + math.sin(a) * d - r * 0.08
        w, h = r * rng.uniform(0.25, 0.42), r * rng.uniform(0.07, 0.12)
        pygame.draw.ellipse(pov, svet, (int(x - w / 2), int(y - h / 2), int(w), int(h)))
    pygame.draw.ellipse(pov, blik, (int(c - r * 0.48), int(c - r * 0.5), int(r * 0.3), int(r * 0.16)))
    for _ in range(rng.randint(6, 10)):          # сухая кисть: проплешины у края
        a = rng.uniform(0, math.tau)
        d = r * rng.uniform(0.72, 0.95)
        pygame.draw.circle(pov, (0, 0, 0, 0), (c + math.cos(a) * d, c + math.sin(a) * d),
                           r * rng.uniform(0.03, 0.06))
    itog = pygame.transform.smoothscale(pov, (razm // M, razm // M))
    _kesh[kl] = itog
    return itog


def krestik(razmer, nomer=0):
    """Крестик попадания — чернилами от руки, как в бумажном морском бое."""
    kl = ("x", razmer, nomer % 6)
    s = _kesh.get(kl)
    if s is not None:
        return s
    rng = random.Random(razmer * 31 + nomer % 6)
    sz = razmer * M
    pov = pygame.Surface((sz, sz), pygame.SRCALPHA)
    t = sz * 0.06
    for x0, y0, x1, y1 in ((0.27, 0.25, 0.75, 0.76), (0.74, 0.26, 0.26, 0.75)):
        a = ((x0 + rng.uniform(-0.03, 0.03)) * sz, (y0 + rng.uniform(-0.03, 0.03)) * sz)
        b = ((x1 + rng.uniform(-0.03, 0.03)) * sz, (y1 + rng.uniform(-0.03, 0.03)) * sz)
        dx, dy = b[0] - a[0], b[1] - a[1]
        dl = math.hypot(dx, dy)
        nx, ny = -dy / dl, dx / dl
        izgib = rng.uniform(-0.03, 0.03) * sz
        levo, pravo = [], []
        for i in range(9):
            u = i / 8
            sdvig = math.sin(u * math.pi) * izgib
            w = t * (0.55 + 0.45 * math.sin(u * math.pi))
            px, py = a[0] + dx * u + nx * sdvig, a[1] + dy * u + ny * sdvig
            levo.append((px + nx * w, py + ny * w))
            pravo.append((px - nx * w, py - ny * w))
        pygame.draw.polygon(pov, (*CHERNILA, 225), levo + pravo[::-1])
    itog = pygame.transform.smoothscale(pov, (razmer, razmer))
    _kesh[kl] = itog
    return itog


def tochka(razmer, cvet=None):
    """Точка промаха: тёмная капля #1B1E27 в 30 % клетки, плотное ядро и мягкий край.
    cvet — та же капля другим цветом (белая точка «пусто» того же размера)."""
    cvet = CHERNILA if cvet is None else tuple(cvet)
    kl = ("t", razmer, cvet)
    s = _kesh.get(kl)
    if s is not None:
        return s
    sz = razmer * M
    pov = pygame.Surface((sz, sz), pygame.SRCALPHA)
    yadro, kraj, shagov = sz * 0.125, sz * 0.175, 12
    for i in range(shagov, -1, -1):          # снаружи внутрь: каждый круг плотнее предыдущего
        a = round(235 * (1 - i / shagov) ** 1.5)
        pygame.draw.circle(pov, (*cvet, a), (sz / 2, sz / 2), yadro + (kraj - yadro) * i / shagov)
    itog = pygame.transform.smoothscale(pov, (razmer, razmer))
    _kesh[kl] = itog
    return itog


def belyj_flag(ekran, x, y, t, m=1.0):
    """Белый флаг закрашенного корабля: древко и полотнище, которое вьётся."""
    vys, dl, h = 30 * m, 22 * m, 13 * m
    pygame.draw.line(ekran, (96, 78, 60), (x, y), (x, y - vys), max(2, int(3 * m)))
    verh, niz = [], []
    for i in range(7):
        u = i / 6
        v = math.sin(t * 6 - u * 5) * 3.0 * m * u
        verh.append((x + u * dl, y - vys + v))
        niz.append((x + u * dl, y - vys + h + v * 1.1))
    pts = verh + niz[::-1]
    pygame.draw.polygon(ekran, (248, 246, 240), pts)
    pygame.draw.polygon(ekran, (110, 112, 120), pts, 1)
    pygame.draw.circle(ekran, (214, 182, 112), (x, y - vys), max(2, int(2.5 * m)))


# --- заглушки ---

CVETA_SKINOV = {"bazovyj": (160, 166, 172), "kamuflyazh": (124, 138, 104),
                "nochnoj": (74, 84, 110), "paradnyj": (232, 228, 218)}


def zaglushka_korabl(imya, dlina, skin, razbit, kletka=128):
    """Игрушечный кораблик сверху, нос вправо, в рамке dlina×1 клеток."""
    w, h = dlina * kletka, kletka
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    k = h / 128
    if dlina == 1:
        korpus = [(14 * k, h * 0.5), (30 * k, h * 0.32), (w * 0.72, h * 0.3), (w - 10 * k, h * 0.5),
                  (w * 0.72, h * 0.7), (30 * k, h * 0.68)]
    else:
        korpus = [(12 * k, h * 0.3), (w - h * 0.55, h * 0.24), (w - 8 * k, h * 0.5),
                  (w - h * 0.55, h * 0.76), (12 * k, h * 0.7)]
    pygame.draw.polygon(s, (*CHERNILA, 70), [(x + 6 * k, y + 9 * k) for x, y in korpus])
    cvet = (138, 126, 110) if razbit else CVETA_SKINOV.get(skin, CVETA_SKINOV["bazovyj"])
    pygame.draw.polygon(s, cvet, korpus)
    pygame.draw.polygon(s, svetlee(cvet, 0.16), [(x + (w / 2 - x) * 0.1, y + (h / 2 - y) * 0.32) for x, y in korpus])
    detal = temnee(cvet, 0.72)
    tolsh = max(2, int(5 * k))
    if imya == "avianosec":
        for i in range(7):
            x = w * 0.08 + i * w * 0.09
            pygame.draw.line(s, svetlee(cvet, 0.55), (x, h * 0.5), (x + w * 0.045, h * 0.5), tolsh)
        pygame.draw.rect(s, detal, (int(w * 0.62), int(h * 0.27), int(w * 0.1), int(h * 0.16)),
                         border_radius=int(6 * k))
    elif imya in ("linkor", "esminec"):
        bashni = (0.2, 0.42, 0.8) if imya == "linkor" else (0.25, 0.78)
        for f in bashni:
            cx = w * f
            pygame.draw.line(s, temnee(cvet, 0.5), (cx, h * 0.5), (cx + h * 0.3, h * 0.5), tolsh)
            pygame.draw.circle(s, detal, (cx, h * 0.5), h * 0.13)
            pygame.draw.circle(s, temnee(cvet, 0.45), (cx, h * 0.5), h * 0.13, max(1, tolsh // 2))
        mx = int(w * (0.58 if imya == "linkor" else 0.46))
        most = (mx, int(h * 0.36), int(h * 0.32), int(h * 0.28))
        pygame.draw.rect(s, svetlee(cvet, 0.35), most, border_radius=int(8 * k))
        pygame.draw.rect(s, temnee(cvet, 0.45), most, max(1, tolsh // 2), border_radius=int(8 * k))
    else:
        pygame.draw.ellipse(s, detal, (int(w * 0.36), int(h * 0.38), int(w * 0.26), int(h * 0.24)))
    pygame.draw.polygon(s, temnee(cvet, 0.42), korpus, tolsh)
    if skin == "paradnyj" and not razbit:
        n = dlina * 3
        for i in range(n):
            x = w * 0.1 + i * (w * 0.75 / n)
            pygame.draw.polygon(s, ((196, 112, 100), (214, 182, 112), (96, 150, 186))[i % 3],
                                [(x, h * 0.18), (x + 10 * k, h * 0.18), (x + 5 * k, h * 0.26)])
    if razbit:
        rng = random.Random(dlina * 17)
        for i in range(dlina + 1):
            x = w * (0.15 + 0.7 * i / max(1, dlina))
            pts = [(x + rng.uniform(-8, 8) * k, h * 0.3 + j * h * 0.1) for j in range(5)]
            pygame.draw.lines(s, temnee(cvet, 0.4), False, pts, max(1, int(3 * k)))
        for i in range(min(3, dlina + 1)):
            cx, cy = w * (0.15 + 0.32 * i), h * (0.12 if i % 2 == 0 else 0.88)
            pygame.draw.circle(s, (220, 128, 100), (cx, cy), h * 0.08, max(2, int(6 * k)))
            pygame.draw.circle(s, (246, 240, 230), (cx, cy), h * 0.08, max(1, int(2 * k)))
    return s


def zaglushka_flagman():
    """Флагман для «VS» и верфи: тот же авианосец крупно, чуть наискось."""
    s = pygame.Surface((1000, 560), pygame.SRCALPHA)
    k = pygame.transform.rotate(zaglushka_korabl("avianosec", 4, "bazovyj", False, 200), 8)
    s.blit(k, k.get_rect(center=(500, 290)))
    return s


def zaglushka_portret(kto, emociya, cvet):
    """Портрет-заглушка 700×800: кот Румб смотрит вправо, капитан — влево."""
    w, h = 700, 800
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    ob = 6
    if kto == "rumb":
        meh = (196, 156, 112)
        pygame.draw.ellipse(s, meh, (150, 540, 400, 300))
        pygame.draw.ellipse(s, CHERNILA, (150, 540, 400, 300), ob)
        pygame.draw.polygon(s, N.CVET_IGROKA, [(240, 560), (460, 560), (350, 640)])
        pygame.draw.polygon(s, CHERNILA, [(240, 560), (460, 560), (350, 640)], ob)
        for ux in (1, -1):
            ux0 = 350 + ux * 150
            pts = [(ux0 - ux * 60, 250), (ux0 + ux * 10, 130), (ux0 + ux * 40, 300)]
            pygame.draw.polygon(s, meh, pts)
            pygame.draw.polygon(s, CHERNILA, pts, ob)
        pygame.draw.circle(s, meh, (350, 380), 190)
        pygame.draw.circle(s, CHERNILA, (350, 380), 190, ob)
        pygame.draw.ellipse(s, svetlee(meh, 0.45), (275, 400, 170, 110))
        glaza, nos = ((300, 350), (420, 350)), (362, 418)
        sdvig = 9
    else:
        kozha = (238, 206, 174)
        pygame.draw.rect(s, cvet, (170, 560, 360, 260), border_radius=90)
        for i in range(3):
            pygame.draw.line(s, svetlee(cvet, 0.7), (200, 620 + i * 40), (500, 620 + i * 40), 10)
        pygame.draw.rect(s, CHERNILA, (170, 560, 360, 260), ob, border_radius=90)
        pygame.draw.circle(s, kozha, (350, 390), 170)
        pygame.draw.circle(s, CHERNILA, (350, 390), 170, ob)
        pygame.draw.ellipse(s, svetlee(cvet, 0.15), (186, 196, 328, 130))
        pygame.draw.ellipse(s, CHERNILA, (186, 196, 328, 130), ob)
        pygame.draw.rect(s, temnee(cvet, 0.8), (110, 290, 160, 34), border_radius=17)
        pygame.draw.rect(s, CHERNILA, (110, 290, 160, 34), ob, border_radius=17)
        glaza, nos = ((290, 390), (410, 390)), (330, 440)
        sdvig = -9
    for gx, gy in glaza:
        pygame.draw.circle(s, (252, 250, 244), (gx, gy), 26)
        pygame.draw.circle(s, CHERNILA, (gx, gy), 26, 4)
        pygame.draw.circle(s, CHERNILA, (gx + sdvig, gy + 2), 12)
    pygame.draw.circle(s, (206, 132, 120), nos, 9)
    rx = nos[0] - 50
    ry = nos[1] + 30
    if emociya == "raduetsya":
        pygame.draw.arc(s, CHERNILA, (rx, ry - 30, 100, 64), math.pi * 1.1, math.pi * 1.9, 7)
    elif emociya == "zlitsya":
        pygame.draw.arc(s, CHERNILA, (rx + 10, ry + 8, 80, 50), math.pi * 0.15, math.pi * 0.85, 7)
        for gx, gy in glaza:
            nakl = 10 if gx < 350 else -10
            pygame.draw.line(s, CHERNILA, (gx - 26, gy - 40 - nakl), (gx + 26, gy - 40 + nakl), 7)
    elif emociya == "ehidnichaet":
        pygame.draw.arc(s, CHERNILA, (rx + 30, ry - 20, 80, 50), math.pi * 1.2, math.pi * 1.9, 7)
        pygame.draw.line(s, CHERNILA, (glaza[1][0] - 26, glaza[1][1] - 34), (glaza[1][0] + 26, glaza[1][1] - 30), 7)
    else:
        pygame.draw.line(s, CHERNILA, (rx + 25, ry + 10), (rx + 75, ry + 10), 7)
    if kto == "rumb":
        for i in (-1, 1):
            for j in (-12, 8):
                pygame.draw.line(s, CHERNILA, (350 + i * 90, 440 + j), (350 + i * 210, 425 + j * 2), 3)
    return s


def zaglushka_fon(vid, razmer=(N.SHIRINA, N.VYSOTA)):
    """Фон-заглушка: бухта, верфь, пролог, серый город, карта или вода поля."""
    w, h = razmer
    s = pygame.Surface(razmer, 0, 32)
    rng = random.Random(vid)
    if vid == "voda":
        s.fill((98, 152, 172))
        for y in range(0, h, 24):
            pts = [(x, y + 5 * math.sin(x / w * math.tau * 2 + y * 0.21)) for x in range(0, w + 8, 8)]
            pygame.draw.lines(s, (110, 162, 180), False, pts, 2)
        return s
    if vid == "karta":
        s.fill((232, 220, 192))
        more = (int(w * 0.08), int(h * 0.1), int(w * 0.84), int(h * 0.8))
        pygame.draw.ellipse(s, (182, 204, 200), more)
        for i in range(1, 4):
            r = pygame.Rect(more).inflate(-i * 56, -i * 36)
            pygame.draw.ellipse(s, (168, 194, 192), r, 2)
        pygame.draw.circle(s, (214, 200, 168), (w // 2, h // 2), 44)
        pygame.draw.circle(s, (126, 110, 90), (w // 2, h // 2), 44, 2)
        pygame.draw.rect(s, (240, 234, 222), (w // 2 - 6, h // 2 - 36, 12, 32), border_radius=3)
        pygame.draw.rect(s, (126, 110, 90), (w // 2 - 6, h // 2 - 36, 12, 32), 2, border_radius=3)
        return s
    seryj = vid == "seryj"

    def sv(c):
        if not seryj:
            return c
        g = sum(c) // 3
        return (g, g, g + 4)

    gor = int(h * 0.48)
    nebo = (sv((158, 198, 220)), sv((228, 236, 232)))
    more = (sv((100, 154, 178)), sv((64, 116, 146)))
    for y in range(gor):
        pygame.draw.line(s, smesh(nebo[0], nebo[1], y / gor), (0, y), (w, y))
    for y in range(gor, h):
        pygame.draw.line(s, smesh(more[0], more[1], (y - gor) / (h - gor)), (0, y), (w, y))
    pts = [(0, gor)] + [(x, gor - 36 - 28 * math.sin(x / w * 5 + 1) - 12 * math.sin(x / w * 13))
                        for x in range(0, w + 16, 16)] + [(w, gor)]
    pygame.draw.polygon(s, sv((142, 168, 128)), pts)
    for _ in range(16 if w >= 400 else 0):
        x = rng.randint(40, w - 80)
        y = gor - rng.randint(18, 56)
        dw = rng.randint(22, 34)
        krysha = sv(rng.choice([(186, 118, 98), (204, 164, 104), (124, 144, 170)]))
        pygame.draw.rect(s, sv((236, 228, 214)), (x, y, dw, 18))
        pygame.draw.polygon(s, krysha, [(x - 3, y), (x + dw // 2, y - 12), (x + dw + 3, y)])
    if vid in ("buhta", "verf"):
        px, py = int(w * 0.28), int(h * 0.7)
        pygame.draw.rect(s, (150, 114, 82), (px, py, int(w * 0.2), 18))
        for i in range(6):
            pygame.draw.rect(s, (112, 84, 60), (px + i * int(w * 0.04), py + 18, 6, 26))
    if vid == "verf":
        y0 = int(h * 0.8)
        pygame.draw.rect(s, (170, 132, 96), (0, y0, w, h - y0))
        for y in range(y0, h, 16):
            pygame.draw.line(s, (146, 110, 78), (0, y), (w, y), 2)
    return s


ZNACHKI = {"tochnost": (96, 150, 186), "seriya": (196, 120, 96), "bez_poter": (120, 160, 112),
           "saper": (150, 120, 170)}


def zaglushka_znachok(vid, razmer, cvet=N.CVET_IGROKA):
    """Медаль, мина-буй, вымпел или карточка улучшения — кодом."""
    w, h = razmer
    s = pygame.Surface(razmer, pygame.SRCALPHA)
    cx, cy = w / 2, h / 2
    r = min(w, h) / 2 - 6
    if vid == "medal":
        for dx in (-1, 1):
            lenta = [(cx + dx * r * 0.1, 4), (cx + dx * r * 0.55, 4), (cx + dx * r * 0.2, cy), (cx - dx * r * 0.15, cy)]
            pygame.draw.polygon(s, cvet, lenta)
            pygame.draw.polygon(s, CHERNILA, lenta, 2)
        pygame.draw.circle(s, (214, 184, 118), (cx, cy + r * 0.25), r * 0.62)
        pygame.draw.circle(s, CHERNILA, (cx, cy + r * 0.25), r * 0.62, 3)
        zv = [(cx + math.cos(-math.pi / 2 + i * math.pi / 5) * r * (0.36 if i % 2 == 0 else 0.16),
               cy + r * 0.25 + math.sin(-math.pi / 2 + i * math.pi / 5) * r * (0.36 if i % 2 == 0 else 0.16))
              for i in range(10)]
        pygame.draw.polygon(s, svetlee((214, 184, 118), 0.4), zv)
    elif vid == "mina":
        pygame.draw.circle(s, (204, 108, 96), (cx, cy), r * 0.7)
        pygame.draw.rect(s, (246, 240, 230), (cx - r * 0.7, cy - r * 0.12, r * 1.4, r * 0.24))
        pygame.draw.circle(s, CHERNILA, (cx, cy), r * 0.7, 3)
        pygame.draw.circle(s, CHERNILA, (cx, cy - r * 0.78), r * 0.12, 3)
        for i in range(3):
            pygame.draw.circle(s, (204, 108, 96), (cx - r * 0.4 + i * r * 0.4, cy + r * 0.82), r * 0.07)
    elif vid == "vympel":
        pygame.draw.line(s, CHERNILA, (w * 0.2, h * 0.05), (w * 0.2, h * 0.95), 4)
        pts = [(w * 0.2, h * 0.08), (w * 0.92, h * 0.25), (w * 0.2, h * 0.45)]
        pygame.draw.polygon(s, cvet, pts)
        pygame.draw.polygon(s, CHERNILA, pts, 3)
    else:
        pygame.draw.circle(s, svetlee(cvet, 0.5), (cx, cy), r * 0.8)
        pygame.draw.circle(s, cvet, (cx, cy), r * 0.5)
        pygame.draw.circle(s, CHERNILA, (cx, cy), r * 0.8, 3)
    return s


def zaglushka_prostaya(razmer, podpis=""):
    w, h = razmer
    s = pygame.Surface(razmer, pygame.SRCALPHA)
    rad = max(4, min(w, h) // 10)
    pygame.draw.rect(s, (*N.CVET_BUMAGA, 255), s.get_rect(), border_radius=rad)
    pygame.draw.rect(s, (*CHERNILA, 255), s.get_rect(), 2, border_radius=rad)
    if podpis and pygame.font.get_init():
        t = pygame.font.Font(None, 20).render(os.path.basename(podpis), True, CHERNILA)
        s.blit(t, t.get_rect(center=(w // 2, h // 2)))
    return s
