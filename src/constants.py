from typing import List
from tree_sitter import Language
import tree_sitter_python as tspython

LANGUAGE_MAP = { ".py": Language(tspython.language()) }
DB_PATH = "code_graph.db"
SCOPE_NODES = {"class_definition", "function_definition", "module"}
DEFINITION_NODES = {"class_definition", "function_definition"}
CALL_NODES = {"call"}

DEFAULT_IGNORES: List[str] = [
    "test", "tests",
    "logs", "*.log", "npm-debug.log*", "yarn-debug.log*", "yarn-error.log*",
    "lerna-debug.log*", ".pnpm-debug.log*", "report.*.json", "pids", "*.pid",
    "*.seed", "*.pid.lock", "lib-cov", "coverage", "*.lcov", ".nyc_output",
    ".grunt", "bower_components", ".lock-wscript", "build/Release", "node_modules/",
    "jspm_packages/", "web_modules/", "*.tsbuildinfo", ".npm", ".eslintcache",
    ".stylelintcache", ".rpt2_cache/", ".rts2_cache_cjs/", ".rts2_cache_es/",
    ".rts2_cache_umd/", ".node_repl_history", "*.tgz", ".yarn-integrity", ".env",
    ".env.*", ".cache", ".parcel-cache", ".next", "out", ".nuxt", "dist",
    ".vuepress/dist", ".temp", ".docusaurus", ".serverless/", ".fusebox/",
    ".dynamodb/", ".tern-port", ".vscode-test", ".yarn/cache", ".yarn/unplugged",
    ".yarn/build-state.yml", ".yarn/install-state.gz", ".pnp.*", ".webpack/",
    ".svelte-kit", "__pycache__/", "*.py[cod]", "*$py.class", "*.so", ".Python",
    "build/", "develop-eggs/", "dist/", "downloads/", "eggs/", ".eggs/", "lib/",
    "lib64/", "parts/", "sdist/", "var/", "wheels/", "share/python-wheels/",
    "*.egg-info/", ".installed.cfg", "*.egg", "MANIFEST", "*.manifest", "*.spec",
    "pip-log.txt", "pip-delete-this-directory.txt", "htmlcov/", ".tox/", ".nox/",
    ".coverage", ".coverage.*", "nosetests.xml", "coverage.xml", "*.cover",
    "*.py,cover", ".hypothesis/", ".pytest_cache/", "cover/", "*.mo", "*.pot",
    "local_settings.py", "db.sqlite3", "db.sqlite3-journal", "instance/",
    ".webassets-cache", ".scrapy", "docs/_build/", ".pybuilder/", "target/",
    ".ipynb_checkpoints", "profile_default/", "ipython_config.py", ".venv",
    "env/", "venv/", "ENV/", "env.bak/", "venv.bak/", ".spyderproject",
    ".spyproject", ".ropeproject", "site", ".mypy_cache/", ".dmypy.json",
    "dmypy.json", ".pyre/", ".pytype/", "cython_debug/", "poetry.toml",
    ".ruff_cache/", "__pypackages__/", ".sage.py", "celerybeat-schedule",
    "celerybeat.pid", "*.sage.py", ".python-version", "Pipfile.lock", "poetry.lock",
    "pdm.lock", ".pdm.toml", ".pybuilder/", ".dmypy.json", "pyrightconfig.json",
    ".pytype/", ".vscode/*", "!.vscode/settings.json", "!.vscode/tasks.json",
    "!.vscode/launch.json", "!.vscode/extensions.json", "!.vscode/*.code-snippets",
    ".history/", "*.vsix", ".ionide", "*.min.js", "*.pyc",
]
