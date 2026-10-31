import re
from typing import Tuple

KNIVES_MAP = {
    "штык-нож m9": "M9 Bayonet",
    "штык нож m9": "M9 Bayonet",
    "м9": "M9 Bayonet",
    "m9": "M9 Bayonet",
    "штык-нож": "Bayonet",
    "штык нож": "Bayonet",
    "керамбит": "Karambit",
    "нож-бабочка": "Butterfly Knife",
    "бабочка": "Butterfly Knife",
    "складной нож": "Flip Knife",
    "нож с лезвием-крюком": "Gut Knife",
    "охотничий нож": "Huntsman Knife",
    "нож боуи": "Bowie Knife",
    "боуи": "Bowie Knife",
    "стилет": "Stiletto Knife",
    "коготь": "Talon Knife",
    "медвежий нож": "Ursus Knife",
    "наваха": "Navaja Knife",
    "нож выживания": "Survival Knife",
    "нож бродяга": "Nomad Knife",
    "нож «бродяга»": "Nomad Knife",
    "бродяга": "Nomad Knife",
    "скелетный нож": "Skeleton Knife",
    "паракорд-нож": "Paracord Knife",
    "классический нож": "Classic Knife",
    "тычковые ножи": "Shadow Daggers",
    "кукри": "Kukri Knife",
}

WEAPONS_MAP = {
    "ак-47": "AK-47",
    "ак47": "AK-47",
    "ак 47": "AK-47",
    "авп": "AWP",
    "м4а4": "M4A4",
    "м4а1-с": "M4A1-S",
    "м4а1": "M4A1-S",
    "юсп": "USP-S",
    "usp": "USP-S",
    "глок": "Glock-18",
    "дигл": "Desert Eagle",
    "пустынный орел": "Desert Eagle",
    "фамас": "FAMAS",
    "галил": "Galil AR",
    "скаут": "SSG 08",
    "муха": "SSG 08",
    "п90": "P90",
    "мп9": "MP9",
    "мак10": "MAC-10",
    "мак-10": "MAC-10",
}

SKINS_MAP = {
    "чистая вода": "Bright Water",
    "красная линия": "Redline",
    "красная сетка": "Crimson Web",
    "кровавая паутина": "Crimson Web",
    "азимов": "Asiimov",
    "волны": "Doppler",
    "гамма-волны": "Gamma Doppler",
    "градиент": "Fade",
    "мраморный градиент": "Marble Fade",
    "убийство": "Slaughter",
    "поверхностная закалка": "Case Hardened",
    "патина": "Case Hardened",
    "африканская сетка": "Safari Mesh",
    "северный лес": "Boreal Forest",
    "ночь": "Night",
    "городская маскировка": "Urban Masked",
    "воронёная сталь": "Blue Steel" ,
    "вороненая сталь": "Blue Steel",
    "дамасская сталь": "Damascus Steel",
    "зуб тигра": "Tiger Tooth",
    "пыльник": "Rust Coat",
    "ультрафиолет": "Ultraviolet",
    "автотроника": "Autotronic",
    "черный глянец": "Black Laminate",
    "император": "The Emperor",
    "императрица": "The Empress",
    "нео-нуар": "Neo-Noir",
    "неонуар": "Neo-Noir",
    "вой": "Howl",
    "история о драконе": "Dragon Lore",
    "драгон лор": "Dragon Lore",
    "скоростной зверь": "Hyper Beast",
    "вулкан": "Vulcan",
    "снежный вихрь": "Frontside Misty",
    "элитное снаряжение": "Elite Build",
    "аквамариновая месть": "Aquamarine Revenge",
    "огненный змей": "Fire Serpent",
    "поток информации": "Printstream",
    "принтстрим": "Printstream",
}

def translate_skin_input(user_input: str) -> Tuple[str, bool]:
    """
    Переводит введенное пользователем название (русское или английское) в официальный Steam формат.
    Возвращает (translated_name, is_knife_or_gloves).
    """
    raw = user_input.strip()
    is_knife = False
    
    # Разделяем по символу '|' если есть
    if "|" in raw:
        weapon_part, skin_part = raw.split("|", 1)
        weapon_part = weapon_part.strip()
        skin_part = skin_part.strip()
    else:
        weapon_part = raw
        skin_part = ""

    # Проверяем нож
    w_lower = weapon_part.lower()
    for ru_knife, en_knife in KNIVES_MAP.items():
        if ru_knife in w_lower or w_lower == ru_knife:
            weapon_part = en_knife
            is_knife = True
            break

    # Проверяем оружие
    if not is_knife:
        for ru_wep, en_wep in WEAPONS_MAP.items():
            if ru_wep in w_lower or w_lower == ru_wep:
                weapon_part = en_wep
                break

    # Проверяем нож по английским ключевым словам
    if any(k in weapon_part.lower() for k in ["knife", "bayonet", "karambit", "daggers"]):
        is_knife = True

    # Проверяем скин
    s_lower = skin_part.lower()
    for ru_skin, en_skin in SKINS_MAP.items():
        if ru_skin in s_lower or s_lower == ru_skin:
            skin_part = en_skin
            break

    if skin_part:
        return f"{weapon_part} | {skin_part}", is_knife
    return weapon_part, is_knife
