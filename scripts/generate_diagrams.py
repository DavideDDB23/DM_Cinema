"""
Generate presentation-ready architecture diagrams for Cinema Analytics DW.

Outputs:
  docs/diagrams/er_reconciled.png
  docs/diagrams/dfm_schema.png
  docs/diagrams/star_schema.png
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle


REPO_ROOT = Path(__file__).resolve().parent.parent
DIAGRAMS = REPO_ROOT / "docs" / "diagrams"

DPI = 180
OUTPUT_WIDTH = 2253
OUTPUT_HEIGHT = 1050
CANVAS_WIDTH = 16
CANVAS_HEIGHT = 7.46

BG = "#ffffff"
SURFACE = "#f7f8fa"
FG = "#111111"
MUTED = "#6b7280"
BORDER = "#d9dee7"
INK = "#27313f"
ACCENT = "#1677ff"
ACCENT_SOFT = "#e8f2ff"
GREEN = "#2f8f4e"
GREEN_SOFT = "#eaf7ef"
ORANGE = "#f57c00"
ORANGE_SOFT = "#fff3e0"


def setup_canvas():
    fig = plt.figure(
        figsize=(OUTPUT_WIDTH / DPI, OUTPUT_HEIGHT / DPI),
        dpi=DPI,
    )
    ax = fig.add_axes((0, 0, 1, 1))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, CANVAS_WIDTH)
    ax.set_ylim(0, CANVAS_HEIGHT)
    ax.axis("off")
    return fig, ax


def card(
    ax,
    x,
    y,
    w,
    h,
    title,
    lines,
    accent=ACCENT,
    fill=BG,
    title_size=11.0,
    body_size=8.2,
    body_y_offset=None,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.03,rounding_size=0.06",
        linewidth=1.05,
        edgecolor=BORDER,
        facecolor=fill,
        zorder=2,
    )
    ax.add_patch(patch)
    ax.add_patch(Rectangle((x, y), 0.055, h, color=accent, zorder=3))
    if body_y_offset is not None:
        title_y = y + h - 0.16
        body_y = y + h - body_y_offset
        line_spacing = 1.12
    elif h < 0.9:
        title_y = y + h - 0.15
        body_y = y + h - 0.42
        line_spacing = 1.08
    else:
        title_y = y + h - 0.18
        body_y = y + h - 0.51
        line_spacing = 1.22
    ax.text(
        x + 0.18,
        title_y,
        title,
        fontsize=title_size,
        fontweight="bold",
        color=FG,
        va="top",
        ha="left",
        zorder=4,
    )
    ax.text(
        x + 0.18,
        body_y,
        "\n".join(lines),
        fontsize=body_size,
        color=INK,
        va="top",
        ha="left",
        linespacing=line_spacing,
        zorder=4,
    )


def badge(ax, x, y, text, color=ACCENT):
    ax.text(
        x,
        y,
        text,
        fontsize=7.5,
        color=color,
        fontweight="bold",
        va="center",
        ha="left",
        bbox=dict(boxstyle="round,pad=0.18,rounding_size=0.08", fc=BG, ec=BORDER, lw=0.8),
        zorder=5,
    )


def straight_arrow(ax, start, end, color=MUTED, lw=1.15):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(
            arrowstyle="-|>",
            lw=lw,
            color=color,
            shrinkA=0,
            shrinkB=0,
            mutation_scale=10,
            connectionstyle="arc3,rad=0",
        ),
        zorder=1,
    )


def save(fig, filename: str):
    DIAGRAMS.mkdir(parents=True, exist_ok=True)
    out = DIAGRAMS / filename
    fig.savefig(out, dpi=DPI, facecolor=BG, edgecolor=BG)
    plt.close(fig)
    print(f"Saved {out}")


def generate_er():
    fig, ax = setup_canvas()

    card(
        ax,
        0.95,
        0.08,
        3.2,
        6.24,
        "film",
        [
            "PK:",
            "  • film_id",
            "Attributes:",
            "  • imdb_id",
            "  • tmdb_id",
            "  • title",
            "  • original_title",
            "  • release_year",
            "  • runtime_min",
            "  • budget_usd",
            "  • revenue_usd",
            "  • avg_rating",
            "  • num_votes",
        ],
        accent=ORANGE,
        fill=ORANGE_SOFT,
        title_size=12,
        body_size=8.4,
        body_y_offset=0.54,
    )
    badge(ax, 1.15, 0.30, "integration hub", ORANGE)

    rows = [
        (
            5.80,
            "film_genre",
            [
                "PK/FK:",
                "  • (film_id, genre_id)",
            ],
            0.95,
            "genre",
            [
                "PK:",
                "  • genre_id",
                "Attributes:",
                "  • genre_name",
            ],
            1.07,
            ACCENT,
            ACCENT_SOFT,
        ),
        (
            4.58,
            "film_language",
            [
                "PK/FK:",
                "  • (film_id, language_id)",
                "Attributes:",
                "  • is_original",
            ],
            1.12,
            "language",
            [
                "PK:",
                "  • language_id",
                "Attributes:",
                "  • iso_code",
                "  • language_name",
                "  • language_family",
            ],
            1.20,
            ACCENT,
            ACCENT_SOFT,
        ),
        (
            3.31,
            "film_country",
            [
                "PK/FK:",
                "  • (film_id, country_id)",
                "Attributes:",
                "  • is_primary",
            ],
            1.12,
            "country",
            [
                "PK:",
                "  • country_id",
                "Attributes:",
                "  • iso_code",
                "  • country_name",
                "  • continent",
            ],
            1.20,
            ACCENT,
            ACCENT_SOFT,
        ),
        (
            2.06,
            "film_company",
            [
                "PK/FK:",
                "  • (film_id, company_id)",
            ],
            0.95,
            "production_company",
            [
                "PK:",
                "  • company_id",
                "Attributes:",
                "  • company_name",
            ],
            1.15,
            ACCENT,
            ACCENT_SOFT,
        ),
        (
            0.75,
            "film_role",
            [
                "PK:",
                "  • (film_id, person_id, role_type)",
                "FK:",
                "  • film_id",
                "  • person_id",
                "Attributes:",
                "  • character_name",
            ],
            1.34,
            "person",
            [
                "PK:",
                "  • person_id",
                "Attributes:",
                "  • imdb_nconst",
                "  • name",
                "  • birth_year",
                "  • nationality",
            ],
            1.34,
            ACCENT,
            ACCENT_SOFT,
        ),
    ]

    bridge_x, bridge_w = 5.3, 3.35
    entity_x, entity_w = 10.45, 4.65
    for (
        center_y,
        bridge_title,
        bridge_lines,
        bridge_h,
        entity_title,
        entity_lines,
        entity_h,
        accent,
        fill,
    ) in rows:
        y = center_y - bridge_h / 2
        card(
            ax,
            bridge_x,
            y,
            bridge_w,
            bridge_h,
            bridge_title,
            bridge_lines,
            accent=accent,
            fill=fill,
            title_size=9.4,
            body_size=5.8,
            body_y_offset=0.44,
        )
        ey = center_y - entity_h / 2
        card(
            ax,
            entity_x,
            ey,
            entity_w,
            entity_h,
            entity_title,
            entity_lines,
            accent=MUTED,
            fill=SURFACE,
            title_size=9.4,
            body_size=5.8,
            body_y_offset=0.44,
        )
        straight_arrow(ax, (4.15, center_y), (bridge_x, center_y), color=accent)
        straight_arrow(
            ax, (bridge_x + bridge_w, center_y), (entity_x, center_y), color=accent
        )

    save(fig, "er_reconciled.png")


def generate_dfm():
    fig, ax = setup_canvas()

    # Reuse the same card-and-arrow language as the ER and star diagrams.
    card(
        ax,
        5.95,
        2.50,
        4.10,
        1.72,
        "FilmPerformance",
        [
            "grain: film (degenerate) × genre × production context",
            "× optional director × optional language",
            "measures: revenue, budget, ROI, rating, votes",
        ],
        accent=ORANGE,
        fill=ORANGE_SOFT,
        title_size=10.4,
        body_size=6.6,
    )
    badge(ax, 6.20, 2.72, "fact", ORANGE)

    # Time hierarchy.
    card(ax, 4.60, 5.02, 1.40, 0.78, "Year", [], title_size=7.8)
    card(ax, 2.60, 5.02, 1.52, 0.78, "Decade", [], title_size=7.8)
    card(ax, 0.60, 5.02, 1.36, 0.78, "Era", [], title_size=7.8)
    straight_arrow(ax, (4.60, 5.41), (4.12, 5.41), color=ACCENT)
    straight_arrow(ax, (2.60, 5.41), (1.96, 5.41), color=ACCENT)
    straight_arrow(ax, (5.30, 5.02), (6.45, 4.22), color=ACCENT)

    # Genre hierarchy.
    card(ax, 3.40, 0.62, 1.60, 0.78, "Genre", [], title_size=7.8)
    card(ax, 0.50, 0.62, 2.20, 0.78, "GenreGroup", [], title_size=7.6)
    straight_arrow(ax, (3.40, 1.01), (2.70, 1.01), color=ACCENT)
    straight_arrow(ax, (5.00, 1.01), (6.42, 2.50), color=ACCENT)

    # ProductionContext branches to company and geographic context.
    card(
        ax,
        10.22,
        5.00,
        2.42,
        0.92,
        "ProductionContext",
        ["film-level tuple"],
        accent=GREEN,
        fill=GREEN_SOFT,
        title_size=7.4,
        body_size=5.5,
    )
    card(
        ax,
        14.00,
        6.00,
        1.48,
        0.72,
        "Company",
        [],
        accent=GREEN,
        fill=GREEN_SOFT,
        title_size=7.2,
    )
    card(
        ax,
        13.50,
        4.50,
        2.34,
        0.74,
        "ProductionCountry",
        [],
        accent=GREEN,
        fill=GREEN_SOFT,
        title_size=7.0,
    )
    card(
        ax,
        13.80,
        3.00,
        1.68,
        0.72,
        "Continent",
        [],
        accent=GREEN,
        fill=GREEN_SOFT,
        title_size=7.2,
    )
    straight_arrow(ax, (12.64, 5.70), (14.00, 6.36), color=GREEN)
    straight_arrow(ax, (12.64, 5.30), (13.50, 4.87), color=GREEN)
    straight_arrow(ax, (14.64, 4.50), (14.64, 3.72), color=GREEN)
    straight_arrow(ax, (10.22, 5.20), (9.58, 4.22), color=GREEN)

    # Director is intentionally flat; birth year is descriptive.
    card(
        ax,
        11.00,
        2.30,
        2.30,
        0.94,
        "Director",
        ["optional · flat", "birthYear descriptive"],
        title_size=7.8,
        body_size=5.5,
    )
    straight_arrow(ax, (11.00, 2.77), (10.05, 2.77), color=ACCENT)

    # Language hierarchy.
    card(
        ax,
        11.20,
        0.62,
        1.84,
        0.82,
        "Language",
        ["optional"],
        title_size=7.6,
        body_size=5.5,
    )
    card(
        ax,
        13.60,
        0.62,
        2.20,
        0.82,
        "LanguageFamily",
        [],
        title_size=7.2,
    )
    straight_arrow(ax, (13.04, 1.03), (13.60, 1.03), color=ACCENT)
    straight_arrow(ax, (11.20, 1.25), (9.58, 2.50), color=ACCENT)

    save(fig, "dfm_schema.png")


def generate_star():
    fig, ax = setup_canvas()

    card(
        ax,
        5.85,
        1.95,
        4.30,
        2.95,
        "fact_film_performance",
        [
            "PK:",
            "  • fact_id",
            "FK:",
            "  • time_id",
            "  • genre_id",
            "  • production_id",
            "  • director_id",
            "  • language_id",
            "Attributes:",
            "  • film_id",
            "  • film_title",
            "Measures:",
            "  • revenue_usd",
            "  • budget_usd",
            "  • roi",
            "  • avg_rating",
            "  • num_votes",
        ],
        accent=ORANGE,
        fill=ORANGE_SOFT,
        title_size=10.0,
        body_size=6.2,
        body_y_offset=0.46,
    )
    dims = [
        (
            1.44,
            5.65,
            "dim_time",
            [
                "PK:",
                "  • time_id",
                "Attributes:",
                "  • release_date",
                "  • year",
                "  • decade",
                "  • era",
            ],
            ACCENT,
            (5.85, 4.30),
            (5.24, 6.32),
        ),
        (
            1.44,
            0.35,
            "dim_genre",
            [
                "PK:",
                "  • genre_id",
                "Attributes:",
                "  • source_genre_id",
                "  • genre_name",
                "  • genre_group",
            ],
            ACCENT,
            (5.85, 2.55),
            (5.24, 1.02),
        ),
        (
            5.85,
            5.55,
            "dim_production",
            [
                "PK:",
                "  • production_id",
                "Attributes:",
                "  • source_company_id",
                "  • source_country_id",
                "  • company_name",
                "  • country_iso",
                "  • country_name",
                "  • continent",
            ],
            GREEN,
            (8.0, 4.90),
            (8.0, 5.55),
        ),
        (
            10.76,
            5.65,
            "dim_director",
            [
                "PK:",
                "  • director_id",
                "Attributes:",
                "  • source_person_id",
                "  • director_name",
                "  • birth_year",
                "  • nationality",
                "  • region",
            ],
            ACCENT,
            (10.15, 4.30),
            (10.76, 6.32),
        ),
        (
            10.76,
            0.35,
            "dim_language",
            [
                "PK:",
                "  • language_id",
                "Attributes:",
                "  • source_language_id",
                "  • language_name",
                "  • language_family",
            ],
            ACCENT,
            (10.15, 2.55),
            (10.76, 1.02),
        ),
    ]

    for x, y, title, lines, accent, fact_point, dim_point in dims:
        fill = GREEN_SOFT if accent == GREEN else BG
        dim_w = 4.30 if title == "dim_production" else 3.80
        dim_h = 1.54 if title == "dim_production" else 1.44
        card(
            ax,
            x,
            y,
            dim_w,
            dim_h,
            title,
            lines,
            accent=accent,
            fill=fill,
            title_size=8.6,
            body_size=5.8,
            body_y_offset=0.43,
        )
        straight_arrow(ax, dim_point, fact_point, color=accent)

    save(fig, "star_schema.png")


def main():
    generate_er()
    generate_dfm()
    generate_star()


if __name__ == "__main__":
    main()
