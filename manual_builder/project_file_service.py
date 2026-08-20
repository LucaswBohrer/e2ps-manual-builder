"""Read and write portable E2PS Manual Builder project archives (.e2ps)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from manual_builder.models import ManualSection, ManualSubsection, PdfPage


PROJECT_FORMAT = "E2PS Manual Builder"
PROJECT_VERSION = 1


@dataclass(slots=True)
class LoadedProject:
    """In-memory representation of a restored .e2ps project."""

    pages: list[PdfPage]
    sections: list[ManualSection]
    metadata: dict[str, Any]
    cover_image_path: Path | None


class ProjectFileService:
    """Persist a complete, portable manual-building session in a .e2ps archive."""

    @staticmethod
    def _page_id(page: PdfPage) -> str:
        return f"page-{page.number:03d}-variant-{page.variant:03d}"

    @staticmethod
    def _content_to_payload(content: list[PdfPage | str]) -> list[dict[str, str]]:
        payload: list[dict[str, str]] = []
        for item in content:
            if isinstance(item, PdfPage):
                payload.append({"type": "page", "id": ProjectFileService._page_id(item)})
            elif isinstance(item, str):
                payload.append({"type": "text", "value": item})
        return payload

    @staticmethod
    def _sections_to_payload(sections: list[ManualSection]) -> list[dict[str, Any]]:
        return [
            {
                "title": section.title,
                "content": ProjectFileService._content_to_payload(section.content),
                "subsections": [
                    {
                        "title": subsection.title,
                        "content": ProjectFileService._content_to_payload(subsection.content),
                    }
                    for subsection in section.subsections
                ],
            }
            for section in sections
        ]

    def save_project(
        self,
        destination: Path,
        pages: list[PdfPage],
        sections: list[ManualSection],
        metadata: dict[str, Any],
        cover_image_path: Path | None,
    ) -> Path:
        """Save all project assets and editable data in a compressed .e2ps archive."""
        archive_path = Path(destination)
        if archive_path.suffix.lower() != ".e2ps":
            archive_path = archive_path.with_suffix(".e2ps")
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        page_payload: list[dict[str, Any]] = []
        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            for page in pages:
                page_id = self._page_id(page)
                image_asset = f"assets/pages/{page_id}.png"
                thumbnail_asset = f"assets/thumbnails/{page_id}.png"
                if not page.image_path.is_file() or not page.thumbnail_path.is_file():
                    raise FileNotFoundError(
                        f"The files for {page.display_name} are not available to save the project."
                    )
                archive.write(page.image_path, image_asset)
                archive.write(page.thumbnail_path, thumbnail_asset)
                page_payload.append(
                    {
                        "id": page_id,
                        "number": page.number,
                        "variant": page.variant,
                        "image_asset": image_asset,
                        "thumbnail_asset": thumbnail_asset,
                        "extracted_text": page.extracted_text,
                        "export_mode": page.export_mode,
                        "source_type": page.source_type,
                    }
                )

            cover_asset: str | None = None
            if cover_image_path is not None and cover_image_path.is_file():
                cover_asset = "assets/cover" + cover_image_path.suffix.lower()
                archive.write(cover_image_path, cover_asset)

            manifest = {
                "format": PROJECT_FORMAT,
                "version": PROJECT_VERSION,
                "metadata": metadata,
                "pages": page_payload,
                "sections": self._sections_to_payload(sections),
                "cover_asset": cover_asset,
            }
            archive.writestr(
                "project.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
        return archive_path

    @staticmethod
    def _extract_asset(archive: ZipFile, asset_name: str, destination_root: Path) -> Path:
        """Extract a manifest-declared asset without using zipfile.extract()."""
        safe_relative = Path(asset_name)
        if safe_relative.is_absolute() or ".." in safe_relative.parts:
            raise ValueError("The .e2ps file contains an invalid asset path.")
        destination = destination_root / safe_relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archive.read(asset_name))
        return destination

    @staticmethod
    def _content_from_payload(
        content: list[dict[str, str]], pages_by_id: dict[str, PdfPage]
    ) -> list[PdfPage | str]:
        restored: list[PdfPage | str] = []
        for item in content:
            if item.get("type") == "page":
                page = pages_by_id.get(item.get("id", ""))
                if page is not None:
                    restored.append(page)
            elif item.get("type") == "text":
                restored.append(str(item.get("value", "")))
        return restored

    def load_project(self, source: Path, asset_root: Path) -> LoadedProject:
        """Restore a .e2ps archive into an isolated working directory."""
        source = Path(source)
        if source.suffix.lower() not in {".e2ps", ".emb"}:
            raise ValueError("Select an E2PS Manual Builder project file (.e2ps).")
        working_root = Path(asset_root)
        working_root.mkdir(parents=True, exist_ok=True)

        try:
            with ZipFile(source, "r") as archive:
                try:
                    manifest = json.loads(archive.read("project.json").decode("utf-8"))
                except KeyError as error:
                    raise ValueError("The .e2ps file does not contain project.json.") from error

                if manifest.get("format") != PROJECT_FORMAT:
                    raise ValueError("This file is not an E2PS Manual Builder project.")
                if manifest.get("version") != PROJECT_VERSION:
                    raise ValueError("This .e2ps file version is not compatible yet.")

                pages: list[PdfPage] = []
                pages_by_id: dict[str, PdfPage] = {}
                for page_data in manifest.get("pages", []):
                    image_path = self._extract_asset(
                        archive, str(page_data["image_asset"]), working_root
                    )
                    thumbnail_path = self._extract_asset(
                        archive, str(page_data["thumbnail_asset"]), working_root
                    )
                    page = PdfPage(
                        number=int(page_data["number"]),
                        image_path=image_path,
                        thumbnail_path=thumbnail_path,
                        variant=int(page_data.get("variant", 1)),
                        extracted_text=str(page_data.get("extracted_text", "")),
                        export_mode=str(page_data.get("export_mode", "image")),
                        source_type=str(page_data.get("source_type", "pdf")),
                    )
                    pages.append(page)
                    pages_by_id[str(page_data["id"])] = page

                sections: list[ManualSection] = []
                for section_data in manifest.get("sections", []):
                    subsections = [
                        ManualSubsection(
                            title=str(subsection_data.get("title", "")),
                            content=self._content_from_payload(
                                subsection_data.get("content", []), pages_by_id
                            ),
                        )
                        for subsection_data in section_data.get("subsections", [])
                    ]
                    sections.append(
                        ManualSection(
                            title=str(section_data.get("title", "")),
                            content=self._content_from_payload(
                                section_data.get("content", []), pages_by_id
                            ),
                            subsections=subsections,
                        )
                    )

                cover_image_path: Path | None = None
                cover_asset = manifest.get("cover_asset")
                if cover_asset:
                    cover_image_path = self._extract_asset(
                        archive, str(cover_asset), working_root
                    )

                return LoadedProject(
                    pages=pages,
                    sections=sections,
                    metadata=dict(manifest.get("metadata", {})),
                    cover_image_path=cover_image_path,
                )
        except BadZipFile as error:
            raise ValueError("The .e2ps file is corrupted or is not a valid archive.") from error
""
