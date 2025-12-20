import asyncio
import threading
import google.generativeai as genai
from src.strategies.base_strategy import BaseStrategy
from src.kis_api import KISApi
from src.kis_api_socket import KISWebSocketClient
from src import token_logger # Import token_logger

class LLMStrategy(BaseStrategy):
    """A trading strategy driven by an LLM agent."""

    def __init__(self, algo_id: int, config: dict, gemini_api_key: str, stock_code: str = "005930"):
        super().__init__(algo_id, config)
        self.stock_code = stock_code
        self.realtime_data = {}
        self.kis_api = KISApi(config=self.config)
        self.ws_client = KISWebSocketClient(
            kis_api=self.kis_api,
            stock_code=self.stock_code,
            on_message=self._on_message
        )
        self.websocket_thread = None
        genai.configure(api_key=gemini_api_key)
        self.llm_model = genai.GenerativeModel('gemini-2.0-flash')
        token_logger.init_db() # Initialize the token usage database

    def _on_message(self, data):
        """Callback function to handle incoming websocket data."""
        try:
            parts = data.split('^')
            self.realtime_data = {
                'execution_time': parts[0],
                'current_price': float(parts[1]),
                'price_change_sign': parts[2],
                'price_change': float(parts[3]),
                'price_change_rate': float(parts[4]),
                'volume': int(parts[12]),
                'cumulative_volume': int(parts[13]),
            }
            print(f"Real-time data updated for {self.stock_code}: {self.realtime_data['current_price']}")
        except (IndexError, ValueError) as e:
            print(f"Error processing real-time data: {e}")

    def _start_websocket(self):
        """Starts the websocket client in a new thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.ws_client.connect())

    def _fetch_data(self):
        """
        Starts the websocket connection to receive real-time data.
        """
        print("PRE-PROCESS (LLM): Starting websocket for real-time data.")
        if self.websocket_thread is None or not self.websocket_thread.is_alive():
            self.websocket_thread = threading.Thread(target=self._start_websocket, daemon=True)
            self.websocket_thread.start()

    def _get_llm_decision(self, current_price):
        """Queries the LLM for a trading decision."""
        # Example stock codes for the LLM to consider. In a real scenario, this might come from a dynamic list.
        example_stock_codes = ["005930", "035720", "000660"] 
        
        prompt = f"""
        You are a trading bot. Based on the following real-time data for stock {self.stock_code}, decide whether to BUY, SELL, or HOLD.
        Also, suggest another stock symbol from the following list that might be interesting to monitor or trade: {', '.join(example_stock_codes)}.
        
        Current Price: {current_price}
        Current Holdings: {self.holdings.get(self.stock_code, {'quantity': 0})}
        
        Your response should be a JSON object with two keys: "action" (BUY, SELL, or HOLD) and "suggested_symbol" (a stock code from the example list or another valid one).
        Example: {{"action": "BUY", "suggested_symbol": "005930"}}
        """
        try:
            print("Querying LLM for decision...")
            response = self.llm_model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Log token usage
            if response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
                token_logger.log_token_usage(self.llm_model.model_name, input_tokens, output_tokens)
            else:
                print("Warning: No usage_metadata found in LLM response.")

            import json
            decision_data = json.loads(response.text)
            llm_action = decision_data.get("action", "HOLD").strip().upper()
            suggested_symbol = decision_data.get("suggested_symbol", self.stock_code).strip()

            print(f"LLM Decision: Action={llm_action}, Suggested Symbol={suggested_symbol}")
            return {"action": llm_action, "suggested_symbol": suggested_symbol}
        except Exception as e:
            print(f"Error querying LLM: {e}")
            # Default to HOLD and current stock_code on error
            return {"action": "HOLD", "suggested_symbol": self.stock_code}

    def decide(self):
        """
        The core logic where the LLM makes a decision based on real-time data.
        """
        if not self.realtime_data:
            print("MAIN-PROCESS (LLM): No real-time data yet. Waiting...")
            return []

        current_price = self.realtime_data.get('current_price')
        print(f"MAIN-PROCESS (LLM): Making a decision based on price: {current_price}")

        llm_decision_data = self._get_llm_decision(current_price)
        llm_action = llm_decision_data["action"]
        suggested_symbol = llm_decision_data["suggested_symbol"]

        print(f"LLM suggested symbol: {suggested_symbol}")

        decisions = []
        # The strategy will still act on its own stock_code for now.
        # The suggested_symbol is logged/printed for informational purposes.
        if llm_action == 'BUY':
            decisions.append({
                'symbol': self.stock_code, # Acting on the strategy's assigned stock_code
                'action': 'BUY',
                'price': current_price,
                'quantity': 10
            })
        elif llm_action == 'SELL' and self.holdings.get(self.stock_code, {'quantity': 0})['quantity'] > 0:
            decisions.append({
                'symbol': self.stock_code, # Acting on the strategy's assigned stock_code
                'action': 'SELL',
                'price': current_price,
                'quantity': 10 # Sell all for simplicity
            })
        
        return decisions

    def stop(self):
        """Stops the websocket client."""
        if self.ws_client:
            self.ws_client.stop()
        if self.websocket_thread and self.websocket_thread.is_alive():
            self.websocket_thread.join()
        print("LLMStrategy stopped.")