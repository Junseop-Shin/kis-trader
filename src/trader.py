"""
Main entry point for running trading strategies.
"""
from src.strategies.llm_strategy import LLMStrategy
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.custom_strategy import CustomStrategy

if __name__ == '__main__':
    """
    This is the main execution block.
    It initializes and runs the desired trading strategies.
    """
    print("Initializing and running trading strategies...")

    # Initialize the LLM-based strategy for algorithm partition 1
    llm_strategy = LLMStrategy(algo_id=1)
    llm_strategy.run()

    # Initialize the RSI-based strategy for algorithm partition 2
    # This strategy will watch two stocks.
    rsi_strategy = RSIStrategy(algo_id=2, symbols=['000660', '035720']) # SK Hynix, Kakao
    rsi_strategy.run()

    # Initialize the Custom strategy for algorithm partition 3
    custom_strategy = CustomStrategy(algo_id=3)
    custom_strategy.run()

    print("\nAll strategies have been run.")

