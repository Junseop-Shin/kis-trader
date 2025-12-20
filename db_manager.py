import sqlite3
import os
import yaml
from src.kis_api import KISApi # Import KISApi class

# CONFIG_FILE = 'config/app_config.yaml' # Old way
CONFIG_FILE = 'config/kis_devlp.yaml' # New way, as per user

DATABASE_FILE = '' # Will be read from config

def load_config():
    """
    Loads configuration from the YAML file.
    """
    global DATABASE_FILE
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            db_path = config.get('database_path')
            if not db_path:
                raise ValueError(f"'database_path' not found in {CONFIG_FILE}")
            DATABASE_FILE = os.path.expanduser(db_path)
    except FileNotFoundError:
        print(f"Error: Config file '{CONFIG_FILE}' not found.")
        exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing config file '{CONFIG_FILE}': {e}")
        exit(1)
    except ValueError as e:
        print(f"Configuration error: {e}")
        exit(1)

def initialize_db():
    """
    Initializes the SQLite database and creates necessary tables.
    """
    # Ensure config is loaded before trying to connect
    if not DATABASE_FILE:
        load_config()

    conn = None
    try:
        # Ensure the directory for the DB file exists
        db_dir = os.path.dirname(DATABASE_FILE)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # 1. algorithms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS algorithms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                initial_capital REAL NOT NULL,
                current_capital REAL NOT NULL,
                description TEXT
            )
        ''')

        # 2. virtual_holdings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS virtual_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                algo_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                average_price REAL NOT NULL,
                current_value REAL NOT NULL,
                FOREIGN KEY (algo_id) REFERENCES algorithms(id)
            )
        ''')

        # 3. trade_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                algo_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL, -- 'BUY', 'SELL'
                price REAL NOT NULL,
                quantity REAL NOT NULL,
                amount REAL NOT NULL, -- price * quantity
                status TEXT, -- 'EXECUTED', 'PENDING', 'CANCELLED'
                notes TEXT,
                FOREIGN KEY (algo_id) REFERENCES algorithms(id)
            )
        ''')

        # 4. performance_snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                algo_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                total_equity REAL NOT NULL,
                profit_loss REAL NOT NULL,
                percentage_return REAL NOT NULL,
                FOREIGN KEY (algo_id) REFERENCES algorithms(id)
            )
        ''')

        # 5. algorithm_parameters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS algorithm_parameters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                algo_id INTEGER NOT NULL,
                param_name TEXT NOT NULL,
                param_value TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (algo_id) REFERENCES algorithms(id),
                UNIQUE(algo_id, param_name)
            )
        ''')

        conn.commit()
        print(f"Database '{DATABASE_FILE}' initialized successfully with all tables.")

    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

def register_algorithms():
    """
    Registers algorithms and allocates capital dynamically.
    """
    if not DATABASE_FILE:
        load_config()

    # 1. Fetch total account balance from KIS API
    try:
        api = KISApi() # Instantiate KISApi
        balance_info = api.get_account_balance()
        if balance_info and balance_info.get('rt_cd') == '0':
            # Ensure output2 is treated as a list and access its first element
            output2_data = list(balance_info['output2'])
            total_capital = float(output2_data[0]['tot_evlu_amt'])
        else:
            print("Could not fetch account balance. Using default 30,000,000 KRW.")
            total_capital = 30000000
    except Exception as e:
        print(f"Error fetching account balance: {e}. Using default 30,000,000 KRW.")
        total_capital = 30000000

    print(f"Total capital to allocate: {total_capital}")

    # 2. Define algorithms
    algos_to_register = [
        {'id': 1, 'name': 'LLM-based Agent', 'description': 'Trading based on LLM agent decisions.'},
        {'id': 2, 'name': 'Real-time RSI', 'description': 'Trading based on real-time RSI indicators.'},
        {'id': 3, 'name': 'Custom Strategy', 'description': 'User-defined custom trading logic.'}
    ]

    num_algos = len(algos_to_register)
    capital_per_algo = total_capital / num_algos if num_algos > 0 else 0
    print(f"Allocating {capital_per_algo:.2f} to each of {num_algos} algorithms.")

    # 3. Register them in the DB
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        for algo in algos_to_register:
            cursor.execute("INSERT OR IGNORE INTO algorithms (id, name, initial_capital, current_capital, description) VALUES (?, ?, ?, ?, ?)",
                           (algo['id'], algo['name'], capital_per_algo, capital_per_algo, algo['description']))

        conn.commit()
        print("Initial algorithms registered successfully.")

    except sqlite3.Error as e:
        print(f"Error registering algorithms: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    load_config() # Load config first
    # Check if DB file already exists
    if not os.path.exists(DATABASE_FILE):
        print(f"Database file '{DATABASE_FILE}' does not exist. Initializing...")
        initialize_db()
        register_algorithms()
    else:
        print(f"Database file '{DATABASE_FILE}' already exists. Checking for algorithms...")
        register_algorithms()
