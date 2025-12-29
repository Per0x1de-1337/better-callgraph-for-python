import argparse
import sqlite3
from src.constants import DB_PATH
from src.database import create_db
from src.symbol_discovery import discover_symbols
from src.graph_construction import build_graph_with_imports, link_calls_from
from src.trace_calculation import calculate_and_store_traces

def main():
    p = argparse.ArgumentParser(description="Build a code-call graph with pre-computed call traces.")
    p.add_argument("codebase_path", nargs='?', default='.', help="Path to the codebase to analyze")
    args = p.parse_args()
    with sqlite3.connect(DB_PATH) as conn:
        import time
        time01=time.time()
        create_db(conn)
        exports_map = discover_symbols(conn, args.codebase_path)
        build_graph_with_imports(conn, args.codebase_path, exports_map)
        link_calls_from(conn)
        calculate_and_store_traces(conn, args.codebase_path)
        time_taken=time.time()-time01
    print(f"completed in {time_taken}s :)")

if __name__ == "__main__":
    main()
