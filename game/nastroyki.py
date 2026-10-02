"""Числа и таблицы «Стального залпа» в одном месте.

Всё, что хочется подкрутить при настройке игры (цены, перезарядки, пороги
медалей, раскладка экрана, громкость слоёв), живёт здесь, а не в сценах.
"""
import os

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SHIRINA, VYSOTA = 1280, 720
FPS = 60
NAZVANIE_OKNA = "Стальной залп"

# --- вид: полудетский и спокойный, всё в одной системе ---
SHRIFT_MELKIJ = 22                # два размера надписей
SHRIFT_KRUPNYJ = 34
SHRIFT_LOGO = 72                  # только название игры, «VS» и итог боя
SHRIFT_OSI = 20                   # оси поля и цифра перезарядки: цифра 16 px высотой
MASHTAB_SHRIFTA = 1.04             # Nunito шире Rubik: кегль × это число — та же ширина строк
SHRIFT_RAZGOVORA = 28             # текст разговора — крупнее надписей интерфейса
RADIUS = 16                       # скругление плашек и кнопок
CVET_BUMAGA = (0xF4, 0xEB, 0xDD)
CVET_CHERNILA = (0x1B, 0x1E, 0x27)
CVET_IGROKA = (78, 152, 194)      # лазурный #2E9BD6, чуть пыльный
CVET_IGROKA_BUHTA = (0x5E, 0x86, 0xA8)   # паруса и флажки бухты: тот же лазурный, насыщенность 0,44
PODLOZHKA_ALFA = 128              # плашка #1B1E27 под надписью поверх картинки — 50 %
PODLOZHKA_ALFA_PLOTNEE = 166      # 65 %: над светлой картой и тельняшкой 50 % мало для чтения
CVET_RUMBA = (196, 150, 104)
CVET_SVETLYJ = (250, 246, 238)    # текст поверх картинок
CVET_VYKL = (214, 208, 198)

# --- звук: два яруса ---
# главный ярус (события боя, интерфейс, бормотание) — доли от общей громкости
UROVNI = {"effekty": 1.0, "bormotanie": 0.50, "pechat": 0.22}   # 0, −6 и −13 дБ (печать букв — тихо)
NAVEDENIE_DB = -10                # звук наведения на клетку — на 10 дБ тише клика
UROVNI["navedenie"] = 10 ** (NAVEDENIE_DB / 20)   # наведение на кнопку, карточку, клетку
KANALOV_FONA = 6                  # каналы 0..5 отданы фону бухты

# --- поле боя ---
RAZMER_POLYA = 10
KLETKA = 52                       # поля занимают большую часть экрана
POLE_IGROKA = (48, 104)           # левый верхний угол своего поля
POLE_VRAGA = (712, 104)           # и поля противника
BUKVY = "АБВГДЕЖЗИК"

# классы флота: имя класса, палуб, умение
FLOT = (
    ("avianosec", 4, "razvedka"),
    ("linkor", 3, "zalp"),
    ("esminec", 2, "sonar"),
    ("podlodka", 1, "torpeda"),
)
# Классический флот, одинаковый у всех: 1×4, 2×3, 3×2, 4×1 — десять кораблей.
SKOLKO = {"avianosec": 1, "linkor": 2, "esminec": 3, "podlodka": 4}
# Каждый корабль: (id, класс). Первый корабль класса носит имя класса,
# следующие — linkor_2, esminec_3, podlodka_4.
SOSTAV = tuple((klass if n == 1 else f"{klass}_{n}", klass)
               for klass, _, _ in FLOT for n in range(1, SKOLKO[klass] + 1))
KLASS = dict(SOSTAV)
MIN_NA_POLE = 2

# Умения. Перезарядка — в своих ходах (ход кончается, когда очередь уходит к
# противнику). Любое умение тратит ход: после разведки и сонара очередь уходит
# к противнику, как после промаха.
UMENIYA = {
    "razvedka": {"korabl": "avianosec", "perezaryadka": 5, "tratit_hod": True},
    "zalp":     {"korabl": "linkor",    "perezaryadka": 4, "tratit_hod": True},
    "sonar":    {"korabl": "esminec",   "perezaryadka": 3, "tratit_hod": True},
    "torpeda":  {"korabl": "podlodka",  "perezaryadka": 5, "tratit_hod": True},
}
PORYADOK_UMENIJ = ("razvedka", "zalp", "sonar", "torpeda")
CENY_UMENIJ = {"razvedka": 20, "zalp": 25, "sonar": 15, "torpeda": 25}   # верфь, на один бой; капитану — бесплатно
RAZVEDKA_LUCH = 2                 # крест: центр и по 2 клетки в каждую сторону
SONAR_KVADRAT = 3
SONAR_KVADRAT_ULUCHSH = 4

# --- верфь: цены в монетах ---
ULUCHSHENIYA = {"bronya": 50, "vtoroj_vystrel": 40, "sonar": 30, "perezaryadka": 60}   # на один бой
PORYADOK_ULUCHSHENIJ = ("bronya", "vtoroj_vystrel", "sonar", "perezaryadka")
SKINY = {"bazovyj": 0, "kamuflyazh": 15, "nochnoj": 20, "paradnyj": 25}   # на один бой
PORYADOK_SKINOV = ("bazovyj", "kamuflyazh", "nochnoj", "paradnyj")
FATALITI = {"aviaudar": {"cena": 40, "korabl": "avianosec"},
            "salyut": {"cena": 40, "korabl": "linkor"}}
PORYADOK_FATALITI = ("aviaudar", "salyut")   # цена — на один бой
FATALITI_KADROV_V_SEKUNDU = 24

# --- награды ---
MONETY_POBEDA = 100
MONETY_PORAZHENIE = 20
PARI = ("net", "avianosec", "vystrely40")
PARI_LIMIT_VYSTRELOV = 40         # выстрел, залп и торпеда — по одному
PARI_LIMIT_PO_STUPENI = (40, 36, 32, 30)   # порог пари на ступени капитана 1, 2, 3, 4 и дальше
PARI_VYPOLNENO = 2.0
PARI_PROVALENO = 0.5
FATALITI_MNOZHITEL = 1.5

# медали (условия — game/pole.py, medali_za_boj)
MEDALI = ("tochnost", "seriya", "bez_poter", "saper")
MEDAL_TOCHNOST = 0.56            # доля попавших шаров краски за бой
MEDAL_SERIYA = 6                  # попаданий подряд без промаха
MONETY_ZA_MEDAL = 30              # за каждую выдачу: медаль дают за каждый бой заново

# --- кампания: новый капитан = файл в game/kapitany и строка здесь ---
KAMPANIYA = ["timoha"]
# порты по порядку кампании, точки сняты по img/fon/karta.jpg:
# рыбацкая, грузовой, маячный мыс, лагуна, военная гавань
PORTY_NA_KARTE = [(400, 215), (380, 440), (990, 300), (540, 570), (860, 575)]
STARTOVAYA_TOCHKA = (600, 470)   # открытая вода посреди бухты карты

PREDEL_DEJSTVIJ = 800             # сторож: бой длиннее — ошибка правил
VERSIYA_SOHRANENIYA = 3           # 2: счётчик медалей, ступени капитанов, рекорд меткости; 3: всё с верфи — на один бой (na_boj)
FAJL_PROGRESSA = os.path.join(KOREN, "progress.json")
FAJL_ZHURNALA = os.path.join(KOREN, "zhurnal.log")
