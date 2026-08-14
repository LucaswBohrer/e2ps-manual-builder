"""Create the Windows application icon from the E2PS brand asset."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "manual_builder" / "assets" / "LogoHeader.png"
TARGET = ROOT / "manual_builder" / "assets" / "e2ps.ico"


def main() -> None:
    with Image.open(SOURCE) as source:
        image = source.convert("RGBA")
        # Windows expects square icon frames. The original logo is kept intact and
        # centered on a white canvas rather than being cropped or stretched.
        canvas = Image.new("RGBA", (512, 512), (255, 255, 255, 255))
        image.thumbnail((440, 440), Image.Resampling.LANCZOS)
        left = (canvas.width - image.width) // 2
        top = (canvas.height - image.height) // 2
        canvas.alpha_composite(image, (left, top))
        canvas.save(
            TARGET,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
    print(f"Created {TARGET}")


if __name__ == "__main__":
    main()
