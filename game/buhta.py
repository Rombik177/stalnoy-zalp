"""Живая бухта капитана: фон-картинка и вещи-спрайты из img/buhty/<id>/*.json поверх неё.

Белые слои кадров умножаются на цвет бухты (BLEND_RGB_MULT) — светотень рисунка остаётся.
Кодом рисуются только туман и блики; нет файла — вещь просто не появляется.
"""
import bisect
import itertools
import math
import random
from operator import attrgetter

import pygame

from game import nastroyki as N
from game import risunki
from game.ui import plavno, smeshat

W, H = N.SHIRINA, N.VYSOTA

RAZMETKA = {
    "voda": [480, 420, 780, 280],
    "tuman": [0, 240, 1280, 76],          # полоса дальней воды у горизонта
    "puti": {},
    "masshtab_hodokov": 1.0,
}
# Лодка у причала: точка из zhivye.json сдвинута вправо-вперёд, чтобы корма
# не налезала на угол причала. Своя точка — "lodka_u_prichala" в razmetka.json.
LODKA_SDVIG = (44, 10)
# Уходящая лодка проявляется за лодкой у причала — с этой доли пути.
LODKA_HOD_S0 = 0.12
CHAJKI = {"chayka_1": {"fps": 12, "opora": [17.8, 32.9]},
          "chayka_2": {"fps": 14, "opora": [14.1, 27.5]}}
PO_Y = attrgetter("y")


def kadry_iz(res, opis, masshtab=1.0):
    """'timoha/lodka/01..16.png' из zhivye.json -> кадры папки img/buhty/timoha/lodka."""
    if not isinstance(opis, str) or "/" not in opis:
        return []
    return res.kadry_hodoka("img/buhty/" + opis.rsplit("/", 1)[0], masshtab)


def svechenie(radius, cvet, stepen=2.0, szhat=1.0):
    """Мягкое пятно света на чёрном — накладывать сложением (BLEND_RGB_ADD)."""
    s = pygame.Surface((radius * 2, radius * 2))
    s.fill((0, 0, 0))
    for r in range(radius, 0, -1):
        k = (1 - r / radius) ** stepen
        pygame.draw.circle(s, [int(c * k) for c in cvet], (radius, radius), r)
    if szhat != 1.0:
        s = pygame.transform.smoothscale(s, (radius * 2, max(2, int(radius * 2 * szhat))))
    return s


def urovni_sveta(s, n):
    """n копий пятна от тусклой к полной: яркость меняется без выделений в кадре."""
    out = []
    for i in range(1, n + 1):
        k = s.copy()
        v = int(255 * i / n)
        k.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
        out.append(k)
    return out


OTRAZHENIE_ALFA = 0.3                 # непрозрачность отражения в воде
OTRAZHENIE_CVET = (124, 146, 164)     # отражение темнее и холоднее самой вещи


def otrazhenie(sprite, vaterliniya, szhatie=1.0):
    """Отражение в воде: часть спрайта выше ватерлинии, перевёрнутая, притемнённая
    к воде и тающая книзу. Возвращает (картинку, полосы-строки для волны).
    Делается один раз на кадр спрайта — в кадре игры только рисуется."""
    w = sprite.get_width()
    h = max(2, min(sprite.get_height(), int(round(vaterliniya))))
    s = pygame.transform.flip(sprite.subsurface((0, 0, w, h)), False, True)
    if szhatie != 1.0:
        s = pygame.transform.smoothscale(s, (w, max(2, round(h * szhatie))))
    s.fill(OTRAZHENIE_CVET, special_flags=pygame.BLEND_RGB_MULT)
    vh = s.get_height()
    tayanie = pygame.Surface((1, vh), pygame.SRCALPHA)
    for y in range(vh):
        tayanie.set_at((0, y), (255, 255, 255, round(255 * (1 - 0.7 * y / vh))))
    s.blit(pygame.transform.scale(tayanie, (w, vh)), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return s, [pygame.Rect(0, y, w, 2) for y in range(0, vh, 2)]


def narisovat_otrazhenie(ekran, otr, x, y_vody, t, alfa=1.0, amplituda=2.0):
    """Полосы отражения сдвигаются лёгкой волной; дальше от ватерлинии — сильнее."""
    s, polosy = otr
    s.set_alpha(round(255 * OTRAZHENIE_ALFA * alfa))
    vh = s.get_height()
    for r in polosy:
        dx = amplituda * (0.3 + 0.7 * r.y / vh) * math.sin(t * 1.8 + r.y * 0.21)
        ekran.blit(s, (round(x + dx), y_vody + r.y), r)


def ten_na_vode(shirina, vysota, alfa=0.35, cvet=N.CVET_CHERNILA):
    """Мягкая тень-пятно под корпусом: эллипс, размытый уменьшением и увеличением."""
    s = pygame.Surface((shirina, vysota * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (*cvet, round(255 * alfa)), (shirina // 8, vysota // 2, shirina * 3 // 4, vysota))
    malo = pygame.transform.smoothscale(s, (max(1, shirina // 6), max(1, vysota // 3)))
    return pygame.transform.smoothscale(malo, (shirina, vysota * 2))


def drevko_vysotoj(res, fayl, vysota):
    """Древко нужной высоты из спрайта древка флажка: навершие (верхние 10 px) как есть,
    ствол растянут только по высоте. Нет файла — None."""
    if not res.est(fayl):
        res.log(("drevko", fayl), f"нет древка {fayl} — вымпел без древка")
        return None
    d = res.kartinka(fayl)
    w, h = d.get_size()
    verh = min(10, h - 2)
    s = pygame.Surface((w, vysota), pygame.SRCALPHA)
    s.blit(d, (0, 0), (0, 0, w, verh))
    s.blit(pygame.transform.smoothscale(d.subsurface((0, verh, w, h - verh)), (w, vysota - verh)), (0, verh))
    return s


class Kraska:
    """Белый слой, умноженный на цвет. Копия делается один раз на (кадр, цвет)."""

    def __init__(self):
        self.kesh = {}

    def __call__(self, surf, cvet):
        kl = (id(surf), cvet)
        s = self.kesh.get(kl)
        if s is None:
            if len(self.kesh) > 600:
                self.kesh.clear()
            s = surf.copy()
            s.fill(cvet, special_flags=pygame.BLEND_RGB_MULT)
            self.kesh[kl] = s
        return s


def _po_puti(put, s):
    """(x, y, масштаб) на доле s пути — сплайн Катмулла — Рома по точкам с равным шагом по воде."""
    n = len(put) - 1
    f = max(0.0, min(1.0, s)) * n
    i = min(int(f), n - 1)
    u = f - i
    p0, p1, p2, p3 = put[max(i - 1, 0)], put[i], put[i + 1], put[min(i + 2, n)]
    u2, u3 = u * u, u * u * u
    return tuple(0.5 * (2 * b + (c - a) * u + (2 * a - 5 * b + 4 * c - d) * u2 + (3 * b - a - 3 * c + d) * u3)
                 for a, b, c, d in zip(p0, p1, p2, p3))


class Hodok:
    """Фигурка ходит туда-обратно по ломаной и листает кадры шага."""
    SKOROST = 40
    KADROV_V_SEKUNDU = 10

    def __init__(self, kadry, put, cvet=None):
        self.kadry = kadry
        self.zerkalnye = [pygame.transform.flip(k, True, False) for k in kadry]
        self.put = [(float(p[0]), float(p[1])) for p in put] or [(640.0, 600.0)]
        if len(self.put) == 1:
            self.put.append(self.put[0])
        self.dliny = [math.dist(self.put[i], self.put[i + 1]) for i in range(len(self.put) - 1)]
        self.vsego = sum(self.dliny)
        self.s = random.uniform(0, self.vsego)
        self.napr = random.choice((1, -1))
        self.t = random.uniform(0, 1)
        self.x, self.y = self.put[0]
        self.vlevo = False
        self._polozhenie()

    def _polozhenie(self):
        ost = self.s
        for i, d in enumerate(self.dliny):
            if ost <= d or i == len(self.dliny) - 1:
                a, b = self.put[i], self.put[i + 1]
                u = 0.0 if d == 0 else min(1.0, ost / d)
                self.x = a[0] + (b[0] - a[0]) * u
                self.y = a[1] + (b[1] - a[1]) * u
                self.vlevo = (b[0] - a[0]) * self.napr < 0
                return
            ost -= d

    def obnovit(self, dt):
        self.t += dt
        if self.vsego <= 0:
            return
        self.s += self.napr * self.SKOROST * dt
        if self.s >= self.vsego:
            self.s, self.napr = self.vsego, -1
        elif self.s <= 0:
            self.s, self.napr = 0.0, 1
        self._polozhenie()

    def narisovat(self, ekran):
        if not self.kadry:
            return
        n = int(self.t * self.KADROV_V_SEKUNDU) % len(self.kadry)
        k = (self.zerkalnye if self.vlevo else self.kadry)[n]
        ekran.blit(k, (round(self.x - k.get_width() / 2), round(self.y - k.get_height())))


class Chajki:
    """Чайки-спрайты пролетают по небу пологими дугами раз в 6–15 с, машут крыльями и
    временами парят; дальние медленнее и мельче."""
    PAUZA = (6.0, 15.0)
    MASSHTABY = (0.6, 0.8, 1.0)
    NE_BOLSHE = 6

    def __init__(self, res, oblast=(0, 60, W, 190), opisanie=None, serye=False, srazu=2):
        self.oblast = pygame.Rect(oblast)
        self.serye = serye
        self.vidy = []
        for imya, o in (opisanie or CHAJKI).items():
            for m in self.MASSHTABY:
                kadry = res.kadry_hodoka(f"img/buhty/{imya}", m)
                if not kadry:
                    break
                vys = [k.get_bounding_rect().h for k in kadry]
                self.vidy.append({"kadry": kadry, "zerk": [pygame.transform.flip(k, True, False) for k in kadry],
                                  "fps": float(o.get("fps", 12)), "m": m,
                                  "opora": (o["opora"][0] * m, o["opora"][1] * m),
                                  "parit": vys.index(min(vys))})     # крылья ровно — кадр парения
        self._seraya = {}
        self.pticy = []
        self.do_sleduyushchej = random.uniform(1.5, 5.0)
        for _ in range(srazu if self.vidy else 0):
            self._novaya(random.uniform(0.15, 0.7))

    def _novaya(self, dolya=0.0):
        vid = random.choice(self.vidy)
        napr = random.choice((1, -1))
        o = self.oblast
        a, b = (o.left - 60, o.right + 60) if napr > 0 else (o.right + 60, o.left - 60)
        self.pticy.append({"vid": vid, "napr": napr, "a": a, "b": b,
                           "y0": random.uniform(o.top + 50, o.bottom),
                           "dyga": random.uniform(18, 50), "u": dolya,
                           "v": random.uniform(25, 40) * (0.55 + 0.45 * vid["m"]) / abs(b - a),
                           "t": random.uniform(0, 1), "faza": random.uniform(0, 6.3),
                           "mah": random.uniform(1.2, 3.0), "parit": 0.0})

    def obnovit(self, dt):
        if not self.vidy:
            return
        self.do_sleduyushchej -= dt
        if self.do_sleduyushchej <= 0:
            self.do_sleduyushchej = random.uniform(*self.PAUZA)
            if len(self.pticy) < self.NE_BOLSHE:
                self._novaya()
        for i in range(len(self.pticy) - 1, -1, -1):
            p = self.pticy[i]
            p["u"] += p["v"] * dt
            p["t"] += dt
            if p["parit"] > 0:
                p["parit"] -= dt
                if p["parit"] <= 0:
                    p["mah"] = random.uniform(1.2, 3.0)
            else:
                p["mah"] -= dt
                if p["mah"] <= 0:
                    p["parit"] = random.uniform(1.0, 2.6)
            if p["u"] >= 1.0:
                del self.pticy[i]

    def _seryj(self, k):
        s = self._seraya.get(id(k))
        if s is None:
            s = pygame.transform.grayscale(k)
            s.fill((196, 196, 202), special_flags=pygame.BLEND_RGB_MULT)
            self._seraya[id(k)] = s
        return s

    def narisovat(self, ekran):
        for p in self.pticy:
            vid, u = p["vid"], p["u"]
            x = p["a"] + (p["b"] - p["a"]) * u
            y = p["y0"] - p["dyga"] * math.sin(math.pi * u) + math.sin(p["t"] * 0.9 + p["faza"]) * 3
            n = vid["parit"] if p["parit"] > 0 else int(p["t"] * vid["fps"]) % len(vid["kadry"])
            k = (vid["kadry"] if p["napr"] > 0 else vid["zerk"])[n]
            if self.serye:
                k = self._seryj(k)
            ox, oy = vid["opora"]
            if p["napr"] < 0:
                ox = k.get_width() - ox
            ekran.blit(k, (round(x - ox), round(y - oy)))


class Bliki:
    """Солнечные блики на воде: мягкие вытянутые искры медленно вспыхивают и гаснут."""
    UROVNEJ = 8

    def __init__(self, oblast, n=22):
        self.oblast = pygame.Rect(oblast)
        self.urovni = urovni_sveta(svechenie(11, (150, 146, 128), 1.6, 0.3), self.UROVNEJ)
        self.tochki = [self._novaya(random.uniform(0, 6.28)) for _ in range(n)]

    def _novaya(self, faza=0.0):
        o = self.oblast
        return [random.uniform(o.left, o.right), random.uniform(o.top, o.bottom), faza,
                random.uniform(0.8, 1.6), random.uniform(0.6, 1.0)]

    def obnovit(self, dt):
        for i, t in enumerate(self.tochki):
            t[2] += t[3] * dt
            if t[2] > math.tau:
                self.tochki[i] = self._novaya()

    def narisovat(self, ekran):
        for x, y, f, _, m in self.tochki:
            i = min(self.UROVNEJ - 1, int(max(0.0, math.sin(f)) ** 2 * m * self.UROVNEJ) - 1)
            if i < 0:
                continue
            k = self.urovni[i]
            ekran.blit(k, (round(x - k.get_width() / 2), round(y - k.get_height() / 2)),
                       special_flags=pygame.BLEND_RGB_ADD)


class Tuman:
    """Два слоя тумана над дальней водой ползут по ветру с разной скоростью и медленно
    «дышат» плотностью; пятно за правым краем рисуется и слева, поэтому шва нет."""
    CVET = (238, 240, 242)
    SLOI = ((6.0, 0.115, 0.18, 11), (14.0, 0.099, 0.165, 9))   # px/с, ровная пелена, пик пятна, пятен
    DYHANIE = ((11.0, 0.0), (17.0, 2.1))                       # период «дыхания» слоя, с; фаза
    DYHANIE_MIN = 0.84                                          # множитель плотности на «выдохе»
    # плотность тумана в бою: гуще — вода вокруг доски противника светлеет и доска теряется
    PLOTNOST_BOYA = 0.87

    def __init__(self, polosa, plotnost=1.0):
        _, y, w, h = (int(v) for v in polosa)
        self.y, self.w = y, w
        rng = random.Random(7)
        profil = pygame.Surface((1, h), pygame.SRCALPHA)
        for i in range(h):
            profil.set_at((0, i), (255, 255, 255, round(255 * math.sin(math.pi * (i + 0.5) / h) ** 0.7)))
        profil = pygame.transform.scale(profil, (w, h))
        pyatno = pygame.Surface((128, 128), pygame.SRCALPHA)
        self.sloi = []
        for skorost, rovno, pik, n in self.SLOI:
            pyatno.fill((*self.CVET, 0))
            for r in range(64, 0, -1):
                a = (rovno + (pik - rovno) * (1 - r / 64) ** 1.2) * plotnost
                pygame.draw.circle(pyatno, (*self.CVET, round(255 * a)), (64, 64), r)
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            s.fill((*self.CVET, round(255 * rovno * plotnost)))
            for _ in range(n):
                bw, bh = rng.randint(260, 560), rng.randint(int(h * 0.5), h)
                b = pygame.transform.smoothscale(pyatno, (bw, bh))
                bx, by = rng.randint(0, w), rng.randint(0, max(0, h - bh))
                for dx in (0, -w):
                    s.blit(b, (bx + dx, by), special_flags=pygame.BLEND_RGBA_MAX)
            s.blit(profil, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.sloi.append([s, skorost, rng.uniform(0, w)])
        self.t = 0.0

    def obnovit(self, dt):
        self.t += dt
        for sl, (period, faza) in zip(self.sloi, self.DYHANIE):
            sl[2] = (sl[2] + sl[1] * dt) % self.w
            vdoh = 0.5 + 0.5 * math.sin(math.tau * self.t / period + faza)
            sl[0].set_alpha(round(255 * (self.DYHANIE_MIN + (1 - self.DYHANIE_MIN) * vdoh)))

    def narisovat(self, ekran):
        for s, _, sdvig in self.sloi:
            x = int(sdvig)
            ekran.blit(s, (x - self.w, self.y))
            ekran.blit(s, (x, self.y))


class LodkaUPrichala:
    """Лодка у причала качается циклом кадров; парус — белый слой цвета бухты."""

    def __init__(self, kadry, parusa, opora, tochka, fps):
        self.kadry, self.parusa, self.fps = kadry, parusa, fps
        self.pos = (round(tochka[0] - opora[0]), round(tochka[1] - opora[1]))
        self.vl = round(opora[1])                 # opora — середина лодки на ватерлинии
        self.t = random.uniform(0, 4)
        self._otr, self._otr_cvet = {}, None

    def _otrazhenie(self, n, kraska, cvet):
        if cvet != self._otr_cvet:                # перекраска бухты: 17 ступеней цвета
            self._otr, self._otr_cvet = {}, cvet
        o = self._otr.get(n)
        if o is None:
            s = self.kadry[n].copy()
            if self.parusa:
                s.blit(kraska(self.parusa[n % len(self.parusa)], cvet), (0, 0))
            o = self._otr[n] = otrazhenie(s, self.vl)
        return o

    def prigotovit(self, kraska, cvet):
        """Отражения всех кадров цикла для цвета — заранее, при создании бухты."""
        for n in range(len(self.kadry)):
            self._otrazhenie(n, kraska, cvet)

    def obnovit(self, dt):
        self.t += dt

    def narisovat(self, ekran, kraska, cvet):
        if not self.kadry:
            return
        n = int(self.t * self.fps) % len(self.kadry)
        narisovat_otrazhenie(ekran, self._otrazhenie(n, kraska, cvet), self.pos[0], self.pos[1] + self.vl, self.t)
        ekran.blit(self.kadry[n], self.pos)
        if self.parusa:
            ekran.blit(kraska(self.parusa[n % len(self.parusa)], cvet), self.pos)


class LodkaVMore:
    """Вторая лодка время от времени уходит из бухты по пути из zhivye.json и тает в дымке
    у горизонта; через 10–22 с — снова."""
    PROYAVLENIE, TAYANIE = 2.5, 3.5
    PAUZA = (10.0, 22.0)

    def __init__(self, kadry, parusa, opora, put, fps, dlit):
        self.kadry, self.parusa, self.opora, self.put, self.fps = kadry, parusa, opora, put, fps
        self.dlit = dlit * (1 - LODKA_HOD_S0)
        self.t = random.uniform(0, 4)
        if random.random() < 0.7:               # чаще всего игрок застаёт лодку в пути
            self.v_puti, self.pauza = random.uniform(0.15, 0.6) * self.dlit, 0.0
        else:
            self.v_puti, self.pauza = None, random.uniform(2.0, 8.0)
        self._m, self._kesh = None, {}

    def obnovit(self, dt):
        self.t += dt
        if self.v_puti is None:
            self.pauza -= dt
            if self.pauza <= 0:
                self.v_puti = 0.0
            return
        self.v_puti += dt
        if self.v_puti >= self.dlit:
            self.v_puti, self.pauza = None, random.uniform(*self.PAUZA)

    def narisovat(self, ekran, kraska, cvet):
        if self.v_puti is None or not self.kadry:
            return
        alfa = plavno(max(0.0, min(1.0, self.v_puti / self.PROYAVLENIE, (self.dlit - self.v_puti) / self.TAYANIE)))
        if alfa <= 0.01:
            return
        x, y, m = _po_puti(self.put, LODKA_HOD_S0 + (1 - LODKA_HOD_S0) * self.v_puti / self.dlit)
        mq = round(m * 200) / 200                     # шаг 0,5 %: кадр масштабируется раз на ступень
        if mq != self._m:
            self._m, self._kesh = mq, {}
        n = int(self.t * self.fps) % len(self.kadry)
        kl = (n, cvet)
        vl = round(self.opora[1] * mq)
        o = self._kesh.get(kl)
        if o is None:
            s = self.kadry[n].copy()
            if self.parusa:
                s.blit(kraska(self.parusa[n % len(self.parusa)], cvet), (0, 0))
            s = pygame.transform.smoothscale_by(s, mq)
            o = self._kesh[kl] = (s, otrazhenie(s, vl))
        s, otr = o
        x0, y0 = round(x - self.opora[0] * mq), round(y - self.opora[1] * mq)
        narisovat_otrazhenie(ekran, otr, x0, y0 + vl, self.t, alfa, amplituda=1.5)
        s.set_alpha(int(255 * alfa))
        ekran.blit(s, (x0, y0))


class Flazhki:
    """Флажки на древках: цикл кадров, у соседей фаза сдвинута на 3–5 кадров."""

    def __init__(self, res, opis):
        self.fps = float(opis.get("fps", 12))
        self.t = random.uniform(0, 2)
        d = opis.get("drevko") if isinstance(opis.get("drevko"), dict) else {}
        drevko0 = None
        if d.get("fayl") and res.est("img/buhty/" + d["fayl"]):
            drevko0 = res.kartinka("img/buhty/" + d["fayl"])
        else:
            res.log(("drevko", str(d.get("fayl"))), f"нет древка флажка {d.get('fayl')} — флажки без древка")
        dop, krepl = d.get("opora", (4.0, 55.8)), d.get("krepl_flazhka", (4.0, 7.8))
        fop = opis.get("opora", (1.8, 2.2))
        self.mesta = []
        faza = 0
        for mesto in opis.get("mesta", []):
            m = float(mesto.get("masshtab", 1.0))
            kadry = kadry_iz(res, opis.get("kadry"), m)
            if not kadry:
                continue
            tx, ty = mesto["tochka"]
            dx, dy = tx - dop[0] * m, ty - dop[1] * m                 # левый верх древка
            drevko = pygame.transform.smoothscale_by(drevko0, m) if drevko0 else None
            fx, fy = dx + (krepl[0] - fop[0]) * m, dy + (krepl[1] - fop[1]) * m
            self.mesta.append((drevko, (round(dx), round(dy)), kadry, (round(fx), round(fy)), faza))
            faza += random.randint(3, 5)

    def obnovit(self, dt):
        self.t += dt

    def narisovat(self, ekran, kraska, cvet):
        kadr = int(self.t * self.fps)
        for drevko, dpos, kadry, fpos, faza in self.mesta:
            if drevko is not None:
                ekran.blit(drevko, dpos)
            ekran.blit(kraska(kadry[(kadr + faza) % len(kadry)], cvet), fpos)


class Belyo:
    """Бельё на верёвке — цикл кадров; цветные вещи — маска, умноженная на цвет бухты."""

    def __init__(self, res, opis):
        self.kadry = kadry_iz(res, opis.get("kadry"))
        self.maski = kadry_iz(res, opis.get("maska"))
        ox, oy = opis.get("opora", (2.5, 6.6))
        kx, ky = opis.get("kuda", (896, 300))
        self.pos = (round(kx - ox), round(ky - oy))
        self.fps = float(opis.get("fps", 8))
        self.t = random.uniform(0, 3)

    def obnovit(self, dt):
        self.t += dt

    def narisovat(self, ekran, kraska, cvet):
        if not self.kadry:
            return
        n = int(self.t * self.fps) % len(self.kadry)
        ekran.blit(self.kadry[n], self.pos)
        if self.maski:
            ekran.blit(kraska(self.maski[n % len(self.maski)], cvet), self.pos)


class ZhivoyKlip:
    """Живая фигура из zhivye2.json (рыбак, матрос, женщина, чайка): цикл кадров на месте или
    проход по пути с проявлением на концах. Точки и время кадров — только из json."""
    PROYAVLENIE = 0.4        # с, появление и уход на концах пути
    PAUZA = (2.0, 5.0)       # с, между проходами по пути
    STUPENEJ = 48            # ступеней масштаба на единицу: готовые кадры в масштабе не плодятся без меры

    def __init__(self, kadry, opis, redkie=None, zvuk=None):
        self.kadry = kadry
        fps = max(0.1, float(opis.get("fps", 6)))
        derzhat = opis.get("derzhat_kadr") if isinstance(opis.get("derzhat_kadr"), dict) else {}
        self.konec_kadra = list(itertools.accumulate(float(derzhat.get(str(i + 1), 1.0 / fps))
                                                     for i in range(len(kadry))))
        self.cikl = self.konec_kadra[-1]
        self.t = random.uniform(0, self.cikl)
        self.n = 0
        op = opis.get("opora") or (0, 0)
        self.opora = (float(op[0]), float(op[1]))
        self.m0 = float(opis.get("masshtab", 1.0))
        self.x, self.y = float(opis["kuda"][0]), float(opis["kuda"][1])
        self.m = self.m0
        self.put = [tuple(map(float, p[:3])) for p in opis.get("put_u_v_masshtab") or () if len(p) >= 3]
        self.skorost = float(opis.get("skorost_px_s") or 0)
        self.dlina = sum(math.dist(a[:2], b[:2]) for a, b in zip(self.put, self.put[1:]))
        self.idet = len(self.put) >= 2 and self.skorost > 0 and self.dlina > 0
        self.s, self.pauza, self.alfa = 0.0, 0.0, 255
        self.v_masshtabe = {}                     # ступень * 1000 + кадр -> кадр в масштабе
        if self.idet:
            self.s = random.uniform(0.1, 0.9)
            self._na_puti()
        # редкий клип (свисток боцмана): раз в kazhdye_s секунд, с кадра покоя nachinat_s_kadra
        rk = opis.get("redkiy_klip") if isinstance(opis.get("redkiy_klip"), dict) else {}
        self.redkie, self.zvuk = redkie or [], zvuk       # звук играет бухта: она знает, слышно ли её
        kazhdye = rk.get("kazhdye_s") or (25, 45)
        self.r_kazhdye = (float(kazhdye[0]), float(kazhdye[-1]))
        self.r_start = min(max(0, int(rk.get("nachinat_s_kadra", 1)) - 1), len(kadry) - 1)
        self.r_shag = 1.0 / max(0.1, float(rk.get("fps", 8)))
        self.r_zvuk, self.r_zvuk_kadr = rk.get("zvuk"), int(rk.get("zvuk_na_kadre", 0)) - 1
        self.r_tajmer = random.uniform(*self.r_kazhdye)
        self.r_t, self.r_n = -1.0, -1                   # r_t < 0 — покой; иначе время внутри редкого клипа

    def _redkiy(self, dt):
        """Один проход редкого клипа со своим fps; на кадре zvuk_na_kadre — звук. Конец — снова
        покой с того же кадра. True — клип ещё идёт."""
        self.r_t += dt
        n = int(self.r_t / self.r_shag)
        if n >= len(self.redkie):
            self.r_t, self.r_tajmer = -1.0, random.uniform(*self.r_kazhdye)
            self.t = self.konec_kadra[self.r_start - 1] if self.r_start > 0 else 0.0
            return False
        if self.r_n < self.r_zvuk_kadr <= n and self.r_zvuk and self.zvuk:
            self.zvuk(self.r_zvuk)
        self.r_n = n
        return True

    def _na_puti(self):
        self.x, self.y, m = _po_puti(self.put, self.s)
        self.m = m * self.m0
        krai = min(self.s, 1.0 - self.s) * self.dlina / self.skorost      # секунд до ближнего конца пути
        self.alfa = round(255 * plavno(krai / self.PROYAVLENIE))

    def obnovit(self, dt):
        if self.r_t >= 0 and self._redkiy(dt):
            return
        self.t = (self.t + dt) % self.cikl
        self.n = min(bisect.bisect_right(self.konec_kadra, self.t), len(self.kadry) - 1)
        if self.redkie:
            self.r_tajmer -= dt
            if self.r_tajmer <= 0 and self.n == self.r_start:    # ждём кадр покоя, с которого клип начинается
                self.r_t, self.r_n = 0.0, -1
        if not self.idet:
            return
        if self.pauza > 0:
            self.pauza -= dt
            if self.pauza <= 0:
                self.s = 0.0
            return
        self.s += self.skorost * dt / self.dlina
        if self.s >= 1.0:
            self.s, self.pauza = 1.0, random.uniform(*self.PAUZA)
        self._na_puti()

    def narisovat(self, ekran):
        if self.alfa <= 0:
            return
        k, m = (self.redkie[max(0, self.r_n)] if self.r_t >= 0 else self.kadry[self.n]), self.m
        st = round(m * self.STUPENEJ)
        if st != self.STUPENEJ:                   # не в родном размере — готовый кадр своей ступени
            kl = st * 1000 + (500 + max(0, self.r_n) if self.r_t >= 0 else self.n)
            k2 = self.v_masshtabe.get(kl)
            if k2 is None:
                k2 = self.v_masshtabe[kl] = pygame.transform.smoothscale_by(k, st / self.STUPENEJ)
            k, m = k2, st / self.STUPENEJ
        if self.idet:
            k.set_alpha(self.alfa)                # 255, а не None: None снимает смешивание — чёрный квадрат вокруг
        ekran.blit(k, (round(self.x - self.opora[0] * m), round(self.y - self.opora[1] * m)))


class Buhta:
    def __init__(self, res, kapitan, cvet, s_lyudmi=True, v_boyu=False):
        papka = f"img/buhty/{kapitan.buhta}"
        self.res, self.papka_zvuka = res, f"buhty/{kapitan.buhta}"
        self.zvuk_vkl = False             # звук живых фигур — только когда сцена разрешит (BuhtaScena)
        zagl = lambda: risunki.zaglushka_fon("buhta")
        if s_lyudmi or not res.est(papka + "/fon_pustoy.jpg"):
            self.fon = res.kartinka(papka + "/fon.jpg", razmer=(W, H), alfa=False, zaglushka=zagl)
        else:
            self.fon = res.kartinka(papka + "/fon_pustoy.jpg", razmer=(W, H), alfa=False, zaglushka=zagl)
        r = res.json(papka + "/razmetka.json", RAZMETKA)
        self.r = {**RAZMETKA, **(r if isinstance(r, dict) else {})}
        self.s_lyudmi = s_lyudmi
        self.t = 0.0
        self.kraska = Kraska()
        self.bliki = Bliki(self.r["voda"])
        self.tuman = Tuman(self.r["tuman"])
        self.chajki = None
        self.hodoki, self.lodka, self.lodka_hod, self.belyo, self.flazhki = [], None, None, None, None
        if s_lyudmi:
            self._hodoki(res, papka)
            z = res.json(papka + "/zhivye.json", {})
            self._zhivye(res, z if isinstance(z, dict) else {})
            z2 = res.json(papka + "/zhivye2.json", {}) if res.est(papka + "/zhivye2.json") else {}
            self._zhivye2(res, z2 if isinstance(z2, dict) else {})
            self.chajki = Chajki(res)
        self.v_boyu = v_boyu
        if v_boyu:          # бой: медленный туман по всей бухте и редкие чайки над полями, всё под полями
            self.tuman = Tuman((0, 0, W, H - 40), plotnost=Tuman.PLOTNOST_BOYA)
            self.chajki = Chajki(res, (0, 6, W, 50), srazu=0)
            self.chajki.PAUZA = (8.0, 15.0)
        self._kapitan = (tuple(kapitan.cvet), tuple(getattr(kapitan, "cvet_buhty", ()) or kapitan.cvet))
        self.cvet = self._v_buhte(cvet)
        if self.lodka is not None:
            self.lodka.prigotovit(self.kraska, self.cvet)
        self._bylo = self._stalo = self.cvet
        self._perekraska = 1.0
        self._dlit = 2.0

    def _hodoki(self, res, papka):
        masshtab = float(self.r.get("masshtab_hodokov", 1.0))
        opisanie = res.json(papka + "/hodoki.json", {}) if res.est(papka + "/hodoki.json") else {}
        puti = self.r.get("puti") or {}
        imena = list(opisanie) if isinstance(opisanie, dict) and opisanie else list(puti)
        for imya in imena:
            put = puti.get(imya) or puti.get(imya.rstrip("0123456789"))   # prohozhiy1 -> путь prohozhiy
            if not put:
                res.log(("put", imya), f"нет пути для ходока {imya} в razmetka.json")
                continue
            pk = f"{papka}/hodok_{imya}"
            opis = opisanie.get(imya) if isinstance(opisanie, dict) else None
            opis = opis if isinstance(opis, dict) else {}
            m = masshtab
            if opis.get("rost_px"):              # рост фигурки по видимым пикселям, а не по листу
                vys = max((k.get_bounding_rect().height for k in res.kadry_hodoka(pk, 1.0)), default=0)
                if vys > 0:
                    m = float(opis["rost_px"]) / vys
            kadry = res.kadry_hodoka(pk, m)
            if not kadry:                        # людей кодом не рисуем: нет кадров — нет ходока
                continue
            h = Hodok(kadry, put)
            h.SKOROST = float(opis.get("skorost_px_s", h.SKOROST))
            h.KADROV_V_SEKUNDU = float(opis.get("fps", h.KADROV_V_SEKUNDU))
            self.hodoki.append(h)

    def _zhivye(self, res, z):
        o = z.get("lodka")
        if isinstance(o, dict) and o.get("kuda"):
            tochka = self.r.get("lodka_u_prichala") or (o["kuda"][0] + LODKA_SDVIG[0], o["kuda"][1] + LODKA_SDVIG[1])
            self.lodka = LodkaUPrichala(kadry_iz(res, o.get("kadry")), kadry_iz(res, o.get("parus")),
                                        o.get("opora", (0, 0)), tochka, float(o.get("fps", 8)))
        o = z.get("lodka_hod")
        if isinstance(o, dict) and len(o.get("put_u_v_masshtab") or ()) >= 2:
            self.lodka_hod = LodkaVMore(kadry_iz(res, o.get("kadry")), kadry_iz(res, o.get("parus")),
                                        o.get("opora", (0, 0)), [tuple(map(float, p)) for p in o["put_u_v_masshtab"]],
                                        float(o.get("fps", 8)), float(o.get("dlitelnost_s", 28.0)))
        if isinstance(z.get("flazhok"), dict):
            self.flazhki = Flazhki(res, z["flazhok"])
        if isinstance(z.get("bele"), dict):
            self.belyo = Belyo(res, z["bele"])

    def _zhivye2(self, res, z):
        """Рыбак, матрос, женщина и чайка из zhivye2.json — в общий список с ходоками:
        все рисуются по высоте опоры, дальние раньше."""
        for imya, opis in z.items():
            if imya.startswith("_") or not isinstance(opis, dict) or len(opis.get("kuda") or ()) < 2:
                continue
            kadry = kadry_iz(res, opis.get("kadry"))
            rk = opis.get("redkiy_klip")
            redkie = kadry_iz(res, rk.get("kadry")) if isinstance(rk, dict) else []
            if isinstance(rk, dict) and not redkie:
                res.log(("zhivye2", imya, "redkiy"), f"zhivye2.json: нет кадров редкого клипа {rk.get('kadry')} для {imya}")
            if kadry:
                self.hodoki.append(ZhivoyKlip(kadry, opis, redkie, self._zvuk))
            else:
                res.log(("zhivye2", imya), f"zhivye2.json: нет кадров {opis.get('kadry')} для {imya}")

    def _zvuk(self, imya):
        """Звук живой фигуры (snd/buhty/<бухта>/<imya>) — только когда бухта на экране сама."""
        if self.zvuk_vkl:
            self.res.igrat(f"{self.papka_zvuka}/{imya}")

    def _v_buhte(self, cvet):
        """Краска бухты приглушена (насыщенность не выше 0,45); на карте и в бою — нет."""
        cvet = tuple(cvet)
        if cvet == tuple(N.CVET_IGROKA):
            return N.CVET_IGROKA_BUHTA
        if cvet == self._kapitan[0]:
            return self._kapitan[1]
        return cvet

    def perekrasit(self, cvet, dlit=2.2):
        self._bylo, self._stalo = self.cvet, self._v_buhte(cvet)
        self._perekraska, self._dlit = 0.0, dlit

    def obnovit(self, dt):
        self.t += dt
        self.bliki.obnovit(dt)
        self.tuman.obnovit(dt)
        if self.v_boyu:
            self.chajki.obnovit(dt)
        if not self.s_lyudmi:
            return
        self.chajki.obnovit(dt)
        for h in self.hodoki:
            h.obnovit(dt)
        for vesh in (self.lodka, self.lodka_hod, self.belyo, self.flazhki):
            if vesh is not None:
                vesh.obnovit(dt)
        if self._perekraska < 1.0:
            self._perekraska = min(1.0, self._perekraska + dt / self._dlit)
            u = round(plavno(self._perekraska) * 16) / 16      # 17 ступеней: окрашенные кадры не плодятся
            self.cvet = tuple(int(round(v)) for v in smeshat(self._bylo, self._stalo, u))

    def narisovat(self, ekran):
        ekran.blit(self.fon, (0, 0))
        if not self.v_boyu:                 # в бою туман рисует narisovat_za_polyami — поверх пелены
            self.tuman.narisovat(ekran)
        self.bliki.narisovat(ekran)
        if not self.s_lyudmi:
            return
        k, c = self.kraska, self.cvet
        for vesh in (self.flazhki, self.belyo, self.lodka_hod, self.lodka):   # от дальнего к ближнему
            if vesh is not None:
                vesh.narisovat(ekran, k, c)
        self.hodoki.sort(key=PO_Y)
        for h in self.hodoki:
            h.narisovat(ekran)
        self.chajki.narisovat(ekran)

    def narisovat_za_polyami(self, ekran):
        """Бой: туман и чайки поверх приглушённой бухты, но под полями (сцена зовёт после пелены)."""
        if self.v_boyu:
            self.tuman.narisovat(ekran)
            self.chajki.narisovat(ekran)
