"""Logical terminal preview for the subway sign without LED hardware."""

import argparse
import sys
import time
from datetime import datetime

from config import load_runtime_config
from display import truncate_to_pixel_width


def placeholder_rows():
    placeholder = {
        "line": "--",
        "direction": "No Data",
        "minutes_until_arrival": "--",
        "route_color": "FFFFFF",
    }
    return [dict(placeholder), dict(placeholder), dict(placeholder)]


def normalize_rows(trip_data):
    if not trip_data:
        return placeholder_rows()
    rows = list(trip_data)
    while len(rows) < 3:
        rows.append(dict(rows[-1]))
    return rows


class ConsoleEmulator:
    def __init__(self, config=None, trip_pipeline=None, clock=time.monotonic, wall_clock=time.time):
        self.config = config or load_runtime_config()
        display = self.config["display"]
        feed = self.config["feed"]
        self.clock = clock
        self.wall_clock = wall_clock
        self.refresh_time_delay = int(display["refresh_time_delay"])
        self.stale_data_grace_sec = int(display["stale_data_grace_sec"])
        self.rotate_trip_delay = int(display["rotate_trip_delay"])
        self.screen_refresh_interval = int(display["screen_refresh_interval"])
        self.routes = [route.strip() for route in feed["mta_routes"].split(",") if route.strip()]
        self.directions = [direction.strip() for direction in display["mta_directions"].split(",") if direction.strip()]
        self.station = feed["mta_stop"]
        if trip_pipeline is None:
            from trips import Trips

            trip_pipeline = Trips(self.station, self.directions, self.routes, config=self.config)
        self.trips = trip_pipeline
        self.trip_data = None
        self.last_success_at = None
        self.last_fetch_error = ""
        self.current_refresh_delay = max(1, self.refresh_time_delay)
        self.next_fetch_at = self.clock()
        self.rotate_at = self.clock() + self.rotate_trip_delay
        self.bottom_row_index = 2

    def fetch_if_due(self, now=None):
        now = self.clock() if now is None else now
        if now < self.next_fetch_at:
            return False

        try:
            latest_trips = self.trips.fetch_trip_data()
        except Exception as exc:  # The console remains usable if a custom pipeline fails.
            latest_trips = None
            self.last_fetch_error = str(exc)

        self.current_refresh_delay = max(
            1, int(getattr(self.trips, "last_refresh_interval_sec", self.refresh_time_delay))
        )
        self.next_fetch_at = now + self.current_refresh_delay
        if latest_trips:
            self.trip_data = latest_trips
            self.last_success_at = now
            self.last_fetch_error = ""
            return True

        if not self.last_fetch_error:
            self.last_fetch_error = str(getattr(self.trips, "last_fetch_error", "") or "No trip data returned")
        return False

    def is_stale(self, now=None):
        now = self.clock() if now is None else now
        return self.last_success_at is not None and now - self.last_success_at > self.stale_data_grace_sec

    def render_rows(self, now=None):
        if self.is_stale(now):
            return placeholder_rows()
        return normalize_rows(self.trip_data)

    def selected_rows(self, now=None):
        now = self.clock() if now is None else now
        rows = self.render_rows(now)
        if now >= self.rotate_at:
            self.bottom_row_index = self.bottom_row_index + 1 if self.bottom_row_index < len(rows) - 1 else 2
            self.rotate_at = now + self.rotate_trip_delay
        bottom_index = min(self.bottom_row_index, len(rows) - 1)
        return [rows[0], rows[1], rows[bottom_index]]

    def freshness(self, now=None):
        if self.is_stale(now):
            return "STALE"
        if self.last_success_at is None:
            return "NO DATA"
        return "FRESH"

    def render_frame(self, now=None):
        now = self.clock() if now is None else now
        rows = self.selected_rows(now)
        remaining = max(0, int(round(self.next_fetch_at - now)))
        last_success = "never"
        if self.last_success_at is not None:
            last_success = datetime.fromtimestamp(self.wall_clock() - (now - self.last_success_at)).strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "Subway Sign Logical Preview (console only)",
            f"Station: {self.station} | Routes: {', '.join(self.routes) or '--'} | Directions: {', '.join(self.directions) or '--'}",
            "",
        ]
        display_cfg = self.config.get("display", {})
        max_pixels = display_cfg.get("line_direction_max_pixels", 40)
        max_chars = display_cfg.get("line_direction_max_length", 10)
        for index, row in enumerate(rows, start=1):
            dir_text = truncate_to_pixel_width(
                None,
                str(row.get("direction", "No Data")),
                max_pixels=max_pixels,
                max_chars=max_chars,
            )
            lines.append(
                f"{index}: {str(row.get('line', '--')):<4} {dir_text:<24} {str(row.get('minutes_until_arrival', '--')):>3} min"
            )
        lines.extend(
            [
                "",
                f"Status: {self.freshness(now)} | Last success: {last_success}",
                f"Next fetch: {remaining}s | Refresh interval: {self.current_refresh_delay}s",
            ]
        )
        if self.last_fetch_error:
            lines.append(f"Fetch error: {self.last_fetch_error}")
        return "\n".join(lines)

    def run(self, interactive=None, once=False):
        interactive = sys.stdout.isatty() if interactive is None else interactive
        try:
            while True:
                now = self.clock()
                self.fetch_if_due(now)
                frame = self.render_frame(now)
                if interactive:
                    print("\033[2J\033[H" + frame, flush=True)
                else:
                    print(frame, flush=True)
                if self.last_fetch_error:
                    print(f"Fetch error: {self.last_fetch_error}", file=sys.stderr, flush=True)
                if once:
                    return
                time.sleep(max(1, self.screen_refresh_interval))
        except KeyboardInterrupt:
            return


def main():
    parser = argparse.ArgumentParser(description="Preview the subway sign's logical rows in a terminal.")
    parser.add_argument("--once", action="store_true", help="Fetch and render one frame, then exit.")
    args = parser.parse_args()
    ConsoleEmulator().run(once=args.once)


if __name__ == "__main__":
    main()