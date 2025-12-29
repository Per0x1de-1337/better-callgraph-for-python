import os
import re
import uuid
import json
import fnmatch
import sqlite3
from typing import Dict
from tree_sitter import Language, Parser, Node
from .constants import DEFAULT_IGNORES, LANGUAGE_MAP

def _should_ignore(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)

def find_language(file_path: str):
    _, ext = os.path.splitext(file_path)
    return LANGUAGE_MAP.get(ext.lower())

def discover_symbols(conn: sqlite3.Connection, root_dir: str) -> Dict[str, Dict[str, str]]:
    cur = conn.cursor()
    cur.execute("DELETE FROM symbols")
    exports_map = {}
    abs_root = os.path.abspath(root_dir)
    for dirpath, dirnames, filenames in os.walk(abs_root):
        dirnames[:] = [d for d in dirnames if not _should_ignore(d, DEFAULT_IGNORES)]
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if _should_ignore(file_path, DEFAULT_IGNORES) or _should_ignore(filename, DEFAULT_IGNORES):
                continue
            
            abs_path = os.path.abspath(file_path)
            rel_path = os.path.relpath(abs_path, abs_root)
            exports_map[abs_path] = {}
            lang = find_language(file_path)
            if not lang: continue
            parser = Parser(lang)
            with open(file_path, "r", encoding="utf-8") as fh:
                content = fh.read()
                tree = parser.parse(content.encode())

            main_block_match = re.search(r'if\s+__name__\s*==\s*["\']__main__["\']\s*:', content)
            if main_block_match:
                uid = f"__main___{uuid.uuid4().hex[:6]}"
                line_start = content[:main_block_match.start()].count('\n') + 1
                line_end = content.count('\n') + 1
                cur.execute(
                    "INSERT INTO symbols (id, name, path, symbol_type, line_start, line_end) VALUES (?, ?, ?, ?, ?, ?)",
                    (uid, "__main__", rel_path, "main_block", line_start, line_end)
                )
                exports_map[abs_path]["__main__"] = uid

            def find_defs_recursive(node: Node, class_name: str | None = None):
                if node.type == 'decorated_definition':
                    definition_node = node.children[-1]
                    find_defs_recursive(definition_node, class_name)
                    return

                docstring = None
                body_node = node.child_by_field_name('body')
                if body_node and body_node.children:
                    first_child = body_node.children[0]
                    if first_child.type == 'expression_statement' and first_child.children[0].type == 'string':
                        docstring_node = first_child.children[0]
                        # Clean up the docstring text (remove quotes, etc.)
                        docstring = docstring_node.text.decode().strip('"""').strip("'''").strip('"').strip("'").strip()

                if node.type == 'class_definition':
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        name = name_node.text.decode()
                        uid = f"{name}_{uuid.uuid4().hex[:6]}"
                        
                        base_classes = []
                        arg_list = node.child_by_field_name('superclasses')
                        if arg_list:
                            base_classes = [
                                child.text.decode() for child in arg_list.children 
                                if child.type in ('identifier', 'attribute')
                            ]

                        cur.execute(
                            "INSERT INTO symbols (id, name, path, symbol_type, line_start, line_end, base_classes, docstring) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (uid, name, rel_path, node.type, node.start_point[0] + 1, node.end_point[0] + 1, json.dumps(base_classes), docstring)
                        )
                        exports_map[abs_path][name] = uid
                        body = node.child_by_field_name('body')
                        if body:
                            for child in body.children:
                                find_defs_recursive(child, class_name=name)
                elif node.type == 'function_definition':
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        simple_name = name_node.text.decode()
                        qualified_name = f"{class_name}.{simple_name}" if class_name else simple_name
                        uid = f"{qualified_name.replace('.', '_')}_{uuid.uuid4().hex[:6]}"
                        symbol_type = 'method_definition' if class_name else 'function_definition'
                        cur.execute(
                            "INSERT INTO symbols (id, name, path, symbol_type, line_start, line_end, docstring) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (uid, qualified_name, rel_path, symbol_type, node.start_point[0] + 1, node.end_point[0] + 1, docstring)
                        )
                        exports_map[abs_path][qualified_name] = uid

            for node in tree.root_node.children:
                find_defs_recursive(node)

    conn.commit()
    return exports_map
