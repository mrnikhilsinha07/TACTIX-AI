# ⚽ TACTIX AI — Football Transition Intelligence

**Interactive football analytics dashboard for exploring candidate possession-loss events and subsequent opponent attacks.**

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Open%20App-FF4B4B?logo=streamlit&logoColor=white)](https://tactix-ai-zqc29qk7pigitffodmsjfj.streamlit.app/)

## 🚀 Live Demo

**[Open TACTIX AI](https://tactix-ai-zqc29qk7pigitffodmsjfj.streamlit.app/)**

TACTIX AI uses **StatsBomb Open Data** from the **2022 FIFA World Cup** to explore candidate possession-loss events and whether the opponent's next possession contains a shot. It is an exploratory analysis tool—not a verified turnover classifier or a causal model.

## 🎯 Problem

Possession losses can precede an opponent's attacking opportunity, but an event that looks like a loss is not necessarily a confirmed turnover. Analysts need a way to inspect candidate events, filter by team or match, and examine what happens next without treating correlation as causation.

## ✨ Features

- Interactive overview metrics and charts.
- Filters for team losing possession, loss indicator, and match ID.
- Visualization of available candidate event locations.
- Transition-outcome comparisons by candidate indicator.
- Data-quality tab with validation summary and event-type coverage.
- Filtered CSV export for further analysis.
- Interpretation warnings that distinguish exploratory indicators from verified or causal conclusions.

## 📊 Dataset and Current Results

| Measure | Current pipeline result |
|---|---:|
| Competition | FIFA World Cup 2022 |
| Matches with event data loaded | 64 |
| Events processed | 234,637 |
| Candidate transition records | 10,942 |
| Candidates whose next opponent possession contains a shot | 987 |
| Share with a subsequent shot | 9.0% |

These are exploratory pipeline counts. They are not verified counts of genuine turnovers, a definitive pressing score, or evidence of causal impact.

## 🧠 Methodology

1. Retrieve the StatsBomb Open Data match index for the 2022 FIFA World Cup.
2. Load event data for available matches.
3. Identify candidate indicators such as dispossessions, miscontrols, explicitly unsuccessful passes, and unsuccessful dribbles.
4. Compare the candidate event's possession team with the team in the subsequent possession.
5. Check whether that subsequent opponent possession contains a shot.
6. Save the analysis and validation reports used by the dashboard.

### Interpretation limits

- A candidate event is a proxy, not automatically a confirmed turnover.
- A shot in the next opponent possession does not prove the candidate event caused it.
- Results depend on event definitions and available data coverage.
- Event-location plots use source event coordinates and are not a full pitch drawing.

## 🛠️ Technology Stack

- Python
- Pandas
- Streamlit
- Plotly
- Requests
- StatsBomb Open Data

## 📁 Repository Structure

```text
TACTIX-AI/
├── app.py                       # Streamlit dashboard
├── requirements.txt             # Python dependencies
├── README.md                    # Project documentation
├── src/                         # Data retrieval and validation scripts
└── reports/
    ├── validation_summary.json  # Pipeline validation summary
    ├── transition_candidates.csv
    ├── sample_matches.csv
    └── event_type_coverage.csv
```

The dashboard expects these four reports inside the root-level `reports/` directory. If they are missing, run the validation pipeline before starting the dashboard.

## 💻 Run Locally

### Prerequisites

- Python 3.10 or newer
- Git
- Internet access for downloading the open dataset

### 1. Clone the repository

```bash
git clone https://github.com/mrnikhilsinha07/TACTIX-AI.git
cd TACTIX-AI
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the virtual environment's Python executable directly.

**macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Generate or validate reports if needed

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe src\validate_statsbomb.py
```

This step may need internet access to retrieve the open event data.

### 5. Launch the dashboard

```bash
streamlit run app.py
```

Open the local address Streamlit prints, usually `http://localhost:8501`.

## ☁️ Deployment

The public dashboard is hosted on Streamlit Community Cloud and connected to this GitHub repository.

To deploy another copy:

1. Sign in to Streamlit Community Cloud.
2. Create an app from `mrnikhilsinha07/TACTIX-AI`.
3. Select branch `main` and entry point `app.py`.
4. Confirm `requirements.txt` includes the app dependencies.
5. Deploy and verify all four tabs, filters, charts, and CSV export.

## 🔎 Validation and Troubleshooting

- **Missing report files:** run `src/validate_statsbomb.py` and confirm the required files exist in `reports/`.
- **Missing Python package:** activate the virtual environment and run `pip install -r requirements.txt`.
- **Online changes do not appear:** check the latest deployment status in Streamlit Community Cloud, then refresh the dashboard.
- **No records appear:** broaden the selected filters and check the Data quality tab.

## 📚 Data Source and Attribution

This project uses **StatsBomb Open Data**. Follow the dataset's current terms, attribution requirements, and usage guidelines before redistributing data or publishing derived outputs. TACTIX AI is an independent exploratory application, not an official StatsBomb product.

- StatsBomb Open Data: https://github.com/statsbomb/open-data

## 🗺️ Future Improvements

- Side-by-side team comparisons.
- Match-level drill-downs and clearer event context.
- More automated validation and regression tests.
- Improved pitch visualization and clearer documentation of candidate-event definitions.

## 📄 Project Status

The dashboard is deployed and the core interface has been manually checked. Future changes should preserve the distinction between exploratory indicators and verified football outcomes.
