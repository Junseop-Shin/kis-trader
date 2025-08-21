from src.strategies.base_strategy import BaseStrategy

class CustomStrategy(BaseStrategy):
    """A custom, user-defined trading strategy."""

    def __init__(self, algo_id: int):
        super().__init__(algo_id)

    def _fetch_data(self):
        """
        Fetches data required for the custom logic.
        """
        print("PRE-PROCESS (Custom): Fetching data for custom analysis (mocked).")
        pass

    def decide(self):
        """
        The core logic for the custom strategy.
        """
        print("MAIN-PROCESS (Custom): Making a decision (mocked).")
        # Mock decision to sell an existing holding if any, otherwise do nothing.
        decisions = []
        if '005930' in self.holdings and self.holdings['005930']['quantity'] > 0:
            decision = {
                'symbol': '005930',
                'action': 'SELL',
                'price': 78000,  # Mock price
                'quantity': 1
            }
            decisions.append(decision)
        return decisions
