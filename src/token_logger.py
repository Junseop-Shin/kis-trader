import sqlite3
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'llm_usage.db')

def init_db():
    """Initializes the SQLite database and creates the llm_token_usage table."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS llm_token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model_name TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print(f"LLM token usage database initialized at {DB_PATH}")

def log_token_usage(model_name: str, input_tokens: int, output_tokens: int):
    """Logs LLM token usage to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO llm_token_usage (timestamp, model_name, input_tokens, output_tokens)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, model_name, input_tokens, output_tokens))
    conn.commit()
    conn.close()
    print(f"Logged token usage: Model={model_name}, Input={input_tokens}, Output={output_tokens}")

if __name__ == '__main__':
    init_db()
    # Example usage:
    # log_token_usage("gemini-pro", 100, 50)
