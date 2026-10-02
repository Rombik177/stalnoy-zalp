"""Капитан как вставка: описание и голова (как он думает).

Новый капитан — файл game/kapitany/<id>.py с KAPITAN = Kapitan(...) и строка "<id>"
в nastroyki.KAMPANIYA; картинки и звуки ищутся по именам файлов.
"""
from dataclasses import dataclass, field

from game import taktika

EMOCII = ("spokoen", "zlitsya", "raduetsya")


class MozgKapitana:
    """Голова капитана. Наследник переопределяет то, чем капитан отличается."""

    def __init__(self, rng, stupen=1):
        self.rng = rng
        self.stupen = max(1, int(stupen))   # сколько раз капитан тренировался после поражений (progress.json)

    def rasstavit_flot(self):
        """Список (imya, x, y, gorizont) — весь флот по правилам."""
        return taktika.rasstavit_sluchajno(self.rng)

    def postavit_miny(self, rasstanovka):
        """Две клетки (x, y) без кораблей."""
        return taktika.miny_sluchajno(self.rng, rasstanovka)

    def vybrat_vystrel(self, vid):
        """Клетка (x, y) по тому, что известно о чужом поле (VidPolya)."""
        return taktika.sluchajnyj_vystrel(vid, self.rng)

    def vybrat_umenie(self, vid, gotovye):
        """Deystvie одного из готовых умений или None — просто стрелять."""
        return None


@dataclass
class Kapitan:
    id: str                     # имя файла и приставка картинок
    imya: str                   # «Капитан Тимофей»
    imya_korotko: str           # «Тимофей» — в разговорах
    cvet: tuple                 # цвет краски
    buhta: str                  # папки img/buhty/<buhta> и snd/buhty/<buhta>
    nazvanie_buhty: str
    stroki_boya: dict           # popal / mimo / zakrasil / proigral
    razgovory: dict             # pered / pobeda / porazhenie -> data/razgovory/*.json
    povadka_sleduyushchego: str
    klass_mozga: type = MozgKapitana
    vympel: str = ""
    cvet_buhty: tuple = ()      # краска парусов и флажков в бухте (приглушена); пусто — cvet
    portrety: dict = field(default_factory=dict)
    bormotanie: str = ""
    pogoda: object = None

    def __post_init__(self):
        for e in EMOCII:
            self.portrety.setdefault(e, f"img/portrety/{self.id}_{e}.png")
        if not self.bormotanie:
            self.bormotanie = self.id
        if not self.vympel:
            self.vympel = f"img/vympely/{self.buhta}.png"
