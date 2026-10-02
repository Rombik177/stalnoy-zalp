"""Кирпичи, из которых капитан складывает свою голову (game/kapitany/*.py).

Кирпич получает VidPolya — то, что капитан знает о чужом поле, — и
генератор случайных чисел; возвращает клетку (x, y) или None.
"""
from game import nastroyki as N
from game.pole import (R, NEIZV, MIMO, POPAL, ZAKRASHEN, OTKRYTA, PUSTO, PODOZR,
                       Deystvie, sluchajnaya_rasstanovka, sluchajnye_miny)

MOZHNO = (NEIZV, OTKRYTA, PODOZR)       # куда имеет смысл стрелять
ZAKRYTO = (MIMO, ZAKRASHEN, PUSTO)      # где корабля точно нет


def rasstavit_sluchajno(rng):
    return sluchajnaya_rasstanovka(rng)


def miny_sluchajno(rng, rasstanovka):
    return sluchajnye_miny(rng, rasstanovka)


def svobodnye(vid):
    s = vid.setka
    return [(x, y) for y in range(R) for x in range(R) if s[y][x] in MOZHNO]


def sluchajnyj_vystrel(vid, rng):
    """Случайный стрелок: любая клетка, о которой ничего не известно."""
    kl = svobodnye(vid)
    if not kl:
        kl = [(x, y) for y in range(R) for x in range(R) if vid.setka[y][x] == PUSTO]
    return rng.choice(kl)


def dobivanie(vid, rng):
    """Добивание раненого: открытая клетка, иначе продолжение линии попаданий."""
    s = vid.setka
    otkr = [(x, y) for y in range(R) for x in range(R) if s[y][x] == OTKRYTA]
    if otkr:
        return rng.choice(otkr)
    ranenye = [(x, y) for y in range(R) for x in range(R) if s[y][x] == POPAL]
    if not ranenye:
        return None
    est = set(ranenye)
    kand = []
    for x, y in ranenye:
        if (x - 1, y) in est or (x + 1, y) in est:
            napr = ((-1, 0), (1, 0))
        elif (x, y - 1) in est or (x, y + 1) in est:
            napr = ((0, -1), (0, 1))
        else:
            napr = ((-1, 0), (1, 0), (0, -1), (0, 1))
        for dx, dy in napr:
            nx, ny = x + dx, y + dy
            if 0 <= nx < R and 0 <= ny < R and s[ny][nx] in MOZHNO:
                kand.append((nx, ny))
    return rng.choice(kand) if kand else None


def shahmatka(vid, rng):
    """Через клетку: любой корабль длиннее одной палубы её не минует."""
    kl = [(x, y) for x, y in svobodnye(vid) if (x + y) % 2 == 0]
    return rng.choice(kl) if kl else sluchajnyj_vystrel(vid, rng)


def karta_veroyatnostej(vid):
    """Сколько раскладок оставшихся кораблей проходит через каждую клетку.
    Раскладки через раненые клетки весят в 26 раз больше."""
    s = vid.setka
    ves = [[0] * R for _ in range(R)]
    for dlina in vid.ostalis:
        for gorizont in ((True, False) if dlina > 1 else (True,)):
            for y in range(R if gorizont else R - dlina + 1):
                for x in range(R - dlina + 1 if gorizont else R):
                    kl = [(x + i, y) if gorizont else (x, y + i) for i in range(dlina)]
                    ranen = 0
                    for cx, cy in kl:
                        st = s[cy][cx]
                        if st in ZAKRYTO:
                            break
                        if st == POPAL or st == OTKRYTA:
                            ranen += 1
                    else:
                        w = 1 + 25 * ranen
                        for cx, cy in kl:
                            st = s[cy][cx]
                            if st == NEIZV:
                                ves[cy][cx] += w
                            elif st == PODOZR:
                                ves[cy][cx] += 2 * w
    return ves


def luchshaya_kletka(vid, rng):
    ves = karta_veroyatnostej(vid)
    luchshie, maks = [], 0
    for x, y in svobodnye(vid):
        v = ves[y][x]
        if v > maks:
            luchshie, maks = [(x, y)], v
        elif v == maks and v > 0:
            luchshie.append((x, y))
    return rng.choice(luchshie) if luchshie else sluchajnyj_vystrel(vid, rng)


def sluchajnoe_umenie(tip, rng):
    return Deystvie(tip, rng.randrange(R), rng.randrange(R), rng.random() < 0.5)


def hod_protivnika(boj, i, mozg):
    """Одно действие компьютерной стороны i: по желанию умение (каждое тратит ход —
    tratit_hod в N.UMENIYA), иначе выстрел. Возвращает события боя."""
    sob = []
    cel = boj.storony[1 - i].pole
    for _ in range(len(N.UMENIYA)):
        um = mozg.vybrat_umenie(cel.vid(), boj.gotovye(i))
        if um is None or um.tip not in N.UMENIYA or not boj.dostupno(i, um.tip):
            break
        sob += boj.vypolnit(um)
        if N.UMENIYA[um.tip]["tratit_hod"] or boj.pobeditel is not None or boj.hod != i:
            return sob
    vid = cel.vid()
    x, y = mozg.vybrat_vystrel(vid)
    if not boj.mozhno_vystrelit(i, x, y):
        x, y = sluchajnyj_vystrel(vid, boj.rng)
    sob += boj.vypolnit(Deystvie("vystrel", x, y))
    return sob


def naugad(vid, rng):
    """Совсем наугад: любая клетка, куда ещё не стреляли, — заметки не в счёт."""
    s = vid.setka
    kl = [(x, y) for y in range(R) for x in range(R) if s[y][x] in (NEIZV, OTKRYTA, PODOZR, PUSTO)]
    return rng.choice(kl)


def umnoe_umenie(vid, gotovye, rng):
    """Умения с толком: пока нет раненых — разведка, сонар, торпеда и залп
    туда, где по карте вероятностей корабль вероятнее всего."""
    if not gotovye:
        return None
    s = vid.setka
    if any(st in (POPAL, OTKRYTA) for ryad in s for st in ryad):
        return None
    ves = karta_veroyatnostej(vid)
    x, y = max(svobodnye(vid), key=lambda c: (ves[c[1]][c[0]], rng.random()))
    for u in ("razvedka", "sonar", "torpeda", "zalp"):
        if u not in gotovye:
            continue
        if u == "razvedka":
            return Deystvie(u, x, y)
        if u == "sonar":
            return Deystvie(u, x - 1, y - 1)
        if u == "torpeda":
            ryad = max(range(R), key=lambda r: sum(ves[r][c] for c in range(R) if s[r][c] in MOZHNO))
            return Deystvie(u, 0, ryad)
        gor = (sum(ves[y][c] for c in (x - 1, x + 1) if 0 <= c < R)
               >= sum(ves[r][x] for r in (y - 1, y + 1) if 0 <= r < R))
        return Deystvie(u, x, y, gor)
    return None


def umenie_bez_traty(vid, gotovye, rng):
    """Умение не впустую, но без расчёта: только пока нет раненых (их добивают
    выстрелом) и только туда, где о клетке ещё ничего не известно."""
    if not gotovye:
        return None
    s = vid.setka
    if any(st in (POPAL, OTKRYTA) for ryad in s for st in ryad):
        return None
    kl = [(x, y) for y in range(R) for x in range(R) if s[y][x] == NEIZV]
    if not kl:
        return None
    x, y = rng.choice(kl)
    u = rng.choice(gotovye)
    if u == "sonar":
        return Deystvie(u, x - 1, y - 1)
    if u == "torpeda":
        return Deystvie(u, 0, y)
    return Deystvie(u, x, y, rng.random() < 0.5)
