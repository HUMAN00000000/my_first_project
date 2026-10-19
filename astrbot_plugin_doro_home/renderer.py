from __future__ import annotations

from math import ceil
from pathlib import Path
from typing import Mapping, Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from .content import MENU_ITEMS


class MenuRenderer:
    MENU_SIZE = (1200, 900)
    GALLERY_WIDTH = 1200

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.regular_font = self._find_font(
            [
                Path("C:/Windows/Fonts/msyh.ttc"),
                Path("C:/Windows/Fonts/simhei.ttf"),
                Path("C:/Windows/Fonts/simsun.ttc"),
            ]
        )
        self.bold_font = self._find_font(
            [
                Path("C:/Windows/Fonts/msyhbd.ttc"),
                Path("C:/Windows/Fonts/simhei.ttf"),
                self.regular_font,
            ]
        )

    @staticmethod
    def _find_font(candidates: Sequence[Path]) -> Path | None:
        for candidate in candidates:
            if candidate and candidate.is_file():
                return candidate
        return None

    def _font(self, size: int, bold: bool = False):
        selected = self.bold_font if bold else self.regular_font
        if selected:
            return ImageFont.truetype(str(selected), size=size)
        return ImageFont.load_default()

    @staticmethod
    def _fit_background(path: Path, size: tuple[int, int]) -> Image.Image:
        with Image.open(path) as source:
            source = ImageOps.exif_transpose(source).convert("RGB")
            return ImageOps.fit(source, size, method=Image.Resampling.LANCZOS)

    @staticmethod
    def _ellipsize(text: str, maximum: int) -> str:
        return text if len(text) <= maximum else f"{text[: maximum - 1]}…"

    def render_menu(self, background_path: Path, output_path: Path) -> Path:
        image = self._fit_background(background_path, self.MENU_SIZE).convert("RGBA")
        shade = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shade_draw = ImageDraw.Draw(shade)
        shade_draw.rectangle((0, 0, 1200, 190), fill=(10, 8, 18, 150))
        shade_draw.rectangle((0, 190, 1200, 900), fill=(7, 6, 14, 68))
        image = Image.alpha_composite(image, shade)

        draw = ImageDraw.Draw(image)
        title_font = self._font(62, bold=True)
        subtitle_font = self._font(24)
        number_font = self._font(22, bold=True)
        item_font = self._font(31, bold=True)
        detail_font = self._font(18)
        footer_font = self._font(20)

        draw.text((65, 45), "DORO 的小窝", font=title_font, fill=(255, 255, 255, 255))
        draw.text(
            (68, 125),
            "今日结局 · 图鉴收集 · 运势 · 表情包 · 吃什么 · 搬史",
            font=subtitle_font,
            fill=(236, 226, 255, 238),
        )

        columns = 3
        tile_width = 344
        tile_height = 150
        gap_x = 24
        gap_y = 24
        start_x = 60
        start_y = 220

        for index, (number, label, detail) in enumerate(MENU_ITEMS):
            row = index // columns
            column = index % columns
            x = start_x + column * (tile_width + gap_x)
            y = start_y + row * (tile_height + gap_y)
            if index == len(MENU_ITEMS) - 1:
                x = start_x + tile_width + gap_x

            box = (x, y, x + tile_width, y + tile_height)
            draw.rounded_rectangle(
                box,
                radius=8,
                fill=(20, 17, 29, 186),
                outline=(223, 188, 255, 105),
                width=2,
            )
            draw.rounded_rectangle(
                (x + 18, y + 17, x + 70, y + 52),
                radius=7,
                fill=(210, 65, 92, 235),
            )
            draw.text((x + 29, y + 21), number, font=number_font, fill="white")
            draw.text((x + 22, y + 64), label, font=item_font, fill="white")
            draw.text(
                (x + 22, y + 112),
                self._ellipsize(detail, 18),
                font=detail_font,
                fill=(242, 156, 171, 255),
            )

        footer_box = (60, 760, 1140, 840)
        draw.rounded_rectangle(footer_box, radius=8, fill=(15, 13, 23, 200))
        draw.text(
            (87, 785),
            "发送对应命令使用功能；若 QQ 按钮可用，也可以直接点击下方按钮。",
            font=footer_font,
            fill=(245, 245, 248, 255),
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(output_path, "JPEG", quality=90, optimize=True)
        return output_path

    def render_gallery(
        self,
        endings: Sequence[tuple[str, Path]],
        unlocked: Mapping[str, int],
        user_name: str,
        output_path: Path,
    ) -> Path:
        columns = 6
        rows = max(1, ceil(len(endings) / columns))
        margin = 42
        header_height = 190
        footer_height = 70
        gap = 14
        cell_width = (self.GALLERY_WIDTH - margin * 2 - gap * (columns - 1)) // columns
        cell_height = 145
        height = header_height + rows * cell_height + (rows - 1) * gap + footer_height

        canvas = Image.new("RGB", (self.GALLERY_WIDTH, height), (236, 240, 248))
        draw = ImageDraw.Draw(canvas)
        title_font = self._font(45, bold=True)
        stat_font = self._font(25)
        label_font = self._font(18, bold=True)
        count_font = self._font(17, bold=True)
        small_font = self._font(16)

        unique_count = sum(1 for name, _ in endings if name in unlocked)
        total_count = len(endings)
        rate = (unique_count / total_count * 100) if total_count else 0
        draw.rounded_rectangle(
            (margin, 32, self.GALLERY_WIDTH - margin, 158),
            radius=8,
            fill=(32, 27, 46),
        )
        draw.text(
            (margin + 28, 52),
            f"{self._ellipsize(user_name, 16)} 的 Doro 结局图鉴",
            font=title_font,
            fill=(255, 255, 255),
        )
        draw.text(
            (margin + 30, 113),
            f"已收集 {unique_count} / {total_count}    收集率 {rate:.2f}%",
            font=stat_font,
            fill=(241, 160, 177),
        )

        for index, (ending_name, image_path) in enumerate(endings):
            row = index // columns
            column = index % columns
            x = margin + column * (cell_width + gap)
            y = header_height + row * (cell_height + gap)
            unlocked_count = int(unlocked.get(ending_name, 0))

            draw.rounded_rectangle(
                (x, y, x + cell_width, y + cell_height),
                radius=7,
                fill=(255, 255, 255) if unlocked_count else (207, 211, 220),
                outline=(214, 108, 133) if unlocked_count else (182, 187, 198),
                width=2,
            )

            preview_box = (x + 7, y + 7, x + cell_width - 7, y + 94)
            if unlocked_count:
                try:
                    with Image.open(image_path) as source:
                        preview = ImageOps.exif_transpose(source).convert("RGB")
                        preview = ImageOps.fit(
                            preview,
                            (preview_box[2] - preview_box[0], preview_box[3] - preview_box[1]),
                            method=Image.Resampling.LANCZOS,
                        )
                    canvas.paste(preview, (preview_box[0], preview_box[1]))
                except Exception:
                    draw.rectangle(preview_box, fill=(242, 220, 226))
                badge = f"x{unlocked_count}"
                badge_width = max(45, draw.textlength(badge, font=count_font) + 18)
                draw.rounded_rectangle(
                    (x + cell_width - badge_width - 10, y + 13, x + cell_width - 10, y + 43),
                    radius=7,
                    fill=(196, 55, 88),
                )
                draw.text(
                    (x + cell_width - badge_width, y + 17),
                    badge,
                    font=count_font,
                    fill="white",
                )
                label = self._ellipsize(ending_name, 9)
                label_color = (39, 35, 48)
            else:
                draw.rectangle(preview_box, fill=(81, 83, 92))
                question = "?"
                question_font = self._font(52, bold=True)
                question_width = draw.textlength(question, font=question_font)
                draw.text(
                    (x + (cell_width - question_width) / 2, y + 20),
                    question,
                    font=question_font,
                    fill=(214, 217, 225),
                )
                label = "未解锁"
                label_color = (112, 116, 126)

            label_width = draw.textlength(label, font=label_font)
            draw.text(
                (x + (cell_width - label_width) / 2, y + 108),
                label,
                font=label_font,
                fill=label_color,
            )

        draw.text(
            (margin, height - 48),
            "每天在本群抽取一次；重复结局会累计次数。发送 /菜单 返回。",
            font=small_font,
            fill=(92, 94, 104),
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, "JPEG", quality=88, optimize=True)
        return output_path
