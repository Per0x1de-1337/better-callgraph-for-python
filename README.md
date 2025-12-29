# Better Call Graph for Python

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Database: SQLite](https://img.shields.io/badge/Database-SQLite-green)](https://www.sqlite.org/)

A lightweight, Tree-sitter-powered tool for building comprehensive call graphs of Python codebases. It goes beyond simple AST parsing by resolving cross-file dependencies, module imports, and dynamic calls, while identifying entry points like HTTP endpoints and CLI commands. Results are stored in a queryable SQLite database, enabling efficient analysis of code structure, dependencies, and execution traces.

 Inspired by [Stack Graphs](https://github.blog/open-source/introducing-stack-graphs/), it implements a scope-aware resolution mechanism to handle Python's nuanced symbol scoping (e.g., nested classes, decorators, and conditional blocks like `if __name__ == "__main__"`), providing a bidirectional graph for callers and callees.

## Features

- **Symbol Discovery**: Automatically detects functions, methods, classes, inheritance hierarchies, docstrings, and main entry points (`if __name__ == "__main__"` blocks).
- **Cross-File Analysis**: Resolves calls and imports across an entire directory or project, supporting relative imports, dotted module paths, and package structures.
- **Dynamic Call Resolution**: Handles attribute chains (e.g., `obj.method()`), self-referential method calls, and variable assignments to callable objects.
- **Entry Point Detection**: Identifies HTTP endpoints (e.g., Flask/FastAPI routes like `@app.get("/")`) and CLI commands (e.g., Click or argparse usage).
- **Bidirectional Call Graph**: Builds edges for both `calls` (callee → caller line) and `calls_from` (caller → callee details), with support for call traces (execution paths).
- **Stack Graph-Inspired Scoping**: Uses a stack-based approach to track scopes (modules, classes, functions) and resolve symbols in context, avoiding naive global lookups.
- **SQLite Persistence**: Stores everything in a single `code_graph.db` file for easy querying, visualization, or integration with tools like Graphviz or Neo4j.
- **Extensible Tagging**: Applies semantic tags (e.g., `http_endpoint`, `command_line_interface`) for filtering and analysis.
- **Performance Optimized**: Processes large codebases efficiently with memoization for traces and batched database operations.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Per0x1de-1337/better-callgraph-for-python.git
   cd better-callgraph-for-python
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
   
## Usage

Run the tool on a Python codebase directory:

```bash
python main.py /path/to/your/codebase
```

- **Optional Argument**: Defaults to current directory (`.`).
- **Output**: Generates `code_graph.db` in the current working directory. Prints completion time.

### Key Data Model

| Column          | Type    | Description |
|-----------------|---------|-------------|
| `id`            | TEXT    | Unique symbol ID (e.g., `func_uuid`). |
| `name`          | TEXT    | Qualified name (e.g., `MyClass.method`). |
| `path`          | TEXT    | Relative file path. |
| `symbol_type`   | TEXT    | e.g., `function_definition`, `class_definition`, `main_block`. |
| `line_start/end`| INTEGER | Source line range. |
| `calls`         | TEXT    | JSON: `[[callee_id, line], ...]`. |
| `calls_from`    | TEXT    | JSON: `[[caller_id, line], ...]`. |
| `call_traces`   | TEXT    | JSON: Formatted execution paths from entry points. |
| `base_classes`  | TEXT    | JSON: Inheritance list (e.g., `["BaseClass1", "BaseClass2"]`). |
| `tags`          | TEXT    | JSON: e.g., `["http_endpoint", "command_line_interface"]`. |
| `docstring`     | TEXT    | Cleaned docstring. |

## How It Differs from Ordinary Tree-sitter Parsers

Tree-sitter excels at fast, incremental AST parsing, but vanilla usage typically yields isolated per-file trees without cross-file resolution or semantic linking. This tool extends it as follows:

- **Ordinary Tree-sitter**: Parses a single file into a AST; you'd manually walk nodes for basic extraction (e.g., find all `function_definition` nodes).
  - Limitations: No scope tracking, import resolution, or call graph building. Cross-file analysis requires custom scripting.

- **This Tool**:
  - **Global Context**: Builds a unified graph across directories by correlating exports with imports via file path resolution.
  - **Scope-Aware Resolution**: Uses a dynamic stack (inspired by Stack Graphs) to handle nested scopes, avoiding false positives (e.g., resolving `self.method` correctly inside classes).
  - **Semantic Enhancements**: Infers dynamics like inheritance chains, decorator intents, and conditional mains—beyond raw syntax.
  - **Graph Output**: Produces queryable relations instead of raw trees, enabling tools like static analysis or IDE plugins.

In essence, it's a "Tree-sitter + Stack Graphs" for call graphs, tailored for Python's import-heavy, class-oriented style.

## Stack Graphs Integration

This tool draws from [Stack Graphs](https://github.blog/open-source/introducing-stack-graphs/). We adapt it for static call graphs:
- **Precedence Rules**: Jumps (e.g., imports) and definitions (e.g., functions) are modeled as graph edges.
- **Path Sensitivity**: Traces respect calling contexts, supporting precise refactoring or dependency auditing.
- Future: Could export to full Stack Graph format for editor integration.

## Performance

Designed for scalability on real-world codebases, this tool balances precision with efficiency:

- **Parsing Efficiency**: Tree-sitter's linear-time parsing handles thousands of files quickly. Ignores non-Python files and common build artifacts (e.g., `__pycache__`, `venv/`) to minimize I/O.

- **Benchmarks** :
  | Codebase Size | Files(excluding tests) | Time |
  |---------------|-------|------|
  | FastChat | 270 | 200ms |
  | llama-index | 10,800 | 1.2s |

These times include full pipeline (discovery → traces). For larger repos, parallelize file parsing via multiprocessing in future iterations.

  - Use async for large directories for parallel parsing. Modify the relevant functions accordingly.

  - I have not included async parsing in this tool for simplicity, but it could be added in future iterations.


## Contributing

1. Fork and clone the repo.
2. Install dev dependencies: `pip install -e .[dev]`.
3. Submit PRs with descriptive commits.

Feedback on edge cases (e.g., type annotations, complex decorators, nested imports,) welcome!

## License

MIT License. See [LICENSE](LICENSE) for details.
