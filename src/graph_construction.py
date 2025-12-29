import os
import re
import json
import sqlite3
from typing import Dict, List, Any
from tree_sitter import Parser, Node
from .symbol_discovery import find_language
from .constants import SCOPE_NODES, CALL_NODES

def build_graph_with_imports(conn: sqlite3.Connection, root_dir: str, exports_map: Dict[str, Dict[str, str]]):
    cur = conn.cursor()
    abs_root = os.path.abspath(root_dir)

    class_hierarchy = {}
    cur.execute("SELECT id, name, path, base_classes FROM symbols WHERE symbol_type='class_definition'")
    for class_id, name, path, base_classes_json in cur.fetchall():
        class_hierarchy[class_id] = {
            "name": name,
            "path": path,
            "base_classes": json.loads(base_classes_json)
        }

    for file_path in exports_map.keys():
        lang = find_language(file_path)
        if not lang: continue
        parser = Parser(lang)
        with open(file_path, "r", encoding="utf-8") as fh:
            tree = parser.parse(fh.read().encode())
        
        scope_stack: List[Dict[str, Dict[str, Any]]] = [{
            name: {'type': 'symbol', 'id': uid} 
            for name, uid in exports_map[file_path].items()
            if '.' not in name
        }]

        def resolve_module_path_from_root(name: str) -> str | None:
            parts = name.split('.')
            potential_path = os.path.join(abs_root, *parts) + ".py"
            if os.path.isfile(potential_path) and potential_path in exports_map:
                return potential_path
            potential_path = os.path.join(abs_root, *parts)
            if os.path.isdir(potential_path) and os.path.isfile(os.path.join(potential_path, "__init__.py")):
                init_path = os.path.join(potential_path, "__init__.py")
                return init_path if init_path in exports_map else None
            return None

        def find_method_in_hierarchy(class_name: str, method_name: str) -> str | None:
            class_id = None
            for cid, cinfo in class_hierarchy.items():
                if cinfo['name'] == class_name:
                    class_id = cid
                    break
            if not class_id: return None

            qualified_name = f"{class_name}.{method_name}"
            class_path = os.path.join(abs_root, class_hierarchy[class_id]['path'])
            if class_path in exports_map and qualified_name in exports_map[class_path]:
                return exports_map[class_path][qualified_name]

            for base_name in class_hierarchy[class_id]['base_classes']:
                found_id = find_method_in_hierarchy(base_name, method_name)
                if found_id:
                    return found_id
            return None

        def resolve_call(node: Node, class_name: str | None = None) -> str | None:
            if node.type == 'identifier':
                name = node.text.decode()
                for scope in reversed(scope_stack):
                    if name in scope and scope[name]['type'] == 'symbol':
                        return scope[name]['id']
                return None

            if node.type == 'attribute':
                method_name = node.child_by_field_name('attribute').text.decode()
                obj_node = node.child_by_field_name('object')
                
                if obj_node.type == 'identifier':
                    obj_name = obj_node.text.decode()
                    
                    if obj_name == 'self' and class_name:
                        return find_method_in_hierarchy(class_name, method_name)

                    var_info = None
                    for scope in reversed(scope_stack):
                        if obj_name in scope:
                            var_info = scope[obj_name]
                            break
                    
                    if var_info and var_info['type'] == 'variable' and var_info.get('class_name'):
                        return find_method_in_hierarchy(var_info['class_name'], method_name)

                chain = []
                curr = node
                while curr.type == 'attribute':
                    chain.append(curr.child_by_field_name('attribute').text.decode())
                    curr = curr.child_by_field_name('object')
                if curr.type != 'identifier': return None
                chain.append(curr.text.decode())
                chain.reverse()
                base_name = chain[0]
                base_res = None
                for scope in reversed(scope_stack):
                    if base_name in scope:
                        base_res = scope[base_name]
                        break
                if not base_res or base_res['type'] != 'module': return None
                module_dot_path = ".".join(chain[:-1])
                final_func_name = chain[-1]
                module_path = resolve_module_path_from_root(module_dot_path)
                if module_path and os.path.isfile(module_path):
                    return exports_map.get(module_path, {}).get(final_func_name)
                final_module_file = os.path.join(base_res['id'], *chain[1:-1]) + ".py"
                if final_module_file in exports_map:
                    return exports_map[final_module_file].get(final_func_name)
                return None
            return None

        def walk_tree(node: Node, current_definition_id: str | None = None, class_name: str | None = None):
            is_scope = node.type in SCOPE_NODES
            new_definition_id = current_definition_id
            new_class_name = class_name

            if node.type == 'if_statement':
                condition_text = node.child_by_field_name('condition').text.decode()
                if '__name__' in condition_text and '__main__' in condition_text:
                    new_definition_id = exports_map.get(file_path, {}).get('__main__')

            if node.type == 'import_statement':
                for import_clause in node.children:
                    if import_clause.type == 'dotted_name':
                        name = import_clause.text.decode()
                        alias = name.split('.')[0]
                        module_path = resolve_module_path_from_root(name)
                        if module_path:
                            scope_stack[-1][alias] = {'type': 'module', 'id': os.path.dirname(module_path)}

            if node.type == 'import_from_statement':
                module_name_node = node.child_by_field_name('module_name')
                if module_name_node:
                    module_name = module_name_node.text.decode()
                    module_path = resolve_module_path_from_root(module_name)
                    if module_path and module_path in exports_map:
                        for name_node in node.children:
                            if name_node.type == 'dotted_name':
                                for identifier_node in name_node.children:
                                    if identifier_node.type == 'identifier':
                                        original_name = identifier_node.text.decode()
                                        if original_name in exports_map[module_path]:
                                            symbol_id = exports_map[module_path][original_name]
                                            scope_stack[-1][original_name] = {'type': 'symbol', 'id': symbol_id}

            if node.type == 'assignment':
                left_node = node.child_by_field_name('left')
                right_node = node.child_by_field_name('right')
                if left_node and right_node and left_node.type == 'identifier' and right_node.type == 'call':
                    var_name = left_node.text.decode()
                    func_node = right_node.child_by_field_name('function')
                    if func_node and func_node.type == 'identifier':
                        class_name_str = func_node.text.decode()
                        scope_stack[-1][var_name] = {'type': 'variable', 'class_name': class_name_str}

            if node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = name_node.text.decode()
                    new_class_name = name
                    new_definition_id = exports_map.get(file_path, {}).get(name)
            elif node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = name_node.text.decode()
                    lookup_name = f"{class_name}.{name}" if class_name else name
                    new_definition_id = exports_map.get(file_path, {}).get(lookup_name)

            if node.type == 'decorated_definition':
                definition_node = node.children[-1]
                
                func_name = None
                if definition_node.type in ('function_definition', 'class_definition'):
                    name_node = definition_node.child_by_field_name('name')
                    if name_node:
                        func_name = name_node.text.decode()

                decorators = node.children[:-1]
                for dec_node in decorators:
                    if dec_node.type == 'decorator' and func_name:
                        decorator_expression_node = dec_node.children[1]

                        def get_full_attribute_chain(n: Node) -> str:
                            if n.type == 'identifier': return n.text.decode()
                            if n.type == 'attribute':
                                obj = get_full_attribute_chain(n.child_by_field_name('object'))
                                attr = n.child_by_field_name('attribute').text.decode()
                                return f"{obj}.{attr}" if obj else attr
                            if n.type == 'call':
                                return get_full_attribute_chain(n.child_by_field_name('function'))
                            return ""

                        decorator_text = get_full_attribute_chain(decorator_expression_node)

                        tag_to_add = None
                        if re.search(r'\.(get|post|put|delete|patch|route|head|options)$', decorator_text, re.IGNORECASE):
                            tag_to_add = 'http_endpoint'
                        elif re.search(r'click\.command$|\.command$', decorator_text):
                            tag_to_add = 'command_line_interface'

                        if tag_to_add:
                            qualified_func_name = f"{class_name}.{func_name}" if class_name else func_name
                            rel_path = os.path.relpath(file_path, abs_root)
                            cur.execute("SELECT id, tags FROM symbols WHERE name=? AND path=?", (qualified_func_name, rel_path))
                            symbol_to_tag = cur.fetchone()
                            if symbol_to_tag:
                                symbol_id, tags_json = symbol_to_tag
                                tags = json.loads(tags_json)
                                if tag_to_add not in tags:
                                    tags.append(tag_to_add)
                                    cur.execute("UPDATE symbols SET tags=? WHERE id=?", (json.dumps(tags), symbol_id))

                defined_symbol_id = None
                if func_name:
                    lookup_name = f"{class_name}.{func_name}" if class_name else func_name
                    defined_symbol_id = exports_map.get(file_path, {}).get(lookup_name)
                
                child_class_name = func_name if definition_node.type == 'class_definition' else class_name
                walk_tree(definition_node, defined_symbol_id, child_class_name)
                return

            if node.type in CALL_NODES and new_definition_id:
                call_name_node = node.child_by_field_name("function")
                if call_name_node:
                    def get_full_call_chain(n: Node) -> str:
                        if n.type == 'identifier': return n.text.decode()
                        if n.type == 'attribute':
                            obj = get_full_call_chain(n.child_by_field_name('object'))
                            attr = n.child_by_field_name('attribute').text.decode()
                            return f"{obj}.{attr}" if obj else attr
                        return ""
                    
                    call_text = get_full_call_chain(call_name_node)
                    if call_text == "argparse.ArgumentParser":
                        cur.execute("SELECT tags FROM symbols WHERE id=?", (new_definition_id,))
                        tags_json = cur.fetchone()[0]
                        tags = json.loads(tags_json)
                        if 'command_line_interface' not in tags:
                            tags.append('command_line_interface')
                            cur.execute("UPDATE symbols SET tags=? WHERE id=?", (json.dumps(tags), new_definition_id))

                    resolved_def_id = resolve_call(call_name_node, new_class_name)
                    if resolved_def_id:
                        calling_line = call_name_node.start_point[0] + 1
                        cur.execute("SELECT calls FROM symbols WHERE id=?", (new_definition_id,))
                        calls = json.loads(cur.fetchone()[0])
                        call_info = [resolved_def_id, calling_line]
                        if call_info not in calls:
                            calls.append(call_info)
                            cur.execute("UPDATE symbols SET calls=? WHERE id=?", (json.dumps(calls), new_definition_id))

                    argument_list_node = node.child_by_field_name('arguments')
                    if argument_list_node:
                        for arg_node in argument_list_node.children:
                            if arg_node.type == 'identifier':
                                callback_id = resolve_call(arg_node, new_class_name)
                                if callback_id:
                                    calling_line = arg_node.start_point[0] + 1
                                    cur.execute("SELECT calls FROM symbols WHERE id=?", (new_definition_id,))
                                    calls = json.loads(cur.fetchone()[0])
                                    call_info = [callback_id, calling_line]
                                    if call_info not in calls:
                                        calls.append(call_info)
                                        cur.execute("UPDATE symbols SET calls=? WHERE id=?", (json.dumps(calls), new_definition_id))

            
            if is_scope: scope_stack.append({})
            try:
                for child in node.children:
                    walk_tree(child, new_definition_id, new_class_name)
            finally:
                if is_scope: scope_stack.pop()
        
        walk_tree(tree.root_node)
    conn.commit()

def link_calls_from(conn: sqlite3.Connection):
    cur, all_calls = conn.cursor(), {}
    cur.execute("SELECT id, calls FROM symbols")
    for caller_id, calls_json in cur.fetchall():
        for callee_id, calling_line in json.loads(calls_json):
            if callee_id not in all_calls:
                all_calls[callee_id] = []
            all_calls[callee_id].append([caller_id, calling_line])
    for callee_id, caller_info_list in all_calls.items():
        unique_callers = [list(x) for x in set(tuple(x) for x in caller_info_list)]
        cur.execute("UPDATE symbols SET calls_from=? WHERE id=?", (json.dumps(unique_callers), callee_id))
    conn.commit()
