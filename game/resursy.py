"""Картинки, звуки, шрифты и строки — с заглушками вместо недостающего.

Нет файла — игра не падает: рисует заглушку кодом и один раз пишет строку в журнал
(zhurnal.log и консоль).
"""
import copy
import json
import os
import random

import pygame

from game import nastroyki as N
from game import risunki

DLINA = {imya: dlina for imya, dlina, _ in N.FLOT}


def vpisat_korabl(s, dl, kletka):
    """Видимый корпус — во всю клетку: длина 92 % клеток корабля, высота не больше 62 % клетки,
    под ним мягкая чернильная тень — иначе мелкий корпус сливается со светлой водой."""
    r = s.get_bounding_rect(min_alpha=8)
    if r.w < 4 or r.h < 2:
        return s
    k = min(dl * kletka * 0.92 / r.w, kletka * 0.62 / r.h)
    vid = pygame.transform.smoothscale(s.subsurface(r), (max(1, round(r.w * k)), max(1, round(r.h * k))))
    kraj = 6
    ten = pygame.Surface((vid.get_width() + 2 * kraj, vid.get_height() + 2 * kraj), pygame.SRCALPHA)
    ten.blit(vid, (kraj, kraj))
    ten.fill((*N.CVET_CHERNILA, 255), special_flags=pygame.BLEND_RGBA_MIN)     # силуэт чернилами
    ten.fill((255, 255, 255, 170), special_flags=pygame.BLEND_RGBA_MULT)
    try:
        ten = pygame.transform.gaussian_blur(ten, 2)
    except (AttributeError, ValueError, pygame.error):
        pass
    itog = pygame.Surface((dl * kletka, kletka), pygame.SRCALPHA)
    c = itog.get_rect().center
    itog.blit(ten, ten.get_rect(center=(c[0] + 1, c[1] + 2)))
    itog.blit(vid, vid.get_rect(center=c))
    return itog


# Тон корпуса на воде: множитель яркости корпуса и альфа тёмной кромки под ним.
# Подлодку темним сильнее — иначе она сливается с водой; рисунок спрайта сохраняется.
TON_KORABLYA = {"podlodka": 0.65}                 # остальные — только кромка
KROMKA_KORABLYA = {"podlodka": 120, "esminec": 120, "linkor": 120}


def ottenit_korabl(s, ton, kromka):
    """Корпус темнее в ton раз, под ним мягкая тёмная кромка (#1B1E27) со сдвигом (1, 2) — свет слева сверху."""
    if ton >= 1.0 and not kromka:
        return s
    s = s.copy()
    if ton < 1.0:
        k = round(255 * ton)
        s.fill((k, k, k), special_flags=pygame.BLEND_RGB_MULT)
    if kromka:
        w, h = s.get_size()
        ten = pygame.mask.from_surface(s, 96).to_surface(setcolor=(27, 30, 39, kromka), unsetcolor=(27, 30, 39, 0))
        ten = pygame.transform.smoothscale(pygame.transform.smoothscale(ten, (max(1, w // 3), max(1, h // 3))), (w, h))
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        out.blit(ten, (1, 2))
        out.blit(s, (0, 0))
        s = out
    return s


class Resursy:
    def __init__(self):
        self._kartinki = {}
        self._zvuki = {}
        self._shrifty = {}
        self._tekst = {}
        self._tusk = {}
        self._poslednij = {}          # последний вариант звука — без повтора подряд
        self.zalogirovano = set()
        self.nedostayushchie_stroki = set()
        self.gromkost = 0.8
        self.gromkost_fona = 1.0
        self.pri_glavnom = None       # микшер фона: зовётся при каждом главном звуке
        self.stroki = self.json("data/stroki.json", {})
        self.stroki.update(self.json("data/stroki_flot.json", {}))   # строки флота — поверх общих

    # --- общее ---
    def put(self, otn):
        return os.path.join(N.KOREN, *otn.split("/"))

    def est(self, otn):
        return bool(otn) and os.path.isfile(self.put(otn))

    def log(self, klyuch, tekst):
        """Одна строка в журнал на одну пропажу."""
        if klyuch in self.zalogirovano:
            return
        self.zalogirovano.add(klyuch)
        print("[resursy] " + tekst)
        try:
            with open(N.FAJL_ZHURNALA, "a", encoding="utf-8") as f:
                f.write(tekst + "\n")
        except OSError:
            pass

    def json(self, otn, po_umolchaniyu):
        if not self.est(otn):
            self.log(("json", otn), f"нет файла {otn} — беру значения по умолчанию")
            return copy.deepcopy(po_umolchaniyu)
        try:
            with open(self.put(otn), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            self.log(("json", otn), f"файл {otn} не прочитан ({e}) — беру значения по умолчанию")
            return copy.deepcopy(po_umolchaniyu)

    def s(self, klyuch, **zn):
        """Строка интерфейса из data/stroki.json."""
        t = self.stroki.get(klyuch)
        if t is None:
            self.nedostayushchie_stroki.add(klyuch)
            self.log(("s", klyuch), f"нет строки «{klyuch}» в data/stroki.json")
            return klyuch
        return t.format(**zn) if zn else t

    # --- картинки ---
    def kartinka(self, otn, razmer=None, vysota=None, zaglushka=None, alfa=True):
        kl = (otn, razmer, vysota, alfa)
        surf = self._kartinki.get(kl)
        if surf is not None:
            return surf
        if self.est(otn):
            try:
                surf = pygame.image.load(self.put(otn))
                surf = surf.convert_alpha() if alfa else surf.convert()
            except pygame.error as e:
                self.log(otn, f"картинка {otn} не читается ({e}) — рисую заглушку")
                surf = None
        else:
            self.log(otn, f"нет файла {otn} — рисую заглушку")
        if surf is None:
            surf = zaglushka() if zaglushka else risunki.zaglushka_prostaya(razmer or (256, 256), otn)
        if razmer and surf.get_size() != tuple(razmer):
            surf = pygame.transform.smoothscale(surf, razmer)
        elif vysota and surf.get_height() != vysota:
            w = max(1, round(surf.get_width() * vysota / surf.get_height()))
            surf = pygame.transform.smoothscale(surf, (w, vysota))
        self._kartinki[kl] = surf
        return surf

    def korabl(self, imya, skin, razbit, kletka, gorizont=True):
        """Спрайт корабля под клетку: нос вправо, вертикальный — повёрнут."""
        kl = ("korabl", imya, skin, razbit, kletka, gorizont)
        s = self._kartinki.get(kl)
        if s is None:
            dl = DLINA[imya]
            otn = f"img/korabli/{imya}_{'razbit' if razbit else skin}.png"
            s = self.kartinka(otn, razmer=(dl * kletka, kletka),
                              zaglushka=lambda: risunki.zaglushka_korabl(imya, dl, skin, razbit))
            s = vpisat_korabl(s, dl, kletka)
            s = ottenit_korabl(s, TON_KORABLYA.get(imya, 1.0), KROMKA_KORABLYA.get(imya, 0))
            if not gorizont:
                s = pygame.transform.rotate(s, -90)
            self._kartinki[kl] = s
        return s

    def portret(self, otn, kto, emociya, vysota, cvet):
        return self.kartinka(otn, vysota=vysota,
                             zaglushka=lambda: risunki.zaglushka_portret(kto, emociya, cvet))

    def pritushit(self, surf):
        """Притушенная копия — слушающий в разговоре. Ключ — id, но рядом лежит
        сам оригинал: пока он в кэше, его id не достанется другой картинке.
        Кэш не больше 256 копий — лишние вытесняются с самой старой."""
        zap = self._tusk.get(id(surf))
        if zap is not None and zap[0] is surf:
            return zap[1]
        s = surf.copy()
        s.fill((150, 150, 158), special_flags=pygame.BLEND_RGB_MULT)
        if len(self._tusk) >= 256:
            self._tusk.pop(next(iter(self._tusk)))
        self._tusk[id(surf)] = (surf, s)
        return s

    def fajly_papki(self, papka, rassh=(".png", ".jpg")):
        p = self.put(papka)
        if not os.path.isdir(p):
            self.log(papka, f"нет папки {papka} — рисую заглушку")
            return []
        return [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.lower().endswith(rassh)]

    def kadry_hodoka(self, papka, masshtab=1.0):
        kl = ("hodok", papka, masshtab)
        if kl not in self._kartinki:
            kadry = []
            for f in self.fajly_papki(papka, (".png",)):
                try:
                    k = pygame.image.load(f).convert_alpha()
                    if masshtab != 1.0:
                        k = pygame.transform.smoothscale_by(k, masshtab)
                    kadry.append(k)
                except pygame.error as e:
                    self.log(f, f"кадр {f} не читается ({e})")
            self._kartinki[kl] = kadry
        return self._kartinki[kl]

    # --- шрифты и текст ---
    def shrift(self, razmer, zhirnyj=True):
        kl = (razmer, zhirnyj)
        f = self._shrifty.get(kl)
        if f is None:
            if zhirnyj and razmer >= N.SHRIFT_LOGO:
                otn = "fonts/Nunito-ExtraBold.ttf"      # название игры, «VS», итог боя
            else:
                otn = "fonts/Nunito-Bold.ttf" if zhirnyj else "fonts/Nunito-Regular.ttf"
            try:
                f = pygame.font.Font(self.put(otn), max(8, round(razmer * N.MASHTAB_SHRIFTA)))
            except (OSError, pygame.error):
                self.log(otn, f"нет шрифта {otn} — беру встроенный")
                f = pygame.font.Font(None, int(razmer * 1.3))
            self._shrifty[kl] = f
        return f

    def tekst(self, stroka, razmer, cvet, zhirnyj=True):
        kl = (stroka, razmer, cvet, zhirnyj)
        s = self._tekst.get(kl)
        if s is None:
            if len(self._tekst) > 1500:
                self._tekst.clear()
            s = self.shrift(razmer, zhirnyj).render(stroka, True, cvet)
            self._tekst[kl] = s
        return s

    # --- звук ---
    def zvuk_fajl(self, otn):
        if otn in self._zvuki:
            return self._zvuki[otn]
        z = None
        if pygame.mixer.get_init():
            if self.est(otn):
                try:
                    z = pygame.mixer.Sound(self.put(otn))
                except pygame.error as e:
                    self.log(otn, f"звук {otn} не читается ({e})")
            else:
                self.log(otn, f"нет звука {otn} — тишина")
        self._zvuki[otn] = z
        return z

    def zvuk(self, imya):
        """Звук snd/<imya>.wav, иначе .ogg."""
        otn = f"snd/{imya}.wav"
        if not self.est(otn) and self.est(f"snd/{imya}.ogg"):
            otn = f"snd/{imya}.ogg"
        return self.zvuk_fajl(otn)

    def igrat(self, imya, variantov=0, uroven="effekty"):
        """Звук главного яруса; variantov — случайный из _1.._n без повтора подряд."""
        if imya in ("knopka", "monety", "kartochka") and uroven == "effekty":
            uroven = "interfejs"          # фон под интерфейсом приседает меньше
        if variantov:
            nomera = [n for n in range(1, variantov + 1) if n != self._poslednij.get(imya)]
            n = random.choice(nomera)
            self._poslednij[imya] = n
            imya = f"{imya}_{n}"
        z = self.zvuk(imya)
        if z is None:
            return
        z.set_volume(self.gromkost * N.UROVNI.get(uroven, 1.0))
        z.play()
        if self.pri_glavnom is not None:
            self.pri_glavnom(z.get_length(), uroven)
