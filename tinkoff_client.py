"""Клиент для работы с Tinkoff Investments API."""

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from tinkoff.invest import Client, RequestError
from tinkoff.invest.sandbox.client import SandboxClient
from tinkoff.invest.schemas import CandleInterval

import config


class TinkoffClient:
    def __init__(self):
        self.token = config.TINKOFF_TOKEN
        self.sandbox_mode = config.SANDBOX_MODE
        print(f"🔧 Инициализация TinkoffClient")
        print(f"   Режим: {'ПЕСОЧНИЦА' if self.sandbox_mode else 'РЕАЛЬНЫЕ ТОРГИ'}")
        print(f"   Токен: {self.token[:10]}...{self.token[-5:]}")

        # Проверяем подключение
        try:
            if self.sandbox_mode:
                with SandboxClient(self.token) as client:
                    # Пробуем получить информацию об аккаунте в песочнице
                    accounts = client.users.get_accounts()
                    print(
                        f"✅ Подключение к SANDBOX успешно! Найдено аккаунтов: {len(accounts.accounts)}"
                    )
            else:
                with Client(self.token) as client:
                    # Пробуем получить информацию об аккаунте
                    accounts = client.users.get_accounts()
                    print(
                        f"✅ Подключение к REAL успешно! Найдено аккаунтов: {len(accounts.accounts)}"
                    )
        except Exception as e:
            print(f"❌ Ошибка подключения к API: {e}")
            print("   Проверьте токен и интернет-соединение")

    def _get_client(self):
        """Получить правильный клиент в зависимости от режима."""
        if self.sandbox_mode:
            return SandboxClient(self.token)
        else:
            return Client(self.token)

    def _get_figi_by_ticker(self, ticker: str) -> Optional[str]:
        """Получить FIGI по тикеру."""
        with self._get_client() as client:
            try:
                print(f"🔍 Поиск инструмента по тикеру: {ticker}")
                # Поиск инструмента по тикеру
                response = client.instruments.find_instrument(query=ticker)

                print(f"📊 Найдено инструментов: {len(response.instruments)}")

                # Предпочитаем BBG FIGI перед TCS
                bbg_instruments = []
                tcs_instruments = []

                for instrument in response.instruments:
                    print(
                        f"   - {instrument.ticker} | {instrument.name} | {instrument.figi}"
                    )
                    if instrument.ticker.upper() == ticker.upper():
                        if instrument.figi.startswith("BBG"):
                            bbg_instruments.append(instrument)
                        elif instrument.figi.startswith("TCS"):
                            tcs_instruments.append(instrument)

                # Сначала пробуем BBG FIGI
                if bbg_instruments:
                    figi = bbg_instruments[0].figi
                    print(f"✅ Найден BBG FIGI: {figi}")
                    return figi

                # Если BBG нет, берем TCS
                if tcs_instruments:
                    figi = tcs_instruments[0].figi
                    print(f"✅ Найден TCS FIGI: {figi}")
                    return figi

                print(f"❌ Точное совпадение по тикеру {ticker} не найдено")
                return None
            except RequestError as e:
                print(f"❌ RequestError при поиске FIGI для {ticker}: {e}")
                return None
            except Exception as e:
                print(f"❌ Общая ошибка при поиске FIGI для {ticker}: {e}")
                return None

    def get_current_price(self, figi_or_ticker: str) -> Optional[float]:
        """Получить текущую цену инструмента."""
        print(f"🔍 Ищем цену для: {figi_or_ticker}")
        figi = figi_or_ticker

        # Если передан тикер, получаем FIGI
        if not (figi.startswith("BBG") or figi.startswith("TCS")):
            print(f"🔍 Ищем FIGI для тикера: {figi_or_ticker}")
            figi = self._get_figi_by_ticker(figi_or_ticker)
            if not figi:
                print(f"❌ FIGI не найден для тикера: {figi_or_ticker}")
                return None
            print(f"✅ Найден FIGI: {figi}")

        with self._get_client() as client:
            try:
                print(f"🌐 Запрашиваем цену для FIGI: {figi}")
                # Получаем последнюю цену
                response = client.market_data.get_last_prices(figi=[figi])

                print(f"📊 Ответ API: {response}")

                if response.last_prices and len(response.last_prices) > 0:
                    price = response.last_prices[0].price
                    print(f"💰 Получена цена: {price.units}.{price.nano}")

                    # Проверяем, что цена не нулевая
                    if price.units == 0 and price.nano == 0:
                        print(
                            "⚠️  Получена нулевая цена, пробуем получить цену через OrderBook"
                        )
                        return self._get_price_from_orderbook(figi, client)

                    # Конвертируем из Quotation в float
                    result = float(f"{price.units}.{price.nano // 1000000:02d}")
                    print(f"✅ Итоговая цена: {result}")
                    return result
                else:
                    print("❌ Пустой ответ от API")

                return None
            except RequestError as e:
                print(f"❌ RequestError при получении цены для {figi_or_ticker}: {e}")
                return None
            except Exception as e:
                print(f"❌ Общая ошибка при получении цены для {figi_or_ticker}: {e}")
                return None

    def _get_price_from_orderbook(self, figi: str, client) -> Optional[float]:
        """Получить цену из стакана заявок."""
        try:
            print(f"📖 Пробуем получить цену из OrderBook для {figi}")
            orderbook = client.market_data.get_order_book(figi=figi, depth=1)

            if orderbook.bids and len(orderbook.bids) > 0:
                bid_price = orderbook.bids[0].price
                result = float(f"{bid_price.units}.{bid_price.nano // 1000000:02d}")
                print(f"✅ Цена из OrderBook (bid): {result}")
                return result
            elif orderbook.asks and len(orderbook.asks) > 0:
                ask_price = orderbook.asks[0].price
                result = float(f"{ask_price.units}.{ask_price.nano // 1000000:02d}")
                print(f"✅ Цена из OrderBook (ask): {result}")
                return result
            else:
                print("❌ OrderBook пустой")
                return None

        except Exception as e:
            print(f"❌ Ошибка получения цены из OrderBook: {e}")
            return None

    def get_historical_data(self, figi_or_ticker: str, period: str) -> pd.DataFrame:
        """Получить исторические данные. period: '1d', '2d', '1w' и т.д."""
        figi = figi_or_ticker

        # Если передан тикер, получаем FIGI
        if not (figi.startswith("BBG") or figi.startswith("TCS")):
            figi = self._get_figi_by_ticker(figi_or_ticker)
            if not figi:
                print(f"FIGI не найден для тикера: {figi_or_ticker}")
                return pd.DataFrame()

        # Парсим период
        if period == "1d":
            days = 1
        elif period == "2d":
            days = 2
        elif period == "1w":
            days = 7
        else:
            days = 1

        from_time = datetime.now() - timedelta(days=days + 1)
        to_time = datetime.now()

        with self._get_client() as client:
            try:
                response = client.market_data.get_candles(
                    figi=figi,
                    from_=from_time,
                    to=to_time,
                    interval=CandleInterval.CANDLE_INTERVAL_DAY,
                )

                data = []
                for candle in response.candles:
                    data.append(
                        {
                            "Date": candle.time.date(),
                            "Open": float(
                                f"{candle.open.units}.{candle.open.nano // 1000000:02d}"
                            ),
                            "High": float(
                                f"{candle.high.units}.{candle.high.nano // 1000000:02d}"
                            ),
                            "Low": float(
                                f"{candle.low.units}.{candle.low.nano // 1000000:02d}"
                            ),
                            "Close": float(
                                f"{candle.close.units}.{candle.close.nano // 1000000:02d}"
                            ),
                            "Volume": candle.volume,
                        }
                    )

                df = pd.DataFrame(data)
                if not df.empty:
                    df["Date"] = pd.to_datetime(df["Date"])
                    df.set_index("Date", inplace=True)

                return df

            except RequestError as e:
                print(f"Ошибка получения исторических данных для {figi_or_ticker}: {e}")
                return pd.DataFrame()

    def get_trading_volume(
        self, figi_or_ticker: str, date: datetime = None
    ) -> Optional[int]:
        """Получить объем торгов за день."""
        if date is None:
            date = datetime.now().date()

        # Получаем данные за день
        df = self.get_historical_data(figi_or_ticker, "1d")

        if not df.empty and len(df) > 0:
            return df.iloc[-1]["Volume"]

        return None


# Глобальный экземпляр клиента
client = TinkoffClient()


# Функции-обертки для совместимости с yfinance интерфейсом
def get_current_price(ticker: str) -> Optional[float]:
    return client.get_current_price(ticker)


def get_historical_data(ticker: str, period: str) -> pd.DataFrame:
    return client.get_historical_data(ticker, period)


def get_trading_volume(ticker: str, date: datetime = None) -> Optional[int]:
    return client.get_trading_volume(ticker, date)
