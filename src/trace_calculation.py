import json
import sqlite3
from typing import List, Set

def calculate_and_store_traces(conn: sqlite3.Connection, root_dir: str):
    cur = conn.cursor()
    symbols_map = {}
    cur.execute("SELECT id, name, path, line_start, line_end, calls_from FROM symbols")
    for row in cur.fetchall():
        symbols_map[row[0]] = {
            "name": row[1], "path": row[2], "line_start": row[3],
            "line_end": row[4], "calls_from": json.loads(row[5])
        }
    
    memo = {}

    def find_paths_recursive(node_id: str, visited: Set[str]) -> List[List[str]]:
        if node_id in visited: return []
        if node_id in memo: return memo[node_id]
        
        visited.add(node_id)
        node_data = symbols_map[node_id]
        
        if not node_data["calls_from"]:
            memo[node_id] = [[node_id]]
            return [[node_id]]

        paths = []
        for caller_id, calling_line in node_data["calls_from"]:
            caller_paths = find_paths_recursive(caller_id, set(visited))
            for path in caller_paths:
                paths.append(path + [f"{node_id}:{calling_line}"])
        
        memo[node_id] = paths
        return paths

    for symbol_id in symbols_map.keys():
        raw_traces = find_paths_recursive(symbol_id, set())
        
        formatted_traces = []
        for trace in raw_traces:
            formatted_trace = []
            for i in range(len(trace)):
                step = trace[i]
                
                node_id = step.split(':')[0]
                node_data = symbols_map[node_id]
                current_step_str = (
                    f"{node_data['path']}:{node_data['name']}"
                    f":L{node_data['line_start']}-L{node_data['line_end']}"
                )

                calling_line_info = ""
                if i + 1 < len(trace):
                    next_step = trace[i+1]
                    next_parts = next_step.split(':')
                    if len(next_parts) > 1:
                        line = next_parts[1]
                        calling_line_info = f" --(calls at L{line})-->"

                formatted_trace.append(current_step_str + calling_line_info)
            
            formatted_traces.append(formatted_trace)

        valid_traces = [trace for trace in formatted_traces if len(trace) > 1]

        if valid_traces:
            cur.execute(
                "UPDATE symbols SET call_traces=? WHERE id=?",
                (json.dumps(valid_traces), symbol_id)
            )
    conn.commit()
