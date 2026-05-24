# Interactive Visualisation of Global Tourism Trends (2015–2022)

An interactive web dashboard built in Python and Dash, designed to make complex international tourism data explorable by non-technical users such as policymakers and researchers.

This project was developed as an MSc dissertation at Bangor University (2025–2026), using the **Five Design-Sheet (FDS)** methodology across four iterative prototypes, with formative evaluation at each stage using the **Critical Design Strategy (CDS)**.

---

## What It Does

The dashboard allows users to:

- Explore international tourism arrivals, receipts, and economic indicators across 15 countries and 8 years (2015–2022)
- Compare post-COVID recovery trajectories across regions using interactive line charts
- Analyse tourism's contribution to GDP and employment by country and year
- Examine visitor behaviour patterns and top source markets
- Compare sustainability metrics (renewable energy share vs tourist density)

All charts are interactive and update in real time based on country and year selections.

---

## Key Findings

- **Divergent recoveries**: Europe (France, Spain) showed V-shaped recovery post-COVID; Asia (Japan, China) showed L-shaped patterns due to extended border restrictions.
- **Mexico as an outlier**: Mexico maintained relatively high arrivals during 2020–2021 due to its open-border policy, making it a statistically unusual case in the dataset.
- **Economic reliance**: Spain's tourism contribution to GDP (~14%) significantly outpaces France (~9%), reflecting a deeper structural dependency on the sector.

---

## Data Sources

- **UN World Tourism Organisation (UNWTO)** – international arrivals and receipts
- **World Bank** – GDP and employment figures
- **National tourism boards** – source market and length-of-stay data

---

## Project Structure

```
tourism-dashboard/
├── app.py                          # Main application: data pipeline and dashboard
├── International Tourism Trends.csv  # Cleaned dataset (15 countries, 2015–2022)
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

---

## Installation and Usage

**1. Clone the repository**

```bash
git clone https://github.com/ogenelson/tourism-dashboard.git
cd tourism-dashboard
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Run the app**

```bash
python app.py
```

**4. Open in your browser**

```
http://127.0.0.1:8050
```

---

## Design Decisions

### Data Cleaning

The raw data required several non-trivial cleaning decisions:

- **Country name standardisation**: The value `'South'` appeared in source market columns as a truncated reference to South Korea. Rather than dropping these rows, the value was corrected explicitly, as South Korea is a significant source market for both China and Thailand.
- **Missing value handling**: Numeric fields with missing or unparseable values were filled with `0` rather than dropped. Dropping rows would have created gaps in the time series that would distort recovery trend charts.
- **Percentage parsing**: Source country share columns arrived as strings (e.g., `"20%"`). These were converted to decimal proportions (`0.20`) to allow consistent scaling across charts.

### Visualisation

- A shared `get_chart_template()` function applies consistent styling across all charts, reducing visual noise and ensuring the interface feels coherent to non-technical users.
- The COVID-19 pandemic year (2020) is marked with a vertical reference line on recovery charts to help users contextualise the data without needing to interpret it themselves.
- The map metric dropdown is hidden on non-map tabs to avoid presenting irrelevant controls.

### Code Structure

- All data loading and transformation is contained in `load_and_clean_data()` so the pipeline is isolated, testable, and easy to modify if the data source changes.
- A single callback handles all five tab renders using the active tab ID as a dispatch key, avoiding duplication of country and year inputs across multiple callbacks.

---

## Requirements

```
dash>=2.0
dash-bootstrap-components>=1.0
plotly>=5.0
pandas>=1.3
```

---

## Author

**Ogechi Nelson**  
MSc Artificial Intelligence and Data Science, Bangor University  
[ogenelsson@gmail.com](mailto:ogenelsson@gmail.com)
