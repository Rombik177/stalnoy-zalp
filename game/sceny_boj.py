"""Бой красками и всё вокруг него: расстановка флота, сам бой, итог и
фаталити-ролик. Правила — game/pole.py, здесь только показ и ввод."""
import io
import math
import os
import random

import pygame

from game import taktika
from game import nastroyki as N
from game import pole as P
from game import effekty as E
from game import risunki
from game.buhta import Buhta
from game.sceny_syuzhet import (Pelena, Karta, Razgovor, BuhtaScena, cvet_buhty, portret_kapitana,
                                klik, klavisha, dalshe_li, plashka_s_tekstom)
from game.ui import Scena, Knopka, plashka, ten_plashki, tekst, puzyr, vyezd, smeshat, plavno, pruzhina

W, H = N.SHIRINA, N.VYSOTA
from game.ui import tekst_na_podlozhke, podlozhka  # noqa: E402

CH = N.CVET_CHERNILA
SV = N.CVET_SVETLYJ
MEL, KRUP = N.SHRIFT_MELKIJ, N.SHRIFT_KRUPNYJ
KL = N.KLETKA
R = N.RAZMER_POLYA
STORONA = KL * R
OSI = N.SHRIFT_OSI
CVET_OSI = (206, 212, 214)          # буквы и цифры осей — бледные, без тени
CVET_SETKI_SVET = (235, 242, 246)   # светлая сетка поверх тёмной
CVET_SETKI = (40, 74, 96)           # сетка — тонко, тёмно-синим по светлой воде
SVET_VODY = (214, 232, 240)         # мягкий светлый слой поверх воды поля
TOCHKA_PUSTO = (206, 220, 226)      # белая точка «пусто»: заметно светлее воды
SERYJ = (150, 144, 136)             # недоступная надпись
SERYJ_TEKST = (96, 96, 104)
CIFRY = tuple(str(i + 1) for i in range(R))

_setka = None
_voda = None


def setka():
    """Тонкая спокойная сетка поля — одна на игру; кромку даёт бумажная рамка."""
    global _setka
    if _setka is None:
        _setka = pygame.Surface((STORONA + 1, STORONA + 1), pygame.SRCALPHA)
        for i in range(1, R):
            pygame.draw.line(_setka, (*CVET_SETKI, 46), (i * KL, 0), (i * KL, STORONA))
            pygame.draw.line(_setka, (*CVET_SETKI, 46), (0, i * KL), (STORONA, i * KL))
        for i in range(1, R):
            pygame.draw.line(_setka, (*CVET_SETKI_SVET, 80), (i * KL, 0), (i * KL, STORONA))
            pygame.draw.line(_setka, (*CVET_SETKI_SVET, 80), (0, i * KL), (STORONA, i * KL))
    return _setka


CVET_BUKV_OSI = (0x1B, 0x1E, 0x27)   # буквы А–К над полем: чернила, 70 % — читаются на картинке бухты
ALFA_BUKV_OSI = 178
_znaki_osi = {}


def znak_osi(res, st):
    """Буква оси: тёмная, 70 % непрозрачности; рисуется один раз на букву."""
    s = _znaki_osi.get(st)
    if s is None:
        s = res.tekst(st, OSI, CVET_BUKV_OSI, False).copy()
        s.set_alpha(ALFA_BUKV_OSI)
        _znaki_osi[st] = s
    return s


def blok_strok(res, stroki, razmer, cvet):
    """Несколько мелких строк одной картинкой, обрезанной по буквам (общая полоса
    по высоте, чтобы строки стояли ровно): подсказка в тесном месте. Один раз, не в кадре."""
    shr = [res.tekst(st, razmer, cvet, False) for st in stroki]
    ramki = [s.get_bounding_rect() for s in shr]
    verh, niz = min(r.top for r in ramki), max(r.bottom for r in ramki)
    h = niz - verh
    shir = max(s.get_width() for s in shr)
    blok = pygame.Surface((shir, len(shr) * h + (len(shr) - 1)), pygame.SRCALPHA)
    for i, s in enumerate(shr):
        blok.blit(s, ((shir - s.get_width()) // 2, i * (h + 1)), (0, verh, s.get_width(), h))
    return blok


def doska(ekran, res, voda, x0, y0, zagolovok, cifry_sprava=False):
    """Поле: тонкая бумажная кромка, светлая вода, тонкая сетка, мелкие бледные
    буквы и цифры; заголовок — у внешнего края поля."""
    ramka = pygame.Rect(x0 - 6, y0 - 6, STORONA + 12, STORONA + 12)
    ten_plashki(ekran, ramka, radius=10, alfa=56)
    plashka(ekran, ramka, N.CVET_BUMAGA, 255, True, 10)
    ekran.blit(voda, (x0, y0))
    ekran.blit(setka(), (x0, y0))
    for i in range(R):
        b = znak_osi(res, N.BUKVY[i])
        ekran.blit(b, b.get_rect(midbottom=(x0 + i * KL + KL // 2, y0 - 10)))
        if cifry_sprava:
            tekst(ekran, res, CIFRY[i], OSI, (x0 + STORONA + 12, y0 + i * KL + KL // 2), CVET_OSI, "midleft",
                  zhirnyj=False)
        else:
            tekst(ekran, res, CIFRY[i], OSI, (x0 - 12, y0 + i * KL + KL // 2), CVET_OSI, "midright",
                  zhirnyj=False)
    if cifry_sprava:
        tekst_na_podlozhke(ekran, res, zagolovok, MEL, (x0 + STORONA + 6, y0 - 42), SV, "bottomright")
    else:
        tekst_na_podlozhke(ekran, res, zagolovok, MEL, (x0 - 6, y0 - 42), SV, "bottomleft")


def kvadratik(cvet, alfa):
    s = pygame.Surface((KL - 6, KL - 6), pygame.SRCALPHA)
    pygame.draw.rect(s, (*cvet, alfa), s.get_rect(), border_radius=8)
    return s


def plashka_korablya(dlina, kl, vys, cvet):
    """Плашка корабля для схемы «сколько осталось»: dlina клеток по kl px, черта между клетками."""
    s = pygame.Surface((dlina * kl - 1, vys), pygame.SRCALPHA)
    temn = (cvet[0] // 2, cvet[1] // 2, cvet[2] // 2)
    pygame.draw.rect(s, cvet, s.get_rect(), border_radius=3)
    pygame.draw.rect(s, temn, s.get_rect(), 1, border_radius=3)
    for i in range(1, dlina):
        pygame.draw.line(s, temn, (i * kl - 1, 1), (i * kl - 1, vys - 2))
    return s


def voda_polya(res):
    """Вода поля: voda_pole.jpg под мягким светлым слоем, чтобы корабли и
    кляксы читались. Готовится один раз на игру."""
    global _voda
    if _voda is None:
        baza = res.kartinka("img/fon/voda_pole.jpg", razmer=(STORONA, STORONA), alfa=False,
                            zaglushka=lambda: risunki.zaglushka_fon("voda", (STORONA, STORONA)))
        _voda = baza.copy()
        sloj = pygame.Surface(_voda.get_size())
        sloj.fill(SVET_VODY)
        sloj.set_alpha(104)
        _voda.blit(sloj, (0, 0))
    return _voda


def znachok_miny(res, razmer=32):
    return res.kartinka("img/znachki/mina.png", razmer=(razmer, razmer),
                        zaglushka=lambda: risunki.zaglushka_znachok("mina", (razmer, razmer)))


# --- расстановка ---

DA = (112, 164, 112)                # рамка «встанет»
NELZYA = (196, 108, 96)             # рамка «так нельзя»


def ustanovit_kursor(nelzya):
    """Системный курсор «нельзя» над стрелянной клеткой, иначе обычная стрелка."""
    try:
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_NO if nelzya else pygame.SYSTEM_CURSOR_ARROW)
    except pygame.error:
        pass


class Rasstanovka(Scena):
    """Десять кораблей мышью (щелчок, ПКМ или R — поворот вокруг клетки под мышью), две мины
    щелчком по воде. Причал справа: строка на класс, спрайт каждого корабля и
    счётчик «осталось поставить». Где стоит корабль — знает только self.razm."""
    DOK_KL = 40                       # клетка спрайтов на причале (на поле — KL)
    VSPYSHKA = 0.7                    # сколько горит красная рамка «так нельзя»

    GLUHOTA = 0.3            # с: двойной щелчок по карточке пари не ставит мину
    DVOJNOJ_MS = 400         # окно двойного щелчка и «щелчок сразу после переноса — не мина»
    SDVIG_PERENOSA = 4       # px: сдвиг больше — это перенос, а не щелчок

    def __init__(self, app, kap, pari):
        super().__init__(app)
        self.kap, self.pari = kap, pari
        self.buhta = Buhta(self.res, kap, cvet_buhty(app, kap), s_lyudmi=False)
        self.pelena = Pelena(96)
        self.voda = voda_polya(self.res)
        self.mina = znachok_miny(self.res)
        self.skin = app.progress.skin
        self.x0, self.y0 = 64, 144                   # поле расстановки — крупно, слева
        self.razm = {imya: None for imya, _ in N.SOSTAV}      # id корабля -> (x, y, gorizont) или None
        self.gor = {imya: True for imya, _ in N.SOSTAV}
        self.klassa = {kl: [imya for imya, k in N.SOSTAV if k == kl] for kl, _, _ in N.FLOT}
        self.miny = []
        self.taschim, self.zahvat, self.otkuda = None, 0, None
        self.mina_v_ruke = False                       # мину тащат с причала
        self._prizrak_min = (None, False)
        self._prizrak_kl, self._prizrak_ok, self._prizrak_kletki = None, False, []
        self.nelzya, self.t_nelzya = [], 0.0
        self.soobshchenie, self.t_soobshcheniya = "", 0.0
        self.panel = pygame.Rect(632, 144, 584, 432)
        dk = self.DOK_KL
        self.dok = {}                                  # класс -> рамки спрайтов его кораблей на причале
        for i, (kl, dl, _) in enumerate(N.FLOT):
            self.dok[kl] = [pygame.Rect(self.panel.x + 24 + j * (dl * dk + 8), self.panel.y + 32 + i * 96,
                                        dl * dk, dk) for j in range(N.SKOLKO[kl])]
        self.kn_sluchajno = Knopka((632, 600, 240, 64), self.res.s("rasst_sluchajno"))
        self.kn_dalshe = Knopka((888, 600, 328, 64), self.res.s("rasst_k_pokraske"), razmer=KRUP)
        self.rng = random.Random()
        # надписи — один раз, не в кадре
        res = self.res
        self.dok_tekst_x = max(r[-1].right for r in self.dok.values()) + 24
        self.podpisi = {kl: res.s(f"korabl_{kl}") for kl, _, _ in N.FLOT}   # только имя: умения объяснит бой
        self.st_ostalos = [res.s("rasst_vse_na_vode")] + [res.s("rasst_ostalos", n=n)
                                                         for n in range(1, max(N.SKOLKO.values()) + 1)]
        self.st_miny = [res.s("rasst_miny", n=n) for n in range(N.MIN_NA_POLE + 1)]
        self.shir_min = [res.shrift(MEL).size(st)[0] for st in self.st_miny]
        self.st_stroka = res.s("rasst_odna_stroka")            # одна строка сверху
        self.st_na_prichale = [res.s("rasst_na_prichale", n=n, iz=len(N.SOSTAV)) for n in range(len(N.SOSTAV) + 1)]
        self.st_flot = res.s("boj_tvoj_flot")
        self.st_nelzya, self.st_min_hvatit = res.s("rasst_nelzya"), res.s("rasst_min_hvatit")
        self.mina_tusk = res.pritushit(self.mina)
        x_min = self.panel.x + 24 + max(self.shir_min) + 16
        self.dok_min = [pygame.Rect(x_min + j * 44, self.panel.bottom - 60, 40, 40) for j in range(N.MIN_NA_POLE)]
        self.kv_da, self.kv_nelzya = kvadratik(DA, 120), kvadratik(NELZYA, 120)   # заливка «встанет» / «нельзя»
        self._klik_t, self._klik_kl = -1000, None      # прошлый щелчок по полю — для двойного
        self._klik_pos, self._t_polozhil = (0, 0), -10 ** 6
        self._t_povorot, self._povorot_imya = -10 ** 6, None   # прошлый поворот щелчком — чтобы двойной не крутил назад
        app.fon_buhty(kap.buhta)

    def kletka_pod(self, pos):
        x, y = (pos[0] - self.x0) // KL, (pos[1] - self.y0) // KL
        return (x, y) if P.v_pole(x, y) else None

    def _korabl_v(self, kl):
        for imya, p in self.razm.items():
            if p and kl in P.kletki_korablya(p[0], p[1], P.DLINA[imya], p[2]):
                return imya
        return None

    def _mozhno(self, imya, x, y, g):
        zanyato = set()
        for drugoj, p in self.razm.items():
            if p and drugoj != imya:
                zanyato.update(P.kletki_korablya(p[0], p[1], P.DLINA[drugoj], p[2]))
        kl = P.kletki_korablya(x, y, P.DLINA[imya], g)
        return P.mozhno_postavit(kl, zanyato) and not any(c in self.miny for c in kl)

    def _yakor(self, pos):
        kl = self.kletka_pod(pos)
        if kl is None:
            return None
        if self.gor[self.taschim]:
            return kl[0] - self.zahvat, kl[1]
        return kl[0], kl[1] - self.zahvat

    def ostalos(self, klass):
        """Сколько кораблей класса ещё у причала (тот, что в руке, уже не там)."""
        return sum(1 for imya in self.klassa[klass] if self.razm[imya] is None and imya != self.taschim)

    def gotovo(self):
        return (self.taschim is None and not self.mina_v_ruke and all(self.razm.values())
                and len(self.miny) == N.MIN_NA_POLE)

    def _sluchajno(self):
        r = P.sluchajnaya_rasstanovka(self.rng)
        for imya, x, y, g in r:
            self.razm[imya] = (x, y, g)
            self.gor[imya] = g
        self.miny = [tuple(m) for m in P.sluchajnye_miny(self.rng, r)]
        self.taschim, self.t_nelzya, self.mina_v_ruke = None, 0.0, False

    def _k_pokraske(self):
        if not self.gotovo():
            return
        self.app.zvuk("knopka")
        rasst = [(imya, p[0], p[1], p[2]) for imya, p in self.razm.items()]
        self.app.perejti(BojScena(self.app, self.kap, self.pari, rasst, list(self.miny)))

    def _skazat(self, st):
        self.soobshchenie, self.t_soobshcheniya = st, 2.4

    def _ne_vyshlo(self, kletki):
        """Красная рамка на 0,7 с там, куда корабль не встал, и почему."""
        self.nelzya = [c for c in kletki if P.v_pole(*c)]
        self.t_nelzya = self.VSPYSHKA
        self._skazat(self.st_nelzya)

    def _v_ruku(self, imya, otkuda, zahvat):
        self.taschim, self.otkuda, self.zahvat = imya, otkuda, zahvat
        self._prizrak_kl = None
        if otkuda:
            self.razm[imya] = None

    def _polozhit(self, pos):
        """Отпустить корабль: встал по правилам — на воду, иначе — туда, откуда взяли."""
        imya = self.taschim
        g = self.gor[imya]
        ya = self._yakor(pos)
        if ya and self._mozhno(imya, ya[0], ya[1], g):
            self.razm[imya] = (ya[0], ya[1], g)
            self.app.zvuk("knopka")
        else:
            if ya:
                self._ne_vyshlo(P.kletki_korablya(ya[0], ya[1], P.DLINA[imya], g))
            if self.otkuda:
                self.razm[imya] = self.otkuda
                self.gor[imya] = self.otkuda[2]
        self.taschim = None

    def _otmenit(self):
        """Корабль или мина из руки — обратно (Esc, окно потеряло фокус)."""
        if self.taschim and self.otkuda:
            self.razm[self.taschim] = self.otkuda
            self.gor[self.taschim] = self.otkuda[2]
        self.taschim = None
        self.mina_v_ruke = False

    def _mina_mozhno(self, kl):
        return (kl is not None and kl not in self.miny and self._korabl_v(kl) is None
                and len(self.miny) < N.MIN_NA_POLE)

    def _polozhit_minu(self, pos):
        """Отпустить мину: на пустую клетку — встала, мимо поля — обратно на причал."""
        kl = self.kletka_pod(pos)
        self.mina_v_ruke = False
        if self._mina_mozhno(kl):
            self.miny.append(kl)
            self.app.zvuk("knopka")
        elif kl is not None:
            self._ne_vyshlo([kl])

    def _povernut(self, imya, kl):
        """Щелчок, ПКМ или R по кораблю: поворот вокруг клетки под мышью; не влез — сдвиг вдоль
        новой оси так, чтобы клетка под мышью осталась кораблём."""
        x, y, g = self.razm[imya]
        dl = P.DLINA[imya]
        o = (kl[0] - x) if g else (kl[1] - y)
        ng = not g
        for j in sorted(range(dl), key=lambda j: abs(j - o)):
            ax, ay = (kl[0] - j, kl[1]) if ng else (kl[0], kl[1] - j)
            if self._mozhno(imya, ax, ay, ng):
                self.razm[imya] = (ax, ay, ng)
                self.gor[imya] = ng
                self.app.zvuk("knopka")
                return
        ax, ay = (kl[0] - o, kl[1]) if ng else (kl[0], kl[1] - o)
        self._ne_vyshlo(P.kletki_korablya(ax, ay, dl, ng))

    def obrabotat(self, e):
        if e.type == pygame.WINDOWFOCUSLOST:
            self._otmenit()
            return
        if klavisha(e, pygame.K_ESCAPE):
            if self.taschim or self.mina_v_ruke:
                self._otmenit()
            else:
                self.app.perejti(Karta(self.app))
            return
        if klavisha(e, pygame.K_r):                       # R — поворот, как ПКМ
            e = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=self.app.mysh, button=3)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not self.taschim:
            self._klik_t, self._klik_kl, self._klik_pos = pygame.time.get_ticks(), self.kletka_pod(e.pos), e.pos
        if self.taschim and e.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONDOWN) and e.button == 1:
            imya, kl = self.taschim, self._klik_kl
            if self.otkuda and kl and math.dist(e.pos, self._klik_pos) <= self.SDVIG_PERENOSA:
                self._otmenit()                           # щелчок без сдвига: корабль на место — и поворот
                if imya != self._povorot_imya or self._klik_t - self._t_povorot > self.DVOJNOJ_MS:
                    self._povernut(imya, kl)              # второй щелчок двойного назад не крутит
                    self._t_povorot, self._povorot_imya = pygame.time.get_ticks(), imya
            else:
                self._polozhit(e.pos)    # второе нажатие тоже кладёт: отпускание могло потеряться
            self._t_polozhil = pygame.time.get_ticks()
            return
        if self.mina_v_ruke and e.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONDOWN) and e.button == 1:
            self._polozhit_minu(e.pos)
            return
        if self.kn_sluchajno.nazhata(e):
            self.app.zvuk("knopka")
            self._sluchajno()
        elif self.kn_dalshe.nazhata(e):
            self._k_pokraske()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            kl = self.kletka_pod(e.pos)
            if kl:
                imya = self._korabl_v(kl)
                if imya:
                    x, y, g = self.razm[imya]
                    self._v_ruku(imya, (x, y, g), (kl[0] - x) if g else (kl[1] - y))
                elif kl in self.miny:
                    self.miny.remove(kl)
                    self.app.zvuk("knopka")
                elif pygame.time.get_ticks() - self._t_polozhil <= self.DVOJNOJ_MS:
                    return                                # щелчок сразу после переноса — не мина
                elif len(self.miny) < N.MIN_NA_POLE:
                    self.miny.append(kl)
                    self.app.zvuk("knopka")
                else:
                    self._skazat(self.st_min_hvatit)
                return
            if len(self.miny) < N.MIN_NA_POLE and any(r.collidepoint(e.pos) for r in self.dok_min):
                self.mina_v_ruke, self._prizrak_min = True, (None, False)     # мину можно и перетащить
                return
            for klass, ramki in self.dok.items():
                for r in ramki:
                    if r.collidepoint(e.pos):
                        imya = next((i for i in self.klassa[klass]
                                     if self.razm[i] is None and i != self.taschim), None)
                        if imya:
                            self.gor[imya] = True
                            self._v_ruku(imya, None, min(P.DLINA[imya] - 1, (e.pos[0] - r.x) // self.DOK_KL))
                        return
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
            if self.taschim:
                self.gor[self.taschim] = not self.gor[self.taschim]
                return
            kl = self.kletka_pod(e.pos)
            imya = self._korabl_v(kl) if kl else None
            if imya:
                self._povernut(imya, kl)

    def obnovit(self, dt):
        super().obnovit(dt)
        self.buhta.obnovit(dt)
        self.t_nelzya = max(0.0, self.t_nelzya - dt)
        self.t_soobshcheniya = max(0.0, self.t_soobshcheniya - dt)
        self.kn_dalshe.vkl = self.gotovo()

    def narisovat(self, ekran):
        res = self.res
        self.buhta.narisovat(ekran)
        self.pelena.narisovat(ekran)
        st = self.soobshchenie if self.t_soobshcheniya > 0 else self.st_stroka
        plashka_s_tekstom(ekran, res, st, (W // 2, 16))
        x0, y0 = self.x0, self.y0
        doska(ekran, res, self.voda, x0, y0, self.st_flot)
        for m in self.miny:
            ekran.blit(self.mina, self.mina.get_rect(center=(x0 + m[0] * KL + KL // 2, y0 + m[1] * KL + KL // 2)))
        for imya, p in self.razm.items():
            if p:
                ekran.blit(res.korabl(N.KLASS[imya], self.skin, False, KL, p[2]), (x0 + p[0] * KL, y0 + p[1] * KL))
        if self.t_nelzya > 0:
            for x, y in self.nelzya:
                pygame.draw.rect(ekran, NELZYA, (x0 + x * KL + 3, y0 + y * KL + 3, KL - 6, KL - 6), 3,
                                 border_radius=8)
        # причал: по строке на класс, спрайт каждого корабля; поставленные — притушены
        ten_plashki(ekran, self.panel)
        plashka(ekran, self.panel, alfa=255)
        tx = self.dok_tekst_x
        for klass, _, _ in N.FLOT:
            ramki = self.dok[klass]
            n = self.ostalos(klass)
            img = res.korabl(klass, self.skin, False, self.DOK_KL, True)
            tusk = res.pritushit(img)
            for j, r in enumerate(ramki):
                ekran.blit(img if j < n else tusk, r.topleft)
            y = ramki[0].centery
            tekst(ekran, res, self.podpisi[klass], MEL, (tx, y), CH, "midleft")
            tekst(ekran, res, self.st_ostalos[n], MEL, (self.panel.right - 24, y), CH if n else SERYJ, "midright",
                  zhirnyj=False)
        k = len(self.miny)
        svobodnyh = N.MIN_NA_POLE - k - (1 if self.mina_v_ruke else 0)
        yc = self.dok_min[0].centery
        tekst(ekran, res, self.st_miny[k], MEL, (self.panel.x + 24, yc), CH, "midleft")
        for j, r in enumerate(self.dok_min):          # мины на причале: свободные яркие, поставленные притушены
            img = self.mina if j < svobodnyh else self.mina_tusk
            ekran.blit(img, img.get_rect(center=r.center))
        na_prichale = sum(self.ostalos(kl) for kl, _, _ in N.FLOT)
        tekst(ekran, res, self.st_na_prichale[na_prichale], MEL, (self.panel.right - 24, yc),
              CH if na_prichale else SERYJ, "midright")
        if self.taschim:
            self._prizrak(ekran)
        if self.mina_v_ruke:
            self._prizrak_miny(ekran)
        self.kn_sluchajno.narisovat(ekran, res, self.app.mysh, self.poyavlenie(0.2))
        self.kn_dalshe.narisovat(ekran, res, self.app.mysh, self.poyavlenie(0.26))

    def _prizrak(self, ekran):
        imya = self.taschim
        g = self.gor[imya]
        img = self.res.korabl(N.KLASS[imya], self.skin, False, KL, g)
        ya = self._yakor(self.app.mysh)
        if ya:
            kl = (imya, ya, g)
            if kl != self._prizrak_kl:            # проверка правил — только когда якорь сменился
                self._prizrak_kl = kl
                self._prizrak_ok = self._mozhno(imya, ya[0], ya[1], g)
                self._prizrak_kletki = [c for c in P.kletki_korablya(ya[0], ya[1], P.DLINA[imya], g) if P.v_pole(*c)]
            cvet = DA if self._prizrak_ok else NELZYA
            kv = self.kv_da if self._prizrak_ok else self.kv_nelzya
            for x, y in self._prizrak_kletki:             # заливка: зелёная — встанет, красная — нельзя
                ekran.blit(kv, (self.x0 + x * KL + 3, self.y0 + y * KL + 3))
                pygame.draw.rect(ekran, cvet, (self.x0 + x * KL + 3, self.y0 + y * KL + 3, KL - 6, KL - 6), 3,
                                 border_radius=8)
            ekran.blit(img, (self.x0 + ya[0] * KL, self.y0 + ya[1] * KL))
        else:
            mx, my = self.app.mysh
            ox = self.zahvat * KL + KL // 2 if g else KL // 2
            oy = KL // 2 if g else self.zahvat * KL + KL // 2
            ekran.blit(img, (mx - ox, my - oy))

    def _prizrak_miny(self, ekran):
        """Мина в руке: клетка под мышью зелёная — встанет, красная — нельзя."""
        kl = self.kletka_pod(self.app.mysh)
        if kl is not None:
            if kl != self._prizrak_min[0]:
                self._prizrak_min = (kl, self._mina_mozhno(kl))
            ok = self._prizrak_min[1]
            x, y = self.x0 + kl[0] * KL + 3, self.y0 + kl[1] * KL + 3
            ekran.blit(self.kv_da if ok else self.kv_nelzya, (x, y))
            pygame.draw.rect(ekran, DA if ok else NELZYA, (x, y, KL - 6, KL - 6), 3, border_radius=8)
        ekran.blit(self.mina, self.mina.get_rect(center=self.app.mysh))


# --- бой ---

def zatemnenie_pod_polyami(alfa_centr, alfa_kraj):
    """Свет, а не вещь: тёмная полупрозрачная заливка поверх бухты под полями, к краям гуще
    (виньетка). Строится один раз из сетки 32×18 и мягко растягивается на экран."""
    m = pygame.Surface((32, 18), pygame.SRCALPHA)
    for y in range(18):
        for x in range(32):
            d = min(1.0, math.hypot((x - 15.5) / 15.5, (y - 8.5) / 8.5) / math.sqrt(2))
            m.set_at((x, y), (12, 16, 26, round(alfa_centr + (alfa_kraj - alfa_centr) * d * d)))
    return pygame.transform.smoothscale(m, (W, H))


class Polet:
    """Шар краски летит по дуге; по прилёте — удар."""
    __slots__ = ("sob", "a", "b", "t", "dlit", "cvet", "zapushchen")

    def __init__(self, sob, a, b, zaderzhka, cvet):
        self.sob, self.a, self.b = sob, a, b
        self.t = -zaderzhka
        self.dlit = 0.5             # полёт шара видим (0,4–0,6 с)
        self.cvet = cvet
        self.zapushchen = False


class BojIgroka(P.Boj):
    """Бой, где у игрока (сторона 0) горят только умения, купленные на верфи на
    этот бой; у капитана (сторона 1) — все, как были. Основной выстрел бесплатен."""

    def __init__(self, nash, ih, um_kupleno, **kw):
        super().__init__(nash, ih, **kw)
        self.um_kupleno = um_kupleno

    def dostupno(self, i, umenie):
        return (i != 0 or umenie in self.um_kupleno) and super().dostupno(i, umenie)


class BojScena(Scena):
    """Состояния: igrok (ждём ход), animaciya (летят шары), vrag (капитан
    думает), konec (пауза перед итогом). Один источник правды — self.etap."""
    PAUZA_VRAGA = (0.45, 0.55) # капитан «думает», с; с полётом 0,5 с и разбросом залпа ход ≤ 1,3 с
    PAUZA_VRAGA_V_SERII = 0.25 # после своего попадания он уже «подумал» в паузе после попадания
    GLUHOTA = 0.3              # с: двойной щелчок по «В бой» не стреляет
    ZATEMNENIE = (108, 150)    # альфа заливки под полями: середина, края — поле светлее фона
    PAUZA_POSLE_POPADANIYA = 0.35
    MIMO_KAZHDYJ = 4           # реплика «мимо» — раз в 4 промаха капитана
    MIMO_NE_CHASHCHE = 6.0     # и не чаще раза в 6 с
    Y_POLOSY = 632             # полоска умений; под ней — две строки подсказки по 16 px
    SONAR_DLIT = 2.6           # ответ сонара на поле: 0,3 с проявляется, держится, последние 0,4 с тает
    SONAR_EST = (236, 170, 52)     # «есть корабль» — тёплая охра, читается на голубой воде
    SONAR_PUSTO = (84, 96, 112)    # «пусто» — сланцевый

    def __init__(self, app, kap, pari, rasstanovka, miny, rng=None):
        super().__init__(app)
        self.kap, self.pari = kap, pari
        self.rng = rng or random.Random()
        pr = app.progress
        vzyato = pr.vzyat_na_boj()                      # всё с верфи — на этот один бой, список очищен
        self.ul, self.skin, self.fat_na_boj = vzyato["ul"], vzyato["skin"], vzyato["fataliti"]
        self.um_kupleno = frozenset(vzyato["umeniya"])  # некупленные кнопки умений погашены
        self.stupen = pr.stupen(kap.id)                 # сколько раз капитан тренировался (progress.json)
        self.limit_pari = P.limit_vystrelov(self.stupen)
        self.mozg = kap.klass_mozga(random.Random(self.rng.random()), self.stupen)
        r_vraga = self.mozg.rasstavit_flot()
        m_vraga = self.mozg.postavit_miny(r_vraga)
        nash = P.Storona(P.Pole(rasstanovka, miny, bronya="bronya" in self.ul), self.ul)
        ih = P.Storona(P.Pole(r_vraga, m_vraga), ())
        self.boj = BojIgroka(nash, ih, self.um_kupleno, pervyj=0, rng=self.rng)
        self.buhta = Buhta(self.res, kap, cvet_buhty(app, kap), s_lyudmi=False, v_boyu=True)
        self.pelena = Pelena(96)
        self.zatemnenie = zatemnenie_pod_polyami(*self.ZATEMNENIE)
        self.voda = voda_polya(self.res)
        self.mina = znachok_miny(self.res, 30)
        self.mina_tusk = self.res.pritushit(self.mina)
        self.doski_mesto = (N.POLE_IGROKA, N.POLE_VRAGA)
        self.doski = self.doski_mesto     # с учётом встряски — пересчитывается в кадре
        self.tryaska = [0.0, 0.0]         # сколько ещё трясётся поле 0 и 1
        self.flagi_t = {}                 # (doska, id корабля) -> когда поднялся белый флаг
        self.navedena = None              # клетка чужого поля под мышью
        self.pricel_xy = None             # где рисуется прицел: плавно догоняет мышь
        self.kursor_nelzya = False
        self.rng_vida = random.Random()   # частицы — свой случай, правила боя его не видят
        self.zvuk_navedeniya = self.res.zvuk("navedenie") if self.res.est("snd/navedenie.wav") else None
        self.cveta = (N.CVET_IGROKA, kap.cvet)       # краска стрелка: 0 — наша, 1 — капитана
        self.pricel = kvadratik((255, 255, 255), 56)
        self.podozr = kvadratik((236, 214, 150), 72)
        self.etap = "igrok"
        self.rezhim = None
        self.gorizont = True
        self.polety, self.effekty, self.vspyshki = [], [], []
        self.skryto = set()           # (doska, x, y) — шар ещё в полёте
        self.pop = {}                 # (doska, x, y) -> возраст свежей кляксы
        self.kesh_korablej = {}
        self.emociya = "spokoen"
        self.puzyr, self.t_puzyrya = "", 0.0
        self.soobshchenie, self.t_soobshcheniya = "", 0.0
        self.sonar = None             # [доска, (x1, y1, x2, y2), заливка, метка, сколько осталось]
        self.st_sonar_metka = {True: self.res.s("boj_sonar_metka_est"), False: self.res.s("boj_sonar_metka_pusto")}
        self.zhdat = 0.0
        self._vrag_popal = False
        self.pauza_posle = 0.0      # короткая пауза после попадания
        self.do_itoga = 0.0
        self.pauza = False
        self.ushli = False
        self.kn_pauza = (Knopka((W // 2 - 144, 328, 288, 56), self.res.s("pauza_prodolzhit")),
                         Knopka((W // 2 - 144, 400, 288, 56), self.res.s("pauza_na_kartu")))
        px = N.POLE_IGROKA[0] - 6
        shag = (STORONA + 12) // len(N.PORYADOK_UMENIJ)
        self.polosa = pygame.Rect(px, self.Y_POLOSY, shag * len(N.PORYADOK_UMENIJ), 48)   # одна полоска умений
        self.kn_umenij = {u: Knopka((px + i * shag, self.Y_POLOSY, shag, 48), "")
                          for i, u in enumerate(N.PORYADOK_UMENIJ)}
        self._ne_kupleno = self.res.s("boj_ne_kupleno")
        # надписи — один раз, не в кадре
        self.st_tvoj_hod = self.res.s("boj_tvoj_hod")
        self.st_hod_vraga = self.res.s("boj_hod_vraga", imya=kap.imya_korotko)
        self.st_podskazka = {u: self.res.s(f"boj_umenie_podskazka_{u}")   # поворот (смена оси) только у залпа,
                             for u in N.PORYADOK_UMENIJ}                  # у остальных ПКМ и R — отмена
        self.shemy, self.rect_shem = None, []            # схемы «сколько осталось» — готовятся при первом кадре
        self._vokrug_kesh = {}                          # корабль -> клетки вокруг (точки «пусто» на моём поле)
        self.podskazka_cifr = blok_strok(self.res, self.res.s("boj_cifra_podskazka").split("\n"), 16, SV)
        self.promahov, self.t_s_mimo = 0, self.MIMO_NE_CHASHCHE   # «мимо» капитана — не на каждый шар
        self.zag_svoj = self.res.s("boj_tvoj_flot")
        self.zag_chuzhoj = self.res.s("boj_flot_vraga", imya=kap.imya_korotko)
        self._nadpisi = {}
        self._schet_kl, self._schet = None, ""
        self.pelena_pauzy = Pelena(150)
        app.fon_buhty(kap.buhta)

    # --- геометрия ---
    def centr_kletki(self, doska, x, y):
        x0, y0 = self.doski[doska]
        return x0 + x * KL + KL // 2, y0 + y * KL + KL // 2

    def kletka_pod(self, doska, pos):
        x0, y0 = self.doski[doska]
        x, y = (pos[0] - x0) // KL, (pos[1] - y0) // KL
        return (x, y) if P.v_pole(x, y) else None

    def kletki_rezhima(self, x, y):
        u = self.rezhim
        if u is None:
            return [(x, y)] if self.boj.storony[1].pole.mozhno_strelyat(x, y) else []
        if u == "zalp":
            return P.liniya(x, y, self.gorizont)
        if u == "razvedka":
            return P.krest(x, y, N.RAZVEDKA_LUCH)
        if u == "sonar":
            n = self.boj.storony[0].razmer_sonara()
            return P.kvadrat(x - (n - 1) // 2, y - (n - 1) // 2, n)
        return [(i, y) for i in range(R)]

    # --- ввод ---
    def obrabotat(self, e):
        if self.pauza:
            if self.kn_pauza[0].nazhata(e) or klavisha(e, pygame.K_ESCAPE):
                self.app.zvuk("knopka")
                self.pauza = False
            elif self.kn_pauza[1].nazhata(e):
                self.app.zvuk("knopka")
                self.app.perejti(Karta(self.app))
            return
        if klavisha(e, pygame.K_ESCAPE):
            if self.rezhim:
                self.rezhim = None
            else:
                self.pauza = True
            return
        if klavisha(e, pygame.K_r):                       # R — смена оси залпа, как ПКМ
            e = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=self.app.mysh, button=3)
        if self.etap != "igrok":
            return
        if e.type == pygame.KEYDOWN and pygame.K_1 <= e.key <= pygame.K_4:
            self._vybrat_umenie(N.PORYADOK_UMENIJ[e.key - pygame.K_1])
            return
        for u, kn in self.kn_umenij.items():
            if kn.nazhata(e):
                self._vybrat_umenie(u)
                return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
            if self.rezhim == "zalp":
                self.gorizont = not self.gorizont
            else:
                self.rezhim = None
        elif klik(e):
            kl = self.kletka_pod(1, e.pos)
            if kl:
                self._strelyat(*kl)

    def _vybrat_umenie(self, u):
        if self.boj.dostupno(0, u):
            self.app.zvuk("knopka")
            self.rezhim = None if self.rezhim == u else u

    def _strelyat(self, x, y):
        boj = self.boj
        if self.rezhim:
            u = self.rezhim
            if u == "sonar":
                n = boj.storony[0].razmer_sonara()
                d = P.Deystvie("sonar", x - (n - 1) // 2, y - (n - 1) // 2)
            else:
                d = P.Deystvie(u, x, y, self.gorizont)
            self.rezhim = None
            self.app.zvuk("umenie")
            self._prinyat(boj.vypolnit(d))
        elif boj.mozhno_vystrelit(0, x, y):
            self._prinyat(boj.vypolnit(P.Deystvie("vystrel", x, y)))
        else:
            return
        self.etap = "animaciya"

    # --- события боя -> показ ---
    def _start(self, kto):
        if kto == 0:
            return N.POLE_IGROKA[0] + STORONA, N.POLE_IGROKA[1] + STORONA
        return N.POLE_VRAGA[0], N.POLE_VRAGA[1] + STORONA

    def _skazat(self, st):
        self.soobshchenie, self.t_soobshcheniya = st, 2.2

    def _replika(self, klyuch, emociya):
        self.puzyr, self.t_puzyrya = self.kap.stroki_boya.get(klyuch, ""), 2.6
        self.emociya = emociya

    def _prinyat(self, sobytiya):
        zad = 0.0
        for s in sobytiya:
            if s.tip == "shar":
                self.skryto.add((s.doska, s.x, s.y))
                self.polety.append(Polet(s, self._start(s.kto), self.centr_kletki(s.doska, s.x, s.y), zad,
                                         self.cveta[s.kto]))
                zad += 0.14
            elif s.tip == "sonar" and s.kto == 0:
                self._pokazat_sonar(s)
            elif s.tip in ("razvedka", "sonar"):
                self.vspyshki.append([s.doska, s.kletki, self.cveta[s.kto], 1.4])
                if s.kto == 1:
                    self.app.zvuk("umenie")
                else:
                    self._skazat(self.res.s("boj_razvedka"))
            elif s.tip == "torpeda":
                self.vspyshki.append([s.doska, s.kletki, self.cveta[s.kto], 0.9])
                zad += 0.2
            elif s.tip == "vtoroj" and s.kto == 0:
                self._skazat(self.res.s("boj_vtoroj"))

    def _pokazat_sonar(self, s):
        """Ответ сонара — заливкой всего квадрата на поле и короткой меткой «есть корабль» / «пусто»;
        та же строка сверху. Заливка готовится один раз на применение, не в кадре."""
        kletki = [c for c in s.kletki if P.v_pole(*c)]
        if not kletki:
            return
        x1, y1 = min(c[0] for c in kletki), min(c[1] for c in kletki)
        x2, y2 = max(c[0] for c in kletki) + 1, max(c[1] for c in kletki) + 1
        est = s.rezultat == "est"
        cvet = self.SONAR_EST if est else self.SONAR_PUSTO
        zalivka = pygame.Surface(((x2 - x1) * KL - 4, (y2 - y1) * KL - 4), pygame.SRCALPHA)
        pygame.draw.rect(zalivka, (*cvet, 100), zalivka.get_rect(), border_radius=10)
        pygame.draw.rect(zalivka, (*cvet, 255), zalivka.get_rect(), 4, border_radius=10)
        self.sonar = [s.doska, (x1, y1, x2, y2), zalivka, self.st_sonar_metka[est], self.SONAR_DLIT]
        self._skazat(self.res.s("boj_sonar_est" if est else "boj_sonar_pusto"))
        self.t_soobshcheniya = self.SONAR_DLIT

    def _sonar(self, ekran):
        if not self.sonar:
            return
        doska_, (x1, y1, x2, y2), zalivka, metka, ostalos = self.sonar
        k = max(0.0, min(1.0, plavno(min(1.0, (self.SONAR_DLIT - ostalos) / 0.3)), ostalos / 0.4))
        zalivka.set_alpha(round(255 * k))
        x0, y0 = self.doski[doska_]
        ekran.blit(zalivka, (x0 + x1 * KL + 2, y0 + y1 * KL + 2))
        cx = x0 + (x1 + x2) * KL // 2
        if y2 < R:
            tekst_na_podlozhke(ekran, self.res, metka, MEL, (cx, y0 + y2 * KL + 4), SV, "midtop")
        else:
            tekst_na_podlozhke(ekran, self.res, metka, MEL, (cx, y0 + y1 * KL - 4), SV, "midbottom")

    def _udar(self, p):
        s = p.sob
        kl = (s.doska, s.x, s.y)
        self.skryto.discard(kl)
        cx, cy = self.centr_kletki(s.doska, s.x, s.y)
        rez = s.rezultat
        if rez in ("popal", "zakrasil"):
            self.pop[kl] = 0.0
            self.pauza_posle = self.PAUZA_POSLE_POPADANIYA
            self.effekty.append(E.Kapli(cx, cy, p.cvet, rng=self.rng_vida))
            self.tryaska[s.doska] = E.TRYASKA_DLIT
            self.app.zvuk("shlep", 3)
        elif rez == "bronya":
            self.effekty.append(E.Kapli(cx, cy, (196, 194, 188), n=10, rng=self.rng_vida))
            self.app.zvuk("shlep", 3)
            self._skazat(self.res.s("boj_bronya" if s.kto == 1 else "boj_bronya_ih"))
        else:
            self.effekty.append(E.Krugi(cx, cy, self.rng_vida))
            self.app.zvuk("plesk", 3)
            if rez == "mina":
                self.app.zvuk("mina")
                self.effekty.append(E.Kapli(cx, cy, self.cveta[1 - s.kto], rng=self.rng_vida))
                self.tryaska[s.doska] = E.TRYASKA_DLIT
                self._skazat(self.res.s("boj_mina_ih" if s.kto == 0 else "boj_mina_nasha"))
        if rez == "zakrasil":
            k = self.boj.storony[s.doska].pole.korabl(s.korabl)
            ax, ay = self.centr_kletki(s.doska, k.x, k.y)
            bx, by = self.centr_kletki(s.doska, *k.kletki()[-1])
            self.effekty.append(E.Konfetti((ax + bx) / 2, (ay + by) / 2, p.cvet, self.rng_vida))
            self.app.zvuk("zakrashen")
            self._skazat(self.res.s("boj_zakrasili_ih" if s.kto == 0 else "boj_zakrasili_nash"))
        if s.kto == 1:
            if rez in ("popal", "zakrasil"):
                self._vrag_popal = True
                self._replika(rez, "raduetsya")         # попал и закрасил — всегда
            else:
                self._mimo_kapitana()
        else:
            self.emociya = "zlitsya" if rez in ("popal", "zakrasil") else "spokoen"

    def _mimo_kapitana(self):
        """«Мимо» — не на каждый шар: раз в MIMO_KAZHDYJ промахов и не чаще раза в MIMO_NE_CHASHCHE с."""
        self.promahov += 1
        if self.promahov >= self.MIMO_KAZHDYJ and self.t_s_mimo >= self.MIMO_NE_CHASHCHE:
            self.promahov, self.t_s_mimo = 0, 0.0
            self._replika("mimo", "zlitsya")
        elif self.t_puzyrya <= 0:
            self.emociya = "zlitsya"

    def _posle_animacii(self):
        b = self.boj
        if b.pobeditel is not None:
            self.etap, self.do_itoga = "konec", 1.8
            if b.pobeditel == 0:
                self._replika("proigral", "spokoen")
                self.app.zvuk("pobeda")
            else:
                self.emociya = "raduetsya"
                self.app.zvuk("porazhenie")
        elif b.hod == 1:
            pauza = self.rng_vida.uniform(*self.PAUZA_VRAGA)    # свой случай: правила боя его не видят
            if self._vrag_popal:
                pauza = max(self.PAUZA_VRAGA_V_SERII, pauza - self.PAUZA_POSLE_POPADANIYA)
            self.etap, self.zhdat, self._vrag_popal = "vrag", pauza, False
        else:
            self.etap = "igrok"

    def obnovit(self, dt):
        super().obnovit(dt)
        self.buhta.obnovit(dt)
        self._navesti(dt)
        if self.pauza:
            return
        for d in (0, 1):
            if self.tryaska[d] > 0:
                self.tryaska[d] = max(0.0, self.tryaska[d] - dt)
        self._sdvig_dosok()
        self.t_puzyrya = max(0.0, self.t_puzyrya - dt)
        self.t_s_mimo += dt
        self.t_soobshcheniya = max(0.0, self.t_soobshcheniya - dt)
        prileteli = []
        for p in self.polety:
            p.t += dt
            if not p.zapushchen and p.t >= 0:
                p.zapushchen = True
                self.app.zvuk("vystrel", 3)
            if p.t >= p.dlit:
                prileteli.append(p)
        if prileteli:
            self.polety = [p for p in self.polety if p.t < p.dlit]
            for p in prileteli:
                self._udar(p)
        if self.effekty:
            self.effekty = [e for e in self.effekty if e.obnovit(dt)]
        if self.sonar:
            self.sonar[4] -= dt
            if self.sonar[4] <= 0:
                self.sonar = None
        if self.vspyshki:
            for v in self.vspyshki:
                v[3] -= dt
            self.vspyshki = [v for v in self.vspyshki if v[3] > 0]
        for k in list(self.pop):
            self.pop[k] += dt
            if self.pop[k] > 0.3:
                del self.pop[k]
        self.pauza_posle = max(0.0, self.pauza_posle - dt)
        if self.etap == "animaciya" and not self.polety and self.pauza_posle <= 0:
            self._posle_animacii()
        elif self.etap == "vrag":
            self.zhdat -= dt
            if self.zhdat <= 0:
                self._prinyat(taktika.hod_protivnika(self.boj, 1, self.mozg))
                self.etap = "animaciya"
        elif self.etap == "konec":
            self.do_itoga -= dt
            if self.do_itoga <= 0:
                self._k_itogu()

    def _k_itogu(self):
        if self.ushli:
            return
        self.ushli = True
        b = self.boj
        pobeda = b.pobeditel == 0
        vyp = P.pari_vypolneno(b, 0, self.pari, self.limit_pari)
        fat = P.fataliti_dlya(b, 0, self.fat_na_boj)     # фаталити, купленные на этот бой
        medali = P.medali_za_boj(b, 0)
        summa, raskladka = P.monety_za_boj(pobeda, self.pari, vyp, fat, len(medali))
        s = b.storony[0]
        d = {"pobeda": pobeda, "pari": self.pari, "vypolneno": vyp, "fataliti": fat,
             "medali": medali, "monety": summa, "raskladka": raskladka,
             "vystrelov": s.vystrelov, "tochnost": round(100 * s.popadanij / s.sharov) if s.sharov else 0,
             "seriya": s.seriya_max}
        self.app.perejti(Itog(self.app, self.kap, d))

    # --- рисование ---
    def _korabl_s_kraskoj(self, doska, k, vidno, zakr, cvet, skin):
        """Спрайт корабля, на который легла краска стрелка — строго по силуэту."""
        kl = (doska, k.imya, len(vidno), zakr, skin)
        s = self.kesh_korablej.get(kl)
        if s is None:
            baza = self.res.korabl(k.klass, skin, zakr, KL, k.gorizont)
            s = baza.copy()
            if vidno:
                kraska = pygame.Surface(s.get_size(), pygame.SRCALPHA)
                for cx, cy in vidno:
                    bl = risunki.klyaksa(int(KL * 0.55), cvet, cx * 7 + cy * 3 + doska)
                    kraska.blit(bl, bl.get_rect(center=((cx - k.x) * KL + KL // 2, (cy - k.y) * KL + KL // 2)))
                maska = baza.copy()
                maska.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
                kraska.blit(maska, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                s.blit(kraska, (0, 0))
            self.kesh_korablej[kl] = s
        return s

    def _flag(self, ekran, doska, k):
        """Белый флаг закрашенного корабля поднимается мягким хлопком (пружина 0,45 с)."""
        t0 = self.flagi_t.setdefault((doska, k.imya), self.t)
        m = 0.9 * pruzhina(min(1.0, (self.t - t0) / 0.45))
        if m < 0.05:
            return
        x, y = k.kletki()[-1]
        cx, cy = self.centr_kletki(doska, x, y)
        risunki.belyj_flag(ekran, cx - 6, cy + 10, self.t + k.dlina, m)

    def _svoe_pole(self, ekran):
        x0, y0 = self.doski[0]
        pole = self.boj.storony[0].pole
        doska(ekran, self.res, self.voda, x0, y0, self.zag_svoj)
        for m in pole.miny:
            img = self.mina_tusk if m in pole.srabotali and (0, *m) not in self.skryto else self.mina
            ekran.blit(img, img.get_rect(center=self.centr_kletki(0, *m)))
        flagi = []
        for k in pole.korabli:
            vidno = [c for c in sorted(k.popadaniya) if (0, *c) not in self.skryto]
            zakr = k.zakrashen and len(vidno) == k.dlina
            ekran.blit(self._korabl_s_kraskoj(0, k, vidno, zakr, self.cveta[1], self.skin),
                       (x0 + k.x * KL, y0 + k.y * KL))
            if zakr:
                flagi.append(k)
        for k in flagi:                                 # вокруг моего закрашенного — точки «пусто», как у чужого
            for c in self._vokrug(k, pole):
                if c in pole.pusto and c not in pole.vystrely:
                    ekran.blit(risunki.tochka(KL, TOCHKA_PUSTO), (x0 + c[0] * KL, y0 + c[1] * KL))
        for x, y in pole.otkryto:                       # это капитан о нас уже знает
            if (x, y) not in pole.vystrely:
                pygame.draw.rect(ekran, self.cveta[1], (x0 + x * KL + 4, y0 + y * KL + 4, KL - 8, KL - 8), 2,
                                 border_radius=8)
        for (x, y), st in pole.vystrely.items():
            if (0, x, y) in self.skryto:
                continue
            img = risunki.krestik(KL, x * 7 + y) if st == P.POPAL else risunki.tochka(KL)
            ekran.blit(img, (x0 + x * KL, y0 + y * KL))
        for k in flagi:
            self._flag(ekran, 0, k)

    def _vokrug(self, k, pole):
        """Клетки воды вокруг корабля — считаются один раз на корабль, не в каждом кадре."""
        kl = self._vokrug_kesh.get(k.imya)
        if kl is None:
            ryadom = {(x + dx, y + dy) for x, y in k.kletki() for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
            kl = self._vokrug_kesh[k.imya] = sorted(c for c in ryadom if P.v_pole(*c) and c not in pole.karta)
        return kl

    def _chuzhoe_pole(self, ekran):
        x0, y0 = self.doski[1]
        pole = self.boj.storony[1].pole
        doska(ekran, self.res, self.voda, x0, y0, self.zag_chuzhoj, True)
        vidnye, flagi = set(), []
        for k in pole.korabli:
            vidno = [c for c in sorted(k.popadaniya) if (1, *c) not in self.skryto]
            if k.zakrashen and len(vidno) == k.dlina:   # чужой корабль виден, только закрашенный целиком
                ekran.blit(self._korabl_s_kraskoj(1, k, vidno, True, self.cveta[0], "bazovyj"),
                           (x0 + k.x * KL, y0 + k.y * KL))
                vidnye.add(k.imya)
                flagi.append(k)
        for x, y in pole.podozr:
            ekran.blit(self.podozr, (x0 + x * KL + 3, y0 + y * KL + 3))
        for x, y in pole.pusto:
            if (x, y) not in pole.vystrely:
                ekran.blit(risunki.tochka(KL, TOCHKA_PUSTO), (x0 + x * KL, y0 + y * KL))
        sila = int(2 + 1.5 * (1 + math.sin(self.t * 5)))
        for x, y in pole.otkryto:
            if (x, y) not in pole.vystrely:
                pygame.draw.rect(ekran, N.CVET_IGROKA, (x0 + x * KL + 3, y0 + y * KL + 3, KL - 6, KL - 6), sila,
                                 border_radius=8)
        for (x, y), st in pole.vystrely.items():
            kl = (1, x, y)
            if kl in self.skryto:
                continue
            if st == P.POPAL:
                k = pole.karta.get((x, y))
                if not (k and k.imya in vidnye):
                    bl = risunki.klyaksa(int(KL * 0.55), self.cveta[0], x * 7 + y * 3 + 1)
                    vozrast = self.pop.get(kl)
                    if vozrast is not None and vozrast < 0.2:
                        bl = pygame.transform.smoothscale_by(bl, 0.55 + 0.45 * vyezd(vozrast / 0.2))
                    ekran.blit(bl, bl.get_rect(center=self.centr_kletki(1, x, y)))
                ekran.blit(risunki.krestik(KL, x * 7 + y), (x0 + x * KL, y0 + y * KL))
            else:
                ekran.blit(risunki.tochka(KL), (x0 + x * KL, y0 + y * KL))
                if (x, y) in pole.srabotali:
                    ekran.blit(self.mina_tusk, self.mina_tusk.get_rect(center=self.centr_kletki(1, x, y)))
        for k in flagi:
            self._flag(ekran, 1, k)

    def _navesti(self, dt):
        """Клетка под мышью: прицел плавно догоняет её; по стрелянной — курсор «нельзя»."""
        kl = self.kletka_pod(1, self.app.mysh) if self.etap == "igrok" and not self.pauza else None
        nelzya = kl is not None and self.rezhim is None and not self.boj.storony[1].pole.mozhno_strelyat(*kl)
        if nelzya != self.kursor_nelzya:
            self.kursor_nelzya = nelzya
            ustanovit_kursor(nelzya)
        if kl != self.navedena:
            self.navedena = kl
            if kl is not None and not nelzya and self.zvuk_navedeniya is not None:
                self.zvuk_navedeniya.set_volume(self.res.gromkost * 10 ** (N.NAVEDENIE_DB / 20))
                self.zvuk_navedeniya.play()
        if kl is None:
            self.pricel_xy = None
            return
        tx, ty = kl[0] * KL, kl[1] * KL
        if self.pricel_xy is None:
            self.pricel_xy = [tx, ty]
        else:
            k = 1 - math.exp(-dt * 22)               # догоняет за ~0,1 с, с торможением
            self.pricel_xy[0] += (tx - self.pricel_xy[0]) * k
            self.pricel_xy[1] += (ty - self.pricel_xy[1]) * k

    def _sdvig_dosok(self):
        """Лёгкая встряска поля после попадания: до 3 px, гаснет за 0,25 с."""
        if self.tryaska[0] <= 0 and self.tryaska[1] <= 0:
            self.doski = self.doski_mesto
            return
        d = []
        for i, (bx, by) in enumerate(self.doski_mesto):
            a = E.TRYASKA_PX * self.tryaska[i] / E.TRYASKA_DLIT
            d.append((bx + round(a * math.sin(self.t * 83)), by + round(a * math.cos(self.t * 61))))
        self.doski = tuple(d)

    def _pricel(self, ekran):
        """Клетка-прицел с мягкой пульсацией; на стрелянной клетке прицела нет."""
        if self.navedena is None or self.pricel_xy is None:
            return
        kletki = self.kletki_rezhima(*self.navedena)
        if not kletki:
            return
        x0, y0 = self.doski[1]
        ox = round(self.pricel_xy[0]) - self.navedena[0] * KL
        oy = round(self.pricel_xy[1]) - self.navedena[1] * KL
        puls = 0.5 + 0.5 * math.sin(self.t * 4.2)
        self.pricel.set_alpha(150 + int(105 * puls))
        r = round(2 * puls)
        for x, y in kletki:
            px, py = x0 + x * KL + ox, y0 + y * KL + oy
            ekran.blit(self.pricel, (px + 3, py + 3))
            pygame.draw.rect(ekran, N.CVET_IGROKA, (px + 3 - r, py + 3 - r, KL - 6 + 2 * r, KL - 6 + 2 * r), 2,
                             border_radius=8)

    def _vspyshka(self, ekran, v):
        doska_, kletki, cvet, ostalos = v
        x0, y0 = self.doski[doska_]
        tolshina = 3 if ostalos > 0.4 else 2
        for x, y in kletki:
            pygame.draw.rect(ekran, cvet, (x0 + x * KL + 2, y0 + y * KL + 2, KL - 4, KL - 4), tolshina,
                             border_radius=8)

    def _shar(self, ekran, p):
        if p.t < 0:
            return
        u = min(1.0, p.t / p.dlit)
        ue = plavno(u)                                 # разгон и торможение, не по прямой
        x = p.a[0] + (p.b[0] - p.a[0]) * ue
        y = p.a[1] + (p.b[1] - p.a[1]) * ue
        vys = math.sin(math.pi * u)
        h = vys * 96
        tw = 14 - 6 * vys                              # тень на воде: шар выше — тень меньше
        pygame.draw.ellipse(ekran, (52, 82, 100), (int(x - tw / 2), int(y - tw / 4), int(tw), max(2, int(tw / 2))))
        r = 7 + 3 * math.sin(math.pi * u)
        pygame.draw.circle(ekran, p.cvet, (x, y - h), r)
        pygame.draw.circle(ekran, CH, (x, y - h), r, 2)
        pygame.draw.circle(ekran, risunki.svetlee(p.cvet, 0.45), (x - r * 0.3, y - h - r * 0.3), r * 0.3)

    def _verh(self, ekran):
        """Одна плашка сверху: сообщение боя, подсказка умения или чей ход."""
        res, b = self.res, self.boj
        if self.t_soobshcheniya > 0:
            plashka_s_tekstom(ekran, res, self.soobshchenie, (W // 2, 18))
            return
        if self.rezhim:
            plashka_s_tekstom(ekran, res, self.st_podskazka.get(self.rezhim, ""),
                              (W // 2, 18))
            return
        if self.etap == "konec":
            st = res.s("itog_pobeda" if b.pobeditel == 0 else "itog_porazhenie")
        else:
            st = self.st_tvoj_hod if b.hod == 0 else self.st_hod_vraga
        plashka_s_tekstom(ekran, res, st, (W // 2, 12), KRUP)

    def _kapitan(self, ekran):
        """Портрет капитана между полями, стоит на нижнем крае экрана."""
        img = portret_kapitana(self.res, self.kap, self.emociya, 168)
        r = img.get_rect(midbottom=(W // 2, H + 2 + int(math.sin(self.t * 2) * 2)))
        ekran.blit(img, r)
        if self.t_puzyrya > 0 and self.puzyr:
            puzyr(ekran, self.res, self.puzyr, (W // 2, r.top + 12), shirina=184)

    def _nadpis_umeniya(self, u, s):
        """(имя умения, число перезарядки или '', закрашен ли корабль); строки из кэша."""
        imya = self._nadpisi.get(u)
        if imya is None:
            imya = self._nadpisi[u] = self.res.s("umenie_" + u)
        if not s.pole.na_plavu(N.UMENIYA[u]["korabl"]):
            return imya, "", True
        n = s.gotovnost[u]
        return imya, (CIFRY[n - 1] if 0 < n <= R else ""), False

    def _stroka_scheta(self, s):
        """Счёт выстрелов и пари — одной строкой; пересобирается только при перемене."""
        av = self.pari == "avianosec" and not s.pole.na_plavu("avianosec")
        kl = (s.vystrelov, av)
        if kl != self._schet_kl:
            res = self.res
            if self.pari == "vystrely40":
                st = res.s("boj_vystrelov_iz", n=s.vystrelov, iz=self.limit_pari)
            else:
                st = res.s("boj_vystrelov", n=s.vystrelov)
                if self.pari == "avianosec":
                    st += "   ·   " + res.s("boj_pari_avianosec_net" if av else "boj_pari_avianosec_cel")
            self._schet_kl, self._schet = kl, st
        return self._schet

    SHEMA_KL, SHEMA_VYS, SHEMA_ZAZOR, SHEMA_ZAZOR_KLASSA = 10, 8, 3, 8   # px: клетка и высота плашки, зазоры
    # плашки, а не спрайты: спрайт при клетке 10 px читается чёрточкой

    def _gotovit_shemy(self):
        """Схемы «сколько кораблей осталось подбить» под полями: плашки флота по
        классам из N.FLOT, первая половина классов в верхнем ряду, остальные — в
        нижнем. Раскладка и спрайты — один раз, в кадре только blit."""
        c, z, zk = self.SHEMA_KL, self.SHEMA_ZAZOR, self.SHEMA_ZAZOR_KLASSA
        klassy = [kl for kl, _, _ in N.FLOT]
        dlina = {kl: dl for kl, dl, _ in N.FLOT}
        pol = (len(klassy) + 1) // 2
        self.shema_mesta, shir = [], 0
        for ryad, chast in enumerate((klassy[:pol], klassy[pol:])):
            x = 0
            for kl in chast:
                for j in range(N.SKOLKO[kl]):
                    self.shema_mesta.append((kl, j, x, ryad * (self.SHEMA_VYS + 4)))
                    x += dlina[kl] * c + z
                x += zk - z
            shir = max(shir, x - zk)
        y = self.polosa.bottom + 10
        self.shemy = []
        yark = {kl: plashka_korablya(dlina[kl], c, self.SHEMA_VYS, N.CVET_BUMAGA) for kl in klassy}   # на плаву
        tusk = {kl: plashka_korablya(dlina[kl], c, self.SHEMA_VYS, (104, 106, 112)) for kl in klassy}  # закрашен
        for d, x in ((0, N.POLE_IGROKA[0]), (1, N.POLE_VRAGA[0] + STORONA - shir)):
            self.shemy.append((pygame.Rect(x, y, shir, 2 * self.SHEMA_VYS + 4), yark, tusk, self.cveta[1 - d]))
        self.rect_shem = [r.inflate(12, 8) for r, _, _, _ in self.shemy]   # с подложкой: по ним проверяются перекрытия
        self._zakr_klassa = dict.fromkeys(klassy, 0)

    def _shemy(self, ekran, dy):
        """Моя схема — под моим полем, схема противника — под его. У противника
        видно только то, что игрок знает: закрашенные корабли, остальные — на плаву."""
        if self.shemy is None:
            self._gotovit_shemy()
        zakr, pol_kl = self._zakr_klassa, self.SHEMA_VYS // 2
        for d, (rect, yark, tusk, cvet) in enumerate(self.shemy):
            for kl in zakr:
                zakr[kl] = 0
            for k in self.boj.storony[d].pole.korabli:      # закрашен и шар уже долетел — как на поле
                if k.zakrashen and not any((d, *c) in self.skryto for c in k.popadaniya):
                    zakr[k.klass] += 1
            podlozhka(ekran, self.rect_shem[d].move(0, dy))
            for kl, j, x, y in self.shema_mesta:
                ubit = j >= N.SKOLKO[kl] - zakr[kl]          # закрашенные — в конце своего класса
                img = tusk[kl] if ubit else yark[kl]
                px, py = rect.x + x, rect.y + y + dy
                ekran.blit(img, (px, py))
                if ubit:
                    pygame.draw.line(ekran, cvet, (px - 2, py + pol_kl), (px + img.get_width() + 1, py + pol_kl), 2)

    def _niz(self, ekran):
        """Полоска умений под своим полем и строка счёта под чужим."""
        res, s = self.res, self.boj.storony[0]
        mysh = self.app.mysh
        dy = round((1 - vyezd(self.poyavlenie(0.2, 0.35))) * 16)
        polosa = self.polosa.move(0, dy)
        ten_plashki(ekran, polosa, radius=12, alfa=48)
        plashka(ekran, polosa, N.CVET_BUMAGA, 255, True, 12)
        for i, (u, kn) in enumerate(self.kn_umenij.items()):
            imya, chislo, net = self._nadpis_umeniya(u, s)
            kn.nadpis = imya
            kn.vkl = self.etap == "igrok" and self.boj.dostupno(0, u)
            kn.vybrana = self.rezhim == u
            r = kn.rect.move(0, dy)
            if kn.vybrana or (kn.vkl and r.collidepoint(mysh)):
                pygame.draw.rect(ekran, smeshat(N.CVET_BUMAGA, N.CVET_IGROKA, 0.35 if kn.vybrana else 0.14),
                                 r.inflate(-8, -10), border_radius=8)
            if i:
                pygame.draw.line(ekran, (200, 192, 178), (r.x, r.y + 12), (r.x, r.bottom - 12), 2)
            cvet = CH if kn.vkl else SERYJ
            if u not in self.um_kupleno:                 # не куплено на верфи: погашена, с пометкой
                tekst(ekran, res, imya, MEL, (r.centerx, r.centery - 9), SERYJ, "center", zhirnyj=False)
                tekst(ekran, res, self._ne_kupleno, OSI, (r.centerx, r.centery + 9), SERYJ, "center", zhirnyj=False)
            elif chislo:                                   # перезарядка — маленькой цифрой у имени
                w = res.shrift(MEL, False).size(imya)[0]
                x = r.centerx - (w + 6 + res.shrift(OSI, False).size(chislo)[0]) // 2
                tekst(ekran, res, imya, MEL, (x, r.centery), cvet, "midleft", zhirnyj=False)
                tekst(ekran, res, chislo, OSI, (x + w + 6, r.centery - 6), cvet, "midleft", zhirnyj=False)
            else:
                rr = tekst(ekran, res, imya, MEL, r.center, cvet, "center", zhirnyj=False)
                if net:                                  # корабль закрашен — умение зачёркнуто
                    pygame.draw.line(ekran, SERYJ, (rr.x - 2, rr.centery + 1), (rr.right + 2, rr.centery + 1), 2)
        r = self.podskazka_cifr.get_rect(midtop=(polosa.centerx, polosa.bottom + 6))   # под своим полем
        podlozhka(ekran, r)
        ekran.blit(self.podskazka_cifr, r)
        self._shemy(ekran, dy)
        if self.pari != "net":                           # счёт выстрелов — только когда он условие пари
            tekst_na_podlozhke(ekran, res, self._stroka_scheta(s), MEL, (N.POLE_VRAGA[0] + STORONA, polosa.centery),
                               SV, "midright", zhirnyj=False)

    def narisovat(self, ekran):
        self.buhta.narisovat(ekran)
        self.pelena.narisovat(ekran)
        ekran.blit(self.zatemnenie, (0, 0))             # свет: фон за полями темнее поля
        self.buhta.narisovat_za_polyami(ekran)          # туман и чайки — на приглушённой бухте, под полями
        self._svoe_pole(ekran)
        self._chuzhoe_pole(ekran)
        for v in self.vspyshki:
            self._vspyshka(ekran, v)
        self._sonar(ekran)
        self._pricel(ekran)
        for e in self.effekty:
            e.narisovat(ekran)
        self._kapitan(ekran)
        for p in self.polety:
            self._shar(ekran, p)
        self._verh(ekran)
        self._niz(ekran)
        if self.pauza:
            self.pelena_pauzy.narisovat(ekran)
            plashka_s_tekstom(ekran, self.res, self.res.s("pauza"), (W // 2, 240), KRUP)
            for k in self.kn_pauza:
                k.narisovat(ekran, self.res, self.app.mysh)


# --- итог ---

def mnozhitel(v):
    if isinstance(v, float):
        return "×" + (f"{v:g}").replace(".", ",")
    return str(v)


class Itog(Scena):
    """Итог боя: монеты с раскладкой, медали. Прогресс пишется здесь, один раз."""

    GLUHOTA = 0.5            # с: последний щелчок боя не нажимает кнопки итога

    def __init__(self, app, kap, d):
        super().__init__(app)
        self.kap, self.d = kap, d
        pr = app.progress
        pr.dobavit_monety(d["monety"])
        for m in d["medali"]:
            pr.dobavit_medal(m)
        if d["pobeda"]:
            pr.otmetit_port(kap.id)
            pr.povysit_stupen(kap.id)                 # проиграл — к реваншу тренируется
        self.st_rekord = self.res.s("itog_rekord", p=pr.obnovit_rekord(d.get("tochnost", 0)))
        pr.sohranit()
        self.buhta = Buhta(self.res, kap, cvet_buhty(app, kap), s_lyudmi=False)
        self.pelena = Pelena(150)
        self.medali = {m: self.res.kartinka(f"img/medali/{m}.png", razmer=(96, 96),
                                            zaglushka=lambda m=m: risunki.zaglushka_znachok("medal", (96, 96),
                                                                                            risunki.ZNACHKI[m]))
                       for m in N.MEDALI}
        self.kn = Knopka((W // 2 - 296, 600, 288, 64), self.res.s("itog_dalshe"), razmer=KRUP)
        self.kn_revansh = Knopka((W // 2 + 8, 600, 288, 64), self.res.s("itog_revansh"), razmer=KRUP)
        self.ushli = False
        self.zvuk_monet = False
        self.zvuk_kart = False
        self.zapas_fataliti = KadryFataliti(self.res, d["fataliti"]) if d["fataliti"] else None
        app.fon_buhty(kap.buhta)

    def obrabotat(self, e):
        if self.kn_revansh.nazhata(e):
            self.app.zvuk("knopka")
            self._revansh()
        elif self.kn.nazhata(e) or klavisha(e, pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            self.app.zvuk("knopka")
            self._dalshe()

    def _dalshe(self):
        if self.ushli:
            return
        self.ushli = True
        app, kap, d = self.app, self.kap, self.d
        chto = "pobeda" if d["pobeda"] else "porazhenie"

        def k_razgovoru():
            app.perejti(Razgovor(app, kap, chto,
                                 lambda: app.perejti(BuhtaScena(app, kap, posle=True, pobeda=d["pobeda"]))))
        if d["fataliti"]:
            app.perejti(Fataliti(app, d["fataliti"], k_razgovoru, self.zapas_fataliti))
        else:
            k_razgovoru()

    def _revansh(self):
        """Реванш: верфь (купить на бой) -> «В бой» -> VS -> пари -> расстановка, мимо
        карты, бухты и разговора. Фаталити победы показывается как обычно — это награда."""
        if self.ushli:
            return
        self.ushli = True
        from game.sceny_syuzhet import Verf
        app, kap = self.app, self.kap
        k_verf = lambda: app.perejti(Verf(app, revansh=kap))
        if self.d["fataliti"]:
            app.perejti(Fataliti(app, self.d["fataliti"], k_verf, self.zapas_fataliti))
        else:
            k_verf()

    def obnovit(self, dt):
        super().obnovit(dt)
        self.buhta.obnovit(dt)
        if not self.zvuk_kart:
            self.zvuk_kart = True
            self.app.zvuk("kartochka")
        if self.zapas_fataliti is not None:
            self.zapas_fataliti.podgruzit(6)           # кадры ролика читаются, пока игрок смотрит итог
        if self.t > 0.6 and not self.zvuk_monet:
            self.zvuk_monet = True
            self.app.zvuk("monety")

    def narisovat(self, ekran):
        res, d = self.res, self.d
        self.buhta.narisovat(ekran)
        self.pelena.narisovat(ekran)
        u = vyezd(self.poyavlenie(0.0, 0.35))
        panel = pygame.Rect(W // 2 - 320, 64 + round((1 - u) * 16), 640, 512)
        ten_plashki(ekran, panel)
        plashka(ekran, panel, alfa=255)
        cvet_zag = risunki.temnee(N.CVET_IGROKA, 0.75) if d["pobeda"] else (110, 104, 100)
        tekst(ekran, res, res.s("itog_pobeda" if d["pobeda"] else "itog_porazhenie"), KRUP,
              (panel.centerx, panel.y + 32), cvet_zag, "midtop")
        y = panel.y + 96
        for klyuch, znach in d["raskladka"]:
            tekst(ekran, res, res.s(klyuch), MEL, (panel.x + 48, y), CH, zhirnyj=False)
            tekst(ekran, res, mnozhitel(znach), MEL, (panel.right - 48, y), CH, "topright")
            y += 32
        pygame.draw.line(ekran, (200, 192, 178), (panel.x + 48, y + 4), (panel.right - 48, y + 4), 2)
        y += 16
        dolya = vyezd((self.t - 0.4) / 1.0)
        tekst(ekran, res, res.s("itog_itogo"), KRUP, (panel.x + 48, y), CH)
        tekst(ekran, res, res.s("monety", n=int(d["monety"] * dolya)), KRUP, (panel.right - 48, y), CH, "topright")
        y += 56
        tekst(ekran, res, res.s("itog_statistika", v=d["vystrelov"], p=d["tochnost"], s=d["seriya"]), MEL,
              (panel.centerx, y), (96, 96, 104), "midtop", zhirnyj=False)
        y += 30
        tekst(ekran, res, self.st_rekord, MEL, (panel.centerx, y), (96, 96, 104), "midtop", zhirnyj=False)
        y += 40
        tekst(ekran, res, res.s("itog_medali"), MEL, (panel.centerx, y), CH, "midtop")
        y += 36
        if d["medali"]:
            n = len(d["medali"])
            x = panel.centerx - (n * 96 + (n - 1) * 16) // 2
            for i, m in enumerate(d["medali"]):
                k = vyezd((self.t - 0.8 - i * 0.12) / 0.3)
                if k > 0:
                    ekran.blit(self.medali[m], (x + i * 112, y + round((1 - k) * 12)))
        else:
            tekst(ekran, res, res.s("itog_bez_medalej"), MEL, (panel.centerx, y + 32), (128, 124, 118), "midtop",
                  zhirnyj=False)
        self.kn.narisovat(ekran, res, self.app.mysh, self.poyavlenie(0.5))
        self.kn_revansh.narisovat(ekran, res, self.app.mysh, self.poyavlenie(0.5))


# --- фаталити ---

class KadryFataliti:
    """Кадры ролика заранее: файлы читаются в память по нескольку за кадр, пока
    идёт экран итога, а в картинку раскладываются по одному при показе — сто
    с лишним готовых картинок 1280×720 заняли бы полгигабайта."""

    def __init__(self, res, imya):
        self.res = res
        self.fajly = res.fajly_papki(f"img/fatality/{imya}", (".jpg", ".png"))
        self.dannye = [None] * len(self.fajly)
        self.gotovo = 0
        self.pervyj = None

    def podgruzit(self, skolko):
        while skolko > 0 and self.gotovo < len(self.fajly):
            try:
                with open(self.fajly[self.gotovo], "rb") as f:
                    self.dannye[self.gotovo] = f.read()
            except OSError as e:
                self.res.log(self.fajly[self.gotovo], f"кадр фаталити не читается: {e}")
            self.gotovo += 1
            skolko -= 1
        if self.pervyj is None and self.gotovo:
            self.pervyj = self.kadr(0)

    def kadr(self, n):
        if n >= self.gotovo:
            self.podgruzit(n + 1 - self.gotovo)
        b = self.dannye[n]
        if b is None:
            return None
        try:
            k = pygame.image.load(io.BytesIO(b), os.path.basename(self.fajly[n])).convert()
        except pygame.error as e:
            self.res.log(self.fajly[n], f"кадр фаталити не читается: {e}")
            self.dannye[n] = None
            return None
        return k if k.get_size() == (W, H) else pygame.transform.smoothscale(k, (W, H))


class Fataliti(Scena):
    """Ролик из кадров img/fatality/<имя>/NNNN.jpg, 24 к/с, под звук snd/fatality_<имя>.wav;
    кадры читаются заранее (KadryFataliti). Кадров нет — короткая заставка кодом."""
    NADPIS = 2.2            # сколько держится последний кадр с надписью, с

    def __init__(self, app, imya, dalshe, zapas=None):
        super().__init__(app)
        app.fon_buhty(None)
        self.imya, self.dalshe = imya, dalshe
        self.zapas = zapas if zapas is not None else KadryFataliti(self.res, imya)
        self.kps = N.FATALITI_KADROV_V_SEKUNDU
        n = len(self.zapas.fajly)
        self.dlit_rolika = n / self.kps if n else 3.0
        self.dlit = self.dlit_rolika + (self.NADPIS if n else 0.0)
        self.kadr = self.zapas.pervyj
        self.nomer = 0 if self.kadr is not None else -1
        self.ushli = False
        self.zvuk = None
        self.nebo = risunki.zaglushka_fon("prolog")
        cveta = (N.CVET_IGROKA, (214, 182, 112), (196, 120, 104), (128, 168, 120), (246, 240, 230))
        self.konfetti = [[random.uniform(0, W), random.uniform(-H, 0), random.uniform(60, 140),
                          random.uniform(0, 6.3), random.choice(cveta)] for _ in range(90)]
        self.vspyshki = [(random.uniform(200, W - 200), random.uniform(120, 360), random.uniform(0.2, 2.4),
                          random.choice(cveta)) for _ in range(9)]

    def _zavershit(self):
        if not self.ushli:
            self.ushli = True
            if self.zvuk:
                self.zvuk.fadeout(400)
            self.dalshe()

    def obrabotat(self, e):
        if dalshe_li(e) or klavisha(e, pygame.K_ESCAPE):
            self._zavershit()

    def obnovit(self, dt):
        super().obnovit(dt)
        if self.zvuk is None:
            self.app.zvuk(f"fatality_{self.imya}")
            self.zvuk = self.res.zvuk(f"fatality_{self.imya}") or False
        if self.t >= self.dlit:
            self._zavershit()
            return
        if self.zapas.fajly:
            self.zapas.podgruzit(8)
            n = min(len(self.zapas.fajly) - 1, int(self.t * self.kps))
            if n != self.nomer:
                self.nomer = n
                k = self.zapas.kadr(n)
                if k is not None:
                    self.kadr = k
        else:
            for k in self.konfetti:
                k[1] += k[2] * dt
                k[3] += dt * 4
                if k[1] > H + 10:
                    k[1] = -10

    def _zaglushka(self, ekran):
        ekran.blit(self.nebo, (0, 0))
        if self.imya == "salyut":
            for x, y, t0, cvet in self.vspyshki:
                tt = (self.t - t0) % 1.6
                if tt < 1.0:
                    r = 20 + tt * 90
                    for i in range(12):
                        a = i * math.tau / 12
                        pygame.draw.circle(ekran, cvet, (x + math.cos(a) * r, y + math.sin(a) * r + tt * tt * 30),
                                           max(1, int(6 * (1 - tt))))
        else:
            for i in range(3):
                x = (self.t * 300 + i * 420) % (W + 400) - 200
                y = 140 + i * 88
                for j in range(5):
                    pygame.draw.circle(ekran, N.CVET_IGROKA, (x - 40 - j * 34, y + 18 + j * j * 3), 7 - j)
                korpus = [(x - 30, y - 5), (x + 26, y - 5), (x + 36, y), (x + 26, y + 5), (x - 30, y + 5)]
                pygame.draw.polygon(ekran, N.CVET_BUMAGA, korpus)
                pygame.draw.polygon(ekran, CH, korpus, 2)
                krylo = [(x - 4, y), (x + 8, y), (x - 8, y + 24), (x - 18, y + 24)]
                pygame.draw.polygon(ekran, N.CVET_IGROKA, krylo)
                pygame.draw.polygon(ekran, CH, krylo, 2)
        for x, y, _, f, cvet in self.konfetti:
            if y > 0:
                pygame.draw.ellipse(ekran, cvet, (int(x), int(y), 8, int(3 + 4 * abs(math.sin(f)))))
        plashka_s_tekstom(ekran, self.res, self.res.s(f"fat_{self.imya}"), (W // 2, 560), KRUP)

    def narisovat(self, ekran):
        if self.kadr is not None:
            ekran.blit(self.kadr, (0, 0))
            k = (self.t - self.dlit_rolika + 0.3) / 0.45       # надпись выезжает к последнему кадру
            if k > 0:
                u = vyezd(min(1.0, k))
                plashka_s_tekstom(ekran, self.res, self.res.s(f"fat_{self.imya}"),
                                  (W // 2, 560 + round((1 - u) * 16)), KRUP)
        else:
            self._zaglushka(ekran)
        tekst_na_podlozhke(ekran, self.res, self.res.s("fat_propusk"), MEL, (W - 32, H - 24), SV, "bottomright",
              zhirnyj=False)
