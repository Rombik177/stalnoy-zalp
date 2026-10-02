"""Капитаны кампании: по файлу на капитана, порядок — nastroyki.KAMPANIYA."""
import importlib

_kesh = {}


def zagruzit(kid):
    """Описание капитана из game/kapitany/<kid>.py (объект KAPITAN)."""
    if kid not in _kesh:
        _kesh[kid] = importlib.import_module(f"game.kapitany.{kid}").KAPITAN
    return _kesh[kid]
