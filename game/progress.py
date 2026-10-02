"""Один файл прогресса: монеты, покупки, медали, пройденные порты, настройки.

Купленное на верфи лежит в na_boj и действует один ближайший бой (vzyat_na_boj).
JSON с номером версии и только именами (id капитанов, ключи покупок); старые версии
разбирает _perevesti, битый файл откладывается в .slomano, и игра начинается заново.
"""
import copy
import json
import os
import shutil

from game import nastroyki as N

PO_UMOLCHANIYU = {
    "versiya": N.VERSIYA_SOHRANENIYA,
    "monety": 0,
    "pokupki": [],            # до версии 3 — вечные покупки; при загрузке уходят в na_boj
    "na_boj": [],             # на ближайший бой: "ul_bronya", "um_zalp", "skin_nochnoj", "fat_salyut"
    "skin": "bazovyj",
    "medali": [],
    "porty": [],              # id побеждённых капитанов
    "medali_schet": {},       # медаль -> сколько раз выдана (с версии 2 дают за каждый бой)
    "stupeni": {},            # id капитана -> ступень тренировки; нет записи — 1, первый бой
    "rekord_metkosti": 0,     # лучшая меткость за бой, %
    "prolog_viden": False,
    "nastrojki": {"gromkost": 0.8, "gromkost_fona": 1.0, "polnyj_ekran": False},
}

# что вообще можно купить на бой: по этому списку чистятся старые и битые файлы
NA_BOJ_MOZHNO = frozenset(
    ["ul_" + u for u in N.PORYADOK_ULUCHSHENIJ] + ["um_" + u for u in N.PORYADOK_UMENIJ]
    + ["skin_" + s for s in N.SKINY if s != "bazovyj"] + ["fat_" + f for f in N.FATALITI])


def _celoe(x):
    """Целое число, но не true/false: в JSON true — не «1 монета»."""
    return isinstance(x, int) and not isinstance(x, bool)


class Progress:
    def __init__(self, put=None):
        self.put = put or N.FAJL_PROGRESSA
        self.d = copy.deepcopy(PO_UMOLCHANIYU)
        self.zagruzit()

    def zagruzit(self):
        if not os.path.isfile(self.put):
            return
        try:
            with open(self.put, encoding="utf-8") as f:
                syroe = json.load(f)
            if not isinstance(syroe, dict):
                raise ValueError("в файле не словарь")
        except (OSError, ValueError) as e:
            try:
                shutil.copyfile(self.put, self.put + ".slomano")
            except OSError:
                pass
            print(f"[progress] файл не прочитан ({e}) — начинаю заново, копия в .slomano")
            return
        self.d = self._perevesti(syroe)

    @staticmethod
    def _perevesti(syroe):
        """Любая прошлая версия -> нынешняя. Версия 0 — черновик без номера и
        без настроек; неизвестные и испорченные поля берутся по умолчанию."""
        d = copy.deepcopy(PO_UMOLCHANIYU)
        if _celoe(syroe.get("monety")) and syroe["monety"] >= 0:
            d["monety"] = syroe["monety"]
        for k in ("pokupki", "medali", "porty"):
            if isinstance(syroe.get(k), list):
                d[k] = [x for x in syroe[k] if isinstance(x, str)]
        # версия 2 и раньше: покупки были навсегда — переносятся на один ближайший бой
        nb = syroe.get("na_boj")
        for x in (nb if isinstance(nb, list) else []) + d["pokupki"]:
            if isinstance(x, str) and x in NA_BOJ_MOZHNO and x not in d["na_boj"]:
                d["na_boj"].append(x)
        d["pokupki"] = []
        ms = syroe.get("medali_schet")
        if isinstance(ms, dict):
            d["medali_schet"] = {str(m): n for m, n in ms.items() if _celoe(n) and n > 0}
        for m in d["medali"]:                  # версия 1: медаль давали один раз на всю игру
            d["medali_schet"].setdefault(m, 1)
        st = syroe.get("stupeni")
        if isinstance(st, dict):
            d["stupeni"] = {str(k): n for k, n in st.items() if _celoe(n) and n >= 1}
        else:                                  # версия 1: капитан уже побеждён — впереди реванш
            d["stupeni"] = {k: 2 for k in d["porty"]}
        r = syroe.get("rekord_metkosti")
        if _celoe(r) and 0 <= r <= 100:
            d["rekord_metkosti"] = r
        skin = syroe.get("skin")
        if isinstance(skin, str) and skin in N.SKINY:     # список или словарь в словаре не ищут — TypeError
            d["skin"] = skin
        d["prolog_viden"] = syroe.get("prolog_viden") is True
        n = syroe.get("nastrojki")
        if isinstance(n, dict):
            for k in ("gromkost", "gromkost_fona"):
                g = n.get(k)
                if isinstance(g, (int, float)) and not isinstance(g, bool) and g == g:   # g == g: не NaN
                    d["nastrojki"][k] = max(0.0, min(1.0, float(g)))
            d["nastrojki"]["polnyj_ekran"] = n.get("polnyj_ekran") is True
        d["versiya"] = N.VERSIYA_SOHRANENIYA
        return d

    def sohranit(self):
        vremennyj = self.put + ".tmp"
        try:
            with open(vremennyj, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False, indent=1)
            os.replace(vremennyj, self.put)
        except OSError as e:
            print(f"[progress] не сохранилось: {e}")

    @property
    def monety(self):
        return self.d["monety"]

    @property
    def nastrojki(self):
        return self.d["nastrojki"]

    def kupleno(self, pid):
        """Куплено на ближайший бой; базовая окраска есть всегда."""
        return pid == "skin_bazovyj" or pid in self.d["na_boj"]

    def kupit(self, pid, cena):
        if self.kupleno(pid):                  # то же второй раз на тот же бой не берут
            return True
        if self.d["monety"] < cena:
            return False
        self.d["monety"] -= cena
        self.d["na_boj"].append(pid)
        self.sohranit()
        return True

    def uluchsheniya(self):
        """Что куплено на ближайший бой; список не трогает."""
        return [u for u in N.PORYADOK_ULUCHSHENIJ if self.kupleno("ul_" + u)]

    def umeniya(self):
        """Умения, купленные на ближайший бой: только их кнопки в бою горят."""
        return [u for u in N.PORYADOK_UMENIJ if self.kupleno("um_" + u)]

    def fataliti(self):
        return [f for f in N.PORYADOK_FATALITI if self.kupleno("fat_" + f)]

    def vzyat_na_boj(self):
        """Бой начался: забрать купленное и очистить список, окраска — снова базовая.
        Чем бы бой ни кончился, на следующий — покупать заново."""
        vzyato = {"ul": self.uluchsheniya(), "umeniya": self.umeniya(), "skin": self.skin,
                  "fataliti": self.fataliti()}
        if self.d["na_boj"] or self.d["skin"] != "bazovyj":
            self.d["na_boj"] = []
            self.d["skin"] = "bazovyj"
            self.sohranit()
        return vzyato

    @property
    def skin(self):
        s = self.d["skin"]
        return s if self.kupleno("skin_" + s) else "bazovyj"

    def nadet_skin(self, skin):
        if self.kupleno("skin_" + skin):
            self.d["skin"] = skin
            self.sohranit()

    def dobavit_monety(self, n):
        self.d["monety"] = max(0, self.d["monety"] + int(n))

    def dobavit_medal(self, m):
        """Медаль дают за каждый бой заново: в списке — один раз, счётчик растёт."""
        if m not in self.d["medali"]:
            self.d["medali"].append(m)
        self.d["medali_schet"][m] = self.d["medali_schet"].get(m, 0) + 1

    def skolko_medalej(self, m):
        return self.d["medali_schet"].get(m, 0)

    def stupen(self, kid):
        """Ступень тренировки капитана: 1 — первый бой, +1 за каждое его поражение."""
        return self.d["stupeni"].get(kid, 1)

    def povysit_stupen(self, kid):
        self.d["stupeni"][kid] = self.stupen(kid) + 1

    def obnovit_rekord(self, procent):
        """Рекорд меткости, %: возвращает рекорд с учётом этого боя."""
        if procent > self.d["rekord_metkosti"]:
            self.d["rekord_metkosti"] = int(procent)
        return self.d["rekord_metkosti"]

    def otmetit_port(self, kid):
        if kid not in self.d["porty"]:
            self.d["porty"].append(kid)

    def proyden(self, kid):
        return kid in self.d["porty"]
