# ⚽ TACTIX AI — Football Transition Intelligence

**Interactive football analytics dashboard for exploring candidate possession-loss events and subsequent opponent attacks.**

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Open%20App-FF4B4B?logo=streamlit&logoColor=white)](https://tactix-ai-zqc29qk7pigitffodmsjfj.streamlit.app/)

## 🚀 Live Demo

**[Open TACTIX AI](https://tactix-ai-zqc29qk7pigitffodmsjfj.streamlit.app/)**

TACTIX AI uses **StatsBomb Open Data** from the **2022 FIFA World Cup** to explore candidate possession-loss events and whether the opponent's next possession contains a shot. It is an exploratory analysis tool—not a verified turnover classifier or a causal model.

## 🎯 Problem

Possession losses can precede an opponent's attacking opportunity, but an event that looks like a loss is not necessarily a confirmed turnover. Analysts need a way to inspect candidate events, filter by team or match, and examine what happens next without treating correlation as causation.

## ✨ Dashboard Features

The dashboard contains seven tabs:

1. **Overview** — high-level dataset and transition metrics.
2. **Where possession was lost** — inspect candidate event locations and filter by team, indicator, or match.
3. **Transition outcomes** — explore whether the next opponent possession contains a shot.
4. **Match analysis** — inspect results for an individual match.
5. **Data quality** — review validation summaries, missing data, and event-type coverage.
6. **Team comparison** — compare observed candidate-event counts and rates between teams.
7. **Advanced analytics** — inspect team-by-match and indicator analyses, confidence intervals, and team-level statistical reliability estimates.

Other features include interactive charts, filtering, tables, CSV exports, and interpretation notes that distinguish exploratory indicators from verified or causal conclusions.

## 📊 Dataset and Current Results

| Measure | Current pipeline result |
|---|---:|
| Competition | FIFA World Cup 2022 |
| Matches with event data loaded | 64 |
| Events processed | 234,637 |
| Candidate transition records | 10,942 |
| Candidates whose next opponent possession contains a shot | 987 |
| Share with a subsequent shot | 9.0% |

These are exploratory pipeline counts. They are not verified counts of genuine turnovers, a definitive pressing score, or evidence of causal impact. Re-run the pipeline to reproduce the results; counts can depend on the dataset version and event definitions.

## 🧠 Methodology

1. Retrieve the StatsBomb Open Data match index for the 2022 FIFA World Cup.
2. Load event data for available matches.
3. Identify candidate indicators such as dispossessions, miscontrols, explicitly unsuccessful passes, and unsuccessful dribbles.
4. Compare the candidate event's possession team with the team in the subsequent possession.
5. Check whether that subsequent opponent possession contains a shot.
6. Save the analysis and validation reports used by the dashboard.
7. Summarize observed rates with confidence intervals where available.

### Statistical methods

- **Wilson 95% confidence intervals:** used for observed proportions to communicate uncertainty around estimated rates.
- **Match-clustered bootstrap:** resamples whole matches to explore how uncertainty may change when match-level clustering is considered.
- **Team-level estimates:** team-specific rates and intervals are descriptive and exploratory. Teams have only 3–7 matches in this dataset, so the limited number of matches makes team-level bootstrap intervals unstable for definitive ranking or strong inferential claims.
- **Interpretation:** intervals quantify statistical uncertainty under the chosen method; they do not remove selection bias, establish causation, or prove that a candidate event caused a later shot.

Bootstrap estimates depend on the implementation, resampling settings, and random seed. They should be interpreted as supporting analysis rather than a definitive measure of team quality.

### Interpretation limits

- A candidate event is a proxy, not automatically a confirmed turnover.
- A shot in the next opponent possession does not prove the candidate event caused it.
- Events within the same match may be correlated; ordinary event-level intervals may not fully account for this dependence.
- Results depend on event definitions and available data coverage.
- Event-location plots use source event coordinates and are not a full pitch drawing.
- Team comparisons are observational and should not be treated as definitive rankings.

## 🛠️ Technology Stack

- Python
- Streamlit
- Pandas
- NumPy
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
├── analysis/                    # Statistical analysis and test scripts
└── reports/
    ├── validation_summary.json  # Pipeline validation summary
    ├── transition_candidates.csv
    ├── sample_matches.csv
    └── event_type_coverage.csv
```

The dashboard expects the required reports inside the root-level `reports/` directory. If they are missing, run the validation pipeline before starting the dashboard. Additional analysis scripts may generate supplementary reports such as bootstrap summaries.

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
5. Deploy and manually verify all seven tabs, filters, charts, statistical reliability section, and CSV export.

## 🧪 Testing and Validation

The project has been manually checked across all seven dashboard tabs. The statistical analysis scripts also have unit tests for the event-level and team-level cluster bootstrap routines; the last recorded run passed 14 tests in total.

These checks do not guarantee correctness for every input, match, dependency version, or deployment condition. Re-run the tests after changing the analysis code. From the repository root, use:

```bash
python -m pytest analysis
```

If the repository's test layout changes, adjust the test command accordingly.

## 🔎 Validation and Troubleshooting

- **Missing report files:** run `src/validate_statsbomb.py` and confirm the required files exist in `reports/`.
- **Missing Python package:** activate the virtual environment and run `pip install -r requirements.txt`.
- **Online changes do not appear:** check the latest deployment status in Streamlit Community Cloud, then refresh the dashboard.
- **No records appear:** broaden the selected filters and check the Data quality tab.
- **Statistical estimates vary:** check bootstrap settings and random seeds, and interpret estimates in light of the small number of matches.

## 📚 Data Source and Attribution

This project uses **StatsBomb Open Data**. Follow the dataset's current terms, attribution requirements, and usage guidelines before redistributing data or publishing derived outputs. TACTIX AI is an independent exploratory application, not an official StatsBomb product.

- StatsBomb Open Data: https://github.com/statsbomb/open-data

## 🗺️ Future Improvements

- Further match-level drill-downs and clearer event context.
- More automated validation and regression tests.
- Improved pitch visualization and clearer documentation of candidate-event definitions.
- Additional sensitivity analyses for candidate-event definitions and uncertainty estimates.

## 📄 Project Status

The dashboard is deployed and the core interface has been manually checked across all seven tabs. The recorded bootstrap test suite passed 14 tests. Future changes should preserve the distinction between exploratory indicators and verified football outcomes.
