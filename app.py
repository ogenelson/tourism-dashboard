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
    script before running.
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
# A consistent colour theme is defined centrally so any future changes to
# branding only need to be made in one place.
COLORS = {
    "primary": "#1B5E20",
    "accent_1": "#01579B",
    "accent_2": "#E65100",
    "accent_3": "#558B2F",
    "contrast": "#AD1457",
    "background": "#F5F5F5",
    "grid": "#E0E0E0",
    "text": "#263238",
}


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

    6. Absolute growth column: A derived column is added for the absolute
       value of arrivals growth. This is used to identify the fastest-changing
       country in a given year, regardless of direction (growth or decline).

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

    # Derived column: absolute growth for ranking fastest-changing destinations
    df["arrivals_growth_abs"] = df["arrivals_growth"].abs()

    logger.info("Data cleaning pipeline completed successfully.")
    return df


# ---------------------------------------------------------------------------
# Visualisation Helpers
# ---------------------------------------------------------------------------

def get_chart_template(fig, title_text, yaxis_title=""):
    """
    Apply a consistent visual style to a Plotly figure.

    Using a shared template function ensures all charts in the dashboard
    follow the same layout conventions (white background, centred bold title,
    consistent grid colour), which reduces visual noise for non-technical users.

    Args:
        fig: A Plotly figure object.
        title_text (str): The chart title to display.
        yaxis_title (str): Optional label for the y-axis.

    Returns:
        The updated Plotly figure with styling applied.
    """
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color=COLORS["text"]),
        title=dict(
            text=f"<b>{title_text}</b>",
            x=0.5,
            font=dict(size=16, color=COLORS["primary"]),
        ),
        xaxis=dict(gridcolor=COLORS["grid"]),
        yaxis=dict(title=yaxis_title, gridcolor=COLORS["grid"]),
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(bgcolor="rgba(255, 255, 255, 0.7)"),
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
app.title = "Interactive Tourism Trends"


# ---------------------------------------------------------------------------
# App Layout
# ---------------------------------------------------------------------------

app.layout = dbc.Container(
    [
        dcc.Download(id="download-dataframe-csv"),

        # Page title
        dbc.Row(
            dbc.Col(
                html.H1(
                    "Interactive Visualisation of International Tourism Trends (2015-2022)",
                    className="text-center my-4",
                    style={"color": COLORS["primary"]},
                )
            )
        ),

        # Global controls: country selector, year slider, map metric
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.Label("Select Countries to Compare:"),
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
                            html.Label("Select a Year:"),
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
                            html.Label("Select Map Metric:"),
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
            className="mt-3",
        ),
        html.Div(id="tab-content", className="p-4 mt-2"),
        html.Hr(),

        # Footer row: download button and data attribution
        dbc.Row(
            [
                dbc.Col(
                    dbc.Button(
                        "Download Data (CSV)",
                        id="btn-download",
                        color="primary",
                        className="mb-2",
                    ),
                    width={"size": "auto"},
                ),
                dbc.Col(
                    html.Span(
                        "Data Source: UN Tourism, World Bank, National Tourism Boards",
                        className="text-muted align-middle",
                        style={"fontStyle": "italic"},
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
            card1_text = f"{top_performer['country_name']}: {top_performer['arrivals_millions']:,.1f}M"
        except IndexError:
            card1_text = "N/A"

        try:
            highest_earner = year_data.nlargest(1, "tourism_receipts_usd_billions").iloc[0]
            card2_text = f"{highest_earner['country_name']}: ${highest_earner['tourism_receipts_usd_billions']:,.1f}B"
        except IndexError:
            card2_text = "N/A"

        try:
            fastest_grower = year_data.nlargest(1, "arrivals_growth_abs").iloc[0]
            card3_text = f"{fastest_grower['country_name']}: {fastest_grower['arrivals_growth']:+,.1f}%"
        except IndexError:
            card3_text = "N/A"

        # Choropleth map
        metric_labels = {
            "arrivals_millions": "Arrivals (Millions)",
            "tourism_receipts_usd_billions": "Receipts (USD Billions)",
            "tourism_gdp": "Tourism GDP (%)",
            "tourist_density_per_1000_residents": "Tourist Density",
        }
        fig_map = px.choropleth(
            year_data,
            locations="country_code",
            color=map_metric,
            hover_name="country_name",
            color_continuous_scale=px.colors.sequential.Greens,
            labels=metric_labels,
        )
        fig_map.update_layout(
            geo=dict(showframe=False, showcoastlines=False, projection_type="equirectangular")
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
                                html.H4(f"Key Insights for {year}", className="text-center mb-3"),
                                dbc.Card(
                                    [
                                        dbc.CardHeader("Top Performer (Arrivals)"),
                                        dbc.CardBody(html.P(card1_text, className="card-text")),
                                    ],
                                    className="mb-3", color="success", inverse=True,
                                ),
                                dbc.Card(
                                    [
                                        dbc.CardHeader("Highest Earner (Receipts)"),
                                        dbc.CardBody(html.P(card2_text, className="card-text")),
                                    ],
                                    className="mb-3", color="info", inverse=True,
                                ),
                                dbc.Card(
                                    [
                                        dbc.CardHeader("Fastest YoY Grower"),
                                        dbc.CardBody(html.P(card3_text, className="card-text")),
                                    ],
                                    className="mb-3", color="warning", inverse=True,
                                ),
                            ],
                            md=4,
                            className="align-self-center",
                        ),
                    ]
                ),
                html.Hr(),
                dbc.Accordion(
                    [
                        dbc.AccordionItem(
                            "The selected countries represent a curated mix of globally leading "
                            "destinations (e.g., France, Spain), major economies (USA, China), "
                            "unique tourism models (Iceland, Rwanda), and rapidly emerging hotspots "
                            "(Vietnam, Georgia). This diversity allows for a comprehensive analysis "
                            "of global tourism trends and recovery patterns.",
                            title="Why These 15 Countries?",
                        ),
                        dbc.AccordionItem(
                            html.Ol(
                                [
                                    html.Li([html.B("Explore the Map: "), "Use the dropdown to select a metric and see its worldwide distribution for the chosen year."]),
                                    html.Li([html.B("Select a Timeframe: "), "Use the year slider to focus on a specific year between 2015 and 2022."]),
                                    html.Li([html.B("Compare & Analyse: "), "Navigate to other tabs and use the country dropdown to compare specific nations over time."]),
                                ]
                            ),
                            title="How to Use This Dashboard",
                        ),
                        dbc.AccordionItem(
                            "Primary data synthesised from the United Nations World Tourism Organisation "
                            "(UNWTO), The World Bank, and national tourism boards.",
                            title="Data Sources",
                        ),
                    ],
                    start_collapsed=True,
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
        )
        # A vertical reference line marks 2020 to anchor the COVID impact visually
        fig_arrivals.update_traces(mode="lines+markers").add_vline(
            x=2020, line_width=1.5, line_dash="dash",
            line_color=COLORS["contrast"], annotation_text="COVID-19 Pandemic",
        )
        fig_arrivals = get_chart_template(fig_arrivals, "Tourism Arrivals Over Time", "Arrivals (Millions)")

        fig_receipts = px.line(
            dff, x="year", y="tourism_receipts_usd_billions", color="country_name",
            labels={"tourism_receipts_usd_billions": "Receipts (USD Billions)", "year": "Year", "country_name": "Country"},
        )
        fig_receipts.update_traces(mode="lines+markers").add_vline(
            x=2020, line_width=1.5, line_dash="dash",
            line_color=COLORS["contrast"], annotation_text="COVID-19 Pandemic",
        )
        fig_receipts = get_chart_template(fig_receipts, "Tourism Receipts Over Time", "Receipts (USD Billions)")

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
                color_discrete_sequence=[COLORS["accent_3"]],
                text_auto=".1f", height=300,
            )
            fig_bar_recovery = get_chart_template(
                fig_bar_recovery, f"Recovery Rate in 2022 vs 2019 ({country})"
            ).update_yaxes(range=[0, max(110, recovery_rate + 10)])
            single_country_content = [html.Hr(), dcc.Graph(figure=fig_bar_recovery)]

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

        fig_bar_employment = px.bar(
            year_data.sort_values(by="tourism_employment_thousands", ascending=False),
            x="country_name", y="tourism_employment_thousands",
            labels={"country_name": "Country", "tourism_employment_thousands": "Employment (Thousands)"},
            color_discrete_sequence=[COLORS["accent_1"]], height=400,
        )
        fig_bar_employment = get_chart_template(fig_bar_employment, f"Tourism Employment ({year})", "Employment (Thousands)")

        fig_gdp_line = px.line(
            dff, x="year", y="tourism_gdp", color="country_name",
            labels={"tourism_gdp": "Tourism GDP (%)", "year": "Year", "country_name": "Country"},
        )
        fig_gdp_line = get_chart_template(fig_gdp_line, "Tourism GDP Over Time", "Tourism GDP (%)")

        fig_employment_line = px.line(
            dff, x="year", y="tourism_employment_thousands", color="country_name",
            labels={"tourism_employment_thousands": "Employment (Thousands)", "year": "Year", "country_name": "Country"},
        )
        fig_employment_line = get_chart_template(fig_employment_line, "Tourism Employment Over Time", "Employment (Thousands)")

        return html.Div(
            [
                html.P("The top charts compare all countries for a given year; the bottom charts show historical trends for the selected countries."),
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(figure=fig_bar_gdp), md=6),
                        dbc.Col(dcc.Graph(figure=fig_bar_employment), md=6),
                    ]
                ),
                html.Hr(),
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
        )
        fig_stay = get_chart_template(fig_stay, "Average Length of Stay", "Average Days")

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
                    color_discrete_sequence=[COLORS["accent_2"], COLORS["accent_3"], COLORS["contrast"]],
                )
                fig_pie_sources.update_traces(textposition="inside", textinfo="percent+label")
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
                html.Hr(),
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
                hovertemplate="<b>%{x}</b><br>Renewable Energy: %{y:.1f}%<extra></extra>",
            ),
            secondary_y=False,
        )
        fig_sustainability.add_trace(
            go.Bar(
                x=year_data["country_name"], y=year_data["tourist_density_per_1000_residents"],
                name="Tourist Density", marker_color=COLORS["contrast"],
                hovertemplate="<b>%{x}</b><br>Tourist Density: %{y:,.0f}<extra></extra>",
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
