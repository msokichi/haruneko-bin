from datetime import timedelta
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("updater", ROOT / "scripts/update-package.py")
updater = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(updater)

RECIPE = (ROOT / "PKGBUILD").read_text()
CURRENT = updater.re.findall(r"^_upstream_tag=(.*)$", RECIPE, updater.re.MULTILINE)[0]
VERSION = updater.re.findall(r"^_electron_version=(.*)$", RECIPE, updater.re.MULTILINE)[0]
NEW = (updater.release_time(CURRENT) + timedelta(minutes=1)).strftime("%y%m%dT%H%M")
SNAP = b"test Snap"
DIGEST = hashlib.sha256(SNAP).hexdigest()
COMMIT = "a" * 40


def release(tag, digest=None, *, draft=False, asset_name=None):
    name = asset_name or f"hakuneko-electron-v{VERSION}-linux-x64.snap"
    return {
        "tag_name": tag, "draft": draft, "prerelease": True,
        "assets": [{
            "name": name, "size": len(SNAP), "digest": digest,
            "browser_download_url": f"https://github.com/{updater.REPO}/releases/download/{tag}/{name}",
        }],
    }


class UpdatePackageTest(unittest.TestCase):
    def test_current_release_writes_nothing(self):
        with TemporaryDirectory() as tmp, patch.object(updater, "api", return_value=[release(CURRENT)]):
            out = Path(tmp) / "update"
            updater.update(ROOT, out)
            self.assertFalse(out.exists())

    def test_selects_new_tag_even_when_electron_version_is_unchanged(self):
        newer_draft = release("991231T2359", draft=True)
        pages = [[newer_draft] + [release(CURRENT)] * 99, [release(NEW)]]
        with patch.object(updater, "api", side_effect=pages):
            self.assertEqual(updater.check_release(RECIPE)[:2], (NEW, VERSION))

    def test_rejects_downgrades(self):
        older = (updater.release_time(CURRENT) - timedelta(minutes=1))
        with patch.object(updater, "api", return_value=[release(older.strftime("%y%m%dT%H%M"))]):
            with self.assertRaisesRegex(ValueError, "downgrade"):
                updater.check_release(RECIPE)

    def test_rejects_changed_asset_on_same_tag(self):
        with patch.object(updater, "api", return_value=[release(CURRENT, f"sha256:{DIGEST}")]):
            with self.assertRaisesRegex(ValueError, "Published asset changed"):
                updater.check_release(RECIPE)

    def test_rejects_new_format_and_bad_api_response(self):
        for response in ({"message": "API rate limit exceeded"},
                         [release(CURRENT), release(NEW, asset_name="hakuneko-linux-x64.tar.gz")]):
            with patch.object(updater, "api", return_value=response):
                with self.assertRaises(ValueError):
                    updater.check_release(RECIPE)

    def test_rejects_digest_mismatch_before_extracting(self):
        def download(url, _, path):
            Path(path).write_bytes(SNAP)

        with TemporaryDirectory() as tmp, \
                patch.object(updater, "api", side_effect=[[release(NEW, "sha256:" + "0" * 64)], {"sha": COMMIT}]), \
                patch.object(updater, "curl", side_effect=download), patch.object(updater, "validate_snap") as validate:
            out = Path(tmp) / "update"
            with self.assertRaisesRegex(ValueError, "does not match GitHub metadata"):
                updater.update(ROOT, out)
            validate.assert_not_called()
            self.assertFalse(out.exists())

    @unittest.skipUnless(shutil.which("makepkg"), "Requires Arch makepkg")
    def test_new_release_regenerates_recipe_and_srcinfo(self):
        icon = bytes.fromhex("89504e470d0a1a0a0000000d494844520000010000000100")

        def download(url, *options):
            if options:
                Path(options[1]).write_bytes(SNAP)
                return b""
            return b"upstream license" if url.endswith("/UNLICENSE") else icon

        with TemporaryDirectory() as tmp, \
                patch.object(updater, "api", side_effect=[[release(NEW, f"sha256:{DIGEST}")], {"sha": COMMIT}]), \
                patch.object(updater, "curl", side_effect=download), patch.object(updater, "validate_snap") as validate:
            source = Path(tmp) / "src"
            source.mkdir()
            for name in ("PKGBUILD", "haruneko.sh", "haruneko.desktop"):
                shutil.copy(ROOT / name, source)
            (source / "PKGBUILD").write_text(RECIPE.replace("\npkgrel=1\n", "\npkgrel=7\n"))
            out = Path(tmp) / "update"
            updater.update(source, out)
            validate.assert_called_once()
            result = (out / "PKGBUILD").read_text()
            self.assertIn(f"_upstream_tag={NEW}\n", result)
            self.assertIn(f"_upstream_commit={COMMIT}\n", result)
            self.assertIn("\npkgrel=1\n", result)
            self.assertIn(DIGEST, result)
            self.assertEqual(
                (out / ".SRCINFO").read_text(),
                subprocess.check_output(["makepkg", "--printsrcinfo"], cwd=out, text=True),
            )
            self.assertIn("\npkgrel=7\n", (source / "PKGBUILD").read_text())


if __name__ == "__main__":
    unittest.main()
