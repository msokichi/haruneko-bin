#!/usr/bin/env python3
"""Prepare a Haruneko package update without modifying the source checkout."""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

REPO = "manga-download/haruneko"
API = f"https://api.github.com/repos/{REPO}"
ASSET = re.compile(r"hakuneko-electron-v([0-9]+\.[0-9]+\.[0-9]+)-linux-x64\.snap")
TAG = r"[0-9]{6}T[0-9]{4}"
HEX = r"[0-9a-f]{64}"
EXECUTABLES = {"hakuneko-electron", "chrome_crashpad_handler", "chrome-sandbox"}
FILES = {
    "chrome_100_percent.pak", "chrome_200_percent.pak", "icudtl.dat",
    "libffmpeg.so", "libvk_swiftshader.so", "libvulkan.so.1", "vk_swiftshader_icd.json",
    "resources.pak", "snapshot_blob.bin", "v8_context_snapshot.bin", "locales/en-US.pak",
    "LICENSE", "LICENSES.chromium.html", "resources/app/main.js",
    "resources/app/preload.js", "resources/app/package.json",
    "resources/app/node_modules/commander/LICENSE", "resources/app/node_modules/ws/LICENSE",
}
ICON = "app/res/darwin/app.iconset/icon_256x256.png"


def curl(url, *options):
    return subprocess.check_output(
        ["curl", "--proto", "=https", "--proto-redir", "=https", "--fail",
         "--silent", "--show-error", "--location", "--retry", "3", "--retry-max-time", "180",
         "--connect-timeout", "15", "--max-time", "180", *options, url],
    )


def api(path):
    return json.loads(curl(f"{API}/{path}", "--header", "Accept: application/vnd.github+json"))


def release_time(tag):
    if not re.fullmatch(TAG, tag):
        raise ValueError(f"Invalid canary tag: {tag!r}")
    return datetime.strptime("20" + tag, "%Y%m%dT%H%M")


def newest_release():
    newest = None
    page = 1
    while True:
        releases = api(f"releases?per_page=100&page={page}")
        if not isinstance(releases, list) or len(releases) > 100:
            raise ValueError("Expected a GitHub release list")
        for release in releases:
            if type(release["draft"]) is not bool:
                raise ValueError("Invalid draft status in release list")
            if release["draft"]:
                continue
            tag = release["tag_name"]
            if not re.fullmatch(TAG, tag):
                continue
            if newest is None or release_time(tag) > release_time(newest["tag_name"]):
                newest = release
        if len(releases) < 100:
            break
        page += 1
    if newest is None:
        raise ValueError("No published Haruneko canary releases found")

    tag = newest["tag_name"]
    if not isinstance(newest["assets"], list):
        raise ValueError(f"Invalid asset list for {tag}")
    compatible = [asset for asset in newest["assets"] if ASSET.fullmatch(asset["name"])]
    if len(compatible) != 1:
        raise ValueError(f"{tag} does not contain exactly one expected Linux x86_64 Electron Snap")
    asset, = compatible
    name = asset["name"]
    url = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
    if asset["browser_download_url"] != url or type(asset["size"]) is not int or asset["size"] <= 0:
        raise ValueError(f"Unexpected download URL or size for {tag}")
    digest = asset.get("digest")
    if digest is not None and not re.fullmatch(f"sha256:{HEX}", digest):
        raise ValueError(f"Malformed SHA-256 digest for {tag}")
    return tag, ASSET.fullmatch(name)[1], url, asset["size"], digest


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def validate_snap(snap, version):
    listing = subprocess.check_output(
        ["unsquashfs", "-ll", "-processors", "1", str(snap)], text=True
    )
    modes = {}
    for line in listing.splitlines():
        prefix, separator, path = line.partition(" squashfs-root/")
        if separator:
            modes[path] = prefix.split()[0]

    for path in FILES | EXECUTABLES:
        mode = modes.get(path, "")
        if not mode.startswith("-") or (path in EXECUTABLES and not re.match(r"^-..x", mode)):
            raise ValueError(f"Missing or unexpected file type/mode in Snap: {path}")

    metadata = subprocess.check_output(["unsquashfs", "-cat", str(snap), "meta/snap.yaml"], text=True)
    if not re.search(r"^architectures:\s*\n- amd64$", metadata, re.MULTILINE):
        raise ValueError("Snap metadata does not identify a Linux amd64 build")
    if not re.search(rf"^version: {re.escape(version)}$", metadata, re.MULTILINE):
        raise ValueError("Snap metadata does not match the Electron asset version")


def change_recipe(recipe, updates, sums):
    for key, value in updates.items():
        recipe, count = re.subn(rf"^{key}=[^\n]*$", f"{key}={value}", recipe, flags=re.MULTILINE)
        if count != 1:
            raise ValueError(f"Expected exactly one {key} setting in PKGBUILD")
    new_sums = "sha256sums=(" + "\n            ".join(f"'{digest}'" for digest in sums) + ")"
    recipe, count = re.subn(r"^sha256sums=\([^)]*\)", new_sums, recipe, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("Expected exactly one SHA-256 checksum array in PKGBUILD")
    return recipe


def check_release(recipe):
    current_tag, = re.findall(rf"^_upstream_tag=({TAG})$", recipe, re.MULTILINE)
    current_version, = re.findall(r"^_electron_version=([0-9.]+)$", recipe, re.MULTILINE)
    current_sha, = re.findall(rf"^sha256sums=\('({HEX})'", recipe, re.MULTILINE)
    release = newest_release()
    tag, version, _, _, digest = release
    if release_time(tag) < release_time(current_tag):
        raise ValueError(f"Refusing to downgrade {current_tag} to {tag}")
    if tag == current_tag:
        if version != current_version or (digest and digest != f"sha256:{current_sha}"):
            raise ValueError(f"Published asset changed for the already packaged tag {tag}")
        return None
    return release


def update(source, output):
    recipe = (source / "PKGBUILD").read_text()
    release = check_release(recipe)
    if release is None:
        print("Haruneko is up to date")
        return
    tag, version, url, size, digest = release

    commit = api(f"commits/{tag}")["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError(f"Invalid source commit for {tag}")
    raw = f"https://raw.githubusercontent.com/{REPO}/{commit}"
    with TemporaryDirectory(prefix="haruneko-update-") as temporary:
        work = Path(temporary)
        snap = work / "upstream.snap"
        curl(url, "--output", str(snap))
        snap_sha = sha256(snap)
        if snap.stat().st_size != size or (digest and digest != f"sha256:{snap_sha}"):
            raise ValueError(f"Downloaded asset does not match GitHub metadata for {tag}")
        if digest is None:
            print(f"GitHub provides no digest for {tag}. Pinning the HTTPS download's SHA-256.")
        validate_snap(snap, version)

        license_text = curl(f"{raw}/UNLICENSE")
        icon = curl(f"{raw}/{ICON}")
        if not license_text.strip() or icon[:24] != bytes.fromhex(
            "89504e470d0a1a0a0000000d494844520000010000000100"
        ):
            raise ValueError("Expected an upstream license and a 256×256 PNG icon")

        changes = {"_upstream_tag": tag, "_electron_version": version,
                   "_upstream_commit": commit, "pkgrel": "1"}
        checksums = [snap_sha, hashlib.sha256(license_text).hexdigest(),
                     hashlib.sha256(icon).hexdigest(), sha256(source / "haruneko.desktop"),
                     sha256(source / "haruneko.sh")]
        updated = change_recipe(recipe, changes, checksums)
        (work / "PKGBUILD").write_text(updated)
        srcinfo = subprocess.check_output(["makepkg", "--printsrcinfo"], cwd=work, text=True)

        output.mkdir(parents=True, exist_ok=True)
        (output / "PKGBUILD").write_text(updated)
        (output / ".SRCINFO").write_text(srcinfo)
        print(f"Prepared update to Haruneko {tag} in {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="separate empty output directory")
    mode.add_argument("--check", action="store_true", help="print a newer release tag if available")
    args = parser.parse_args()
    try:
        if args.check:
            release = check_release((args.source / "PKGBUILD").read_text())
            if release:
                print(release[0])
        else:
            if args.output.exists() and any(args.output.iterdir()):
                raise ValueError("The output directory must be empty")
            update(args.source, args.output)
    except (KeyError, OSError, TypeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Upstream update failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
