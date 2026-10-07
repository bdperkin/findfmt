"""Multi-format asset generation utility for findfmt brand and documentation suites."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


class AssetToolError(RuntimeError):
    """Base exception for asset generation tools."""


class ConverterNotFoundError(AssetToolError):
    """Raised when neither inkscape nor magick is found in PATH."""

    def __init__(self) -> None:
        """Initialize error with explanation."""
        super().__init__("Neither 'inkscape' nor 'magick' executable found in system PATH.")


class RenderError(AssetToolError):
    """Raised when SVG rasterization fails."""

    def __init__(self, svg_path: Path, output_png: Path, tool: str, stderr: str) -> None:
        """Initialize render error with command output details."""
        super().__init__(
            f"Failed to render {svg_path} to {output_png} using {tool}:\n{stderr.strip()}",
        )


class FaviconAssemblyError(AssetToolError):
    """Raised when favicon assembly fails."""

    def __init__(self, output_ico: Path, stderr: str) -> None:
        """Initialize favicon assembly error."""
        super().__init__(f"Failed to assemble favicon.ico at {output_ico}:\n{stderr.strip()}")


class MagickNotFoundError(AssetToolError):
    """Raised when ImageMagick executable is not available."""

    def __init__(self) -> None:
        """Initialize error indicating missing magick binary."""
        super().__init__("'magick' executable is required to generate multi-resolution .ico.")


def find_converter() -> str:
    """Detect available vector-to-raster conversion command.

    Returns:
        Command name ('inkscape' or 'magick').

    Raises:
        ConverterNotFoundError: If neither inkscape nor magick is found in PATH.
    """
    if shutil.which("inkscape"):
        return "inkscape"

    if shutil.which("magick"):
        return "magick"

    raise ConverterNotFoundError


def render_svg_to_png(
    svg_path: Path,
    output_png: Path,
    width: int,
    height: int | None = None,
    converter: str | None = None,
) -> None:
    """Rasterize an SVG file to a PNG image at specified dimensions.

    Args:
        svg_path: Path to source SVG file.
        output_png: Destination path for generated PNG.
        width: Desired pixel width.
        height: Desired pixel height (optional, defaults to width).
        converter: Conversion tool to use ('inkscape' or 'magick').
    """
    selected_tool = converter or find_converter()
    h = height if height is not None else width
    output_png.parent.mkdir(parents=True, exist_ok=True)

    if selected_tool == "inkscape":
        cmd = [
            "inkscape",
            str(svg_path),
            f"--export-filename={output_png}",
            f"--export-width={width}",
            f"--export-height={h}",
        ]
    else:
        cmd = [
            "magick",
            "-background",
            "none",
            "-size",
            f"{width}x{h}",
            str(svg_path),
            str(output_png),
        ]

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RenderError(svg_path, output_png, selected_tool, proc.stderr)


def build_favicon_ico(png_layers: list[Path], output_ico: Path) -> None:
    """Assemble multiple PNG layers into a multi-resolution favicon.ico.

    Args:
        png_layers: List of square PNG paths in ascending resolution.
        output_ico: Destination path for favicon.ico.
    """
    magick = shutil.which("magick")
    if not magick:
        raise MagickNotFoundError

    output_ico.parent.mkdir(parents=True, exist_ok=True)
    cmd = [magick, *[str(p) for p in png_layers], str(output_ico)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise FaviconAssemblyError(output_ico, proc.stderr)


def optimize_png(png_path: Path, max_colors: int = 1024) -> None:
    """Optimize PNG file size using color reduction when ImageMagick is present.

    Args:
        png_path: Path to PNG file to optimize in-place.
        max_colors: Maximum palette colors to retain.
    """
    magick = shutil.which("magick")
    if not magick:
        return

    cmd = [magick, str(png_path), "-colors", str(max_colors), str(png_path)]
    subprocess.run(cmd, capture_output=True, text=True, check=False)


def sync_file(source: Path, target: Path) -> None:
    """Copy a generated asset file to a destination directory if modified.

    Args:
        source: Source file path.
        target: Target destination path.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def build_all_assets(
    assets_dir: Path,
    docs_static_dir: Path,
    source_preview: Path,
    source_icon: Path,
) -> None:
    """Generate the complete brand and web icon suite.

    Args:
        assets_dir: Directory where primary assets are saved.
        docs_static_dir: Sphinx static assets directory.
        source_preview: Source SVG for social media preview card.
        source_icon: Source SVG for icon/mark derivatives.
    """
    converter = find_converter()
    sys.stdout.write(f"Using vector rasterizer: {converter}\n")

    # 1. Social Media / Open Graph Preview Card (1280x640)
    social_preview_png = assets_dir / "social-preview.png"
    sys.stdout.write(f"Generating social preview card (1280x640): {social_preview_png}\n")
    render_svg_to_png(
        source_preview,
        social_preview_png,
        width=1280,
        height=640,
        converter=converter,
    )
    optimize_png(social_preview_png, max_colors=1024)

    # 2. Square Avatar & Application Icons
    icon_512 = assets_dir / "icon-512.png"
    icon_256 = assets_dir / "icon-256.png"
    sys.stdout.write(f"Generating 512x512 ecosystem icon: {icon_512}\n")
    render_svg_to_png(source_icon, icon_512, width=512, height=512, converter=converter)
    sys.stdout.write(f"Generating 256x256 ecosystem icon: {icon_256}\n")
    render_svg_to_png(source_icon, icon_256, width=256, height=256, converter=converter)

    # 3. Favicon and Touch Icon Layers
    touch_icon = assets_dir / "apple-touch-icon.png"
    fav_16 = assets_dir / "favicon-16x16.png"
    fav_32 = assets_dir / "favicon-32x32.png"
    fav_48 = assets_dir / "favicon-48x48.png"
    sys.stdout.write(f"Generating apple-touch-icon (180x180): {touch_icon}\n")
    render_svg_to_png(source_icon, touch_icon, width=180, height=180, converter=converter)
    render_svg_to_png(source_icon, fav_16, width=16, height=16, converter=converter)
    render_svg_to_png(source_icon, fav_32, width=32, height=32, converter=converter)
    render_svg_to_png(source_icon, fav_48, width=48, height=48, converter=converter)

    # 4. Multi-resolution favicon.ico
    favicon_ico = assets_dir / "favicon.ico"
    sys.stdout.write(f"Assembling multi-resolution favicon: {favicon_ico}\n")
    build_favicon_ico([fav_16, fav_32, fav_48], favicon_ico)
    fav_48.unlink(missing_ok=True)

    # 5. Sync web and documentation assets to Sphinx docs
    sys.stdout.write(f"Syncing static icons to documentation: {docs_static_dir}\n")
    sync_file(source_icon, docs_static_dir / "icon.svg")
    sync_file(favicon_ico, docs_static_dir / "favicon.ico")
    sync_file(fav_16, docs_static_dir / "favicon-16x16.png")
    sync_file(fav_32, docs_static_dir / "favicon-32x32.png")
    sync_file(touch_icon, docs_static_dir / "apple-touch-icon.png")

    sys.stdout.write("All assets successfully generated and synced.\n")


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Command-line arguments list.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Generate social preview cards, favicons, and application icons from SVGs.",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=Path("assets"),
        help="Target assets directory (default: assets)",
    )
    parser.add_argument(
        "--docs-static-dir",
        type=Path,
        default=Path("docs/source/_static"),
        help="Documentation static directory (default: docs/source/_static)",
    )
    parser.add_argument(
        "--preview-svg",
        type=Path,
        default=Path("assets/social-preview.svg"),
        help="Source SVG for social preview card (default: assets/social-preview.svg)",
    )
    parser.add_argument(
        "--icon-svg",
        type=Path,
        default=Path("assets/icon.svg"),
        help="Source SVG for mark icons (default: assets/icon.svg)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for asset generator CLI.

    Args:
        argv: Command-line arguments.

    Returns:
        Exit code (0 on success, non-zero on failure).
    """
    args = parse_arguments(argv)
    try:
        build_all_assets(
            assets_dir=args.assets_dir,
            docs_static_dir=args.docs_static_dir,
            source_preview=args.preview_svg,
            source_icon=args.icon_svg,
        )
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Asset generation failed: {exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
