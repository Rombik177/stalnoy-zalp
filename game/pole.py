"""Правила боя красками — без картинок и без pygame.

Поле 10×10, флот 1×4, 2×3, 3×2, 4×1; корабли не касаются даже углами. Попал — стреляешь
ещё раз. Ход игрока и ход капитана идут через один Boj.vypolnit.
"""
import random
from dataclasses import dataclass, field

from game import nastroyki as N

R = N.RAZMER_POLYA
DLINA = {imya: dlina for imya, dlina, _ in N.FLOT}               # по классу …
DLINA.update({imya: DLINA[klass] for imya, klass in N.SOSTAV})   # … и по id корабля

# Что противник знает о клетке (так её и рисуем на чужом поле).
NEIZV, MIMO, POPAL, ZAKRASHEN, OTKRYTA, PUSTO, PODOZR = range(7)


def v_pole(x, y):
    return 0 <= x < R and 0 <= y < R


def kletki_korablya(x, y, dlina, gorizont):
    if gorizont:
        return [(x + i, y) for i in range(dlina)]
    return [(x, y + i) for i in range(dlina)]


def mozhno_postavit(kletki, zanyato):
    """Клетки в поле и не касаются занятых даже углом."""
    for x, y in kletki:
        if not v_pole(x, y):
            return False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (x + dx, y + dy) in zanyato:
                    return False
    return True


def sluchajnaya_rasstanovka(rng):
    """Весь флот наугад по правилам: список (imya, x, y, gorizont)."""
    while True:
        zanyato, itog = set(), []
        for imya, klass in N.SOSTAV:
            dlina = DLINA[klass]
            for _popytka in range(300):
                g = rng.random() < 0.5
                x = rng.randrange(R - (dlina - 1 if g else 0))
                y = rng.randrange(R - (0 if g else dlina - 1))
                kl = kletki_korablya(x, y, dlina, g)
                if mozhno_postavit(kl, zanyato):
                    zanyato.update(kl)
                    itog.append((imya, x, y, g))
                    break
            else:
                break
        else:
            return itog


def sluchajnye_miny(rng, rasstanovka, n=N.MIN_NA_POLE):
    """n мин на пустые клетки (не на корабли)."""
    korabli = set()
    for imya, x, y, g in rasstanovka:
        korabli.update(kletki_korablya(x, y, DLINA[imya], g))
    pustye = [(x, y) for y in range(R) for x in range(R) if (x, y) not in korabli]
    return rng.sample(pustye, n)


def krest(x, y, luch):
    """Крест разведки: центр и по luch клеток в четыре стороны."""
    kl = [(x, y)]
    for d in range(1, luch + 1):
        kl += [(x - d, y), (x + d, y), (x, y - d), (x, y + d)]
    return [c for c in kl if v_pole(*c)]


def kvadrat(x, y, n):
    """Квадрат n×n с левым верхним углом (x, y), прижатый к полю."""
    x = max(0, min(R - n, x))
    y = max(0, min(R - n, y))
    return [(x + i, y + j) for j in range(n) for i in range(n)]


def liniya(x, y, gorizont):
    """Три клетки залпа с центром (x, y)."""
    kl = [(x + d, y) if gorizont else (x, y + d) for d in (-1, 0, 1)]
    return [c for c in kl if v_pole(*c)]


class Korabl:
    __slots__ = ("imya", "klass", "dlina", "x", "y", "gorizont", "popadaniya")

    def __init__(self, imya, x, y, gorizont):
        self.imya = imya                  # id: linkor, linkor_2 …
        self.klass = N.KLASS[imya]
        self.dlina = DLINA[imya]
        self.x, self.y, self.gorizont = x, y, gorizont
        self.popadaniya = set()

    def kletki(self):
        return kletki_korablya(self.x, self.y, self.dlina, self.gorizont)

    @property
    def zakrashen(self):
        return len(self.popadaniya) >= self.dlina


class VidPolya:
    """То, что о поле знает противник: сетка состояний и длины незакрашенных."""
    __slots__ = ("setka", "ostalis")

    def __init__(self, setka, ostalis):
        self.setka = setka
        self.ostalis = ostalis

    def kletka(self, x, y):
        return self.setka[y][x]


class Pole:
    """Одно поле: свой флот, свои мины и то, что о нём уже знает противник."""

    def __init__(self, rasstanovka, miny, bronya=False):
        self.korabli = [Korabl(imya, x, y, g) for imya, x, y, g in rasstanovka]
        self._proverit_rasstanovku()
        self.karta = {}
        for k in self.korabli:
            for kl in k.kletki():
                self.karta[kl] = k
        self.miny = set(tuple(m) for m in miny)
        for m in self.miny:
            if m in self.karta or not v_pole(*m):
                raise ValueError(f"мина на корабле или вне поля: {m}")
        self.bronya = bronya          # первое попадание не считается
        self.vystrely = {}            # (x, y) -> MIMO / POPAL
        self.otkryto = set()          # противник знает: здесь корабль
        self.pusto = set()            # противник знает: здесь пусто
        self.podozr = set()           # сонар сказал «есть» — где-то тут
        self.srabotali = set()        # мины, в которые уже попали

    def _proverit_rasstanovku(self):
        imena = sorted(k.imya for k in self.korabli)
        if imena != sorted(imya for imya, _ in N.SOSTAV):
            raise ValueError(f"флот неполный: {imena}")
        zanyato = set()
        for k in self.korabli:
            kl = k.kletki()
            if not mozhno_postavit(kl, zanyato):
                raise ValueError(f"корабль {k.imya} стоит не по правилам")
            zanyato.update(kl)

    def korabl(self, imya):
        for k in self.korabli:
            if k.imya == imya:
                return k
        raise KeyError(imya)

    def na_plavu(self, klass):
        """Хоть один корабль класса не закрашен — умение класса работает."""
        return any(k.klass == klass and not k.zakrashen for k in self.korabli)

    def sostoyanie(self, x, y):
        v = self.vystrely.get((x, y))
        if v is not None:
            k = self.karta.get((x, y))
            if k is not None and k.zakrashen:
                return ZAKRASHEN
            return v
        if (x, y) in self.otkryto:
            return OTKRYTA
        if (x, y) in self.pusto:
            return PUSTO
        if (x, y) in self.podozr:
            return PODOZR
        return NEIZV

    def vid(self):
        setka = [[self.sostoyanie(x, y) for x in range(R)] for y in range(R)]
        return VidPolya(setka, [k.dlina for k in self.korabli if not k.zakrashen])

    def ves_zakrashen(self):
        return all(k.zakrashen for k in self.korabli)

    def mozhno_strelyat(self, x, y):
        return v_pole(x, y) and (x, y) not in self.vystrely

    def popast(self, x, y):
        """Шар краски в клетку. Возвращает (результат, корабль или None)."""
        c = (x, y)
        if c in self.vystrely:
            return "povtor", None
        k = self.karta.get(c)
        self.podozr.discard(c)
        if k is None:
            self.vystrely[c] = MIMO
            self.otkryto.discard(c)
            self.pusto.discard(c)
            if c in self.miny and c not in self.srabotali:
                self.srabotali.add(c)
                return "mina", None
            return "mimo", None
        if self.bronya:
            self.bronya = False
            self.otkryto.add(c)       # броня выдала, что тут палуба
            return "bronya", k
        self.vystrely[c] = POPAL
        self.otkryto.discard(c)
        k.popadaniya.add(c)
        if k.zakrashen:
            self._obvesti(k)
            return "zakrasil", k
        return "popal", k

    def _obvesti(self, k):
        """Вокруг закрашенного корабля кораблей быть не может."""
        for x, y in k.kletki():
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    c = (x + dx, y + dy)
                    if v_pole(*c) and c not in self.karta and c not in self.vystrely:
                        self.pusto.add(c)
                        self.podozr.discard(c)

    def otkryt_kletku(self, rng):
        """Мина противника сработала — показать ему одну клетку нашего корабля."""
        kand = sorted(c for c in self.karta
                      if c not in self.vystrely and c not in self.otkryto)
        if not kand:
            return None
        c = rng.choice(kand)
        self.otkryto.add(c)
        self.podozr.discard(c)
        return c


@dataclass
class Deystvie:
    tip: str            # vystrel / razvedka / zalp / sonar / torpeda
    x: int
    y: int
    gorizont: bool = True


@dataclass
class Sobytie:
    tip: str            # shar / mina / razvedka / sonar / torpeda / vtoroj / pobeda
    kto: int            # чей это ход
    doska: int          # на чьём поле случилось
    x: int = 0
    y: int = 0
    rezultat: str = ""
    korabl: str = ""
    kletki: list = field(default_factory=list)


class Storona:
    """Сторона боя: своё поле, свои улучшения, перезарядки и счёт."""

    def __init__(self, pole, uluchsheniya=()):
        self.pole = pole
        self.ul = set(uluchsheniya)
        self.gotovnost = {u: 0 for u in N.UMENIYA}   # ходов до готовности
        self.vtoroj_vystrel = "vtoroj_vystrel" in self.ul
        self.vystrelov = 0      # ходов с краской: выстрел, залп, торпеда
        self.sharov = 0         # шаров краски всего
        self.popadanij = 0
        self.seriya = 0
        self.seriya_max = 0
        self.na_minah = 0       # сколько раз наш шар попал во вражескую мину

    def perezaryadka(self, umenie):
        n = N.UMENIYA[umenie]["perezaryadka"]
        if "perezaryadka" in self.ul:
            n -= 1
        return max(1, n)

    def razmer_sonara(self):
        return N.SONAR_KVADRAT_ULUCHSH if "sonar" in self.ul else N.SONAR_KVADRAT


class Boj:
    def __init__(self, storona0, storona1, pervyj=0, rng=None):
        self.storony = (storona0, storona1)
        self.hod = pervyj
        self.pobeditel = None
        self.dejstvij = 0
        self.rng = rng or random.Random()

    def dostupno(self, i, umenie):
        s = self.storony[i]
        return (self.pobeditel is None and self.hod == i
                and s.pole.na_plavu(N.UMENIYA[umenie]["korabl"]) and s.gotovnost[umenie] == 0)

    def gotovye(self, i):
        return [u for u in N.PORYADOK_UMENIJ if self.dostupno(i, u)]

    def mozhno_vystrelit(self, i, x, y):
        return (self.pobeditel is None and self.hod == i
                and self.storony[1 - i].pole.mozhno_strelyat(x, y))

    def vypolnit(self, d):
        """Выполнить действие того, чей ход. Возвращает список событий."""
        if self.pobeditel is not None:
            raise ValueError("бой уже окончен")
        self.dejstvij += 1
        if self.dejstvij > N.PREDEL_DEJSTVIJ:
            raise RuntimeError("бой не кончается — ошибка правил")
        i = self.hod
        s, cel = self.storony[i], self.storony[1 - i].pole
        sob = []
        if d.tip == "vystrel":
            if not cel.mozhno_strelyat(d.x, d.y):
                raise ValueError(f"в клетку {d.x},{d.y} стрелять нельзя")
            s.vystrelov += 1
            popal = self._shar(i, d.x, d.y, sob)
            self._posle_strelby(i, popal, sob)
            return sob

        if d.tip not in N.UMENIYA:
            raise ValueError(f"нет такого действия: {d.tip}")
        if not self.dostupno(i, d.tip):
            raise ValueError(f"умение {d.tip} не готово")
        s.gotovnost[d.tip] = s.perezaryadka(d.tip)

        if d.tip == "razvedka":
            kl = krest(d.x, d.y, N.RAZVEDKA_LUCH)
            for c in kl:
                if c in cel.vystrely:
                    continue
                cel.podozr.discard(c)
                if c in cel.karta:
                    cel.otkryto.add(c)
                else:
                    cel.pusto.add(c)
            sob.append(Sobytie("razvedka", i, 1 - i, d.x, d.y, kletki=kl))
        elif d.tip == "sonar":
            kl = kvadrat(d.x, d.y, s.razmer_sonara())
            est = any(c in cel.karta and c not in cel.vystrely for c in kl)
            for c in kl:
                if c in cel.vystrely or c in cel.otkryto:
                    continue
                if est:
                    if c not in cel.pusto:
                        cel.podozr.add(c)
                else:
                    cel.pusto.add(c)
                    cel.podozr.discard(c)
            sob.append(Sobytie("sonar", i, 1 - i, kl[0][0], kl[0][1],
                               "est" if est else "pusto", kletki=kl))
        elif d.tip == "zalp":
            s.vystrelov += 1
            popal = False
            for c in liniya(d.x, d.y, d.gorizont):
                if cel.mozhno_strelyat(*c) and self.pobeditel is None:
                    popal = self._shar(i, c[0], c[1], sob) or popal
            self._posle_strelby(i, popal, sob)
        elif d.tip == "torpeda":
            s.vystrelov += 1
            put, popal = [], False
            for x in range(R):
                c = (x, d.y)
                if c in cel.vystrely:
                    continue
                if c in cel.karta or (c in cel.miny and c not in cel.srabotali):
                    popal = self._shar(i, x, d.y, sob)
                    break
                cel.pusto.add(c)
                cel.podozr.discard(c)
                put.append(c)
            sob.insert(0, Sobytie("torpeda", i, 1 - i, 0, d.y, kletki=put))
            self._posle_strelby(i, popal, sob)
        if d.tip in ("razvedka", "sonar") and N.UMENIYA[d.tip]["tratit_hod"]:
            self._peredat_hod(i)        # залп и торпеда отдают ход сами, в _posle_strelby: попал — ещё выстрел
        return sob

    def _shar(self, i, x, y, sob):
        s, cel = self.storony[i], self.storony[1 - i]
        rez, k = cel.pole.popast(x, y)
        s.sharov += 1
        if rez in ("popal", "zakrasil"):
            s.popadanij += 1
            s.seriya += 1
            s.seriya_max = max(s.seriya_max, s.seriya)
        else:
            s.seriya = 0
        sob.append(Sobytie("shar", i, 1 - i, x, y, rez, k.imya if k else ""))
        if rez == "mina":
            s.na_minah += 1
            kl = s.pole.otkryt_kletku(self.rng)
            sob.append(Sobytie("mina", i, i, *(kl if kl else (-1, -1))))
        if rez == "zakrasil" and cel.pole.ves_zakrashen():
            self.pobeditel = i
        return rez in ("popal", "zakrasil")

    def _posle_strelby(self, i, popal, sob):
        if self.pobeditel is not None:
            sob.append(Sobytie("pobeda", i, 1 - i))
            return
        if popal:
            return                      # попал — стреляет ещё раз
        s = self.storony[i]
        if s.vtoroj_vystrel:            # улучшение: раз за бой промах не отдаёт ход
            s.vtoroj_vystrel = False
            sob.append(Sobytie("vtoroj", i, 1 - i))
            return
        self._peredat_hod(i)

    def _peredat_hod(self, i):
        """Очередь — противнику; его умения на ход ближе к готовности."""
        self.hod = 1 - i
        dr = self.storony[self.hod]
        for u, v in dr.gotovnost.items():
            if v > 0:
                dr.gotovnost[u] = v - 1


# --- награды за бой ---

def limit_vystrelov(stupen):
    """Порог пари «за N выстрелов» на ступени капитана: 40, 36, 32, дальше 30."""
    t = N.PARI_LIMIT_PO_STUPENI
    return t[min(max(1, stupen), len(t)) - 1]


def pari_vypolneno(boj, i, pari, limit=N.PARI_LIMIT_VYSTRELOV):
    """None — пари не было; True/False — выполнено или нет. limit — порог пари на выстрелы."""
    if pari == "net":
        return None
    if boj.pobeditel != i:
        return False
    s = boj.storony[i]
    if pari == "avianosec":
        return s.pole.na_plavu("avianosec")
    if pari == "vystrely40":
        return s.vystrelov <= limit
    return False


def medali_za_boj(boj, i):
    """Условия медалей (только за победу):
    меткость — попала не меньше MEDAL_TOCHNOST шаров краски;
    серия — MEDAL_SERIYA попаданий подряд без промаха;
    сберёг флагманы (bez_poter) — авианосец и оба линкора не закрашены целиком;
    сапёр — ни разу не попал во вражескую мину."""
    if boj.pobeditel != i:
        return []
    s = boj.storony[i]
    m = []
    if s.sharov and s.popadanij / s.sharov >= N.MEDAL_TOCHNOST:
        m.append("tochnost")
    if s.seriya_max >= N.MEDAL_SERIYA:
        m.append("seriya")
    if not any(k.zakrashen for k in s.pole.korabli if k.klass in ("avianosec", "linkor")):
        m.append("bez_poter")
    if s.na_minah == 0 and boj.storony[1 - i].pole.miny:
        m.append("saper")
    return m


def fataliti_dlya(boj, i, kupleno):
    """Какое фаталити играть: куплено и его корабль дожил до победы."""
    if boj.pobeditel != i:
        return None
    for f in N.PORYADOK_FATALITI:
        if f in kupleno and boj.storony[i].pole.na_plavu(N.FATALITI[f]["korabl"]):
            return f
    return None


def monety_za_boj(pobeda, pari, vypolneno, fataliti, medalej=0):
    """Итог в монетах и раскладка для экрана итога: [(ключ строки, число)].
    Медали — сверху, после множителей: MONETY_ZA_MEDAL за каждую."""
    baza = N.MONETY_POBEDA if pobeda else N.MONETY_PORAZHENIE
    raskladka = [("itog_baza_pobeda" if pobeda else "itog_baza_porazhenie", baza)]
    summa = float(baza)
    if pari != "net":
        k = N.PARI_VYPOLNENO if vypolneno else N.PARI_PROVALENO
        summa *= k
        raskladka.append(("itog_pari_ok" if vypolneno else "itog_pari_net", k))
    if fataliti:
        summa *= N.FATALITI_MNOZHITEL
        raskladka.append(("itog_fataliti", N.FATALITI_MNOZHITEL))
    if medalej:
        summa += N.MONETY_ZA_MEDAL * medalej
        raskladka.append(("itog_za_medali", f"+{N.MONETY_ZA_MEDAL * medalej}"))
    return int(round(summa)), raskladka
