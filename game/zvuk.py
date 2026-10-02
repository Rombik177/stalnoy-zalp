"""Звук в два яруса.

Главный ярус — события боя, интерфейс, бормотание — играет через Resursy.igrat и сообщает
сюда о себе: пока он звучит, фон плавно приседает. Второстепенный ярус — фон бухты из
snd/buhty/<бухта>/: петли-слои и случайные вкрапления, описанные в sloi.json:
{"<слой>": {"fayl": "voda.ogg", "gromkost_db": -8, "rol": "vtorostepennyy",
"sluchaynye_vkrapleniya": false, "vhod_s": 2}}
Нет описания — запасные петли snd/port_petlya.ogg и snd/chayki_petlya.ogg.
"""
import os
import random
import re

import pygame

from game import nastroyki as N


def iz_db(db):
    return 10 ** (db / 20.0)


PRISEDANIE_DB = {"effekty": -8.0, "bormotanie": -5.0, "interfejs": -4.0, "pechat": -2.0, "navedenie": -1.0}
ZAPASNYE_SLOI = {
    "port_petlya": {"fayl": "port_petlya.ogg", "gromkost_db": -4, "rol": "vtorostepennyy"},
    "chayki_petlya": {"fayl": "chayki_petlya.ogg", "gromkost_db": -8, "rol": "vtorostepennyy"},
}


class Miksher:
    ATAKA = 0.03                  # с на полное приседание
    OTPUSK = 0.6
    VHOD = 2.0
    PAUZA_VKRAPLENIJ = (3.0, 10.0)
    RAZBROS_DB = (-4.0, 0.0)
    PANORAMA = 0.6

    def __init__(self, res):
        self.res = res
        self.vkl = pygame.mixer.get_init() is not None
        self.buhta = None
        self.sloi = []            # [kanal, uroven, vtorostepennyj]
        self.vkrapleniya = []     # [zvuki, uroven, vtorostepennyj, do_sleduyushchego, poslednij]
        self.vkr_tek = None       # [uroven, panorama, vtorostepennyj] — звучащее вкрапление
        self.kanal_vkraplenij = None
        self.vhod = self.VHOD
        self.vstuplenie = 0.0
        self.pris_db = 0.0
        self.vremya = 0.0
        self.aktivnye = {}        # ярус главного звука -> до какого времени звучит

    def glavnyj_zvuk(self, dlitelnost, uroven="effekty"):
        """Зовётся при каждом звуке главного яруса."""
        konec = self.vremya + dlitelnost
        if self.aktivnye.get(uroven, 0.0) < konec:
            self.aktivnye[uroven] = konec

    def _cel_db(self):
        cel = 0.0
        for u, konec in self.aktivnye.items():
            if konec > self.vremya:
                cel = min(cel, PRISEDANIE_DB.get(u, -8.0))
        return cel

    def _imena_vkraplenij(self, papka, imya, fayl):
        if isinstance(fayl, list):
            imena = [str(f) for f in fayl]
        elif isinstance(fayl, str) and "{n}" in fayl:
            imena = [fayl.format(n=n) for n in range(1, 10)]
        else:
            imena = [f"{imya}_{n}.wav" for n in range(1, 10)]
        imena = [f for f in imena if self.res.est(f"{papka}/{f}")]
        if not imena:                 # любые пронумерованные .wav папки: chayka_1..5.wav
            p = self.res.put(papka)
            if os.path.isdir(p):
                imena = sorted(f for f in os.listdir(p) if re.match(r".+_\d+\.wav$", f))
        return imena

    def vklyuchit_buhtu(self, buhta):
        """Фон бухты buhta (имя папки) или тишина при None."""
        if buhta == self.buhta:
            return
        self._ostanovit()
        self.buhta = buhta
        if buhta is None or not self.vkl:
            return
        papka = f"snd/buhty/{buhta}"
        opisanie = None
        if self.res.est(papka + "/sloi.json"):
            opisanie = self.res.json(papka + "/sloi.json", None)
        if not isinstance(opisanie, dict):
            self.res.log(("sloi", buhta), f"нет {papka}/sloi.json — звучат запасные петли порта и чаек")
            papka, opisanie = "snd", ZAPASNYE_SLOI
        self.vhod = self.VHOD
        nomer = 0
        for imya, o in opisanie.items():
            if not isinstance(o, dict):
                continue
            uroven = iz_db(float(o.get("gromkost_db", -8)))
            vtor = o.get("rol", "vtorostepennyy") != "glavnyy"
            if isinstance(o.get("vhod_s"), (int, float)):
                self.vhod = max(0.1, float(o["vhod_s"]))
            fayl = o.get("fayl")
            if o.get("sluchaynye_vkrapleniya"):
                zvuki = [z for z in (self.res.zvuk_fajl(f"{papka}/{f}")
                                     for f in self._imena_vkraplenij(papka, imya, fayl)) if z]
                if zvuki:
                    self.vkrapleniya.append([zvuki, uroven, vtor, random.uniform(*self.PAUZA_VKRAPLENIJ), -1])
            elif nomer < N.KANALOV_FONA - 1:
                z = self.res.zvuk_fajl(f"{papka}/{fayl if isinstance(fayl, str) else imya + '.ogg'}")
                if z is not None:
                    kanal = pygame.mixer.Channel(nomer)
                    nomer += 1
                    kanal.play(z, loops=-1)
                    kanal.set_volume(0.0)
                    self.sloi.append([kanal, uroven, vtor])
        self.kanal_vkraplenij = pygame.mixer.Channel(N.KANALOV_FONA - 1)
        self.vstuplenie = 0.0

    def _ostanovit(self):
        for kanal, _, _ in self.sloi:
            kanal.fadeout(500)
        if self.kanal_vkraplenij is not None:
            self.kanal_vkraplenij.fadeout(300)
        self.sloi, self.vkrapleniya, self.vkr_tek = [], [], None

    def _gromkost(self, uroven, vtor):
        v = self.vstuplenie
        g = self.res.gromkost * self.res.gromkost_fona * uroven * v * v * (3 - 2 * v)
        return g * iz_db(self.pris_db) if vtor else g

    def obnovit(self, dt):
        self.vremya += dt
        if not self.sloi and not self.vkrapleniya:
            return
        self.vstuplenie = min(1.0, self.vstuplenie + dt / self.vhod)
        cel = self._cel_db()
        if self.pris_db > cel:
            self.pris_db = max(cel, self.pris_db - 8.0 * dt / self.ATAKA)
        else:
            self.pris_db = min(cel, self.pris_db + 8.0 * dt / self.OTPUSK)
        for kanal, uroven, vtor in self.sloi:
            kanal.set_volume(self._gromkost(uroven, vtor))
        for v in self.vkrapleniya:
            v[3] -= dt
            if v[3] <= 0:
                v[3] = random.uniform(*self.PAUZA_VKRAPLENIJ)
                nomera = [i for i in range(len(v[0])) if i != v[4]] or [0]
                v[4] = random.choice(nomera)
                self.vkr_tek = [v[1] * iz_db(random.uniform(*self.RAZBROS_DB)),
                                random.uniform(-self.PANORAMA, self.PANORAMA), v[2]]
                self.kanal_vkraplenij.play(v[0][v[4]])
        if self.vkr_tek is not None and self.kanal_vkraplenij.get_busy():
            g = self._gromkost(self.vkr_tek[0], self.vkr_tek[2])
            pan = self.vkr_tek[1]
            self.kanal_vkraplenij.set_volume(g * min(1.0, 1 - pan), g * min(1.0, 1 + pan))
