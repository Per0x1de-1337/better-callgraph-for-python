import sqlite3

def create_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS symbols (
            id TEXT PRIMARY KEY, name TEXT, path TEXT, symbol_type TEXT,
            line_start INTEGER, line_end INTEGER, calls TEXT DEFAULT '[]',
            calls_from TEXT DEFAULT '[]', call_traces TEXT DEFAULT '[]',
            base_classes TEXT DEFAULT '[]', tags TEXT DEFAULT '[]'
        );
        """
    )
    cur.execute("PRAGMA table_info(symbols)")
    columns = [row[1] for row in cur.fetchall()]
    if "call_traces" not in columns:
        cur.execute("ALTER TABLE symbols ADD COLUMN call_traces TEXT DEFAULT '[]'")
    if "base_classes" not in columns:
        cur.execute("ALTER TABLE symbols ADD COLUMN base_classes TEXT DEFAULT '[]'")
    if "docstring" not in columns:
        cur.execute("ALTER TABLE symbols ADD COLUMN docstring TEXT")
    conn.commit()
