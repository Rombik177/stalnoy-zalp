"""Интерфейс в одной системе: бумажные кнопки и плашки с чернильной
обводкой, два размера Nunito, отступы по сетке 8 px, мягкие появления
(ease-out 0,2–0,35 с) и едва заметный подъём кнопки под мышью."""
import pygame

from game import nastroyki as N

CHERNILA = N.CVET_CHERNILA


def plavno(t):
    """Разгон и торможение (smoothstep), t в [0, 1]."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def vyezd(t):
    """Быстрый старт и мягкая остановка (ease-out cubic)."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def pruzhina(t):
    """Мягкий выезд с едва заметным перебегом (слабый ease-out back)."""
    t = max(0.0, min(1.0, t))
    c = 0.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def smeshat(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def perenos(stroka, shrift, shirina):
    """Разбить строку на строчки не шире shirina."""
    strochki, tek = [], ""
    for slovo in stroka.split():
        proba = slovo if not tek else tek + " " + slovo
        if not tek or shrift.size(proba)[0] <= shirina:
            tek = proba
        else:
            strochki.append(tek)
            tek = slovo
    if tek:
        strochki.append(tek)
    return strochki


def tekst(ekran, res, stroka, razmer, pos, cvet=CHERNILA, yakor="topleft", zhirnyj=True, ten=None):
    """Надпись; ten — цвет мягкой тени для текста поверх картинок."""
    s = res.tekst(stroka, razmer, cvet, zhirnyj)
    r = s.get_rect(**{yakor: pos})
    if ten is not None:
        ekran.blit(res.tekst(stroka, razmer, ten, zhirnyj), (r.x + 2, r.y + 2))
    ekran.blit(s, r)
    return r



def podlozhka(ekran, rect, alfa=N.PODLOZHKA_ALFA):
    """Мягкая плашка #1B1E27 под надпись поверх картинки: поля 12×4 px, скругление."""
    r = pygame.Rect(rect).inflate(24, 8)
    plashka(ekran, r, CHERNILA, alfa, False, min(14, r.h // 2))


def tekst_na_podlozhke(ekran, res, stroka, razmer, pos, cvet=N.CVET_SVETLYJ, yakor="topleft", zhirnyj=True,
                       alfa=N.PODLOZHKA_ALFA):
    """Надпись поверх картинки на плашке: читается на любом фоне."""
    s = res.tekst(stroka, razmer, cvet, zhirnyj)
    r = s.get_rect(**{yakor: pos})
    podlozhka(ekran, r, alfa)
    ekran.blit(s, r)
    return r


_paneli = {}


def plashka(ekran, rect, cvet=N.CVET_BUMAGA, alfa=240, ramka=True, radius=N.RADIUS):
    """Бумажная плашка с чернильной обводкой; поверхности кэшируются."""
    rect = pygame.Rect(rect)
    kl = (rect.size, tuple(cvet), alfa, ramka, radius)
    s = _paneli.get(kl)
    if s is None:
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*cvet, alfa), s.get_rect(), border_radius=radius)
        if ramka:
            pygame.draw.rect(s, (*CHERNILA, 255), s.get_rect(), 2, border_radius=radius)
        _paneli[kl] = s
    ekran.blit(s, rect.topleft)


def ten_plashki(ekran, rect, radius=N.RADIUS, alfa=56):
    plashka(ekran, pygame.Rect(rect).move(0, 4), CHERNILA, alfa, False, radius)


class Knopka:
    """Одна форма кнопки на всю игру: бумага, чернильная обводка, полоска
    цветного акцента; под мышью едва заметно поднимается."""

    def __init__(self, rect, nadpis, akcent=N.CVET_IGROKA, razmer=N.SHRIFT_MELKIJ):
        self.rect = pygame.Rect(rect)
        self.nadpis = nadpis
        self.akcent = akcent
        self.razmer = razmer
        self.vkl = True
        self.vybrana = False
        self._pod = 0.0
        self._naved = False
        self._videl = False       # первый кадр молчит: мышь могла уже стоять на кнопке

    def nazhata(self, e):
        return (self.vkl and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1
                and self.rect.collidepoint(e.pos))

    def narisovat(self, ekran, res, mysh, poyavlenie=1.0):
        naved = self.vkl and self.rect.collidepoint(mysh)
        if naved and not self._naved and self._videl and poyavlenie >= 1.0:
            res.igrat("navedenie", uroven="navedenie")       # −10 дБ к клику (N.UROVNI)
        self._naved, self._videl = naved, True
        self._pod += ((1.0 if naved else 0.0) - self._pod) * 0.2
        sdvig = (1 - vyezd(poyavlenie)) * 16
        r = self.rect.move(0, round(sdvig - 2 * self._pod))
        ten_plashki(ekran, r.move(0, round(self._pod)), alfa=48 + int(16 * self._pod))
        bumaga = N.CVET_BUMAGA if self.vkl else N.CVET_VYKL
        if self.vybrana:
            bumaga = smeshat(bumaga, self.akcent, 0.22)
        pygame.draw.rect(ekran, bumaga, r, border_radius=N.RADIUS)
        if self.vkl:
            pygame.draw.rect(ekran, self.akcent, (r.centerx - 20, r.bottom - 9, 40, 3), border_radius=2)
        pygame.draw.rect(ekran, CHERNILA, r, 2, border_radius=N.RADIUS)
        cvet = CHERNILA if self.vkl else (128, 124, 118)
        tekst(ekran, res, self.nadpis, self.razmer, (r.centerx, r.centery - 2), cvet, "center")


class Pechat:
    """Текст по буквам: щелчок — дописать, ещё щелчок — дальше."""
    SKOROST = 40                      # букв в секунду

    def __init__(self, stroka):
        self.stroka = stroka
        self.pokazano = 0.0

    @property
    def gotov(self):
        return self.pokazano >= len(self.stroka)

    def obnovit(self, dt):
        """Сколько букв (не пробелов) появилось в этом кадре."""
        bylo = int(self.pokazano)
        self.pokazano = min(len(self.stroka), self.pokazano + dt * self.SKOROST)
        return sum(1 for ch in self.stroka[bylo:int(self.pokazano)] if ch.isalnum())

    def dopisat(self):
        self.pokazano = len(self.stroka)

    def vidno(self):
        return int(self.pokazano)


def pechatnyj_tekst(ekran, res, strochki, vidno, pos, razmer, cvet=CHERNILA, interval=32, centr=False):
    """Нарисовать первые vidno букв уже разбитого на строчки текста."""
    x, y = pos
    ostalos = vidno
    for i, st in enumerate(strochki):
        if ostalos <= 0:
            break
        kusok = st[:ostalos]
        ostalos -= len(st) + 1
        s = res.shrift(razmer, False).render(kusok, True, cvet)
        if centr:
            polnaya = res.shrift(razmer, False).size(st)[0]
            ekran.blit(s, (x - polnaya // 2, y + i * interval))
        else:
            ekran.blit(s, (x, y + i * interval))


def puzyr(ekran, res, stroka, niz_centr, shirina=248):
    """Пузырь реплики: бумага, обводка, хвостик вниз к портрету."""
    shr = res.shrift(N.SHRIFT_MELKIJ, False)
    strochki = perenos(stroka, shr, shirina - 32)
    h = 16 + len(strochki) * 28 + 12
    rect = pygame.Rect(0, 0, shirina, h)
    rect.midbottom = (niz_centr[0], niz_centr[1] - 16)
    ten_plashki(ekran, rect)
    plashka(ekran, rect, alfa=255)
    cx, b = rect.centerx, rect.bottom
    hvost = [(cx - 12, b - 2), (cx + 12, b - 2), (cx - 2, b + 14)]
    pygame.draw.polygon(ekran, N.CVET_BUMAGA, hvost)
    pygame.draw.line(ekran, CHERNILA, (cx - 13, b - 1), (cx - 2, b + 14), 2)
    pygame.draw.line(ekran, CHERNILA, (cx + 13, b - 1), (cx - 2, b + 14), 2)
    for i, st in enumerate(strochki):
        tekst(ekran, res, st, N.SHRIFT_MELKIJ, (rect.centerx, rect.y + 14 + i * 28), CHERNILA,
              "midtop", zhirnyj=False)


class Scena:
    """Основа сцены: время с появления и доступ к приложению."""

    def __init__(self, app):
        self.app = app
        self.res = app.res
        self.t = 0.0

    def obrabotat(self, e):
        pass

    def obnovit(self, dt):
        self.t += dt

    def narisovat(self, ekran):
        pass

    def poyavlenie(self, zaderzhka=0.0, dlit=0.3):
        return (self.t - zaderzhka) / dlit
