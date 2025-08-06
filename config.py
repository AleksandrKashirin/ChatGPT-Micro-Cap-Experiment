"""Конфигурация для работы с Tinkoff Investments API."""

import os
from pathlib import Path

# Базовые настройки
SANDBOX_MODE = True  # True для песочницы, False для реальных торгов
CURRENCY = "RUB"
BASELINE_CAPITAL = 10000  # рублей вместо $100
MARKET_TIMEZONE = "Europe/Moscow"

# Путь к папке с токенами
TOKENS_DIR = Path(__file__).resolve().parent / "Tokens"


def get_token():
    """Получить токен в зависимости от режима работы."""
    if SANDBOX_MODE:
        token_file = TOKENS_DIR / "sandbox_token.txt"
        print("🏖️  Режим: ПЕСОЧНИЦА")
    else:
        token_file = TOKENS_DIR / "real_token.txt"
        print("💰 Режим: РЕАЛЬНЫЕ ТОРГИ")

    if not token_file.exists():
        raise FileNotFoundError(f"Файл с токеном не найден: {token_file}")

    with open(token_file, "r", encoding="utf-8") as f:
        token = f.read().strip()

    if not token:
        raise ValueError(f"Пустой токен в файле: {token_file}")

    return token


# Текущий токен
TINKOFF_TOKEN = get_token()

# Настройки для российского рынка
RUSSIAN_INDICES = {
    "IMOEX": "BBG004730N88",  # FIGI для индекса Мосбиржи
    "RTSI": "BBG004S68614",  # FIGI для RTS
}

# Торговые сессии (МСК)
TRADING_START = "10:00"
TRADING_END = "18:40"
