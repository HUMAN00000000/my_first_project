from __future__ import annotations

import asyncio
import json
import random
import re
import time
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image, Plain
from astrbot.api.star import Context, Star, register

from .content import (
    NORMAL_FOODS,
    RECIPES,
    RECIPE_DESCRIPTIONS,
    STRANGE_BUT_EDIBLE_FOODS,
)
from .renderer import MenuRenderer
from .storage import DoroStore


PLUGIN_NAME = "astrbot_plugin_doro_home"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


@register(
    PLUGIN_NAME,
    "Codex & HUMAN",
    "Doro 小窝：菜单、每日结局图鉴、随机表情、吃什么和手动搬史",
    "0.1.0",
)
class DoroHomePlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.config = config or {}
        self.plugin_dir = Path(__file__).resolve().parent
        self.data_root = self._detect_data_root()
        self.data_dir = self.data_root / "plugin_data" / PLUGIN_NAME
        self.cache_dir = self.data_dir / "cache"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.store = DoroStore(self.data_dir / "doro_home.db")
        self.renderer = MenuRenderer(self.cache_dir)
        self.source_groups = self._load_source_groups()
        self._draw_lock = asyncio.Lock()
        self._render_lock = asyncio.Lock()
        self._last_banshi_at: dict[str, float] = {}
        self._keyboard_unavailable = False
        self._meme_files: tuple[float, list[Path]] = (0.0, [])
        self._recipe_requests = 0
        self._import_legacy_history_cache()

    def _detect_data_root(self) -> Path:
        if self.plugin_dir.parent.name == "plugins":
            return self.plugin_dir.parent.parent
        return self.plugin_dir / ".runtime"

    @staticmethod
    def _clean_ids(values: Any) -> list[str]:
        if not isinstance(values, (list, tuple, set)):
            return []
        result: list[str] = []
        for value in values:
            normalized = str(value).strip()
            if normalized and normalized not in result:
                result.append(normalized)
        return result

    def _load_source_groups(self) -> list[str]:
        configured = self._clean_ids(self.config.get("banshi_source_groups", []))
        if configured:
            return configured

        legacy_config = (
            self.data_root / "config" / "astrbot_sowing_discord_config.json"
        )
        try:
            payload = json.loads(legacy_config.read_text(encoding="utf-8-sig"))
            return self._clean_ids(payload.get("banshi_group_list", []))
        except (OSError, ValueError, TypeError):
            return []

    def _import_legacy_history_cache(self) -> None:
        if len(self.source_groups) != 1:
            return
        cache_file = self.data_root / "sowing_discord_cache" / "local_cache.json"
        try:
            payload = json.loads(cache_file.read_text(encoding="utf-8-sig"))
            entries = [
                (str(message_id), float(timestamp))
                for message_id, timestamp in payload.items()
            ]
            imported = self.store.import_history(self.source_groups[0], entries)
            if imported:
                logger.info(f"[DoroHome] Imported {imported} history message IDs")
        except (OSError, ValueError, TypeError, AttributeError):
            return

    def _doro_directory(self) -> Path:
        configured = str(self.config.get("doro_image_dir", "") or "").strip()
        candidates = []
        if configured:
            candidates.append(Path(configured).expanduser())
        candidates.extend(
            [
                self.plugin_dir.parent / "astrbot_plugin_doro_today" / "doro",
                self.plugin_dir / "assets" / "doro",
            ]
        )
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0] if candidates else self.plugin_dir / "assets" / "doro"

    def _doro_endings(self) -> list[tuple[str, Path]]:
        directory = self._doro_directory()
        if not directory.is_dir():
            return []
        return sorted(
            [
                (path.stem, path)
                for path in directory.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            ],
            key=lambda item: item[0].casefold(),
        )

    @staticmethod
    def _group_id(event: AstrMessageEvent) -> str | None:
        message = getattr(event, "message_obj", None)
        value = getattr(message, "group_id", None)
        if value in (None, "", 0, "0"):
            return None
        return str(value)

    @staticmethod
    def _message_id(event: AstrMessageEvent) -> str | None:
        message = getattr(event, "message_obj", None)
        value = getattr(message, "message_id", None)
        if value in (None, ""):
            return None
        return str(value)

    @staticmethod
    def _sender_name(event: AstrMessageEvent) -> str:
        try:
            return str(event.get_sender_name() or event.get_sender_id())
        except (AttributeError, TypeError):
            return str(event.get_sender_id())

    @staticmethod
    def _scope_id(event: AstrMessageEvent) -> str:
        group_id = DoroHomePlugin._group_id(event)
        return group_id if group_id else f"private:{event.get_sender_id()}"

    @staticmethod
    def _safe_cache_part(value: str) -> str:
        return re.sub(r"[^0-9A-Za-z_-]", "_", value)[:80] or "unknown"

    def _menu_text(self) -> str:
        return (
            "Doro 的小窝\n"
            "/今日 - 每日结局\n"
            "/图鉴 - 查看个人收集\n"
            "/运势 - 今日运势\n"
            "/随机表情包 - 随机收藏表情\n"
            "/吃点啥 - 本地菜谱推荐\n"
            "/菜谱搜索 <关键词> - 搜索菜名/食材\n"
            "/怎么做 <菜名> - 查看简易做法\n"
            "/随机推荐 [数量] - 随机多道菜\n"
            "/菜谱分类 - 查看分类\n"
            "/搬史 - 随机搬一条已缓存的史\n"
            "/帮助 - 完整说明"
        )

    async def _menu_image(self) -> Path | None:
        background = self.plugin_dir / "assets" / "menu_background.jpg"
        if not background.is_file():
            return None
        output = self.cache_dir / "menu.jpg"
        if output.is_file() and output.stat().st_mtime >= background.stat().st_mtime:
            return output
        async with self._render_lock:
            if output.is_file() and output.stat().st_mtime >= background.stat().st_mtime:
                return output
            return await asyncio.to_thread(
                self.renderer.render_menu, background, output
            )

    @staticmethod
    def _button_rows(
        buttons: Sequence[tuple[str, str]], columns: int = 2
    ) -> list[dict[str, Any]]:
        rows = []
        for row_index in range(0, len(buttons), columns):
            row_buttons = []
            for index, (label, command) in enumerate(
                buttons[row_index : row_index + columns], start=row_index
            ):
                row_buttons.append(
                    {
                        "id": f"doro_home_{index}",
                        "render_data": {
                            "label": label,
                            "visited_label": label,
                            "style": 1,
                        },
                        "action": {
                            "type": 2,
                            "permission": {"type": 2},
                            "data": command,
                            "enter": True,
                        },
                    }
                )
            rows.append({"buttons": row_buttons})
        return rows

    async def _try_send_keyboard(
        self,
        event: AstrMessageEvent,
        buttons: Sequence[tuple[str, str]],
        columns: int = 2,
    ) -> bool:
        if not bool(self.config.get("enable_qq_keyboard", True)):
            return False
        if self._keyboard_unavailable:
            return False
        group_id = self._group_id(event)
        bot = getattr(event, "bot", None)
        api = getattr(bot, "api", None)
        if not group_id or api is None:
            return False

        keyboard = {
            "type": "keyboard",
            "data": {"content": {"rows": self._button_rows(buttons, columns)}},
        }
        try:
            await api.call_action(
                "send_group_msg", group_id=int(group_id), message=[keyboard]
            )
            return True
        except Exception as exc:
            self._keyboard_unavailable = True
            logger.warning(
                "[DoroHome] QQ keyboard is unavailable; using command fallback: "
                f"{exc}"
            )
            return False

    async def _send_return_button(self, event: AstrMessageEvent) -> None:
        await self._try_send_keyboard(event, [("返回 Doro 小窝", "/菜单")], 1)

    @filter.command("菜单", alias={"doro菜单"})
    async def menu(self, event: AstrMessageEvent):
        """Show the Doro Home menu."""
        event.stop_event()
        try:
            menu_image = await self._menu_image()
        except Exception as exc:
            menu_image = None
            logger.error(f"[DoroHome] Failed to render menu: {exc}")

        chain = []
        if menu_image:
            chain.append(Image.fromFileSystem(str(menu_image)))
        chain.append(Plain(self._menu_text()))
        yield event.chain_result(chain)
        await self._try_send_keyboard(
            event,
            [
                ("今日结局", "/今日"),
                ("个人图鉴", "/图鉴"),
                ("今日运势", "/运势"),
                ("随机表情", "/随机表情包"),
                ("吃点啥", "/吃点啥"),
                ("今日搬史", "/搬史"),
                ("帮助", "/帮助"),
            ],
        )

    @filter.command(
        "今日", alias={"doro今日", "今日doro", "doro结局", "dorotoday", "doro今日结局"}
    )
    async def doro_today(self, event: AstrMessageEvent):
        """Draw one ending per day for each user in each group."""
        event.stop_event()
        endings = self._doro_endings()
        if not endings:
            yield event.plain_result(
                "没有找到 Doro 结局图片。请保留原 astrbot_plugin_doro_today 插件目录。"
            )
            return

        candidates = [(name, str(path)) for name, path in endings]
        async with self._draw_lock:
            result = await asyncio.to_thread(
                self.store.draw_ending,
                self._scope_id(event),
                str(event.get_sender_id()),
                date.today().isoformat(),
                candidates,
            )

        ending_paths = {name: path for name, path in endings}
        image_path = ending_paths.get(result.ending_name, Path(result.image_file))
        if result.is_new_today:
            lead = f"你今天的 Doro 结局是：{result.ending_name}"
            if result.total_times > 1:
                lead += f"\n这是你在本群第 {result.total_times} 次抽到这个结局。"
        else:
            lead = (
                f"你今天已经抽过了：{result.ending_name}\n"
                "每天只能抽一次，再次查看不会增加次数。"
            )

        chain = [Plain(f"{lead}\n")]
        if image_path.is_file():
            chain.append(Image.fromFileSystem(str(image_path)))
        chain.append(Plain("\n发送 /图鉴 查看收集，发送 /菜单 返回。"))
        yield event.chain_result(chain)
        await self._send_return_button(event)

    @filter.command("图鉴", alias={"doro图鉴", "我的doro", "我的图鉴", "doro收集"})
    async def doro_gallery(self, event: AstrMessageEvent):
        """Render the current user's collection for this group."""
        event.stop_event()
        endings = self._doro_endings()
        if not endings:
            yield event.plain_result("没有找到 Doro 结局图片，暂时无法生成图鉴。")
            return
        collection = await asyncio.to_thread(
            self.store.get_collection,
            self._scope_id(event),
            str(event.get_sender_id()),
        )
        output = self.cache_dir / (
            "gallery_"
            f"{self._safe_cache_part(self._scope_id(event))}_"
            f"{self._safe_cache_part(str(event.get_sender_id()))}.jpg"
        )
        try:
            async with self._render_lock:
                await asyncio.to_thread(
                    self.renderer.render_gallery,
                    endings,
                    collection,
                    self._sender_name(event),
                    output,
                )
            yield event.chain_result(
                [
                    Image.fromFileSystem(str(output)),
                    Plain("\n发送 /今日 抽取，发送 /菜单 返回。"),
                ]
            )
        except Exception as exc:
            logger.error(f"[DoroHome] Failed to render collection: {exc}")
            collected = "\n".join(
                f"- {name} x{count}" for name, count in collection.items()
            ) or "还没有收集到结局。"
            yield event.plain_result(
                f"已收集 {len(collection)} / {len(endings)}\n{collected}\n\n发送 /菜单 返回。"
            )
        await self._send_return_button(event)

    @filter.command("运势说明", alias={"doro运势说明", "运势入口"})
    async def fortune_entry(self, event: AstrMessageEvent):
        """Explain the standalone jrys command without shadowing it."""
        event.stop_event()
        yield event.plain_result(
            "今日运势\n发送 /运势 查看今天的运势和签到经验。\n发送 /菜单 返回。"
        )
        await self._try_send_keyboard(
            event,
            [("查看今日运势", "/运势"), ("返回 Doro 小窝", "/菜单")],
            2,
        )

    def _stealer_images(self) -> list[Path]:
        now = time.time()
        cached_at, cached_files = self._meme_files
        if now - cached_at < 60 and cached_files:
            return cached_files

        configured = str(self.config.get("meme_directory", "") or "").strip()
        roots = []
        if configured:
            roots.append(Path(configured).expanduser())
        roots.extend(
            [
                # Reuse meme_manager's managed packs without invoking its LLM
                # tools during ordinary chat.
                self.data_root / "plugin_data" / "meme_manager" / "packs",
                self.data_root / "plugin_data" / PLUGIN_NAME / "memes",
                self.data_root
                / "plugin_data"
                / "astrbot_plugin_stealer"
                / "categories",
                self.data_root / "plugin_data" / "astrbot_plugin_stealer" / "raw",
            ]
        )

        files: list[Path] = []
        for root in roots:
            if not root.is_dir():
                continue
            files.extend(
                path
                for path in root.rglob("*")
                if path.is_file()
                and path.suffix.lower() in IMAGE_EXTENSIONS
                and path.stat().st_size > 0
            )
            if files:
                break
        self._meme_files = (now, files)
        return files

    @filter.command("随机表情包", alias={"来张表情", "随机表情"})
    async def random_meme(self, event: AstrMessageEvent):
        """Send one image collected by astrbot_plugin_stealer."""
        event.stop_event()
        files = await asyncio.to_thread(self._stealer_images)
        if not files:
            yield event.plain_result(
                "表情包小偷的收藏目录目前没有可用图片。先让它收集并完成分类，"
                "或者在插件配置中指定表情包目录。\n发送 /菜单 返回。"
            )
            return
        selected = random.SystemRandom().choice(files)
        yield event.chain_result(
            [
                Image.fromFileSystem(str(selected)),
                Plain("\n发送 /随机表情包 再来一张，发送 /菜单 返回。"),
            ]
        )
        await self._send_return_button(event)

    def _message_args(self, event: AstrMessageEvent) -> str:
        text = str(getattr(event, "message_str", "") or "").strip()
        # AstrBot may prepend an internal message id to message_str. It is
        # metadata, not a user argument, so remove it before parsing commands.
        text = re.sub(r"^\s*\[MSG_ID:\s*[^\]]+\]\s*", "", text)
        return re.sub(r"^[/！!]?\S+\s*", "", text, count=1).strip()

    def _recipe_rows(self, keyword: str = "") -> list[tuple[str, str, str, str]]:
        keyword = keyword.casefold().strip()
        if not keyword:
            return list(RECIPES)
        return [row for row in RECIPES if keyword in " ".join(row[:3]).casefold()]

    @filter.command("吃点啥", alias={"吃什么"})
    async def what_to_eat(self, event: AstrMessageEvent):
        """Offline recipe recommendation with the original odd menu preserved."""
        event.stop_event()
        self._recipe_requests += 1
        requested = self._message_args(event)
        rows = self._recipe_rows(requested)
        if requested and rows:
            normal = random.SystemRandom().choice(rows)[0]
        elif requested:
            normal = random.SystemRandom().choice(RECIPES)[0]
        else:
            normal = random.SystemRandom().choice(RECIPES)[0]
        description = RECIPE_DESCRIPTIONS.get(
            normal,
            "这道菜暂时没有写完简介，但它已经被 Doro 选中了。先吃，简介以后再加载。",
        )
        prefix = f"没有找到“{requested}”，Doro 先端上一份随机的：" if requested and not rows else ""
        chooser = random.SystemRandom()
        strange = chooser.choice(STRANGE_BUT_EDIBLE_FOODS)
        yield event.plain_result(
            "今天吃什么\n\n"
            f"【正常推荐】\n\n　　{prefix}{normal}\n\n"
            f"　　{description}\n\n"
            f"【怪味菜单】\n\n　　{strange}\n\n"
            "怪味菜单仅供娱乐；过敏、忌口或食材安全问题请自行避开。\n"
            "发送 /吃点啥 荤菜，或 /菜单 返回。"
        )
        await self._send_return_button(event)

    @filter.command("菜谱搜索")
    async def recipe_search(self, event: AstrMessageEvent):
        event.stop_event()
        keyword = self._message_args(event)
        if not keyword:
            yield event.plain_result("用法：/菜谱搜索 鸡蛋\n发送 /菜单 返回。")
            return
        rows = self._recipe_rows(keyword)
        if not rows:
            yield event.plain_result(f"没有搜到“{keyword}”。换个食材试试。")
            return
        lines = [f"搜索“{keyword}”的结果（{len(rows)} 道）："]
        lines.extend(f"· {name}（{category}）" for name, category, _, _ in rows[:15])
        yield event.plain_result("\n".join(lines) + "\n发送 /怎么做 菜名 查看做法。")

    @filter.command("怎么做")
    async def recipe_detail(self, event: AstrMessageEvent):
        event.stop_event()
        keyword = self._message_args(event)
        rows = self._recipe_rows(keyword)
        if not keyword or not rows:
            yield event.plain_result("用法：/怎么做 蛋炒饭\n暂时只支持本地菜谱。")
            return
        name, category, _, steps = rows[0]
        yield event.plain_result(f"【{name}】（{category}）\n\n做法：{steps}\n\n发送 /吃点啥 返回推荐。")

    @filter.command("随机推荐")
    async def random_recipes(self, event: AstrMessageEvent):
        event.stop_event()
        raw = self._message_args(event)
        try:
            count = max(1, min(int(raw or "3"), 8))
        except ValueError:
            count = 3
        selected = random.SystemRandom().sample(RECIPES, min(count, len(RECIPES)))
        lines = [f"随机推荐 {len(selected)} 道菜："]
        lines.extend(f"· {name}（{category}）" for name, category, _, _ in selected)
        yield event.plain_result("\n".join(lines) + "\n发送 /菜单 返回。")

    @filter.command("菜谱分类")
    async def recipe_categories(self, event: AstrMessageEvent):
        event.stop_event()
        counts: dict[str, int] = {}
        for _, category, _, _ in RECIPES:
            counts[category] = counts.get(category, 0) + 1
        lines = ["本地菜谱分类："]
        lines.extend(f"· {category}：{count} 道" for category, count in counts.items())
        yield event.plain_result("\n".join(lines) + "\n用法：/吃点啥 荤菜")

    @filter.command("食谱帮助")
    async def recipe_help(self, event: AstrMessageEvent):
        event.stop_event()
        yield event.plain_result(
            "本地食谱帮助\n\n/吃点啥 [分类或关键词]\n/菜谱搜索 <关键词>\n"
            "/怎么做 <菜名>\n/随机推荐 [数量]\n/菜谱分类\n\n"
            "数据随插件保存，不依赖外网。发送 /菜单 返回。"
        )

    @filter.command("食谱统计")
    async def recipe_stats(self, event: AstrMessageEvent):
        event.stop_event()
        yield event.plain_result(f"本地食谱共 {len(RECIPES)} 道，已完成推荐 {self._recipe_requests} 次。")

    @filter.command("重载食谱")
    async def reload_recipes(self, event: AstrMessageEvent):
        event.stop_event()
        self._recipe_requests = 0
        yield event.plain_result("本地食谱已重新载入，不需要联网。")

    @filter.command("怪味菜单")
    async def strange_food(self, event: AstrMessageEvent):
        """Return one odd but edible combination."""
        event.stop_event()
        selected = random.SystemRandom().choice(STRANGE_BUT_EDIBLE_FOODS)
        yield event.plain_result(
            f"Doro 怪味菜单\n\n【{selected}】\n\n"
            "仅供娱乐，请根据过敏和忌口自行判断。\n发送 /菜单 返回。"
        )
        await self._send_return_button(event)

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def cache_history_message(self, event: AstrMessageEvent):
        """Cache message IDs from configured trusted source groups."""
        group_id = self._group_id(event)
        message_id = self._message_id(event)
        if not group_id or not message_id or group_id not in self.source_groups:
            return
        if not message_id.isdigit():
            return
        await asyncio.to_thread(
            self.store.record_history, group_id, message_id, time.time()
        )

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def respond_to_poke(self, event: AstrMessageEvent):
        """Reply when NapCat delivers a OneBot poke notice.

        Poke is represented as a message component on different AstrBot
        versions, so detect it by component type name to keep this plugin
        compatible with both old and new APIs.
        """
        message = getattr(event, "message_obj", None)
        components = getattr(message, "message", None) or getattr(
            message, "message_chain", None
        ) or []
        if not any(type(component).__name__.lower() == "poke" for component in components):
            return
        event.stop_event()
        replies = (
            "你戳我干嘛？",
            "别戳啦，我在认真工作。",
            "戳到了，Doro 已经注意到你了。",
        )
        yield event.plain_result(random.choice(replies))

    @filter.command("搬史", alias={"今日搬史"})
    async def manual_history(self, event: AstrMessageEvent):
        """Forward one cached source-group message into the current group."""
        event.stop_event()
        target_group = self._group_id(event)
        if not target_group:
            yield event.plain_result("搬史只能在群聊中使用。发送 /菜单 返回。")
            return
        if not self.source_groups:
            yield event.plain_result(
                "还没有配置搬史来源群。请在本插件配置中填写来源群，"
                "或保留原搬史插件的来源群配置。\n发送 /菜单 返回。"
            )
            return

        cooldown = max(0, int(self.config.get("banshi_cooldown_seconds", 30)))
        now = time.time()
        remaining = cooldown - int(now - self._last_banshi_at.get(target_group, 0))
        if remaining > 0:
            yield event.plain_result(
                f"搬史冷却中，还要等 {remaining} 秒。\n发送 /菜单 返回。"
            )
            return

        bot = getattr(event, "bot", None)
        api = getattr(bot, "api", None)
        if api is None:
            yield event.plain_result("当前平台不是可用的 NapCat/OneBot 连接。")
            return

        for _ in range(5):
            selected = await asyncio.to_thread(
                self.store.pick_history, self.source_groups
            )
            if not selected:
                break
            source_group, message_id = selected
            try:
                detail = await api.call_action("get_msg", message_id=int(message_id))
                reported_group = str(detail.get("group_id", source_group))
                if reported_group not in ("", "0", source_group):
                    await asyncio.to_thread(
                        self.store.remove_history, source_group, message_id
                    )
                    continue
                await api.call_action(
                    "forward_group_single_msg",
                    group_id=int(target_group),
                    message_id=int(message_id),
                )
                await asyncio.to_thread(
                    self.store.mark_history_used, source_group, message_id
                )
                self._last_banshi_at[target_group] = time.time()
                yield event.plain_result("今日份搬史完成。发送 /菜单 返回。")
                await self._send_return_button(event)
                return
            except Exception as exc:
                logger.warning(
                    f"[DoroHome] Failed to forward cached message {message_id}: {exc}"
                )
                await asyncio.to_thread(
                    self.store.remove_history, source_group, message_id
                )

        yield event.plain_result(
            "当前没有可搬的历史消息。机器人需要先在来源群收到一些新消息，"
            "之后再试。\n发送 /菜单 返回。"
        )
        await self._send_return_button(event)

    @filter.command("帮助", alias={"doro帮助"})
    async def doro_help(self, event: AstrMessageEvent):
        """Show help without invoking the global AstrBot help menu."""
        event.stop_event()
        yield event.plain_result(
            "Doro 小窝帮助\n\n"
            "@doro子 菜单：打开主菜单\n"
            "/今日：每日抽一次结局\n"
            "/图鉴：查看本群个人图鉴\n"
            "/运势：今日运势\n"
            "/随机表情包：随机发送一张收藏\n"
            "/吃点啥：本地菜谱推荐（/吃什么 兼容）\n"
            "/菜谱搜索、/怎么做、/随机推荐、/菜谱分类：食谱工具\n"
            "/搬史：手动随机搬一条\n"
            "/状态：查看模块状态\n\n"
            "结局按群、按 QQ 用户分别统计；同一天重复查看不会重复计数。\n"
            "发送 /菜单 返回。"
        )
        await self._send_return_button(event)

    @filter.command("状态", alias={"doro状态"})
    async def doro_status(self, event: AstrMessageEvent):
        """Show non-sensitive diagnostics."""
        event.stop_event()
        endings = self._doro_endings()
        memes = await asyncio.to_thread(self._stealer_images)
        history_count = await asyncio.to_thread(
            self.store.history_count, self.source_groups
        )
        yield event.plain_result(
            "Doro 小窝状态\n"
            f"结局图片：{len(endings)}\n"
            f"可用表情包：{len(memes)}\n"
            f"搬史来源群：{len(self.source_groups)} 个\n"
            f"已缓存史：{history_count} 条\n"
            f"QQ 按钮：{'已回退到命令' if self._keyboard_unavailable else '等待实机验证'}\n"
            "发送 /菜单 返回。"
        )
        await self._send_return_button(event)
