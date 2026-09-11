#!/usr/bin/env python3

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


USERNAME = "Aaron9115"

# Visual settings
BG = "#0D1117"
GRID_EMPTY = "#161B22"
GRID_LEVELS = [
    "#161B22",  # 0
    "#0E4429",  # 1
    "#006D32",  # 2
    "#26A641",  # 3
    "#39D353",  # 4
]
SNAKE = "#39D353"
SNAKE_HEAD = "#B6F7C7"

COLS = 53
ROWS = 7

CELL = 14
GAP = 4
RADIUS = 4
PADDING_X = 22
PADDING_Y = 20

WIDTH = PADDING_X * 2 + COLS * CELL + (COLS - 1) * GAP
HEIGHT = PADDING_Y * 2 + ROWS * CELL + (ROWS - 1) * GAP

# More frames + interpolation = smoother movement.
FRAMES_PER_CELL = 7
FRAME_DURATION_MS = 42
TAIL_LENGTH = 10


def load_contributions(path):
    data = json.loads(Path(path).read_text())
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

    # GitHub normally returns 53 weeks x 7 days.
    grid = [[0 for _ in range(ROWS)] for _ in range(COLS)]

    for x, week in enumerate(weeks[-COLS:]):
        days = week["contributionDays"]
        for day in days:
            # JS/Python weekday: Monday=0 ... Sunday=6
            from datetime import date
            d = date.fromisoformat(day["date"])
            y = d.weekday()
            if 0 <= x < COLS and 0 <= y < ROWS:
                count = int(day["contributionCount"])
                grid[x][y] = count

    return grid


def contribution_level(count, max_count):
    if count <= 0:
        return 0
    if max_count <= 0:
        return 0

    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    if ratio <= 0.50:
        return 2
    if ratio <= 0.75:
        return 3
    return 4


def build_grid(grid):
    max_count = max(max(col) for col in grid) if grid else 1

    levels = []
    for x in range(COLS):
        column = []
        for y in range(ROWS):
            column.append(contribution_level(grid[x][y], max_count))
        levels.append(column)

    return levels


def cell_center(x, y):
    return (
        PADDING_X + x * (CELL + GAP) + CELL / 2,
        PADDING_Y + y * (CELL + GAP) + CELL / 2,
    )


def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def make_route():
    # Serpentine path through the actual contribution grid.
    # It follows the same overall concept as snk: left-to-right,
    # then right-to-left on the next column.
    route = []
    for x in range(COLS):
        ys = range(ROWS) if x % 2 == 0 else range(ROWS - 1, -1, -1)
        for y in ys:
            route.append((x, y))
    return route


def interpolate(a, b, t):
    t = smoothstep(t)
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t)


def draw_rounded_rect(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def draw_frame(levels, eaten, snake_pos, snake_history):
    image = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    # Outer rounded container.
    draw.rounded_rectangle(
        (0, 0, WIDTH - 1, HEIGHT - 1),
        radius=18,
        fill=BG,
    )

    # Contribution squares.
    for x in range(COLS):
        for y in range(ROWS):
            level = levels[x][y]

            # Once eaten, the contribution square disappears back into
            # the dark empty-grid color.
            if (x, y) in eaten:
                level = 0

            px = PADDING_X + x * (CELL + GAP)
            py = PADDING_Y + y * (CELL + GAP)

            draw.rounded_rectangle(
                (px, py, px + CELL, py + CELL),
                radius=RADIUS,
                fill=GRID_LEVELS[level],
            )

    # Smooth snake trail.
    if snake_history:
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)

        if len(snake_history) >= 2:
            for i in range(1, len(snake_history)):
                p1 = snake_history[i - 1]
                p2 = snake_history[i]
                alpha = int(40 + 180 * i / len(snake_history))
                width = max(2, int(3 * i / len(snake_history)))
                glow_draw.line(
                    (p1[0], p1[1], p2[0], p2[1]),
                    fill=(57, 211, 83, alpha),
                    width=width,
                )

        glow = glow.filter(ImageFilter.GaussianBlur(5))
        image = Image.alpha_composite(image, glow)
        draw = ImageDraw.Draw(image)

        for i in range(1, len(snake_history)):
            p1 = snake_history[i - 1]
            p2 = snake_history[i]
            alpha = int(60 + 190 * i / len(snake_history))
            width = max(2, int(2 + 4 * i / len(snake_history)))
            draw.line(
                (p1[0], p1[1], p2[0], p2[1]),
                fill=(57, 211, 83, alpha),
                width=width,
            )

    # Snake head.
    hx, hy = snake_pos
    r = 7
    draw.ellipse(
        (hx - r, hy - r, hx + r, hy + r),
        fill=SNAKE,
    )
    draw.ellipse(
        (hx - 3.5, hy - 3.5, hx + 3.5, hy + 3.5),
        fill=SNAKE_HEAD,
    )

    # Tiny highlight.
    draw.ellipse(
        (hx - 2, hy - 3, hx, hy - 1),
        fill="#FFFFFF",
    )

    return image


def main():
    if len(sys.argv) != 3:
        print("Usage: generate_snake_gif.py contribution-data.json output.gif")
        sys.exit(1)

    data_path = sys.argv[1]
    output_path = sys.argv[2]

    grid = load_contributions(data_path)
    levels = build_grid(grid)
    route = make_route()

    # Build smooth movement points.
    points = [cell_center(x, y) for x, y in route]

    frames = []
    eaten = set()
    history = []

    # Add a short intro pause.
    start_frame = draw_frame(levels, eaten, points[0], [])
    for _ in range(5):
        frames.append(start_frame.copy())

    for idx in range(len(points) - 1):
        a = points[idx]
        b = points[idx + 1]
        cell = route[idx]

        for f in range(FRAMES_PER_CELL):
            t = f / FRAMES_PER_CELL
            pos = interpolate(a, b, t)

            # Eat the contribution at the cell once the head reaches it.
            if f >= FRAMES_PER_CELL // 2:
                eaten.add(cell)

            history.append(pos)
            if len(history) > TAIL_LENGTH * FRAMES_PER_CELL:
                history.pop(0)

            frame = draw_frame(levels, eaten, pos, history)
            frames.append(frame)

    # Eat the final cell and pause briefly.
    eaten.add(route[-1])
    final = draw_frame(levels, eaten, points[-1], history)
    for _ in range(8):
        frames.append(final.copy())

    # Save optimized GIF.
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    rgb_frames = [f.convert("RGB") for f in frames]
    rgb_frames[0].save(
        output_path,
        save_all=True,
        append_images=rgb_frames[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )

    print(f"Generated {output_path} with {len(rgb_frames)} frames.")


if __name__ == "__main__":
    main()
