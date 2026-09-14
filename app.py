"""
Interactive Visualisation of Global Tourism Trends (2015-2022)
==============================================================
MSc Dissertation Project - Bangor University, 2025-2026
Author: Ogechi Nelson

Overview
--------
This application is an interactive web dashboard built with Python and Dash,
designed to make complex international tourism data explorable by non-technical
users such as policymakers and researchers.

The dataset covers 15 countries across multiple regions from 2015 to 2022,
sourced from the UN World Tourism Organisation (UNWTO) and the World Bank.
It includes metrics on arrivals, economic impact, visitor behaviour, and
sustainability.

Design Approach
---------------
The dashboard was developed using the Five Design-Sheet (FDS) methodology,
moving through four iterative prototypes. Each iteration was evaluated using
the Critical Design Strategy (CDS), which tested usability and robustness
before the next version was built. The final design prioritises:
  - Clarity over visual complexity
  - Comparative analysis across countries and years
  - Accessible layout for users without a data background

Key Analytical Findings
-----------------------
- Europe (France, Spain) showed V-shaped recovery post-COVID; Asia (Japan,
  China) showed L-shaped patterns due to extended border restrictions.
- Mexico remained a global outlier in 2020-2021, maintaining relatively high
  arrivals due to its open-border policy during the pandemic.
- Spain's tourism GDP contribution (~14%) significantly outpaces neighbouring
  France (~9%), reflecting a deeper structural reliance on the sector.

Dependencies
------------
    pip install dash dash-bootstrap-components plotly pandas

Usage
-----
    python app.py
    Then open http://127.0.0.1:8050 in your browser.

Data File
---------
    Place 'International Tourism Trends.csv' in the same directory as this
    script before running. All custom styling is defined and injected inline
    in this file (see CUSTOM_CSS below) — no separate assets folder needed.
"""

import logging

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
# Logging is configured at INFO level so that data loading steps and any
# errors are visible in the terminal without overwhelming output.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Colour Palette
# ---------------------------------------------------------------------------
# Ink navy on a white page, with deep teal and bronze as the two accents.
# Defined centrally so the CSS, the layout, and the Plotly charts all draw
# from the same set of values.
COLORS = {
    "primary": "#1B2733",      # deep ink — headings, primary lines
    "accent_1": "#1C3F39",     # deep teal — secondary series, slider/track
    "accent_2": "#6B5B2A",     # deep bronze — highlight accent
    "accent_3": "#37475C",     # deep slate blue — tertiary series
    "contrast": "#6E2C3B",     # deep wine — COVID marker, negative values
    "background": "#FFFFFF",   # page background
    "panel": "#FFFFFF",        # chart background, matching the page
    "grid": "#E2E4E6",
    "text": "#1B2733",
    "text_soft": "#5B6672",
}

# A curated categorical sequence for country-by-country comparisons. Plotly
# cycles through this list if more categories are selected than colours
# provided, so it comfortably covers all 15 countries in the data.
CATEGORICAL_SEQUENCE = [
    COLORS["primary"],
    COLORS["accent_2"],
    COLORS["accent_1"],
    COLORS["contrast"],
    "#37475C",   # deep slate blue
    "#5C4A36",   # deep umber
    "#4F5D3A",   # deep olive
    "#52395B",   # deep plum
]

# A sequential scale (near-white to deep ink-blue) used for the choropleth.
SEQUENTIAL_SCALE = [
    [0.0, "#F5F5F4"],
    [0.4, "#9AA9B7"],
    [0.75, "#3F5468"],
    [1.0, "#1B2733"],
]


# ---------------------------------------------------------------------------
# Data Loading and Cleaning
# ---------------------------------------------------------------------------

def load_and_clean_data(file_path):
    """
    Load the tourism CSV dataset and apply a standardised cleaning pipeline.

    This function handles several real-world data quality issues present in
    the raw source files:

    1. Column name normalisation: Source data from UNWTO and World Bank uses
       inconsistent capitalisation and spacing. All column names are lowercased
       and non-alphanumeric characters are replaced with underscores to allow
       reliable programmatic access.

    2. Whitespace stripping: String fields sometimes contain leading/trailing
       spaces introduced during data entry. These are stripped to prevent
       silent mismatches in filtering and grouping operations.

    3. Country name standardisation: The raw data contains 'South' as a
       truncated reference to 'South Korea'. This is corrected explicitly
       rather than dropped, as it represents a real and significant tourism
       source market (notably for China and Thailand).

    4. Numeric conversion: Several columns arrive as strings due to comma
       formatting (e.g., "84,452.00"). These are stripped of commas and
       coerced to numeric. Missing or unparseable values are filled with 0
       rather than NaN to prevent downstream chart rendering failures.

    5. Percentage share columns: Source country share fields use percentage
       strings (e.g., "20%"). These are converted to decimal proportions
       (0.20) to support consistent chart scaling.

    Args:
        file_path (str): Path to the CSV data file.

    Returns:
        pd.DataFrame: A cleaned DataFrame ready for visualisation.

    Raises:
        FileNotFoundError: If the data file does not exist at the given path.
    """
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        logger.error(f"Data file not found: '{file_path}'")
        raise

    # Normalise column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-zA-Z0-9]+", "_", regex=True)
    )

    # Strip whitespace from all string columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # Fix truncated country name in source market columns
    source_country_cols = [
        "top_source_country_1",
        "top_source_country_2",
        "top_source_country_3",
    ]
    for col in source_country_cols:
        if col in df.columns:
            df[col] = df[col].replace({"South": "South Korea"})

    # Convert comma-formatted numeric strings to float
    numeric_cols = [
        "arrivals_millions",
        "arrivals_growth",
        "tourism_receipts_usd_billions",
        "tourism_receipts_growth",
        "average_length_of_stay_days",
        "arrivals_by_purpose_personal",
        "arrivals_by_purpose_business",
        "tourism_gdp",
        "tourism_employment_thousands",
        "renewable_energy",
        "tourist_density_per_1000_residents",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = (
                pd.to_numeric(
                    df[col].astype(str).str.replace(",", ""),
                    errors="coerce"
                ).fillna(0)
            )

    # Convert percentage strings to decimal proportions
    share_cols = [
        "top_source_country_1_share",
        "top_source_country_2_share",
        "top_source_country_3_share",
    ]
    for col in share_cols:
        if col in df.columns:
            df[col] = (
                pd.to_numeric(
                    df[col].astype(str).str.replace("%", ""),
                    errors="coerce"
                ).fillna(0) / 100
            )

    logger.info("Data cleaning pipeline completed successfully.")
    return df


# ---------------------------------------------------------------------------
# Visualisation Helpers
# ---------------------------------------------------------------------------

def get_chart_template(fig, title_text, yaxis_title=""):
    """
    Apply a consistent visual style to a Plotly figure.

    Using a shared template function ensures all charts in the dashboard
    follow the same layout conventions, which reduces visual noise for
    non-technical users. Typography mirrors the page: a serif for the
    title, a plain sans for axes and labels.

    Args:
        fig: A Plotly figure object.
        title_text (str): The chart title to display.
        yaxis_title (str): Optional label for the y-axis.

    Returns:
        The updated Plotly figure with styling applied.
    """
    fig.update_layout(
        plot_bgcolor=COLORS["panel"],
        paper_bgcolor=COLORS["panel"],
        font=dict(family="IBM Plex Sans, sans-serif", color=COLORS["text"], size=12),
        title=dict(
            text=title_text,
            x=0.02,
            xanchor="left",
            font=dict(
                family="Source Serif 4, Georgia, serif",
                size=17,
                color=COLORS["primary"],
            ),
        ),
        xaxis=dict(gridcolor=COLORS["grid"], zeroline=False),
        yaxis=dict(title=yaxis_title, gridcolor=COLORS["grid"], zeroline=False),
        margin=dict(l=40, r=40, t=56, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        colorway=CATEGORICAL_SEQUENCE,
    )
    return fig


def apply_country_year_hover(fig, y_label, y_format=",.1f", y_suffix=""):
    """
    Replace Plotly Express's default hover text ('country_name=France') with
    a plain-language tooltip ('France' / 'Year: 2022' / 'Arrivals: 62.3M').

    Each trace produced by a colour-by-country line chart already carries the
    country name as its trace name, so that name becomes the bold header line
    and every other field is written out as 'Label: value' beneath it.

    Args:
        fig: A Plotly figure with one trace per country (e.g. from px.line
            with color="country_name").
        y_label (str): Human-readable name for the y-value, e.g. "Arrivals (Millions)".
        y_format (str): A d3-format spec for the y-value, e.g. ",.1f".
        y_suffix (str): Optional unit suffix appended after the formatted value.

    Returns:
        The same figure, with hovertemplate set on every trace.
    """
    for trace in fig.data:
        trace.hovertemplate = (
            f"<b>{trace.name}</b><br>"
            f"Year: %{{x}}<br>"
            f"{y_label}: %{{y:{y_format}}}{y_suffix}<extra></extra>"
        )
    return fig


# ---------------------------------------------------------------------------
# Application Initialisation
# ---------------------------------------------------------------------------

try:
    df = load_and_clean_data("International Tourism Trends.csv")
except (FileNotFoundError, Exception) as e:
    # If data loading fails, initialise an empty DataFrame so the app still
    # starts without crashing. Error messages will appear in the UI via alerts.
    df = pd.DataFrame()
    logger.error(f"Failed to load data: {e}")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "Global Tourism Trends"

# ---------------------------------------------------------------------------
# Custom Stylesheet
# ---------------------------------------------------------------------------
# Ink navy, deep teal and bronze accents on a white page, with Source Serif 4
# for headings and IBM Plex Sans for everything else. Injected straight into
# the page head below so the whole app stays in a single file.
CUSTOM_CSS = """
:root {
  --ink: #1B2733;
  --ink-soft: #5B6672;
  --paper: #FFFFFF;
  --paper-panel: #FFFFFF;
  --brass: #6B5B2A;
  --teal: #1C3F39;
  --brick: #6E2C3B;
  --rule: #E2E4E6;
}

body {
  background-color: var(--paper);
  color: var(--ink);
  font-family: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 15px;
}

/* ---- Masthead ---------------------------------------------------- */

.masthead {
  padding: 8px 0 20px 0;
  border-bottom: 2px solid var(--ink);
  margin-bottom: 8px;
}

.masthead-title {
  font-family: "Source Serif 4", Georgia, serif;
  font-weight: 600;
  font-size: 2.05rem;
  color: var(--ink);
  margin-bottom: 6px;
  text-align: left;
}

.masthead-subtitle {
  font-family: "IBM Plex Sans", sans-serif;
  color: var(--ink-soft);
  font-size: 1rem;
  max-width: 62ch;
  margin-bottom: 0;
  text-align: left;
}

/* ---- Form controls -------------------------------------------------- */

.control-label {
  font-family: "IBM Plex Sans", sans-serif;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--ink-soft);
  margin-bottom: 4px;
  display: block;
}

.Select-control,
.dash-dropdown .Select-control {
  border-radius: 2px !important;
  border-color: var(--rule) !important;
}

.Select-control:hover {
  border-color: var(--brass) !important;
}

.Select--multi .Select-value {
  background-color: var(--paper-panel) !important;
  border-color: var(--rule) !important;
  color: var(--ink) !important;
  border-radius: 2px !important;
}

/* ---- Slider --------------------------------------------------------
   Targets Dash's own slider classes directly rather than shared design
   tokens, since those tokens are also read by other components (e.g. the
   Dropdown) and would recolour them too. */

.dash-slider-track {
  background-color: var(--rule) !important;
}

.dash-slider-range {
  background-color: var(--teal) !important;
}

.dash-slider-thumb {
  background-color: #FFFFFF !important;
  border: 2px solid var(--teal) !important;
  box-shadow: none !important;
}

.dash-slider-thumb:hover,
.dash-slider-thumb:focus {
  border-color: var(--brass) !important;
  box-shadow: 0 0 0 4px rgba(28, 63, 57, 0.12) !important;
}

.dash-slider-dot {
  border-color: var(--rule) !important;
  background-color: #FFFFFF !important;
}

.dash-slider-mark {
  color: var(--ink-soft) !important;
}

.dash-slider-tooltip {
  background-color: var(--ink) !important;
  border: none !important;
  border-radius: 2px !important;
}

.dash-slider-tooltip,
.dash-slider-tooltip * {
  color: #FFFFFF !important;
}

/* Older rc-slider-based builds of Dash (pre-4.0) use these class names
   instead — harmless no-ops on newer Dash, kept for compatibility. */
.rc-slider-track {
  background-color: var(--teal) !important;
}

.rc-slider-handle {
  border-color: var(--teal) !important;
}

.rc-slider-handle:hover,
.rc-slider-handle:active {
  border-color: var(--brass) !important;
  box-shadow: none !important;
}

.rc-slider-dot-active {
  border-color: var(--teal) !important;
}

/* ---- Tabs: underlined nav style ------------------------------------- */

.doc-tabs .nav-link {
  font-family: "IBM Plex Sans", sans-serif;
  font-weight: 500;
  color: var(--ink-soft) !important;
  background: transparent !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  padding: 8px 4px;
  margin-right: 28px;
}

.doc-tabs .nav-link.active {
  color: var(--ink) !important;
  border-bottom: 2px solid var(--brass) !important;
}

.doc-tabs {
  border-bottom: 1px solid var(--rule) !important;
}

/* ---- Stat strip ------------------------------------------------------ */

.section-heading {
  font-family: "Source Serif 4", Georgia, serif;
  font-weight: 600;
  color: var(--ink);
  font-size: 1.1rem;
  margin-bottom: 14px;
  text-align: left;
}

.stat-strip {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--rule);
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 14px 4px;
  border-bottom: 1px solid var(--rule);
}

.stat-label {
  font-family: "IBM Plex Sans", sans-serif;
  color: var(--ink-soft);
  font-size: 0.92rem;
}

.stat-value {
  font-family: "Source Serif 4", Georgia, serif;
  font-weight: 600;
  color: var(--ink);
  font-size: 1.15rem;
  text-align: right;
}

/* ---- Accordion --------------------------------------------------- */

.doc-accordion .accordion-button {
  font-family: "IBM Plex Sans", sans-serif;
  font-weight: 500;
  color: var(--ink) !important;
  background-color: var(--paper-panel) !important;
  box-shadow: none !important;
}

.doc-accordion .accordion-button:not(.collapsed) {
  color: var(--teal) !important;
}

.doc-accordion .accordion-button::after {
  filter: none;
}

.doc-accordion .accordion-body {
  font-family: "IBM Plex Sans", sans-serif;
  color: var(--ink-soft);
  line-height: 1.6;
  background-color: var(--paper-panel);
}

.doc-accordion .accordion-item {
  border-color: var(--rule) !important;
}

/* ---- Buttons and footer ------------------------------------------- */

.btn-quiet {
  font-family: "IBM Plex Sans", sans-serif;
  font-weight: 500;
  background-color: transparent !important;
  color: var(--ink) !important;
  border: 1px solid var(--ink) !important;
  border-radius: 2px !important;
  padding: 8px 18px;
}

.btn-quiet:hover {
  background-color: var(--ink) !important;
  color: var(--paper) !important;
}

.footer-note {
  font-family: "IBM Plex Sans", sans-serif;
  color: var(--ink-soft);
  font-style: normal !important;
  font-size: 0.85rem;
}

/* ---- Alerts, kept quiet -------------------------------------------- */

.alert {
  font-family: "IBM Plex Sans", sans-serif;
  border-radius: 2px;
}
"""

# Load the two typefaces used throughout (Source Serif 4 for headings,
# IBM Plex Sans for everything else), and inject CUSTOM_CSS directly into
# the page head — so the whole app is one file, no assets/ folder needed.
app.index_string = f"""
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&display=swap" rel="stylesheet">
        {{%css%}}
        <style>
        {CUSTOM_CSS}
        </style>
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
"""


# ---------------------------------------------------------------------------
# App Layout
# ---------------------------------------------------------------------------

app.layout = dbc.Container(
    [
        dcc.Download(id="download-dataframe-csv"),

        # Masthead
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.H1(
                            "Global tourism trends",
                            className="masthead-title",
                        ),
                        html.P(
                            "An exploratory dashboard covering arrivals, receipts, "
                            "recovery and sustainability across fifteen leading "
                            "destinations, 2015 to 2022.",
                            className="masthead-subtitle",
                        ),
                    ],
                    className="masthead",
                )
            )
        ),

        # Global controls: country selector, year slider, map metric
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.Label("Countries to compare", className="control-label"),
                            dcc.Dropdown(
                                id="country-dropdown",
                                options=[
                                    {"label": c, "value": c}
                                    for c in sorted(df["country_name"].unique())
                                ] if not df.empty else [],
                                value=["France", "Spain", "United States"],
                                multi=True,
                            ),
                        ]
                    ),
                    md=4,
                    className="mt-4",
                ),
                dbc.Col(
                    html.Div(
                        [
                            html.Label("Year", className="control-label"),
                            dcc.Slider(
                                id="year-slider",
                                min=df["year"].min() if not df.empty else 2015,
                                max=df["year"].max() if not df.empty else 2022,
                                step=1,
                                value=df["year"].max() if not df.empty else 2022,
                                marks={
                                    str(y): str(y)
                                    for y in sorted(df["year"].unique())
                                } if not df.empty else {},
                                tooltip={"placement": "bottom", "always_visible": True},
                            ),
                        ]
                    ),
                    md=4,
                    className="mt-4",
                ),
                dbc.Col(
                    html.Div(
                        [
                            html.Label("Map metric", className="control-label"),
                            dcc.Dropdown(
                                id="map-metric-dropdown",
                                options=[
                                    {"label": "International Arrivals", "value": "arrivals_millions"},
                                    {"label": "Tourism Receipts (USD Billions)", "value": "tourism_receipts_usd_billions"},
                                    {"label": "Tourism's Contribution to GDP (%)", "value": "tourism_gdp"},
                                    {"label": "Tourist Density (per 1000 residents)", "value": "tourist_density_per_1000_residents"},
                                ],
                                value="arrivals_millions",
                                clearable=False,
                            ),
                        ]
                    ),
                    id="map-controls-div",
                    md=4,
                    className="mt-4",
                    style={"display": "block"},
                ),
            ],
            className="mb-4",
        ),

        # Navigation tabs
        dbc.Tabs(
            [
                dbc.Tab(label="Global Overview", tab_id="tab-overview"),
                dbc.Tab(label="Post-COVID Recovery", tab_id="tab-recovery"),
                dbc.Tab(label="Economic Impact", tab_id="tab-economy"),
                dbc.Tab(label="Visitor Behavior", tab_id="tab-behavior"),
                dbc.Tab(label="Sustainability", tab_id="tab-sustainability"),
            ],
            id="tabs",
            active_tab="tab-overview",
            className="mt-3 doc-tabs",
        ),
        html.Div(id="tab-content", className="p-4 mt-2"),
        html.Hr(style={"borderColor": COLORS["grid"]}),

        # Footer row: download button and data attribution
        dbc.Row(
            [
                dbc.Col(
                    dbc.Button(
                        "Download data (CSV)",
                        id="btn-download",
                        className="mb-2 btn-quiet",
                    ),
                    width={"size": "auto"},
                ),
                dbc.Col(
                    html.Span(
                        "Data source: UN Tourism, World Bank, national tourism boards",
                        className="footer-note align-middle",
                    ),
                    width=True,
                    className="text-md-end text-center",
                ),
            ],
            align="center",
            className="mt-4 mb-2",
        ),
    ],
    fluid=True,
    style={"background-color": COLORS["background"]},
)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    Output("map-controls-div", "style"),
    Input("tabs", "active_tab"),
)
def toggle_map_controls(active_tab):
    """
    Show the map metric dropdown only on the Global Overview tab.

    This avoids confusing users on tabs where no map is displayed.
    The control is hidden via inline CSS rather than removed from the DOM
    so its state is preserved when switching back to the Overview tab.
    """
    if active_tab == "tab-overview":
        return {"display": "block"}
    return {"display": "none"}


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab"),
    Input("country-dropdown", "value"),
    Input("year-slider", "value"),
    Input("map-metric-dropdown", "value"),
)
def render_main_content(tab, countries, year, map_metric):
    """
    Render the content area for the currently active tab.

    A single callback handles all five tabs to avoid duplicating the
    country and year inputs across multiple callbacks. The tab ID is used
    as a dispatch key to determine which charts and layout to construct.

    Args:
        tab (str): The active tab ID (e.g. 'tab-overview').
        countries (list): List of country names selected in the dropdown.
        year (int): The year selected on the slider.
        map_metric (str): The column name for the choropleth map metric.

    Returns:
        A Dash HTML component tree for the selected tab.
    """

    # --- TAB 1: GLOBAL OVERVIEW ---
    if tab == "tab-overview":
        year_data = df[df["year"] == year].copy()
        if year_data.empty:
            return dbc.Alert("No data available for the selected year.", color="warning")

        # Compute headline insight cards with safe fallbacks
        try:
            top_performer = year_data.nlargest(1, "arrivals_millions").iloc[0]
            card1_text = f"{top_performer['country_name']} — {top_performer['arrivals_millions']:,.1f}M"
        except IndexError:
            card1_text = "N/A"

        try:
            highest_earner = year_data.nlargest(1, "tourism_receipts_usd_billions").iloc[0]
            card2_text = f"{highest_earner['country_name']} — ${highest_earner['tourism_receipts_usd_billions']:,.1f}B"
        except IndexError:
            card2_text = "N/A"

        try:
            fastest_grower = year_data.nlargest(1, "arrivals_growth").iloc[0]
            card3_text = f"{fastest_grower['country_name']} — {fastest_grower['arrivals_growth']:+,.1f}%"
        except IndexError:
            card3_text = "N/A"

        # Choropleth map
        metric_labels = {
            "arrivals_millions": "Arrivals (Millions)",
            "tourism_receipts_usd_billions": "Receipts (USD Billions)",
            "tourism_gdp": "Tourism GDP (%)",
            "tourist_density_per_1000_residents": "Tourist Density",
        }
        # A per-metric d3-format spec and unit suffix for the hover value, so
        # the tooltip reads as plain "Label: value" text rather than Plotly's
        # default "field_name=value".
        metric_hover_formats = {
            "arrivals_millions": (",.1f", "M"),
            "tourism_receipts_usd_billions": (",.1f", "B"),
            "tourism_gdp": (".1f", "%"),
            "tourist_density_per_1000_residents": (",.0f", " per 1,000 residents"),
        }
        fig_map = px.choropleth(
            year_data,
            locations="country_code",
            color=map_metric,
            hover_name="country_name",
            color_continuous_scale=SEQUENTIAL_SCALE,
            labels=metric_labels,
        )
        value_format, value_suffix = metric_hover_formats.get(map_metric, (",.1f", ""))
        fig_map.update_traces(
            hovertemplate=(
                f"<b>%{{hovertext}}</b><br>"
                f"{metric_labels.get(map_metric, 'Value')}: %{{z:{value_format}}}{value_suffix}"
                f"<extra></extra>"
            )
        )
        fig_map.update_layout(
            geo=dict(
                showframe=False,
                showcoastlines=False,
                projection_type="equirectangular",
                bgcolor=COLORS["panel"],
                landcolor="#EDEDEC",
            )
        )
        fig_map = get_chart_template(
            fig_map, f"{metric_labels.get(map_metric, '')} in {year}"
        )

        return html.Div(
            [
                html.P(
                    "This tool visualises key metrics for 15 leading tourist destinations. "
                    "Use the interactive map and tabs to explore trends.",
                    className="text-center lead",
                ),
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(figure=fig_map), md=8),
                        dbc.Col(
                            [
                                html.H4(f"Key insights for {year}", className="section-heading"),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Span("Top performer, arrivals", className="stat-label"),
                                                html.Span(card1_text, className="stat-value"),
                                            ],
                                            className="stat-item",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Highest earner, receipts", className="stat-label"),
                                                html.Span(card2_text, className="stat-value"),
                                            ],
                                            className="stat-item",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Fastest year-on-year grower", className="stat-label"),
                                                html.Span(card3_text, className="stat-value"),
                                            ],
                                            className="stat-item",
                                        ),
                                    ],
                                    className="stat-strip",
                                ),
                            ],
                            md=4,
                            className="align-self-center",
                        ),
                    ]
                ),
                html.Hr(style={"borderColor": COLORS["grid"]}),
                dbc.Accordion(
                    [
                        dbc.AccordionItem(
                            "The selected countries represent a curated mix of globally leading "
                            "destinations (e.g., France, Spain), major economies (USA, China), "
                            "unique tourism models (Iceland, Rwanda), and rapidly emerging hotspots "
                            "(Vietnam, Georgia). This diversity allows for a comprehensive analysis "
                            "of global tourism trends and recovery patterns.",
                            title="Why these 15 countries?",
                        ),
                        dbc.AccordionItem(
                            html.Ol(
                                [
                                    html.Li([html.B("Explore the map: "), "use the dropdown to select a metric and see its worldwide distribution for the chosen year."]),
                                    html.Li([html.B("Select a timeframe: "), "use the year slider to focus on a specific year between 2015 and 2022."]),
                                    html.Li([html.B("Compare and analyse: "), "navigate to other tabs and use the country dropdown to compare specific nations over time."]),
                                ]
                            ),
                            title="How to use this dashboard",
                        ),
                        dbc.AccordionItem(
                            "Primary data synthesised from the United Nations World Tourism Organisation "
                            "(UNWTO), The World Bank, and national tourism boards.",
                            title="Data sources",
                        ),
                    ],
                    start_collapsed=True,
                    className="doc-accordion",
                ),
            ]
        )

    if not countries:
        return dbc.Alert("Please select at least one country to view analysis.", color="warning")

    dff = df[df["country_name"].isin(countries)].copy()
    year_data = df[df["year"] == year].copy()

    # --- TAB 2: POST-COVID RECOVERY ---
    if tab == "tab-recovery":
        fig_arrivals = px.line(
            dff, x="year", y="arrivals_millions", color="country_name",
            labels={"arrivals_millions": "Arrivals (Millions)", "year": "Year", "country_name": "Country"},
            color_discrete_sequence=CATEGORICAL_SEQUENCE,
        )
        # A vertical reference line marks 2020 to anchor the COVID impact visually
        fig_arrivals.update_traces(mode="lines+markers").add_vline(
            x=2020, line_width=1.5, line_dash="dash",
            line_color=COLORS["contrast"], annotation_text="COVID-19 Pandemic",
        )
        fig_arrivals = get_chart_template(fig_arrivals, "Tourism Arrivals Over Time", "Arrivals (Millions)")
        apply_country_year_hover(fig_arrivals, "Arrivals (Millions)", ",.1f", "M")

        fig_receipts = px.line(
            dff, x="year", y="tourism_receipts_usd_billions", color="country_name",
            labels={"tourism_receipts_usd_billions": "Receipts (USD Billions)", "year": "Year", "country_name": "Country"},
            color_discrete_sequence=CATEGORICAL_SEQUENCE,
        )
        fig_receipts.update_traces(mode="lines+markers").add_vline(
            x=2020, line_width=1.5, line_dash="dash",
            line_color=COLORS["contrast"], annotation_text="COVID-19 Pandemic",
        )
        fig_receipts = get_chart_template(fig_receipts, "Tourism Receipts Over Time", "Receipts (USD Billions)")
        apply_country_year_hover(fig_receipts, "Receipts (USD Billions)", ",.1f", "B")

        # Single-country recovery rate chart: compares 2022 arrivals to 2019 baseline
        single_country_content = []
        if len(countries) == 1:
            country = countries[0]
            single_country_df = dff[dff["country_name"] == country]
            arrivals_2019 = single_country_df.loc[single_country_df["year"] == 2019, "arrivals_millions"].values[0] if 2019 in single_country_df["year"].values else 0
            arrivals_2022 = single_country_df.loc[single_country_df["year"] == 2022, "arrivals_millions"].values[0] if 2022 in single_country_df["year"].values else 0
            recovery_rate = (arrivals_2022 / arrivals_2019) * 100 if arrivals_2019 > 0 else 0
            fig_bar_recovery = px.bar(
                x=["Recovery Rate %"], y=[recovery_rate],
                labels={"y": "Value (%)"},
                color_discrete_sequence=[COLORS["accent_1"]],
                text_auto=".1f", height=300,
            )
            fig_bar_recovery = get_chart_template(
                fig_bar_recovery, f"Recovery Rate in 2022 vs 2019 ({country})"
            ).update_yaxes(range=[0, max(110, recovery_rate + 10)])
            fig_bar_recovery.update_traces(
                hovertemplate="Recovery rate: %{y:.1f}%<extra></extra>"
            )
            single_country_content = [html.Hr(style={"borderColor": COLORS["grid"]}), dcc.Graph(figure=fig_bar_recovery)]

        return html.Div(
            [
                html.P("Explore the impact of the COVID-19 pandemic on tourism. Select multiple countries to compare their recovery trajectories."),
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(figure=fig_arrivals), md=6),
                        dbc.Col(dcc.Graph(figure=fig_receipts), md=6),
                    ]
                ),
                *single_country_content,
            ]
        )

    # --- TAB 3: ECONOMIC IMPACT ---
    elif tab == "tab-economy":
        fig_bar_gdp = px.bar(
            year_data.sort_values(by="tourism_gdp", ascending=False),
            x="country_name", y="tourism_gdp",
            labels={"country_name": "Country", "tourism_gdp": "Tourism GDP (%)"},
            color_discrete_sequence=[COLORS["accent_2"]], height=400,
        )
        fig_bar_gdp = get_chart_template(fig_bar_gdp, f"Tourism's Contribution to GDP ({year})", "Tourism GDP (%)")
        fig_bar_gdp.update_traces(
            hovertemplate="Country: %{x}<br>Tourism GDP: %{y:.1f}%<extra></extra>"
        )

        fig_bar_employment = px.bar(
            year_data.sort_values(by="tourism_employment_thousands", ascending=False),
            x="country_name", y="tourism_employment_thousands",
            labels={"country_name": "Country", "tourism_employment_thousands": "Employment (Thousands)"},
            color_discrete_sequence=[COLORS["accent_1"]], height=400,
        )
        fig_bar_employment = get_chart_template(fig_bar_employment, f"Tourism Employment ({year})", "Employment (Thousands)")
        fig_bar_employment.update_traces(
            hovertemplate="Country: %{x}<br>Employment: %{y:,.0f} thousand<extra></extra>"
        )

        fig_gdp_line = px.line(
            dff, x="year", y="tourism_gdp", color="country_name",
            labels={"tourism_gdp": "Tourism GDP (%)", "year": "Year", "country_name": "Country"},
            color_discrete_sequence=CATEGORICAL_SEQUENCE,
        )
        fig_gdp_line = get_chart_template(fig_gdp_line, "Tourism GDP Over Time", "Tourism GDP (%)")
        apply_country_year_hover(fig_gdp_line, "Tourism GDP", ".1f", "%")

        fig_employment_line = px.line(
            dff, x="year", y="tourism_employment_thousands", color="country_name",
            labels={"tourism_employment_thousands": "Employment (Thousands)", "year": "Year", "country_name": "Country"},
            color_discrete_sequence=CATEGORICAL_SEQUENCE,
        )
        fig_employment_line = get_chart_template(fig_employment_line, "Tourism Employment Over Time", "Employment (Thousands)")
        apply_country_year_hover(fig_employment_line, "Employment", ",.0f", " thousand")

        return html.Div(
            [
                html.P("The top charts compare all countries for a given year; the bottom charts show historical trends for the selected countries."),
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(figure=fig_bar_gdp), md=6),
                        dbc.Col(dcc.Graph(figure=fig_bar_employment), md=6),
                    ]
                ),
                html.Hr(style={"borderColor": COLORS["grid"]}),
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(figure=fig_gdp_line), md=6),
                        dbc.Col(dcc.Graph(figure=fig_employment_line), md=6),
                    ]
                ),
            ]
        )

    # --- TAB 4: VISITOR BEHAVIOUR ---
    elif tab == "tab-behavior":
        fig_stay = px.line(
            dff, x="year", y="average_length_of_stay_days", color="country_name",
            labels={"average_length_of_stay_days": "Avg. Stay (Days)", "year": "Year", "country_name": "Country"},
            markers=True,
            color_discrete_sequence=CATEGORICAL_SEQUENCE,
        )
        fig_stay = get_chart_template(fig_stay, "Average Length of Stay", "Average Days")
        apply_country_year_hover(fig_stay, "Average Stay", ".1f", " days")

        # Pie chart for source markets is only meaningful for a single country
        single_country_content = html.Div()
        if len(countries) == 1:
            country = countries[0]
            year_data_for_country = dff[dff["year"] == year].copy()
            try:
                pie_data = year_data_for_country
                top_sources_data = [
                    (pie_data["top_source_country_1_share"].iloc[0], pie_data["top_source_country_1"].iloc[0]),
                    (pie_data["top_source_country_2_share"].iloc[0], pie_data["top_source_country_2"].iloc[0]),
                    (pie_data["top_source_country_3_share"].iloc[0], pie_data["top_source_country_3"].iloc[0]),
                ]
                valid_sources = [(s, n) for s, n in top_sources_data if pd.notna(s) and s > 0]
                if not valid_sources:
                    raise ValueError("No valid source shares found.")
                fig_pie_sources = px.pie(
                    values=[s * 100 for s, n in valid_sources],
                    names=[n for s, n in valid_sources],
                    hole=0.3,
                    color_discrete_sequence=[COLORS["accent_2"], COLORS["accent_1"], COLORS["contrast"]],
                )
                fig_pie_sources.update_traces(
                    textposition="inside", textinfo="percent+label",
                    hovertemplate="Source country: %{label}<br>Share of visitors: %{value:.1f}%<extra></extra>",
                )
                fig_pie_sources = get_chart_template(fig_pie_sources, f"Top Source Countries ({country}, {year})")
                single_country_content = dcc.Graph(figure=fig_pie_sources)
            except Exception:
                single_country_content = dbc.Alert(
                    f"Top source country data unavailable for {country} in {year}.", color="info"
                )

        return html.Div(
            [
                html.P("Select a single country to see a breakdown of its top visitor markets for the chosen year."),
                dcc.Graph(figure=fig_stay),
                html.Hr(style={"borderColor": COLORS["grid"]}),
                single_country_content,
            ]
        )

    # --- TAB 5: SUSTAINABILITY ---
    elif tab == "tab-sustainability":
        # Dual y-axis chart: renewable energy share (left) vs tourist density (right)
        # A grouped bar chart is used rather than a scatter to allow direct
        # country-by-country comparison without requiring the user to read coordinates.
        fig_sustainability = make_subplots(specs=[[{"secondary_y": True}]])
        fig_sustainability.add_trace(
            go.Bar(
                x=year_data["country_name"], y=year_data["renewable_energy"],
                name="Renewable Energy Share (%)", marker_color=COLORS["accent_1"],
                hovertemplate="Country: %{x}<br>Renewable Energy: %{y:.1f}%<extra></extra>",
            ),
            secondary_y=False,
        )
        fig_sustainability.add_trace(
            go.Bar(
                x=year_data["country_name"], y=year_data["tourist_density_per_1000_residents"],
                name="Tourist Density", marker_color=COLORS["contrast"],
                hovertemplate="Country: %{x}<br>Tourist Density: %{y:,.0f} per 1,000 residents<extra></extra>",
            ),
            secondary_y=True,
        )
        fig_sustainability = get_chart_template(fig_sustainability, f"Sustainability Metrics by Country ({year})")
        fig_sustainability.update_layout(
            barmode="group", xaxis_tickangle=-45,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig_sustainability.update_yaxes(title_text="Renewable Energy Share (%)", secondary_y=False)
        fig_sustainability.update_yaxes(title_text="Tourists per 1,000 Residents", secondary_y=True)

        return html.Div(
            [
                html.P(
                    "This tab compares environmental effort (Renewable Energy) and social pressure "
                    "(Tourist Density) across all destinations for the selected year."
                ),
                dcc.Graph(figure=fig_sustainability),
            ]
        )

    return None


@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("btn-download", "n_clicks"),
    prevent_initial_call=True,
)
def download_csv(n_clicks):
    """Trigger a CSV download of the full cleaned dataset."""
    return dcc.send_data_frame(df.to_csv, "international_tourism_data_2015-2022.csv", index=False)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
