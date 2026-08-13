import ast
import json
from pathlib import Path
import tempfile
import unittest


SOURCE = (
    Path(__file__).parents[1] / "com.enigmeta.foxhunt" / "assets" / "screens_system.py"
)


def load_build_info():
    tree = ast.parse(SOURCE.read_text())
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_build_info"
    )
    namespace = {"json": json}
    exec(compile(ast.Module([function], []), str(SOURCE), "exec"), namespace)
    return namespace["_build_info"]


class BuildInfoTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Path(self.temp.name)
        (self.app / "META-INF").mkdir()
        (self.app / "assets").mkdir()
        (self.app / "META-INF" / "MANIFEST.JSON").write_text(
            json.dumps({"version": "0.9.0"})
        )
        self.build_info = load_build_info()

    def tearDown(self):
        self.temp.cleanup()

    def test_badgehub_bytecode_install_shows_plain_version(self):
        (self.app / "assets" / "screens_system.mpy").touch()
        self.assertEqual(self.build_info(str(self.app)), "0.9.0")

    def test_source_checkout_is_labelled_dev(self):
        (self.app / "assets" / "screens_system.py").touch()
        self.assertEqual(self.build_info(str(self.app)), "0.9.0 @ dev")

    def test_usb_deploy_shows_commit_and_dirty_state(self):
        (self.app / ".deploy.sha").write_text("#src /checkout deadbee dirty\n")
        self.assertEqual(self.build_info(str(self.app)), "0.9.0 @ deadbee*")


if __name__ == "__main__":
    unittest.main()
