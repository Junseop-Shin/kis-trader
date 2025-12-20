import sqlite3
import datetime
import os
import time
from abc import ABC, abstractmethod

import db_manager
from src import kis_api

# Load the database path from the config
db_manager.load_config()
DATABASE_FILE = db_manager.DATABASE_FILE

class BaseStrategy(ABC):
    """The base class for all trading strategies."""

    def __init__(self, algo_id: int, config: dict):
        """
        Initializes the strategy by loading its state from the database.

        Args:
            algo_id (int): The ID of the algorithm in the database.
            config (dict): The configuration dictionary.
        """
        self.algo_id = algo_id
        self.config = config
        self.initial_capital = 0
        self.current_capital = 0
        self.holdings = {}
        self.running = False

        self._load_state_from_db()

    def _get_db_connection(self):
        """Establishes a connection to the SQLite database."""
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_state_from_db(self):
        """Loads the algorithm's current capital and holdings from the DB."""
        print(f"Loading state for algo_id {self.algo_id}...")
        conn = self._get_db_connection()
        try:
            # Load capital
            cursor = conn.cursor()
            cursor.execute("SELECT initial_capital, current_capital FROM algorithms WHERE id = ?", (self.algo_id,))
            algo_data = cursor.fetchone()
            if algo_data:
                self.initial_capital = algo_data['initial_capital']
                self.current_capital = algo_data['current_capital']
            else:
                raise ValueError(f"Algorithm with id {self.algo_id} not found in the database.")

            # Load holdings
            cursor.execute("SELECT symbol, quantity, average_price FROM virtual_holdings WHERE algo_id = ?", (self.algo_id,))
            self.holdings = {row['symbol']: {'quantity': row['quantity'], 'average_price': row['average_price']} for row in cursor.fetchall()}
            print(f"State loaded: Capital={self.current_capital}, Holdings={self.holdings}")
        finally:
            conn.close()

    def _execute_and_log_trade(self, symbol: str, trade_type: str, price: float, quantity: int, notes: str = ""):
        """
        Executes a trade and logs the transaction in the database.
        This is the 'post-process' step.
        """
        print(f"POST-PROCESS: Attempting to {trade_type} {quantity} shares of {symbol} at {price}")
        # Mocking successful execution for now
        print("Mock trade execution successful.")
        status = 'EXECUTED'
        amount = price * quantity
        timestamp = datetime.datetime.now().isoformat()

        conn = self._get_db_connection()
        cursor = conn.cursor()
        try:
            # Log the trade
            cursor.execute("""
                INSERT INTO trade_logs (algo_id, timestamp, symbol, trade_type, price, quantity, amount, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.algo_id, timestamp, symbol, trade_type, price, quantity, amount, status, notes))

            # Update holdings in DB and in memory
            self._update_holdings(cursor, symbol, trade_type, price, quantity)

            # Update algorithm's current capital in DB and in memory
            capital_change = -amount if trade_type == 'BUY' else amount
            self.current_capital += capital_change
            cursor.execute("UPDATE algorithms SET current_capital = ? WHERE id = ?", (self.current_capital, self.algo_id))

            conn.commit()
            print(f"POST-PROCESS: Trade logged and state updated successfully.")
            return True
        except sqlite3.Error as e:
            print(f"Database error during trade logging: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def _update_holdings(self, cursor, symbol: str, trade_type: str, price: float, quantity: int):
        """Helper function to update holdings in the DB and the instance variable."""
        holding = self.holdings.get(symbol)

        if trade_type == 'BUY':
            if holding:
                # Update existing holding
                new_quantity = holding['quantity'] + quantity
                new_avg_price = ((holding['average_price'] * holding['quantity']) + (price * quantity)) / new_quantity
                cursor.execute("UPDATE virtual_holdings SET quantity = ?, average_price = ? WHERE algo_id = ? AND symbol = ?",
                               (new_quantity, new_avg_price, self.algo_id, symbol))
                self.holdings[symbol]['quantity'] = new_quantity
                self.holdings[symbol]['average_price'] = new_avg_price
            else:
                # Insert new holding
                cursor.execute("INSERT INTO virtual_holdings (algo_id, symbol, quantity, average_price, current_value) VALUES (?, ?, ?, ?, 0)",
                               (self.algo_id, symbol, quantity, price))
                self.holdings[symbol] = {'quantity': quantity, 'average_price': price}

        elif trade_type == 'SELL':
            if not holding or holding['quantity'] < quantity:
                raise ValueError(f"Not enough shares of {symbol} to sell.")

            new_quantity = holding['quantity'] - quantity
            if new_quantity == 0:
                cursor.execute("DELETE FROM virtual_holdings WHERE algo_id = ? AND symbol = ?", (self.algo_id, symbol))
                del self.holdings[symbol]
            else:
                cursor.execute("UPDATE virtual_holdings SET quantity = ? WHERE algo_id = ? AND symbol = ?", (new_quantity, self.algo_id, symbol))
                self.holdings[symbol]['quantity'] = new_quantity

    @abstractmethod
    def _fetch_data(self):
        """
        Pre-process: Fetches necessary data for the strategy.
        This should be implemented by subclasses.
        """
        pass

    @abstractmethod
    def decide(self):
        """
        Main-process: Makes trading decisions.
        This should be implemented by subclasses.
        Returns a list of decision dictionaries, e.g.:
        [{'symbol': '005930', 'action': 'BUY', 'price': 75000, 'quantity': 10}]
        or an empty list if no action is to be taken.
        """
        pass

    def run(self):
        """Orchestrates the entire trading process in a loop."""
        print(f"\n----- Running Strategy: {self.__class__.__name__} -----")
        self.running = True
        try:
            while self.running:
                # 1. Pre-process
                self._fetch_data()

                # 2. Main-process
                decisions = self.decide()

                # 3. Post-process
                if decisions:
                    for decision in decisions:
                        self._execute_and_log_trade(
                            symbol=decision['symbol'],
                            trade_type=decision['action'],
                            price=decision['price'],
                            quantity=decision['quantity'],
                            notes=f"Trade by {self.__class__.__name__}"
                        )
                else:
                    print("No action taken.")
                
                print("----- Strategy run finished. Waiting for next cycle... -----")
                time.sleep(5) # 5-second interval

        except KeyboardInterrupt:
            print(f"Strategy {self.__class__.__name__} stopped by user.")
        finally:
            self.stop()

    def stop(self):
        """Stops the strategy loop."""
        self.running = False
        print(f"----- Stopping Strategy: {self.__class__.__name__} -----")
