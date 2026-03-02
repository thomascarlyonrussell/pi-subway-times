import logging
import pathlib
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from rgbmatrix import graphics

from display import get_clamped_color

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency for image backend
    Image = None


SUPPORTED_IMAGE_EXTENSIONS = (".png",)
DEFAULT_BACKEND_ORDER = ("image", "font", "text")
DEFAULT_ROUTE_SYMBOL_ALIASES = {
    "5X": "5D",
    "6X": "6D",
    "7X": "7D",
    "FS": "SF",
    "FX": "FD",
    "GS": "S",
    "SI": "SIR",
}


def _normalize_route_id(route_id: str) -> str:
    return "".join(str(route_id or "").upper().split())


def parse_backend_order(value) -> List[str]:
    if isinstance(value, str):
        tokens = [token.strip().lower() for token in value.split(",") if token.strip()]
    elif isinstance(value, (list, tuple)):
        tokens = [str(token).strip().lower() for token in value if str(token).strip()]
    else:
        tokens = []

    deduplicated = []
    for token in tokens:
        if token not in deduplicated:
            deduplicated.append(token)
    return deduplicated or list(DEFAULT_BACKEND_ORDER)


def _fallback_label(route_id: str, max_chars: int) -> str:
    normalized = _normalize_route_id(route_id)
    if not normalized:
        return "--"
    return normalized[: max(1, int(max_chars))]


class RouteSymbolBackend:
    name = "backend"

    def can_render(self, route_id: str) -> bool:
        raise NotImplementedError

    def render(self, canvas, route_id: str, x: int, baseline_y: int, color_value: int) -> None:
        raise NotImplementedError


class FontRouteSymbolBackend(RouteSymbolBackend):
    name = "font"

    def __init__(self, font):
        self.font = font

    def can_render(self, route_id: str) -> bool:
        return bool(_normalize_route_id(route_id))

    def render(self, canvas, route_id: str, x: int, baseline_y: int, color_value: int) -> None:
        graphics.DrawText(canvas, self.font, x, baseline_y, get_clamped_color(color_value), _normalize_route_id(route_id))


class TextRouteSymbolBackend(RouteSymbolBackend):
    name = "text"

    def __init__(self, font, max_chars: int):
        self.font = font
        self.max_chars = max(1, int(max_chars))

    def can_render(self, route_id: str) -> bool:
        return True

    def render(self, canvas, route_id: str, x: int, baseline_y: int, color_value: int) -> None:
        graphics.DrawText(
            canvas,
            self.font,
            x,
            baseline_y,
            get_clamped_color(color_value),
            _fallback_label(route_id, self.max_chars),
        )


@dataclass
class _AssetMask:
    width: int
    height: int
    pixels: List[Tuple[int, int]]


class ImageRouteSymbolBackend(RouteSymbolBackend):
    name = "image"

    def __init__(
        self,
        assets_dir: pathlib.Path,
        max_asset_px: int,
        cache_limit: int,
        route_symbol_aliases: Dict[str, str],
        logger: logging.Logger,
    ):
        self.assets_dir = assets_dir
        self.max_asset_px = max(1, int(max_asset_px))
        self.cache_limit = max(1, int(cache_limit))
        self.route_symbol_aliases = {
            _normalize_route_id(alias): _normalize_route_id(target)
            for alias, target in (route_symbol_aliases or {}).items()
            if _normalize_route_id(alias) and _normalize_route_id(target)
        }
        self.logger = logger
        self._asset_index = self._build_asset_index()
        self._cache: "OrderedDict[str, _AssetMask]" = OrderedDict()

    def _resolve_symbol_key(self, route_id: str) -> str:
        normalized = _normalize_route_id(route_id)
        if normalized in self._asset_index:
            return normalized
        alias = self.route_symbol_aliases.get(normalized, "")
        if alias and alias in self._asset_index:
            return alias
        return normalized

    def _build_asset_index(self) -> Dict[str, pathlib.Path]:
        if not self.assets_dir.exists():
            return {}
        index = {}
        for path in self.assets_dir.iterdir():
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                continue
            route_id = _normalize_route_id(path.stem)
            if route_id:
                index[route_id] = path
        return index

    def _load_asset(self, route_id: str) -> Optional[_AssetMask]:
        if Image is None:
            return None
        path = self._asset_index.get(route_id)
        if path is None:
            return None

        with Image.open(path) as img:
            rgba = img.convert("RGBA")
            width, height = rgba.size
            if width > self.max_asset_px or height > self.max_asset_px:
                self.logger.warning(
                    "Route symbol asset %s exceeds %sx%s and will be ignored",
                    path,
                    self.max_asset_px,
                    self.max_asset_px,
                )
                return None

            pixels = []
            for x in range(width):
                for y in range(height):
                    if rgba.getpixel((x, y))[3] > 0:
                        pixels.append((x, y))
            return _AssetMask(width=width, height=height, pixels=pixels)

    def _get_mask(self, route_id: str) -> Optional[_AssetMask]:
        if route_id in self._cache:
            self._cache.move_to_end(route_id)
            return self._cache[route_id]

        mask = self._load_asset(route_id)
        if mask is None:
            return None

        self._cache[route_id] = mask
        if len(self._cache) > self.cache_limit:
            self._cache.popitem(last=False)
        return mask

    def can_render(self, route_id: str) -> bool:
        return self._resolve_symbol_key(route_id) in self._asset_index and Image is not None

    def render(self, canvas, route_id: str, x: int, baseline_y: int, color_value: int) -> None:
        symbol_key = self._resolve_symbol_key(route_id)
        mask = self._get_mask(symbol_key)
        if mask is None:
            raise ValueError("Missing or invalid image symbol asset")

        top = baseline_y - mask.height + 1
        red = (color_value >> 16) & 0xFF
        green = (color_value >> 8) & 0xFF
        blue = color_value & 0xFF
        for px, py in mask.pixels:
            canvas.SetPixel(x + px, top + py, red, green, blue)


class RouteSymbolRenderer:
    def __init__(self, backends: Iterable[RouteSymbolBackend], logger: logging.Logger):
        backend_map = {backend.name: backend for backend in backends}
        self._backend_order = list(backend_map.keys())
        self._backends = backend_map
        self._logger = logger
        self.last_backend = "none"

    def render(self, canvas, route_id: str, x: int, baseline_y: int, color_value: int) -> str:
        normalized = _normalize_route_id(route_id)
        for backend_name in self._backend_order:
            backend = self._backends[backend_name]
            try:
                if not backend.can_render(normalized):
                    continue
                backend.render(canvas, normalized, x, baseline_y, color_value)
                self.last_backend = backend_name
                return backend_name
            except Exception as exc:
                self._logger.error(
                    "Route symbol backend '%s' failed for route '%s': %s",
                    backend_name,
                    normalized,
                    exc,
                )
                continue

        # Final safety fallback keeps render loop alive.
        color = get_clamped_color(color_value)
        graphics.DrawText(canvas, self._backends["text"].font, x, baseline_y, color, "--")
        self.last_backend = "hardcoded"
        return self.last_backend


def build_route_symbol_renderer(display_config: dict, route_font, text_font, logger: Optional[logging.Logger] = None):
    logger = logger or logging.getLogger(__name__)
    backend_order = parse_backend_order(display_config.get("route_symbol_backends", DEFAULT_BACKEND_ORDER))
    max_asset_px = int(display_config.get("route_symbol_max_asset_px", 10))
    cache_limit = int(display_config.get("route_symbol_cache_limit", 128))
    text_max_chars = int(display_config.get("route_symbol_text_max_chars", 2))
    route_symbol_aliases = display_config.get("route_symbol_aliases", DEFAULT_ROUTE_SYMBOL_ALIASES)
    assets_dir = pathlib.Path(display_config.get("route_symbol_assets_dir", "assets/route_symbols"))
    if not assets_dir.is_absolute():
        assets_dir = pathlib.Path(__file__).resolve().parent.parent / assets_dir

    backends: Dict[str, RouteSymbolBackend] = {
        "font": FontRouteSymbolBackend(route_font),
        "text": TextRouteSymbolBackend(text_font, text_max_chars),
    }
    backends["image"] = ImageRouteSymbolBackend(
        assets_dir=assets_dir,
        max_asset_px=max_asset_px,
        cache_limit=cache_limit,
        route_symbol_aliases=route_symbol_aliases,
        logger=logger,
    )

    resolved = []
    for backend_name in backend_order:
        backend = backends.get(backend_name)
        if backend is None:
            continue
        resolved.append(backend)

    # Text backend is always available as deterministic fallback.
    if "text" not in [backend.name for backend in resolved]:
        resolved.append(backends["text"])

    return RouteSymbolRenderer(resolved, logger)
