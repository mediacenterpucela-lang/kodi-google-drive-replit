#!/usr/bin/env python3
"""Build a Kodi repository and its installable ZIP packages using only stdlib."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ADDONS = (
    ROOT / "addons" / "plugin.googledrive",
    ROOT / "addons" / "script.module.clouddrive.common",
)
MARKER = ".generated-by-kodi-builder"
REPOSITORY_ID = "repository.kodi-drive"
REPOSITORY_VERSION = "1.0.0"
REPOSITORY_NAME = "Kodi Google Drive Community Repository"
EXCLUDED_PARTS = {
    ".git",
    ".github",
    ".settings",
    "__pycache__",
}
EXCLUDED_FILES = {
    ".gitignore",
    ".project",
    ".pydevproject",
    "README.md",
}


def parse_addon_metadata(addon_xml: Path) -> tuple[str, str]:
    root = ET.parse(addon_xml).getroot()
    addon_id = root.get("id")
    version = root.get("version")
    if not addon_id or not version:
        raise ValueError(f"Missing id or version in {addon_xml}")
    return addon_id, version


def checksum(path: Path) -> None:
    digest = hashlib.md5(path.read_bytes()).hexdigest()
    path.with_name(path.name + ".md5").write_text(
        f"{digest} {path.name}\n",
        encoding="ascii",
    )


def addon_files(source: Path):
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.name in EXCLUDED_FILES or path.suffix in {".pyc", ".pyo"}:
            continue
        yield path, relative


def copy_addon_metadata(source: Path, target: Path, addon_xml: bytes | None = None) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if addon_xml is None:
        shutil.copy2(source / "addon.xml", target / "addon.xml")
    else:
        (target / "addon.xml").write_bytes(addon_xml)

    for name in ("icon.png", "fanart.jpg", "LICENSE.txt"):
        file_path = source / name
        if file_path.is_file():
            shutil.copy2(file_path, target / name)


def package_addon(
    source: Path,
    output: Path,
    addon_xml: bytes | None = None,
) -> tuple[str, str, Path]:
    source_xml = source / "addon.xml"
    if addon_xml is None:
        addon_id, version = parse_addon_metadata(source_xml)
    else:
        root = ET.fromstring(addon_xml)
        addon_id, version = root.get("id"), root.get("version")
        if not addon_id or not version:
            raise ValueError("Generated repository metadata needs id and version")

    package_dir = output / addon_id
    package_dir.mkdir(parents=True, exist_ok=True)
    copy_addon_metadata(source, package_dir, addon_xml)

    archive_path = package_dir / f"{addon_id}-{version}.zip"
    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path, relative in addon_files(source):
            archive.write(path, (Path(addon_id) / relative).as_posix())
        icon = source / "icon.png"
        if not icon.is_file() and addon_xml is not None:
            upstream_icon = ROOT / "addons" / "plugin.googledrive" / "icon.png"
            archive.write(upstream_icon, f"{addon_id}/icon.png")

    checksum(archive_path)
    return addon_id, version, package_dir / "addon.xml"


def make_repository_addon_xml(base_url: str) -> bytes:
    addon = ET.Element(
        "addon",
        {
            "id": REPOSITORY_ID,
            "name": REPOSITORY_NAME,
            "version": REPOSITORY_VERSION,
            "provider-name": "Community",
        },
    )
    repository_extension = ET.SubElement(
        addon,
        "extension",
        {
            "point": "xbmc.addon.repository",
            "name": REPOSITORY_NAME,
        },
    )
    ET.SubElement(repository_extension, "info").text = f"{base_url}addons.xml"
    ET.SubElement(repository_extension, "checksum").text = (
        f"{base_url}addons.xml.md5"
    )
    ET.SubElement(repository_extension, "datadir", {"zip": "true"}).text = base_url

    metadata = ET.SubElement(addon, "extension", {"point": "xbmc.addon.metadata"})
    ET.SubElement(metadata, "summary", {"lang": "es_ES"}).text = (
        "Addon comunitario Google Drive para Kodi Jarvis."
    )
    ET.SubElement(metadata, "description", {"lang": "es_ES"}).text = (
        "Distribuye el addon Google Drive de cguZZman y su módulo común "
        "para Kodi/Python 2. No es un repositorio oficial."
    )
    ET.SubElement(metadata, "platform").text = "all"
    ET.SubElement(metadata, "license").text = "GPL-3.0-or-later"
    ET.SubElement(metadata, "source").text = (
        "https://github.com/cguZZman/repository.plugins"
    )
    return ET.tostring(addon, encoding="utf-8", xml_declaration=True)


def prepare_output(output: Path) -> None:
    if output.exists():
        if not (output / MARKER).is_file():
            raise FileExistsError(
                f"Refusing to overwrite {output}: generated-output marker missing."
            )
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / MARKER).write_text(
        "Generated by tools/build_kodi_repository.py\n",
        encoding="utf-8",
    )


def build(base_url: str, output: Path) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("--base-url must be a public https URL")
    base_url = base_url.rstrip("/") + "/"

    for source in SOURCE_ADDONS:
        if not (source / "addon.xml").is_file():
            raise FileNotFoundError(f"Missing Kodi add-on source: {source}")

    prepare_output(output)
    metadata_files = []

    for source in SOURCE_ADDONS:
        _, _, metadata_path = package_addon(source, output)
        metadata_files.append(metadata_path)

    repository_xml = make_repository_addon_xml(base_url)
    with tempfile.TemporaryDirectory(prefix="kodi-repo-addon-") as temp_dir:
        repository_source = Path(temp_dir) / REPOSITORY_ID
        repository_source.mkdir()
        (repository_source / "addon.xml").write_bytes(repository_xml)
        shutil.copy2(
            ROOT / "addons" / "plugin.googledrive" / "icon.png",
            repository_source / "icon.png",
        )
        plugin_license = ROOT / "addons" / "plugin.googledrive" / "LICENSE.txt"
        if plugin_license.is_file():
            shutil.copy2(plugin_license, repository_source / "LICENSE.txt")
        _, _, repository_metadata_path = package_addon(
            repository_source, output, repository_xml
        )
        metadata_files.append(repository_metadata_path)

    addons_root = ET.Element("addons")
    for metadata_path in metadata_files:
        addons_root.append(ET.parse(metadata_path).getroot())
    addons_xml_path = output / "addons.xml"
    addons_xml_path.write_bytes(
        ET.tostring(addons_root, encoding="utf-8", xml_declaration=True)
    )
    checksum(addons_xml_path)

    installer_path = output / f"{REPOSITORY_ID}-{REPOSITORY_VERSION}.zip"
    shutil.copy2(
        output / REPOSITORY_ID / f"{REPOSITORY_ID}-{REPOSITORY_VERSION}.zip",
        installer_path,
    )
    checksum(installer_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        required=True,
        help="Public HTTPS URL to the directory where repository files are hosted.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "repository",
        help="Output folder (default: kodi-addon/repository).",
    )
    args = parser.parse_args()
    build(args.base_url, args.output.resolve())
    print(f"Kodi repository written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
