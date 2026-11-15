"""Stdlib unittest suite:  python -m unittest discover -s tests -v"""
import shutil, subprocess, sys, tempfile, textwrap, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import repo_map  # noqa: E402


def make_repo(files):
    root = Path(tempfile.mkdtemp())
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return root


class Base(unittest.TestCase):
    files = {}

    def setUp(self):
        self.root = make_repo(self.files)
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.map = repo_map.build_map(self.root)

    def section(self, rel):
        """The lines of the map that belong to one file's section."""
        lines = self.map.splitlines()
        start = lines.index(next(l for l in lines if l.startswith(f"## {rel} ")))
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        return "\n".join(lines[start:end])


class PythonTest(Base):
    files = {
        "shop/__init__.py": "",
        "shop/models.py": """
            from dataclasses import dataclass

            @dataclass
            class Item:
                name: str
                def label(self, upper=False):
                    return self.name
                def _hidden(self):
                    pass
        """,
        "shop/cart.py": """
            from shop.models import Item
            from .models import Item as I2

            def total(path, *, rounding=2):
                return 0

            async def fetch(url):
                return url

            def _private():
                pass
        """,
        "tests/test_cart.py": """
            import shop.cart

            assert shop.cart.total("x") == 0
        """,
        "tests/test_import_only.py": """
            import shop.cart
        """,
        "broken.py": "def oops(:\n",
    }

    def test_lists_classes_methods_and_functions_with_signatures(self):
        models = self.section("shop/models.py")
        self.assertIn("class Item", models)
        self.assertIn(".label(self, upper=False)", models)
        cart = self.section("shop/cart.py")
        self.assertIn("def total(path, *, rounding=2)", cart)
        self.assertIn("async def fetch(url)", cart)

    def test_hides_private_names(self):
        self.assertNotIn("_private", self.map)
        self.assertNotIn("_hidden", self.map)

    def test_resolves_absolute_and_relative_imports_to_files(self):
        self.assertIn("imports: shop/models.py", self.section("shop/cart.py"))

    def test_reverse_index_shows_who_uses_a_file(self):
        self.assertIn("used by: shop/cart.py", self.section("shop/models.py"))
        self.assertIn("used by: tests/test_cart.py", self.section("shop/cart.py"))

    def test_syntax_error_does_not_crash(self):
        self.assertIn("## broken.py ", self.map)

    def test_find_reports_definition_and_users(self):
        out = repo_map.find(self.root, "total")
        self.assertIn("shop/cart.py:", out)
        self.assertIn("def total", out)
        self.assertIn("tests/test_cart.py:3", out)

    def test_find_lists_only_files_that_mention_the_symbol(self):
        """An importer that never uses the symbol is a false lead, not a reference."""
        self.assertNotIn("test_import_only", repo_map.find(self.root, "total"))

    def test_find_lists_references_inside_the_defining_file(self):
        out = repo_map.find(self.root, "Item")
        self.assertIn("shop/cart.py:1", out)


class SiblingImportTest(Base):
    """Scripts run from their own folder import siblings by bare name: `import common`."""
    files = {
        "tool/scripts/common.py": "def load():\n    pass\n",
        "tool/scripts/cli.py": "import common\nfrom common import load\n",
        "other/common.py": "def unrelated():\n    pass\n",
    }

    def test_resolves_bare_imports_to_the_sibling_file(self):
        self.assertIn("imports: tool/scripts/common.py", self.section("tool/scripts/cli.py"))
        self.assertIn("used by: tool/scripts/cli.py", self.section("tool/scripts/common.py"))

    def test_does_not_link_a_same_named_file_elsewhere(self):
        self.assertNotIn("used by", self.section("other/common.py"))


class JavaScriptTest(Base):
    files = {
        "src/api.ts": """
            import { helper } from './util';
            import React from 'react';
            export async function getUser(id: string): Promise<User> { return helper(id); }
            export class Client {}
            export const makeClient = (url: string) => new Client();
            export interface User { id: string }
            export default function main() {}
        """,
        "src/util.js": """
            export function helper(x) { return x; }
        """,
        "node_modules/pkg/index.js": "export function shouldNotAppear() {}\n",
    }

    def test_lists_exported_symbols(self):
        api = self.section("src/api.ts")
        for name in ("getUser", "class Client", "makeClient", "interface User", "main"):
            self.assertIn(name, api)

    def test_resolves_relative_imports_and_ignores_packages(self):
        api = self.section("src/api.ts")
        self.assertIn("imports: src/util.js", api)
        self.assertNotIn("react", api.split("imports:")[-1])

    def test_skips_vendored_dirs(self):
        self.assertNotIn("shouldNotAppear", self.map)


class GoTest(Base):
    files = {
        "main.go": """
            package main

            type Server struct{}

            func (s *Server) Start(port int) error { return nil }

            func main() {}
        """,
    }

    def test_lists_types_and_funcs(self):
        go = self.section("main.go")
        self.assertIn("type Server struct", go)
        self.assertIn("func (s *Server) Start(port int) error", go)


class CliTest(Base):
    files = {"a.py": "def f():\n    pass\n"}

    def test_writes_map_file_and_reports_size(self):
        out = self.root / ".nuts" / "repo-map.md"
        r = subprocess.run([sys.executable, str(SCRIPTS / "repo_map.py"), str(self.root)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("def f()", out.read_text(encoding="utf-8"))
        self.assertIn("chars", r.stdout)

    def test_map_does_not_include_itself(self):
        subprocess.run([sys.executable, str(SCRIPTS / "repo_map.py"), str(self.root)], capture_output=True)
        self.assertNotIn(".nuts", repo_map.build_map(self.root))


if __name__ == "__main__":
    unittest.main()
