"""Сцены между боями: меню, пролог, карта кампании, живая бухта, разговор,
экран «VS», пари и верфь. Переход между сценами — app.perejti(...)."""
import math
import random

import threading

import pygame

from game import nastroyki as N
from game.pole import limit_vystrelov
from game import risunki
from game.buhta import Buhta, Chajki, svechenie, urovni_sveta
from game.buhta import drevko_vysotoj, narisovat_otrazhenie, otrazhenie, ten_na_vode
from game.kapitany import zagruzit
from game.ui import (Scena, Knopka, Pechat, plashka, ten_plashki, tekst, perenos,
                     pechatnyj_tekst, plavno, vyezd, pruzhina, smeshat)

W, H = N.SHIRINA, N.VYSOTA
from game.ui import podlozhka, tekst_na_podlozhke  # noqa: E402

CH = N.CVET_CHERNILA
SV = N.CVET_SVETLYJ
MEL, KRUP, LOGO = N.SHRIFT_MELKIJ, N.SHRIFT_KRUPNYJ, N.SHRIFT_LOGO
SERYJ_TEKST = (96, 96, 104)


# --- общее для сцен ---

def klik(e):
    return e.type == pygame.MOUSEBUTTONDOWN and e.button == 1


def klavisha(e, *klavishi):
    return e.type == pygame.KEYDOWN and e.key in klavishi


def dalshe_li(e):
    """Щелчок, пробел или Enter — «дальше»."""
    return klik(e) or klavisha(e, pygame.K_SPACE, pygame.K_RETURN)


def cvet_buhty(app, kap):
    return N.CVET_IGROKA if app.progress.proyden(kap.id) else kap.cvet


def portret_kapitana(res, kap, emociya, vysota):
    otn = kap.portrety.get(emociya) or kap.portrety["spokoen"]
    return res.portret(otn, kap.id, emociya, vysota, kap.cvet)


def portret_rumba(res, emociya, vysota):
    return res.portret(f"img/portrety/rumb_{emociya}.png", "rumb", emociya, vysota, N.CVET_RUMBA)


class Pelena:
    """Полупрозрачная чернильная пелена поверх картинки."""

    def __init__(self, alfa):
        self.s = pygame.Surface((W, H))
        self.s.fill(CH)
        self.s.set_alpha(alfa)

    def narisovat(self, ekran):
        ekran.blit(self.s, (0, 0))


def gradient(shirina, vysota, alfa, napravlenie):
    """Мягкая чернильная тень для читаемости текста: слева или снизу."""
    s = pygame.Surface((shirina, vysota), pygame.SRCALPHA)
    if napravlenie == "sleva":
        for x in range(shirina):
            pygame.draw.line(s, (*CH, int(alfa * (1 - x / shirina) ** 1.5)), (x, 0), (x, vysota))
    elif napravlenie == "sverhu":
        for y in range(vysota):
            pygame.draw.line(s, (*CH, int(alfa * (1 - y / vysota) ** 1.5)), (0, y), (shirina, y))
    else:
        for y in range(vysota):
            pygame.draw.line(s, (*CH, int(alfa * (y / vysota) ** 1.4)), (0, y), (shirina, y))
    return s


def kursor_dalshe(ekran, x, y, t):
    dy = math.sin(t * 4) * 2
    pygame.draw.polygon(ekran, CH, [(x - 7, y - 4 + dy), (x + 7, y - 4 + dy), (x, y + 5 + dy)])


def monety(ekran, res, n, pravyj_verh):
    """Счётчик монет: бумажная плашка с монеткой."""
    st = res.s("monety", n=n)
    rect = pygame.Rect(0, 0, res.shrift(MEL).size(st)[0] + 64, 48)
    rect.topright = pravyj_verh
    ten_plashki(ekran, rect)
    plashka(ekran, rect, alfa=245)
    pygame.draw.circle(ekran, (214, 184, 118), (rect.x + 24, rect.centery), 11)
    pygame.draw.circle(ekran, CH, (rect.x + 24, rect.centery), 11, 2)
    tekst(ekran, res, st, MEL, (rect.x + 44, rect.centery), CH, "midleft")


def plashka_s_tekstom(ekran, res, stroka, centr_verh, razmer=MEL, cvet=CH):
    rect = pygame.Rect(0, 0, res.shrift(razmer).size(stroka)[0] + 48, 40 if razmer == MEL else 52)
    rect.midtop = centr_verh
    rect.clamp_ip(ekran.get_rect())               # длинная надпись не уходит за край экрана
    ten_plashki(ekran, rect)
    plashka(ekran, rect, alfa=245)
    tekst(ekran, res, stroka, razmer, rect.center, cvet, "center")
    return rect


class KorablikNaKarte:
    """Наш авианосец на карте — спрайт флота в надетой окраске, уменьшенный и
    повёрнутый по ходу; повороты (шаг 4°) хранятся, в кадре не создаются."""
    DLINA = 104

    def __init__(self, res, skin):
        self.osnova = res.korabl("avianosec", skin, False, self.DLINA // 4)
        self.kesh = {}
        self.kurs = 0.0

    def narisovat(self, ekran, x, y, t):
        ugol = int(round(self.kurs / 4.0)) * 4 % 360
        s = self.kesh.get(ugol)
        if s is None:
            s = pygame.transform.rotozoom(self.osnova, ugol, 1.0)
            self.kesh[ugol] = s
        y += math.sin(t * 1.6) * 1.5
        ekran.blit(s, s.get_rect(center=(round(x), round(y))))


def skin_igroka(app):
    s = app.progress.skin
    return s() if callable(s) else s


class ZvukPechati:
    """Печать букв: тихий щелчок pechat_1..3 под буквами (без повтора подряд,
    не чаще раза в 0,07 с) и бормотание говорящего через 2–3 буквы."""
    CHASHCHE = 0.07

    def __init__(self, app):
        self.app = app
        self.pauza = 0.0
        self.do_bormotaniya = 2

    def obnovit(self, dt, novyh, bormotanie=None):
        self.pauza -= dt
        if not novyh:
            return
        if self.pauza <= 0:
            self.app.zvuk("pechat", 3, "pechat")
            self.pauza = self.CHASHCHE
        if bormotanie:
            self.do_bormotaniya -= novyh
            if self.do_bormotaniya <= 0:
                self.app.zvuk(f"bormotanie/{bormotanie}", 6, "bormotanie")
                self.do_bormotaniya = random.choice((2, 3))


# --- настройки ---

class PanelNastroek:
    """Громкость общая и фона, полный экран. Всё сразу пишется в прогресс."""
    X_ZNACHENIYA = 420         # «100 %» — посередине между «−» (304…360) и «+» (480…536)

    def __init__(self, app, zakryt):
        self.app, self.res, self.zakryt = app, app.res, zakryt
        self.t = 0.0
        self.rect = pygame.Rect(0, 0, 576, 424)
        # по сетке 8 px и не на заголовке игры: справа от него, если влезает, иначе под ним
        logo = pygame.Rect(88, 152, *self.res.shrift(LOGO).size(self.res.s("nazvanie")))
        sprava = (logo.right + 32 + 7) // 8 * 8
        if sprava + self.rect.w <= W - 32:
            self.rect.topleft = (sprava, 144)
        else:
            self.rect.topleft = (400, min(H - 16 - self.rect.h, (logo.bottom + 16 + 7) // 8 * 8))
        x, y = self.rect.topleft
        s = self.res.s
        self.kn = {
            "minus": Knopka((x + 304, y + 104, 56, 56), "−"),
            "plus": Knopka((x + 480, y + 104, 56, 56), "+"),
            "fon_minus": Knopka((x + 304, y + 176, 56, 56), "−"),
            "fon_plus": Knopka((x + 480, y + 176, 56, 56), "+"),
            "ekran": Knopka((x + 304, y + 248, 232, 56), ""),
            "nazad": Knopka((self.rect.centerx - 112, y + 336, 224, 56), s("nazad")),
        }

    def obrabotat(self, e):
        n = self.app.progress.nastrojki
        kn = self.kn
        if kn["minus"].nazhata(e):
            self.app.ustanovit_gromkost(n["gromkost"] - 0.1)
        elif kn["plus"].nazhata(e):
            self.app.ustanovit_gromkost(n["gromkost"] + 0.1)
        elif kn["fon_minus"].nazhata(e):
            self.app.ustanovit_gromkost(n["gromkost_fona"] - 0.1, fon=True)
        elif kn["fon_plus"].nazhata(e):
            self.app.ustanovit_gromkost(n["gromkost_fona"] + 0.1, fon=True)
        elif kn["ekran"].nazhata(e):
            self.app.pereklyuchit_ekran()
        elif kn["nazad"].nazhata(e) or klavisha(e, pygame.K_ESCAPE):
            self.app.zvuk("knopka")
            self.zakryt()
            return
        else:
            return
        self.app.zvuk("knopka")

    def narisovat(self, ekran, dt):
        self.t += dt
        p = self.t / 0.3
        rect = self.rect.move(0, round((1 - vyezd(p)) * 16))
        ten_plashki(ekran, rect)
        plashka(ekran, rect, alfa=250)
        res, n = self.res, self.app.progress.nastrojki
        tekst(ekran, res, res.s("nastr_zagolovok"), KRUP, (rect.x + 40, rect.y + 32), CH)
        ryady = (("nastr_gromkost", 132, res.s("procent", n=round(n["gromkost"] * 100))),
                 ("nastr_fon", 204, res.s("procent", n=round(n["gromkost_fona"] * 100))),
                 ("nastr_ekran", 276, None))
        for klyuch, yy, znach in ryady:
            tekst(ekran, res, res.s(klyuch), MEL, (rect.x + 40, rect.y + yy), CH, "midleft")
            if znach:
                tekst(ekran, res, znach, MEL, (rect.x + self.X_ZNACHENIYA, rect.y + yy), CH, "center")
        self.kn["ekran"].nadpis = res.s("vkl" if n["polnyj_ekran"] else "vykl")
        for k in self.kn.values():
            k.narisovat(ekran, res, self.app.mysh, p)


# --- меню ---

class Menyu(Scena):
    def __init__(self, app):
        super().__init__(app)
        app.fon_buhty(None)
        self.fon = self.res.kartinka("img/prolog/prolog_1.jpg", razmer=(1600, 900), alfa=False,
                                     zaglushka=lambda: risunki.zaglushka_fon("prolog", (1600, 900)))
        self.kadr = pygame.Surface((W, H), 0, self.fon)
        self.ten = gradient(640, H, 170, "sleva")
        self.chajki = Chajki(self.res, (0, 48, W, 280))
        s = self.res.s
        self.knopki = {
            "igrat": Knopka((96, 360, 288, 64), s("menyu_igrat"), razmer=KRUP),
            "nastrojki": Knopka((96, 440, 288, 64), s("menyu_nastrojki"), razmer=KRUP),
            "vyhod": Knopka((96, 520, 288, 64), s("menyu_vyhod"), razmer=KRUP),
        }
        self.nastrojki = None
        self.pelena = Pelena(110)

    def _zakryt_nastrojki(self):
        self.nastrojki = None

    def obrabotat(self, e):
        if self.nastrojki:
            self.nastrojki.obrabotat(e)
            return
        kn = self.knopki
        if kn["igrat"].nazhata(e):
            self.app.zvuk("knopka")
            self.app.perejti(Prolog(self.app))      # пролог — в начале каждой игры
        elif kn["nastrojki"].nazhata(e):
            self.app.zvuk("knopka")
            self.nastrojki = PanelNastroek(self.app, self._zakryt_nastrojki)
        elif kn["vyhod"].nazhata(e):
            self.app.rabotaet = False

    def obnovit(self, dt):
        super().obnovit(dt)
        self.chajki.obnovit(dt)
        self._dt = dt

    def narisovat(self, ekran):
        p = 0.5 + 0.5 * math.sin(self.t * 0.04 - 1.57)
        rect = pygame.Rect(0, 0, 1440, 810)
        rect.center = (int(720 + 160 * p), int(430 + 40 * p))
        pygame.transform.smoothscale(self.fon.subsurface(rect), (W, H), self.kadr)
        ekran.blit(self.kadr, (0, 0))
        self.chajki.narisovat(ekran)
        ekran.blit(self.ten, (0, 0))
        u = vyezd(self.poyavlenie(0.0, 0.5))
        tekst(ekran, self.res, self.res.s("nazvanie"), LOGO, (88, 152 + round((1 - u) * 16)), SV, ten=CH)
        tekst_na_podlozhke(ekran, self.res, self.res.s("podzagolovok"), MEL, (96, 248 + round((1 - u) * 16)), SV,
              zhirnyj=False)
        for i, k in enumerate(self.knopki.values()):
            k.narisovat(ekran, self.res, self.app.mysh, self.poyavlenie(0.15 + i * 0.06))
        if self.nastrojki:
            self.pelena.narisovat(ekran)
            self.nastrojki.narisovat(ekran, getattr(self, "_dt", 1 / 60))


# --- пролог ---

class Prolog(Scena):
    """Пролог: картины с параллаксом из data/prolog_sloi.json, фразы рассказчика и музыка.
    Идёт сам, Esc — сразу на карту; нет слоёв — запасной путь data/prolog.json."""
    SLOI = ("dal", "sred", "pered")     # снизу вверх
    PEREHOD = 0.5                       # наплыв между картинами, с
    NAPLYV = 0.6                        # фраза проявляется, с
    TAYANIE = 0.5                       # фраза тает перед следующей, с
    FRAZA_OSNOVA = 2.5                  # время фразы: основа + знаки / FRAZA_ZNAKOV_V_S, с
    FRAZA_ZNAKOV_V_S = 14
    FRAZA_MIN = 5.0
    PAUZA_V_KONCE = 1.5                 # после последней фразы — до карты, с
    MUZYKA = ("snd/muzyka_prolog.ogg", "snd/muzyka_prolog.wav")
    MUZYKA_DOLYA = 0.6                  # доля общей громкости игры
    MUZYKA_VHOD_MS = 1500
    MUZYKA_UHOD_MS = 1500
    CVET_ESC = (176, 170, 160)          # подсказка «Esc — пропустить»: мелко и бледно
    ALFA_ESC = 170
    # фонарь маяка на исходной картине 1600×900 и цвет его света;
    # маяк стоит на среднем слое и едет вместе с ним
    MAYAK = {"img/prolog/prolog_1.jpg": ((895, 190), (150, 118, 70)),
             "img/prolog/prolog_2.jpg": ((896, 190), (170, 72, 62))}
    PULS = 2.8              # период пульса света, с
    SVET_UROVNEJ = 24

    def __init__(self, app):
        super().__init__(app)
        app.fon_buhty(None)
        self.ishodnik = (1600, 900)               # размер исходных картин; sdvig_px — в его пикселях
        self.razmer_sloya = (round(W * 1.04), round(H * 1.04))
        self.kartiny, self.kadry = self._iz_sloev()
        if not self.kartiny:
            self.kartiny, self.kadry = self._iz_starogo()
        self.dlit_fraz = [self.dlit_frazy_dlya(k["tekst"]) for k in self.kadry]
        self.dlit_kartin = [0.0] * len(self.kartiny)      # сдвиг картины длится сумму времён её фраз
        for k, d in zip(self.kadry, self.dlit_fraz):
            self.dlit_kartin[k["kartina"]] += d
        self.zapas = (self.razmer_sloya[0] - W) / 2   # на сколько px слой может уехать без пустого края
        self.sloi_gotovye = {}                    # путь -> слой в размере razmer_sloya
        self.nomer = 0
        self.kartina = -1                         # индекс в self.kartiny
        self.t_kartiny = 0.0
        self.dlit_kartiny = 7.0
        self.t_frazy = 0.0
        self.dlit_frazy = self.FRAZA_MIN
        self.perehod = 1.0
        self.holst = pygame.Surface((W, H)).convert()     # картины без текста — то, что сейчас на экране
        self.holst.fill(CH)
        self.staryj = pygame.Surface((W, H)).convert()    # снимок холста в начале наплыва
        self.svet = {}
        self.chajki = Chajki(self.res, (0, 40, W, 230))
        self.niz = gradient(W, 272, 215, "snizu")
        self.shr = self.res.shrift(KRUP, False)
        self.zavershen = False
        self.muzyka_igraet = False
        esc = self.res.tekst(self.res.s("prolog_esc"), MEL, self.CVET_ESC, False).copy()   # своя копия: alpha
        esc.set_alpha(self.ALFA_ESC)                                                        # не трогает кэш
        self.esc = esc
        self.rect_esc = esc.get_rect(bottomright=(W - 32, H - 24))   # текст фраз кончается на H−72
        self.kto, self.strochki = "rasskazchik", []
        self.fraza, self.verh_frazy = None, H     # фраза целиком на прозрачном листе и его верх на экране
        if self.kadry:
            self._nachat(0)
            for put, _, alfa in self.kartiny[self.kartina]["sloi"]:
                self._sloj(put, alfa)
            self._muzyka_vkl()
        self._gotovo_v_fone = {}                  # путь -> слой, прочитанный и масштабированный фоновым потоком
        puti = [(put, alfa) for k in self.kartiny[1:] for put, _, alfa in k["sloi"] if self.res.est(put)]
        self._potok = threading.Thread(target=self._chitat_v_fone, args=(puti,), daemon=True)
        self._potok.start()

    def dlit_frazy_dlya(self, stroka):
        """Сколько секунд идёт фраза: 2,5 с + знаки / 14, не меньше 5 с (≈9,6 с на 100 знаков)."""
        return max(self.FRAZA_MIN, self.FRAZA_OSNOVA + len(stroka) / self.FRAZA_ZNAKOV_V_S)

    def dlitelnost(self):
        """Полная длина пролога, с: все фразы и пауза до карты."""
        return sum(self.dlit_fraz) + self.PAUZA_V_KONCE

    def _iz_sloev(self):
        """data/prolog_sloi.json -> (картины, реплики). Картина: слои (путь, сдвиг в px экрана,
        прозрачный ли), знак сдвига, исходник (по нему свет маяка), число реплик."""
        d = self.res.json("data/prolog_sloi.json", {})
        if not isinstance(d, dict) or not isinstance(d.get("kartiny"), list):
            return [], []
        razmer = d.get("razmer") or self.ishodnik
        self.ishodnik = (int(razmer[0]), int(razmer[1]))
        m = float(d.get("masshtab", 1.04))
        self.razmer_sloya = (round(W * m), round(H * m))
        k = W / self.ishodnik[0]                  # пиксели исходника -> пиксели экрана
        kartiny, kadry = [], []
        for opis in d["kartiny"]:
            if not isinstance(opis, dict):
                continue
            repliki = [r for r in opis.get("kadry") or () if isinstance(r, dict) and r.get("tekst")]
            if not repliki:
                continue
            sdvig = opis.get("sdvig_px") if isinstance(opis.get("sdvig_px"), dict) else {}
            if all(self.res.est(opis.get(s)) for s in self.SLOI):
                sloi = [(opis[s], float(sdvig.get(s, 0)) * k, i > 0) for i, s in enumerate(self.SLOI)]
            else:
                self.res.log(("prolog", opis.get("n")), f"пролог: у картины {opis.get('n')} нет слоёв — беру цельную")
                sloi = [(opis.get("celaya") or opis.get("istochnik") or "", float(sdvig.get("dal", 0)) * k, False)]
            for r in repliki:
                kadry.append({**r, "kartina": len(kartiny)})
            kartiny.append({"sloi": sloi, "napr": -1 if float(opis.get("napravlenie", 1)) < 0 else 1,
                            "istochnik": opis.get("istochnik", ""), "replik": len(repliki)})
        return kartiny, kadry

    def _iz_starogo(self):
        """Запасной путь: data/prolog.json и цельные img/prolog/prolog_N.jpg, сдвиг одним слоем."""
        d = self.res.json("data/prolog.json", {"kadry": []})
        kartiny, kadry, nomera = [], [], {}
        for r in d.get("kadry", []) if isinstance(d, dict) else ():
            if not (isinstance(r, dict) and r.get("tekst")):
                continue
            n = int(r.get("kartina", 1))
            if n not in nomera:
                nomera[n] = len(kartiny)
                put = f"img/prolog/prolog_{n}.jpg"
                kartiny.append({"sloi": [(put, 12.0, False)], "napr": 1 if n % 2 else -1, "istochnik": put,
                                "replik": 0})
            kartiny[nomera[n]]["replik"] += 1
            kadry.append({**r, "kartina": nomera[n]})
        return kartiny, kadry

    def _zaglushka(self):
        return risunki.zaglushka_fon("prolog", self.ishodnik)

    def _sloj(self, put, alfa):
        s = self.sloi_gotovye.get(put)
        if s is None:
            s = getattr(self, "_gotovo_v_fone", {}).pop(put, None)
            if s is not None:                     # поток уже прочёл: в кадре только convert
                s = self.sloi_gotovye[put] = s.convert_alpha() if alfa else s.convert()
            else:
                s = self.sloi_gotovye[put] = self.res.kartinka(put, razmer=self.razmer_sloya, alfa=alfa,
                                                               zaglushka=self._zaglushka)
        return s

    def _chitat_v_fone(self, puti):
        """Фоновый поток: чтение файла слоя и масштаб 1,04 — вне кадра (pygame отпускает GIL на чтении
        и масштабе). convert остаётся главному потоку. Не вышло — слой прочтёт _sloj сам."""
        for put, _ in puti:
            if self.zavershen:
                return
            try:
                s = pygame.image.load(self.res.put(put))
                if s.get_size() != self.razmer_sloya:
                    s = pygame.transform.smoothscale(s, self.razmer_sloya)
                self._gotovo_v_fone[put] = s
            except (pygame.error, ValueError, OSError):
                pass

    def _podgruzit(self):
        """Слои текущей и следующей картины — заранее, по одному за кадр. Файл читает фоновый поток,
        здесь только convert: чтение в кадре даёт рывок. Поток кончился, а слоя нет — читаем сами."""
        for i in (self.kartina, self.kartina + 1):
            if 0 <= i < len(self.kartiny):
                for put, _, alfa in self.kartiny[i]["sloi"]:
                    if put in self.sloi_gotovye:
                        continue
                    if put in self._gotovo_v_fone or i == self.kartina or not self._potok.is_alive():
                        self._sloj(put, alfa)
                    return
    def _nachat(self, i, lishnee=0.0):
        """Фраза i. lishnee — на сколько прошлая фраза пересидела в своём последнем кадре: время
        не теряется, и пролог длится ровно сумму времён фраз."""
        k = self.kadry[i]
        if k["kartina"] != self.kartina:
            if self.kartina >= 0:                 # снимок того, что на экране: наплыв без скачка
                self.staryj.blit(self.holst, (0, 0))
                self.perehod = 0.0
            self.kartina = k["kartina"]
            self.t_kartiny = lishnee
            self.dlit_kartiny = self.dlit_kartin[self.kartina]
        self.t_frazy = lishnee
        self.dlit_frazy = self.dlit_fraz[i]
        self.kto = k.get("kto", "rasskazchik")
        self.strochki = perenos(k["tekst"], self.shr, 1040)
        self.fraza, self.verh_frazy = self._list_frazy()
        self.chajki.serye = bool(k.get("serye_chajki"))

    def _list_frazy(self):
        """Фраза целиком на прозрачном листе — рисуется раз на фразу, в кадре только alpha и blit.
        Строки крупно, по центру, низ текста на H−72; у Румба над строками имя."""
        y0 = H - 72 - len(self.strochki) * 44
        verh = max(0, y0 - 48)                    # запас над строками под имя Румба
        lst = pygame.Surface((W, H - verh), pygame.SRCALPHA)
        for i, st in enumerate(self.strochki):
            s = self.shr.render(st, True, SV)
            lst.blit(s, s.get_rect(midtop=(W // 2, y0 - verh + i * 44)), special_flags=pygame.BLEND_RGBA_MAX)
        if self.kto == "rumb":
            tekst(lst, self.res, self.res.s("imya_rumb"), MEL, (W // 2, y0 - verh - 12), N.CVET_RUMBA,
                  "midbottom", ten=CH)
        return lst, verh

    def _zavershit(self):
        if self.zavershen:
            return
        self.zavershen = True
        self._muzyka_vykl()
        self.app.progress.d["prolog_viden"] = True
        self.app.progress.sohranit()
        self.app.perejti(Karta(self.app))

    def _muzyka_vkl(self):
        """Музыка пролога потоком через mixer.music, с повтором (запись может быть короче пролога),
        вход наплывом. Нет микшера — молча; нет файла или не читается — одна строка в журнал."""
        if not pygame.mixer.get_init():
            return
        put = next((p for p in self.MUZYKA if self.res.est(p)), None)
        if put is None:
            self.res.log(("prolog", "muzyka"), "пролог: нет snd/muzyka_prolog.ogg (.wav) — пролог идёт без музыки")
            return
        try:
            pygame.mixer.music.load(self.res.put(put))
            pygame.mixer.music.set_volume(self.res.gromkost * self.MUZYKA_DOLYA)
            pygame.mixer.music.play(loops=-1, fade_ms=self.MUZYKA_VHOD_MS)
            self.muzyka_igraet = True
        except pygame.error as e:
            self.res.log(("prolog", "muzyka"), f"пролог: музыка {put} не запустилась ({e}) — пролог идёт без музыки")

    def _muzyka_vykl(self):
        """Конец пролога (сам или Esc): музыка затухает и на карту не тянется."""
        if self.muzyka_igraet and pygame.mixer.get_init():
            pygame.mixer.music.fadeout(self.MUZYKA_UHOD_MS)
        self.muzyka_igraet = False

    def rect_podskazki(self):
        """Прямоугольник подсказки «Esc — пропустить» внизу справа, с запасом (для проверки перекрытий)."""
        return self.rect_esc.inflate(16, 8)

    def alfa_frazy(self):
        """Непрозрачность фразы 0…255: наплыв NAPLYV в начале, таяние TAYANIE в конце её времени."""
        a = plavno(self.t_frazy / self.NAPLYV) * plavno((self.dlit_frazy - self.t_frazy) / self.TAYANIE)
        return round(255 * a)

    def obrabotat(self, e):
        """Пролог идёт сам: щелчки и прочие клавиши не листают, Esc — сразу на карту."""
        if klavisha(e, pygame.K_ESCAPE):
            self._zavershit()

    def obnovit(self, dt):
        super().obnovit(dt)
        if not self.kadry:
            self._zavershit()
            return
        self.t_kartiny += dt
        self.t_frazy += dt
        self.perehod = min(1.0, self.perehod + dt / self.PEREHOD)
        if self.t_frazy >= self.dlit_frazy:
            if self.nomer + 1 < len(self.kadry):
                self.nomer += 1
                self._nachat(self.nomer, self.t_frazy - self.dlit_frazy)
            elif self.t_frazy >= self.dlit_frazy + self.PAUZA_V_KONCE:
                self._zavershit()
                return
        self._podgruzit()
        self.chajki.obnovit(dt)

    def _svet(self, surf, sx, sy, cvet):
        """Мягкий пульс фонаря маяка: радиальное свечение сложением."""
        urovni = self.svet.get(cvet)
        if urovni is None:
            urovni = self.svet[cvet] = urovni_sveta(svechenie(96, cvet, 2.2), self.SVET_UROVNEJ)
        puls = 0.6 + 0.4 * math.sin(self.t * math.tau / self.PULS)
        i = min(self.SVET_UROVNEJ - 1, int(puls * self.SVET_UROVNEJ) - 1)
        if i >= 0:
            k = urovni[i]
            surf.blit(k, (round(sx - k.get_width() / 2), round(sy - k.get_height() / 2)),
                      special_flags=pygame.BLEND_RGB_ADD)

    def sdvigi(self):
        """Сдвиг каждого слоя текущей картины, px экрана (для проверки): от −sdvig до +sdvig."""
        kart = self.kartiny[self.kartina]
        u = 2 * plavno(min(1.0, self.t_kartiny / self.dlit_kartiny)) - 1
        return [max(-self.zapas, min(self.zapas, kart["napr"] * sdvig * u)) for _, sdvig, _ in kart["sloi"]]

    def narisovat(self, ekran):
        if not self.kadry:
            ekran.fill(CH)
            return
        kart = self.kartiny[self.kartina]
        u = 2 * plavno(min(1.0, self.t_kartiny / self.dlit_kartiny)) - 1   # от −1 до +1 с разгоном и торможением
        sw, sh = self.razmer_sloya
        x0, y0 = (W - sw) / 2, (H - sh) / 2
        dx_mayaka = 0.0
        for i, (put, sdvig, alfa) in enumerate(kart["sloi"]):
            dx = max(-self.zapas, min(self.zapas, kart["napr"] * sdvig * u))
            self.holst.blit(self._sloj(put, alfa), (round(x0 + dx), round(y0)))
            if i <= 1:
                dx_mayaka = dx
        m = self.MAYAK.get(kart["istochnik"])
        if m:
            (px, py), cvet = m
            self._svet(self.holst, x0 + dx_mayaka + px * sw / self.ishodnik[0], y0 + py * sh / self.ishodnik[1], cvet)
        if self.perehod < 1.0:
            self.staryj.set_alpha(round(255 * (1 - plavno(self.perehod))))
            self.holst.blit(self.staryj, (0, 0))
        ekran.blit(self.holst, (0, 0))
        self.chajki.narisovat(ekran)
        ekran.blit(self.niz, (0, H - 272))
        a = self.alfa_frazy()
        if a > 0 and self.fraza is not None:
            self.fraza.set_alpha(a)
            ekran.blit(self.fraza, (0, self.verh_frazy))
        ekran.blit(self.esc, self.rect_esc)


# --- карта кампании ---

def progret_buhtu(app, kap):
    """Фоновый поток карты: картинки бухты (и её звуки) — в кэш ресурсов, пока судно плывёт 2 с,
    чтобы BuhtaScena открылась без замирания."""
    import os
    try:
        Buhta(app.res, kap, cvet_buhty(app, kap))
        papka = f"snd/buhty/{kap.buhta}"
        if pygame.mixer.get_init() and os.path.isdir(app.res.put(papka)):
            for imya in sorted(os.listdir(app.res.put(papka))):
                if imya.endswith((".ogg", ".wav")):
                    app.res.zvuk_fajl(f"{papka}/{imya}")
    except Exception as e:          # noqa: BLE001 — прогрев не должен ронять игру: сцена прочтёт сама
        app.res.log(("progrev", kap.id), f"прогрев бухты не вышел: {e}")


class Karta(Scena):
    """Карта кампании: порты — вымпелы (закрытый — обесцвеченный и
    полупрозрачный), наш авианосец плывёт к выбранному порту по дуге."""
    PLAVANIE = 2.0
    VYMPEL = "img/vympely/rybackaya.png"
    VYMPEL_VYSOTA = 80

    def __init__(self, app):
        super().__init__(app)
        app.fon_buhty(None)
        self.fon = self.res.kartinka("img/fon/karta.jpg", razmer=(W, H), alfa=False,
                                     zaglushka=lambda: risunki.zaglushka_fon("karta"))
        pr = app.progress
        obshchij = self.res.kartinka(self.VYMPEL, vysota=self.VYMPEL_VYSOTA)
        self.vympel_zakryt = pygame.transform.grayscale(obshchij)
        self.vympel_zakryt.fill((232, 228, 220), special_flags=pygame.BLEND_RGB_MULT)
        self.vympel_zakryt.set_alpha(130)
        self.porty = []
        for i, pos in enumerate(N.PORTY_NA_KARTE):
            kid = N.KAMPANIYA[i] if i < len(N.KAMPANIYA) else None
            kap = None
            if kid:
                try:
                    kap = zagruzit(kid)
                except Exception as e:      # битый файл капитана не валит карту
                    self.res.log(("kapitan", kid), f"капитан {kid} не загрузился: {e}")
            proyden = kap is not None and pr.proyden(kap.id)
            otkryt = kap is not None and (i == 0 or pr.proyden(N.KAMPANIYA[i - 1]))
            vympel = obshchij
            if kap is not None and getattr(kap, "vympel", None):
                vympel = self.res.kartinka(kap.vympel, vysota=self.VYMPEL_VYSOTA)
            self.porty.append({"pos": pos, "kap": kap, "otkryt": otkryt or proyden, "proyden": proyden,
                               "vympel": vympel})
        self.korablik = N.STARTOVAYA_TOCHKA
        for p in self.porty:
            if p["proyden"]:
                self.korablik = self._stoyanka(p["pos"])
        self.sudno = KorablikNaKarte(self.res, skin_igroka(app))
        self.plyvem = None                 # [откуда, куда, капитан, доля пути]
        self._progrev = False
        self.soobshchenie, self.t_soobshcheniya = "", 0.0
        self.kn_verf = Knopka((32, 648, 200, 56), self.res.s("karta_verf"))
        self.kn_menyu = Knopka((248, 648, 200, 56), self.res.s("karta_menyu"))

    @staticmethod
    def _stoyanka(pos):
        """Где наш корабль стоит у порта: от вымпела к середине бухты, на воде — ближайшая точка,
        где корпус (≈112×40) не задевает ни вымпел, ни подпись под ним (≈240×52)."""
        dx, dy = 640 - pos[0], 400 - pos[1]
        d = math.hypot(dx, dy) or 1.0
        x, y = pos
        zanyato = (pygame.Rect(x - 36, y - 56, 72, 90), pygame.Rect(x - 120, y + 34, 240, 52))
        for r in range(90, 260, 6):
            cx, cy = x + dx / d * r, y + dy / d * r
            if not any(z.colliderect((cx - 56, cy - 20, 112, 40)) for z in zanyato):
                break
        return cx, cy

    def obrabotat(self, e):
        if self.plyvem:
            return
        if klavisha(e, pygame.K_ESCAPE) or self.kn_menyu.nazhata(e):
            self.app.zvuk("knopka")
            self.app.perejti(Menyu(self.app))
        elif self.kn_verf.nazhata(e):
            self.app.zvuk("knopka")
            self.app.perejti(Verf(self.app))
        elif klik(e):
            for p in self.porty:
                if math.dist(e.pos, p["pos"]) <= 40:
                    if p["otkryt"]:
                        self.app.zvuk("knopka")
                        self.plyvem = [self.korablik, self._stoyanka(p["pos"]), p["kap"], 0.0]
                    else:
                        self.soobshchenie, self.t_soobshcheniya = self.res.s("karta_zakryt"), 2.0
                    return

    def obnovit(self, dt):
        super().obnovit(dt)
        self.t_soobshcheniya = max(0.0, self.t_soobshcheniya - dt)
        if self.plyvem:
            if not self._progrev:
                self._progrev = True
                threading.Thread(target=progret_buhtu, args=(self.app, self.plyvem[2]), daemon=True).start()
            self.plyvem[3] += dt / self.PLAVANIE
            if self.plyvem[3] >= 1.0:
                kap = self.plyvem[2]
                self.korablik = self.plyvem[1]
                self.plyvem = None
                self.app.perejti(BuhtaScena(self.app, kap))

    def _gde_korablik(self):
        """Точка на дуге пути; курс судна — по касательной к дуге."""
        if not self.plyvem:
            return self.korablik
        a, b, _, t = self.plyvem
        u = plavno(t)
        dx, dy = b[0] - a[0], b[1] - a[1]
        kx, ky = (a[0] + b[0]) / 2 - dy * 0.25, (a[1] + b[1]) / 2 + dx * 0.25
        x = (1 - u) ** 2 * a[0] + 2 * (1 - u) * u * kx + u * u * b[0]
        y = (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * ky + u * u * b[1]
        vx = 2 * (1 - u) * (kx - a[0]) + 2 * u * (b[0] - kx)
        vy = 2 * (1 - u) * (ky - a[1]) + 2 * u * (b[1] - ky)
        if vx or vy:
            self.sudno.kurs = math.degrees(math.atan2(-vy, vx))
        return x, y

    def _port(self, ekran, p, i):
        x, y = p["pos"]
        u = vyezd(self.poyavlenie(0.1 + i * 0.06, 0.35))
        if u <= 0:
            return
        v = p["vympel"] if p["otkryt"] else self.vympel_zakryt
        kach = 0.0
        if p["otkryt"] and not p["proyden"]:
            kach = math.sin(self.t * 2.0 + i) * 2.5          # ждущий порт чуть покачивает вымпел
        ekran.blit(v, v.get_rect(midbottom=(x, y + 30 + round((1 - u) * 12 + kach))))

    def _podpis(self, ekran, p, i):
        """Подпись порта на плашке — поверх кораблика."""
        if vyezd(self.poyavlenie(0.1 + i * 0.06, 0.35)) <= 0:
            return
        x, y = p["pos"]
        podpis = p["kap"].nazvanie_buhty if p["otkryt"] else self.res.s("karta_neizvesten")
        plashka_s_tekstom(ekran, self.res, podpis, (x, y + 38), cvet=CH if p["otkryt"] else SERYJ_TEKST)

    def narisovat(self, ekran):
        ekran.blit(self.fon, (0, 0))
        plashka_s_tekstom(ekran, self.res, self.res.s("karta_zagolovok"), (W // 2, 24), KRUP)
        monety(ekran, self.res, self.app.progress.monety, (W - 32, 24))
        for i, p in enumerate(self.porty):
            self._port(ekran, p, i)
        x, y = self._gde_korablik()
        self.sudno.narisovat(ekran, x, y, self.t)
        for i, p in enumerate(self.porty):            # подписи — поверх кораблика
            self._podpis(ekran, p, i)
        st = self.soobshchenie if self.t_soobshcheniya > 0 else self.res.s("karta_podskazka")
        tekst_na_podlozhke(ekran, self.res, st, MEL, (W - 32, H - 40), SV, "midright", zhirnyj=False,
                           alfa=N.PODLOZHKA_ALFA_PLOTNEE)
        self.kn_verf.narisovat(ekran, self.res, self.app.mysh, self.poyavlenie(0.2))
        self.kn_menyu.narisovat(ekran, self.res, self.app.mysh, self.poyavlenie(0.26))


# --- живая бухта ---

class BuhtaScena(Scena):
    """Прибытие в порт (кнопка «Поговорить») или возвращение после боя: после победы бухта
    перекрашивается в цвет игрока, а на причале по древку поднимается вымпел."""
    DREVKO_NIZ = (250, 560)           # низ древка — на настиле причала, позади тропы мальчишки
    DREVKO_VYSOTA = 176               # ~4,5 м при 39 px/м на причале
    VYMPEL_VYSOTA = 120

    def __init__(self, app, kap, posle=False, pobeda=False):
        super().__init__(app)
        self.kap, self.posle = kap, posle
        self.perekraska = posle and pobeda
        nach = kap.cvet if self.perekraska else cvet_buhty(app, kap)
        self.buhta = Buhta(self.res, kap, nach)
        self.buhta.zvuk_vkl = True                  # свисток боцмана — только в самой бухте
        self.vympel, self.drevko = None, None
        self.st_kapitan = self.res.s("buhta_kapitan", imya=kap.imya)
        stupen = app.progress.stupen(kap.id)            # реванш: капитан тренировался
        self.nadpis_stupeni = (self.res.tekst(self.res.s("buhta_stupen", imya=kap.imya_korotko, n=stupen), MEL, SV,
                                              False) if stupen > 1 and not posle else None)
        if self.perekraska:
            self.vympel = self.res.kartinka(kap.vympel, vysota=self.VYMPEL_VYSOTA,
                                            zaglushka=lambda: risunki.zaglushka_znachok(
                                                "vympel", (80, 120), N.CVET_IGROKA)).copy()   # прозрачность своя
            self.drevko = drevko_vysotoj(self.res, f"img/buhty/{kap.buhta}/flazhok_drevko.png", self.DREVKO_VYSOTA)
        nadpis = self.res.s("buhta_na_verf" if posle else "buhta_pogovorit")
        self.kn = Knopka((W // 2 - 144, 632, 288, 64), nadpis, akcent=N.CVET_IGROKA if posle else kap.cvet,
                         razmer=KRUP)
        self.verh = gradient(W, 176, 150, "sverhu")
        self.nachata = False
        app.fon_buhty(kap.buhta)

    def obrabotat(self, e):
        if klavisha(e, pygame.K_ESCAPE):
            self.app.perejti(Karta(self.app))
        elif self.kn.nazhata(e):
            self.app.zvuk("knopka")
            if self.posle:
                self.app.perejti(Verf(self.app))
            else:
                app, kap = self.app, self.kap
                chto = "revansh" if app.progress.stupen(kap.id) > 1 and "revansh" in kap.razgovory else "pered"
                app.perejti(Razgovor(app, kap, chto, lambda: app.perejti(VS(app, kap)), buhta=self.buhta))

    def obnovit(self, dt):
        super().obnovit(dt)
        self.buhta.obnovit(dt)
        if self.perekraska and not self.nachata and self.t > 0.8:
            self.nachata = True
            self.buhta.perekrasit(N.CVET_IGROKA)
            self.app.zvuk("monety")

    def narisovat(self, ekran):
        self.buhta.narisovat(ekran)
        if self.drevko is not None:
            x, y = self.DREVKO_NIZ
            ekran.blit(self.drevko, self.drevko.get_rect(midbottom=(x, y)))
            if self.nachata:                          # вымпел поднимается по древку и проявляется
                k = self.t - 0.8
                self.vympel.set_alpha(round(255 * min(1.0, k / 0.4)))
                verh = y - self.DREVKO_VYSOTA + 8
                ekran.blit(self.vympel, (x + 3, verh + round((1 - vyezd(k / 0.9)) * 56)))
        ekran.blit(self.verh, (0, 0))
        u = vyezd(self.poyavlenie(0.15, 0.35))
        y = 32 + round((1 - u) * 16)
        nazv = self.res.tekst(self.kap.nazvanie_buhty, KRUP, SV)
        kapitan = self.res.tekst(self.st_kapitan, MEL, SV, False)
        r1, r2 = nazv.get_rect(midtop=(W // 2, y)), kapitan.get_rect(midtop=(W // 2, y + 48))
        ramka = r1.union(r2)
        if self.nadpis_stupeni is not None:
            r3 = self.nadpis_stupeni.get_rect(midtop=(W // 2, y + 82))
            ramka = ramka.union(r3)
        podlozhka(ekran, ramka)
        ekran.blit(nazv, r1)
        ekran.blit(kapitan, r2)
        if self.nadpis_stupeni is not None:
            ekran.blit(self.nadpis_stupeni, r3)
        if self.perekraska and self.nachata:
            v = vyezd((self.t - 0.8) / 0.5)
            plashka_s_tekstom(ekran, self.res, self.res.s("buhta_perekrashena"), (W // 2, 560 + round((1 - v) * 16)))
        self.kn.narisovat(ekran, self.res, self.app.mysh, self.poyavlenie(0.3))


# --- разговор ---

class ZhivojPortret:
    """Портрет в разговоре: дышит, моргает (<портрет>_morg.png), у говорящего ходит рот
    (<портрет>_rot.png); смена эмоции — наплыв 0,2 с. Масштабы готовятся заранее, не в кадре."""
    SMENA = 0.2
    MORG = 0.12
    PAUZA_MORG = (2.5, 6.0)
    ROT = (0.10, 0.16)

    def __init__(self, res, kto, put, vysota, cvet, period):
        self.res, self.kto, self.put, self.vysota, self.cvet = res, kto, put, vysota, cvet
        self.period, self.faza = period, random.uniform(0, math.tau)
        self.t = 0.0
        self.em = self.em_bylo = None
        self.smena = 1.0
        self.morg, self.do_morg = 0.0, random.uniform(*self.PAUZA_MORG)
        self.rot, self.do_rta = False, 0.0
        self._nabory, self._masshtaby = {}, {}

    def emociya(self, em):
        if em == self.em:
            return
        if self.em is not None:
            self.em_bylo, self.smena = self.em, 0.0
        self.em = em

    def _nabor(self, em):
        n = self._nabory.get(em)
        if n is None:
            otn = self.put(em)
            osnova = self.res.portret(otn, self.kto, em, self.vysota, self.cvet)
            dop = []
            for sufiks in ("morg", "rot"):
                varianty = [f"{otn.rsplit('.', 1)[0]}_{sufiks}.png"]
                if em == "spokoen":
                    varianty.append(f"img/portrety/{self.kto}_{sufiks}.png")
                f = next((v for v in varianty if self.res.est(v)), None)
                dop.append(self.res.kartinka(f, vysota=self.vysota) if f else None)
            n = self._nabory[em] = (osnova, dop[0], dop[1])
        return n

    def obnovit(self, dt, rech):
        self.t += dt
        self.smena = min(1.0, self.smena + dt / self.SMENA)
        if self.morg > 0:
            self.morg -= dt
        else:
            self.do_morg -= dt
            if self.do_morg <= 0:
                self.morg, self.do_morg = self.MORG, random.uniform(*self.PAUZA_MORG)
        if rech:
            self.do_rta -= dt
            if self.do_rta <= 0:
                self.rot, self.do_rta = not self.rot, random.uniform(*self.ROT)
        else:
            self.rot, self.do_rta = False, 0.0

    def _kadr(self, em):
        osnova, morg, rot = self._nabor(em)
        if self.morg > 0 and morg is not None:
            return morg
        if self.rot and rot is not None:
            return rot
        return osnova

    def _postavit(self, ekran, img, q, midbottom, alfa):
        kl = (id(img), q)
        s = self._masshtaby.get(kl)
        if s is None:
            if len(self._masshtaby) > 64:
                self._masshtaby.clear()
            s = pygame.transform.smoothscale(img, (round(img.get_width() * q / 400),
                                                   round(img.get_height() * q / 400)))
            self._masshtaby[kl] = s
        s.set_alpha(alfa)
        ekran.blit(s, s.get_rect(midbottom=midbottom))

    def narisovat(self, ekran, midbottom, pritushen):
        q = round(400 * (1 + 0.01 * math.sin(math.tau * self.t / self.period + self.faza)))
        if self.smena < 1.0 and self.em_bylo is not None:
            sloi = ((self.em_bylo, 255), (self.em, int(255 * plavno(self.smena))))
        else:
            sloi = ((self.em, 255),)
        for em, alfa in sloi:
            img = self._kadr(em)
            if pritushen:
                img = self.res.pritushit(img)
            self._postavit(ekran, img, q, midbottom, alfa)


class Razgovor(Scena):
    """Разговор: Румб слева, капитан справа, говорящий ярче; текст по буквам с «бормотанием».
    Щелчок — дописать, ещё щелчок — дальше, Esc — всё; бухта за портретами приглушена."""
    VYSOTA = 470
    VYEZD = 0.35
    NIZ = H                   # портреты стоят на нижнем крае экрана

    def __init__(self, app, kap, chto, dalshe, buhta=None):
        super().__init__(app)
        self.kap, self.dalshe = kap, dalshe
        d = self.res.json(kap.razgovory.get(chto, ""), {"repliki": []})
        self.repliki = [r for r in d.get("repliki", []) if isinstance(r, dict) and r.get("tekst")]
        self.buhta = buhta or Buhta(self.res, kap, cvet_buhty(app, kap))
        self.buhta.zvuk_vkl = False                  # звук из бухты в разговоре не играет
        self.pelena = Pelena(77)                         # приглушить на 30 %
        self.emocii = {"rumb": "spokoen", kap.id: "spokoen"}
        self.portrety = {
            "rumb": ZhivojPortret(self.res, "rumb", lambda em: f"img/portrety/rumb_{em}.png",
                                  self.VYSOTA, N.CVET_RUMBA, 3.4),
            kap.id: ZhivojPortret(self.res, kap.id, lambda em: kap.portrety.get(em) or kap.portrety["spokoen"],
                                  self.VYSOTA, kap.cvet, 3.9),
        }
        self.nomer = -1
        self.pechat, self.strochki = Pechat(""), []
        self.govorit = None
        self.t_repliki = 0.0
        self.zvuk_pechati = ZvukPechati(app)
        self.zvuk_plashki = False
        self.zakonchen = False
        self.shr = self.res.shrift(N.SHRIFT_RAZGOVORA, False)
        self._sleduyushchaya()
        for kto, p in self.portrety.items():
            p.emociya(self.emocii[kto])
            p.smena = 1.0                                # первая эмоция — без наплыва
        app.fon_buhty(kap.buhta)

    def _sleduyushchaya(self):
        if self.nomer + 1 >= len(self.repliki):
            self.nomer = len(self.repliki)               # конец — сработает в obnovit
            return
        self.nomer += 1
        r = self.repliki[self.nomer]
        kto = "rumb" if r.get("kto") == "rumb" else self.kap.id
        if r.get("emociya"):
            self.emocii[kto] = r["emociya"]
            self.portrety[kto].emociya(r["emociya"])
        self.govorit = kto
        self.pechat = Pechat(r["tekst"])
        self.strochki = perenos(r["tekst"], self.shr, W - 128)
        self.t_repliki = 0.0

    def _konec(self):
        if not self.zakonchen:
            self.zakonchen = True
            self.dalshe()

    def obrabotat(self, e):
        if klavisha(e, pygame.K_ESCAPE):
            self._konec()
        elif dalshe_li(e) and self.t >= self.VYEZD:
            if not self.pechat.gotov:
                self.pechat.dopisat()
            else:
                self._sleduyushchaya()

    def obnovit(self, dt):
        super().obnovit(dt)
        self.buhta.obnovit(dt)
        if self.nomer >= len(self.repliki):
            self._konec()
            return
        if not self.zvuk_plashki:
            self.zvuk_plashki = True
            self.app.zvuk("kartochka")
        rech = self.t >= self.VYEZD and not self.pechat.gotov
        for kto, p in self.portrety.items():
            p.obnovit(dt, rech and kto == self.govorit)
        if self.t < self.VYEZD:
            return
        self.t_repliki += dt
        novyh = self.pechat.obnovit(dt)
        self.zvuk_pechati.obnovit(dt, novyh, "rumb" if self.govorit == "rumb" else self.kap.bormotanie)

    def narisovat(self, ekran):
        self.buhta.narisovat(ekran)
        self.pelena.narisovat(ekran)
        u = vyezd(self.t / self.VYEZD)
        for kto, cel, start in (("rumb", 264, -280), (self.kap.id, W - 264, W + 280)):
            pryzhok = 0.0
            if kto == self.govorit and self.t_repliki < 0.32:
                pryzhok = -10 * math.sin(math.pi * self.t_repliki / 0.32)
            cx = start + (cel - start) * u
            self.portrety[kto].narisovat(ekran, (int(cx), int(self.NIZ + pryzhok)), kto != self.govorit)
        box = pygame.Rect(32, 560, W - 64, 144)        # поверх груди портретов
        ten_plashki(ekran, box)
        plashka(ekran, box, alfa=252)
        if self.govorit:
            rumb = self.govorit == "rumb"
            imya = self.res.s("imya_rumb") if rumb else self.kap.imya_korotko
            ir = pygame.Rect(0, 0, self.res.shrift(MEL).size(imya)[0] + 48, 40)
            if rumb:
                ir.bottomleft = (box.x + 24, box.y + 12)
            else:
                ir.bottomright = (box.right - 24, box.y + 12)
            pygame.draw.rect(ekran, N.CVET_RUMBA if rumb else self.kap.cvet, ir, border_radius=12)
            pygame.draw.rect(ekran, CH, ir, 2, border_radius=12)
            tekst(ekran, self.res, imya, MEL, ir.center, CH, "center")
        pechatnyj_tekst(ekran, self.res, self.strochki, self.pechat.vidno(), (box.x + 32, box.y + 28),
                        N.SHRIFT_RAZGOVORA, CH, interval=36)
        if self.pechat.gotov and self.govorit:
            kursor_dalshe(ekran, box.right - 32, box.bottom - 24, self.t)
        tekst_na_podlozhke(ekran, self.res, self.res.s("podskazka_dalshe"), MEL, (W - 32, 24), SV, "topright",
              zhirnyj=False)


# --- «VS» ---

def myagkaya_ten(s, alfa=140):
    """Размытая тень надписи: сжать вчетверо и растянуть обратно."""
    w, h = s.get_size()
    pole = pygame.Surface((w + 24, h + 24), pygame.SRCALPHA)
    pole.blit(s, (12, 12))
    mal = pygame.transform.smoothscale(pole, (max(1, (w + 24) // 4), max(1, (h + 24) // 4)))
    ten = pygame.transform.smoothscale(mal, (w + 24, h + 24))
    ten.set_alpha(alfa)
    return ten


class VS(Scena):
    """Приглушённая бухта капитана; слева въезжает флагман, справа — капитан,
    по центру «VS» с мягкой тенью. Всё въезжает с замедлением (ease-out)."""
    DLIT = 3.4

    def __init__(self, app, kap):
        super().__init__(app)
        self.kap = kap
        self.buhta = Buhta(self.res, kap, cvet_buhty(app, kap))
        self.pelena = Pelena(150)
        self.flagman = self.res.kartinka("img/korabli/flagman_vs.png", razmer=(656, 367),
                                         zaglushka=risunki.zaglushka_flagman)
        self.rumb = portret_rumba(self.res, "spokoen", Razgovor.VYSOTA)
        self.portret = portret_kapitana(self.res, kap, "raduetsya", 500)
        self.vs = self.res.tekst(self.res.s("vs"), LOGO, N.CVET_BUMAGA)
        self.vs_ten = myagkaya_ten(self.res.tekst(self.res.s("vs"), LOGO, CH))
        self.st_flagman = self.res.s("vs_flagman")
        self.ushli = False
        app.fon_buhty(kap.buhta)

    def _dalshe(self):
        if not self.ushli:
            self.ushli = True
            self.app.perejti(Pari(self.app, self.kap))

    def obrabotat(self, e):
        if klavisha(e, pygame.K_ESCAPE) or (dalshe_li(e) and self.t > 1.2):
            self._dalshe()

    def obnovit(self, dt):
        super().obnovit(dt)
        self.buhta.obnovit(dt)
        if self.t >= self.DLIT:
            self._dalshe()

    def narisovat(self, ekran):
        t = self.t
        self.buhta.narisovat(ekran)
        self.pelena.narisovat(ekran)
        u = plavno(t / 0.4)
        if u < 1:                                     # Румб уходит со сцены разговора
            ekran.blit(self.rumb, self.rumb.get_rect(midbottom=(int(264 - u * 600), H)))
        v = vyezd((t - 0.15) / 0.8)
        if v > 0:
            ekran.blit(self.flagman, self.flagman.get_rect(midleft=(int(-680 + v * 688), 376)))
        k = vyezd((t - 0.25) / 0.8)
        ekran.blit(self.portret, self.portret.get_rect(midbottom=(int(W + 300 - 556 * k), H)))
        a = vyezd((t - 0.8) / 0.45)
        if a > 0:
            vs, ten = self.vs, self.vs_ten
            if a < 1:
                m = 1.18 - 0.18 * a
                vs = pygame.transform.smoothscale_by(vs, m)
                ten = pygame.transform.smoothscale_by(ten, m)
                vs.set_alpha(int(255 * a))
                ten.set_alpha(int(140 * a))
            ekran.blit(ten, ten.get_rect(center=(W // 2 + 4, 328 + 8)))
            ekran.blit(vs, vs.get_rect(center=(W // 2, 328)))
        p = vyezd((t - 1.0) / 0.4)
        if p > 0:
            dy = round((1 - p) * 16)
            tekst_na_podlozhke(ekran, self.res, self.st_flagman, KRUP, (336, 456 + dy), SV, "midtop")
            tekst_na_podlozhke(ekran, self.res, self.kap.imya, KRUP, (W - 256, 648 + dy), SV, "midtop",
                               alfa=N.PODLOZHKA_ALFA_PLOTNEE)


# --- пари ---

class Pari(Scena):
    GLUHOTA = 0.6            # с: второй щелчок по VS не выбирает пари сам

    def __init__(self, app, kap):
        super().__init__(app)
        self.kap = kap
        self.buhta = Buhta(self.res, kap, cvet_buhty(app, kap), s_lyudmi=False)
        self.pelena = Pelena(140)
        self.naved, self.zvuk_kart = None, False
        self.kartochki = [(pid, pygame.Rect(64 + i * 392, 216, 368, 296)) for i, pid in enumerate(N.PARI)]
        lim = limit_vystrelov(app.progress.stupen(kap.id))   # порог пари растёт со ступенью капитана
        self.nadpisi = {pid: (self.res.s("pari_" + pid, n=lim), self.res.s(f"pari_{pid}_opis", n=lim))
                        for pid in N.PARI}
        self.stavka = self.res.s("pari_stavka").split("\n")   # что умножается — монеты: «×2 монет»
        app.fon_buhty(kap.buhta)

    def obrabotat(self, e):
        if klavisha(e, pygame.K_ESCAPE):
            self.app.perejti(Karta(self.app))
        elif klik(e):
            for pid, rect in self.kartochki:
                if rect.collidepoint(e.pos):
                    self.app.zvuk("knopka")
                    from game.sceny_boj import Rasstanovka
                    self.app.perejti(Rasstanovka(self.app, self.kap, pid))
                    return

    def obnovit(self, dt):
        super().obnovit(dt)
        self.buhta.obnovit(dt)
        if not self.zvuk_kart:
            self.zvuk_kart = True
            self.app.zvuk("kartochka")
        naved = None
        for pid, r in self.kartochki:
            if r.collidepoint(self.app.mysh):
                naved = pid
        if naved != self.naved:
            self.naved = naved
            if naved is not None:
                self.app.zvuk("navedenie", uroven="navedenie")

    def narisovat(self, ekran):
        self.buhta.narisovat(ekran)
        self.pelena.narisovat(ekran)
        tekst_na_podlozhke(ekran, self.res, self.res.s("pari_zagolovok"), KRUP, (W // 2, 120), SV, "midtop")
        for i, (pid, rect) in enumerate(self.kartochki):
            p = self.poyavlenie(0.1 + i * 0.08, 0.35)
            if p <= 0:
                continue
            naved = rect.collidepoint(self.app.mysh)
            r = rect.move(0, round((1 - vyezd(p)) * 24) - (2 if naved else 0))
            ten_plashki(ekran, r, alfa=64 if naved else 48)
            plashka(ekran, r, alfa=255)
            akcent = (178, 174, 166) if pid == "net" else N.CVET_IGROKA
            pygame.draw.rect(ekran, akcent, (r.x + 24, r.y + 24, 48, 8), border_radius=4)
            y = r.y + 48
            for st in perenos(self.nadpisi[pid][0], self.res.shrift(KRUP), r.w - 48):
                tekst(ekran, self.res, st, KRUP, (r.x + 24, y), CH)
                y += 40
            y += 8
            for st in perenos(self.nadpisi[pid][1], self.res.shrift(MEL, False), r.w - 48):
                tekst(ekran, self.res, st, MEL, (r.x + 24, y), SERYJ_TEKST, zhirnyj=False)
                y += 30
            if pid != "net":
                for j, st in enumerate(self.stavka):
                    tekst(ekran, self.res, st, MEL, (r.x + 24, r.bottom - 20 - 28 * (len(self.stavka) - j)),
                          risunki.temnee(N.CVET_IGROKA, 0.7))


# --- верфь ---

class Verf(Scena):
    """Улучшения, окраска флота, фаталити и витрина медалей; флагман на воде у причала."""
    FLAGMAN_RAZMER = (334, 187)       # лист 1000×560 ×0,334: корпус ~315 px — между кромкой и карточками
    FLAGMAN_LEVO = 326                # левый край корпуса: каменная кромка verf.jpg кончается у x≈310 на y≈415
    VODA_Y = 415                      # ватерлиния в кадре: вода перед причалом с краном (стенка — y≈380)

    def __init__(self, app, revansh=None):
        super().__init__(app)
        app.fon_buhty(None)
        self.revansh = revansh                   # капитан реванша: кнопка «В бой» ведёт к VS, а не на карту
        res = self.res
        self.fon = res.kartinka("img/fon/verf.jpg", razmer=(W, H), alfa=False,
                                zaglushka=lambda: risunki.zaglushka_fon("verf"))
        self.flagman = res.kartinka("img/korabli/flagman_vs.png", razmer=self.FLAGMAN_RAZMER,
                                    zaglushka=risunki.zaglushka_flagman)
        ram = self.flagman.get_bounding_rect()          # корпус по видимым пикселям, а не по листу
        vl = ram.bottom - 3                             # корпус чуть сидит в воде
        self.flagman_pos = (self.FLAGMAN_LEVO - ram.x, self.VODA_Y - vl)
        self.flagman_otr = otrazhenie(self.flagman, vl, szhatie=0.6)
        self.flagman_ten = ten_na_vode(round(ram.w * 0.96), 16)
        self.flagman_ten_pos = (self.FLAGMAN_LEVO + (ram.w - self.flagman_ten.get_width()) // 2, self.VODA_Y - 14)
        self.kartochki = []
        x0 = 640
        for i, u in enumerate(N.PORYADOK_ULUCHSHENIJ):
            self.kartochki.append(("ul", u, pygame.Rect(x0 + (i % 2) * 296, 112 + (i // 2) * 120, 280, 112)))
        for i, sk in enumerate(N.PORYADOK_SKINOV):
            self.kartochki.append(("skin", sk, pygame.Rect(x0 + i * 144, 400, 136, 104)))
        for i, f in enumerate(N.PORYADOK_FATALITI):
            self.kartochki.append(("fat", f, pygame.Rect(x0 + i * 296, 560, 280, 96)))
        for i, u in enumerate(N.PORYADOK_UMENIJ):          # над флагманом, слева
            self.kartochki.append(("um", u, pygame.Rect(40 + i * 144, 144, 136, 88)))
        self.medali = [(m, pygame.Rect(40 + i * 136, 488, 120, 120)) for i, m in enumerate(N.MEDALI)]
        self._st_raz = {}                        # число выдач -> «×N», строка собирается один раз
        self.kn_karta = Knopka((40, 640, 240, 64), res.s("verf_v_boj" if revansh else "verf_na_kartu"))
        self.soobshchenie, self.t_soobshcheniya = "", 0.0
        self.ten = gradient(W, 176, 120, "sverhu")
        self.naved, self.zvuk_kart = None, False

    @staticmethod
    def _cena(vid, kid):
        if vid == "ul":
            return N.ULUCHSHENIYA[kid]
        if vid == "um":
            return N.CENY_UMENIJ[kid]
        if vid == "skin":
            return N.SKINY[kid]
        return N.FATALITI[kid]["cena"]

    def _skazat(self, st):
        self.soobshchenie, self.t_soobshcheniya = st, 1.8

    def obrabotat(self, e):
        if self.revansh is not None and self.kn_karta.nazhata(e):
            self.app.zvuk("knopka")
            self.app.perejti(VS(self.app, self.revansh))
            return
        if klavisha(e, pygame.K_ESCAPE) or self.kn_karta.nazhata(e):
            self.app.zvuk("knopka")
            self.app.perejti(Karta(self.app))
            return
        if not klik(e):
            return
        pr = self.app.progress
        for vid, kid, rect in self.kartochki:
            if not rect.collidepoint(e.pos):
                continue
            pid = f"{vid}_{kid}"
            if vid == "skin" and pr.kupleno(pid):
                pr.nadet_skin(kid)
                self.app.zvuk("knopka")
            elif pr.kupleno(pid):
                pass
            elif pr.kupit(pid, self._cena(vid, kid)):
                if vid == "skin":
                    pr.nadet_skin(kid)
                self.app.zvuk("monety")
                self._skazat(self.res.s("verf_kupil_na_boj"))
            else:
                self.app.zvuk("knopka")
                self._skazat(self.res.s("verf_malo"))
            return

    def obnovit(self, dt):
        super().obnovit(dt)
        self.t_soobshcheniya = max(0.0, self.t_soobshcheniya - dt)
        if not self.zvuk_kart:
            self.zvuk_kart = True
            self.app.zvuk("kartochka")
        naved = None
        for vid, kid, r in self.kartochki:
            if r.collidepoint(self.app.mysh):
                naved = (vid, kid)
        if naved != self.naved:
            self.naved = naved
            if naved is not None:
                self.app.zvuk("navedenie", uroven="navedenie")

    def _kartinka(self, vid, kid):
        res = self.res
        if vid == "ul":
            return res.kartinka(f"img/kartochki/{kid}.png", razmer=(80, 80),
                                zaglushka=lambda: risunki.zaglushka_znachok("kartochka", (80, 80)))
        if vid == "skin":
            return res.korabl("linkor", kid, False, 30)
        return res.kartinka(f"img/fatality/{kid}/0001.jpg", razmer=(112, 63), alfa=False,
                            zaglushka=lambda: risunki.zaglushka_fon("prolog", (112, 63)))

    def _status(self, vid, kid):
        pr = self.app.progress
        pid = f"{vid}_{kid}"
        if vid == "skin" and pr.skin == kid:
            return self.res.s("verf_nadeto"), True
        if pr.kupleno(pid):
            return self.res.s("verf_nadet" if vid == "skin" else "verf_kupleno_na_boj"), True
        return self.res.s("verf_cena", n=self._cena(vid, kid)), False

    def _podskazka(self):
        mysh = self.app.mysh
        for vid, kid, rect in self.kartochki:
            if rect.collidepoint(mysh):
                if vid == "ul":
                    return self.res.s(f"ul_{kid}_opis")
                if vid == "um":
                    return self.res.s("verf_um_opis")
                if vid == "fat":
                    return self.res.s(f"fat_{kid}_opis")
                return self.res.s(f"skin_{kid}")
        for m, rect in self.medali:
            if rect.collidepoint(mysh):
                return self.res.s(f"medal_{m}")
        return ""

    def _kartochka(self, ekran, vid, kid, rect, p):
        mysh = self.app.mysh
        naved = rect.collidepoint(mysh)
        r = rect.move(0, round((1 - vyezd(p)) * 16) - (2 if naved else 0))
        status, est = self._status(vid, kid)
        ten_plashki(ekran, r, alfa=64 if naved else 48)
        plashka(ekran, r, smeshat(N.CVET_BUMAGA, N.CVET_IGROKA, 0.14) if est else N.CVET_BUMAGA, 255)
        cvet_st = risunki.temnee(N.CVET_IGROKA, 0.7) if est else CH
        if vid == "um":                                  # умение: имя сверху, цена или «есть на бой» снизу
            tekst(ekran, self.res, self.res.s(f"umenie_{kid}"), MEL, (r.centerx, r.y + 12), CH, "midtop")
            tekst(ekran, self.res, status, MEL, (r.centerx, r.bottom - 6), cvet_st, "midbottom", zhirnyj=False)
            return
        img = self._kartinka(vid, kid)
        if vid == "skin":
            ekran.blit(img, img.get_rect(midtop=(r.centerx, r.y + 14)))
            tekst(ekran, self.res, self.res.s(f"skin_{kid}"), MEL, (r.centerx, r.y + 44), CH, "midtop")
            tekst(ekran, self.res, status, MEL, (r.centerx, r.bottom - 6), cvet_st, "midbottom", zhirnyj=False)
            return
        ekran.blit(img, (r.x + 16, r.y + 16))
        tx = r.x + 16 + img.get_width() + 16
        imya = self.res.s(f"{vid}_{kid}")
        y = r.y + 8
        for st in perenos(imya, self.res.shrift(MEL), r.right - tx - 12)[:2]:
            tekst(ekran, self.res, st, MEL, (tx, y), CH)
            y += 24
        tekst(ekran, self.res, status, MEL, (tx, r.bottom - 6), cvet_st, "bottomleft", zhirnyj=False)

    def narisovat(self, ekran):
        res = self.res
        ekran.blit(self.fon, (0, 0))
        ekran.blit(self.ten, (0, 0))
        ekran.blit(self.flagman_ten, self.flagman_ten_pos)
        x, y = self.flagman_pos
        narisovat_otrazhenie(ekran, self.flagman_otr, x, self.VODA_Y, self.t)
        ekran.blit(self.flagman, (x, y + round(math.sin(self.t * 1.2) * 1.5)))
        tekst_na_podlozhke(ekran, res, res.s("verf_zagolovok"), KRUP, (40, 32), SV)
        monety(ekran, res, self.app.progress.monety, (W - 40, 24))
        tekst_na_podlozhke(ekran, res, res.s("verf_uluchsheniya"), MEL, (640, 104), SV, "bottomleft")
        tekst_na_podlozhke(ekran, res, res.s("verf_skiny"), MEL, (640, 392), SV, "bottomleft")
        tekst_na_podlozhke(ekran, res, res.s("verf_fataliti"), MEL, (640, 552), SV, "bottomleft")
        tekst_na_podlozhke(ekran, res, res.s("verf_medali"), MEL, (40, 480), SV, "bottomleft")
        tekst_na_podlozhke(ekran, res, res.s("verf_umeniya"), MEL, (40, 136), SV, "bottomleft")
        for i, (vid, kid, rect) in enumerate(self.kartochki):
            p = self.poyavlenie(0.1 + i * 0.025, 0.3)
            if p > 0:
                self._kartochka(ekran, vid, kid, rect, p)
        est, schet = self.app.progress.d["medali"], self.app.progress.d["medali_schet"]
        for m, rect in self.medali:
            plashka(ekran, rect, alfa=255)
            img = res.kartinka(f"img/medali/{m}.png", razmer=(96, 96), zaglushka=lambda m=m: risunki.zaglushka_znachok(
                "medal", (96, 96), risunki.ZNACHKI[m]))
            ekran.blit(img if m in est else res.pritushit(res.pritushit(img)), img.get_rect(center=rect.center))
            n = schet.get(m, 0)
            if n:
                st = self._st_raz.get(n) or self._st_raz.setdefault(n, f"×{n}")
                tekst(ekran, res, st, MEL, (rect.right - 8, rect.bottom - 4), CH, "bottomright")
        st = self.soobshchenie if self.t_soobshcheniya > 0 else self._podskazka()
        if st:
            tekst_na_podlozhke(ekran, res, st, MEL, (640, 680), SV, "midleft", zhirnyj=False)
        self.kn_karta.narisovat(ekran, res, self.app.mysh, self.poyavlenie(0.2))
