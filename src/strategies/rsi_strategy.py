from src.strategies.base_strategy import BaseStrategy
from src import kis_api

class RSIStrategy(BaseStrategy):
    """A trading strategy based on the RSI indicator for multiple symbols."""

    def __init__(self, algo_id: int, symbols: list, rsi_period: int = 14, rsi_oversold: int = 30, rsi_overbought: int = 70):
        super().__init__(algo_id)
        self.symbols_to_watch = symbols
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.current_prices = {}

    def _fetch_data(self):
        """
        Fetches the current price for all symbols to be watched.
        """
        print(f"PRE-PROCESS (RSI): Fetching current prices for {self.symbols_to_watch}...")
        for symbol in self.symbols_to_watch:
            # In a real scenario, fetch real prices
            # price_data = kis_api.get_current_price(symbol)
            # self.current_prices[symbol] = price_data.get('price', 0)

            # For now, using mock prices
            mock_price = 135000 if symbol == '000660' else 55000
            self.current_prices[symbol] = mock_price
            print(f"Mock price for {symbol} is {self.current_prices[symbol]}")

    def decide(self):
        """
        Makes decisions for each symbol based on a mock RSI value.
        """
        print("MAIN-PROCESS (RSI): Calculating RSI and making decisions (mocked).")
        decisions = []
        for symbol in self.symbols_to_watch:
            # Mock RSI calculation
            mock_rsi = 25 # Mock value indicating oversold

            if mock_rsi < self.rsi_oversold:
                print(f"RSI ({mock_rsi}) for {symbol} is below oversold threshold ({self.rsi_oversold}). Suggesting BUY.")
                decision = {
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': self.current_prices.get(symbol, 0),
                    'quantity': 5
                }
                decisions.append(decision)
            elif mock_rsi > self.rsi_overbought:
                # Check if we have holdings to sell
                if symbol in self.holdings and self.holdings[symbol]['quantity'] > 0:
                    print(f"RSI ({mock_rsi}) for {symbol} is above overbought threshold ({self.rsi_overbought}). Suggesting SELL.")
                    decision = {
                        'symbol': symbol,
                        'action': 'SELL',
                        'price': self.current_prices.get(symbol, 0),
                        'quantity': self.holdings[symbol]['quantity'] # Sell all
                    }
                    decisions.append(decision)
        return decisions
