BOT_TOKEN = "9030472922:AAEqXq9uMRYTFBuOaPhjysxozrAFaIic1u0"
MANAGER_CHAT_ID = 5388087554

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 8080

# Типы конструкций и корректирующий коэффициент площади (учет масштаба, как на сайте)
WINDOW_TYPES = {
    "single": {"name": "Одностворчатое окно", "area_coef": 1.00, "is_balcony": False},
    "double": {"name": "Двухстворчатое окно", "area_coef": 0.91, "is_balcony": False},
    "triple": {"name": "Трехстворчатое окно", "area_coef": 0.86, "is_balcony": False},
    "balcony": {"name": "Балконный блок (окно + дверь)", "area_coef": 0.88, "is_balcony": True},
}

# Профильные системы с сайта ekipazh.com.ua (цена за м² изделия в грн)
PROFILES = {
    "ultra60": {
        "name": "Ekipazh ultra 60 (3 кам., 32 мм)",
        "price_m2": 3400,
        "hardware": "Axor / Winkhaus",
    },
    "ultra70": {
        "name": "Ekipazh ultra 70 (5 кам., 40 мм)",
        "price_m2": 4250,
        "hardware": "Axor / Winkhaus",
    },
    "wds76ad": {
        "name": "WDS 76AD (5 кам., 48 мм)",
        "price_m2": 4500,
        "hardware": "WDS / Winkhaus",
    },
    "wds76md": {
        "name": "WDS 76MD (6 кам., 48 мм)",
        "price_m2": 5000,
        "hardware": "Winkhaus",
    },
    "aluplast4000": {
        "name": "Aluplast 4000 (6 кам., 40 мм)",
        "price_m2": 5800,
        "hardware": "Winkhaus",
    },
    "aluplast7000": {
        "name": "Aluplast 7000 (6 кам., 44 мм)",
        "price_m2": 6500,
        "hardware": "Winkhaus",
    },
    "aluplast8000": {
        "name": "Aluplast 8000 (6 кам., 44 мм, премиум)",
        "price_m2": 7000,
        "hardware": "Winkhaus",
    },
}

# Варианты открывания створок (надбавка за фурнитуру в грн)
OPENING_TYPES = {
    "blind": {"name": "Глухое (не открывается)", "extra_price": 0},
    "tilt_turn_1": {"name": "1 поворотно-откидная створка", "extra_price": 950},
    "tilt_turn_2": {"name": "2 поворотно-откидные створки", "extra_price": 1850},
}

# Комплектация «Под ключ» (подоконник 250 мм, отлив 150 мм, монтаж, замер, доставка)
TURNKEY_BASE_PRICE = 2400       # базовая стоимость работ и комплектующих
TURNKEY_PER_M2 = 950            # доплата за квадратный метр монтажа/комплектующих

# Дополнительные опции
LAMINATION_COEF = 1.25          # +25% к стоимости профиля за ламинацию
MOSQUITO_NET_PRICE = 450        # фиксированная цена москитной сетки
