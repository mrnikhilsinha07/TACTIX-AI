# ⚽ TACTIX AI — Football Transition Intelligence

### Sports Analytics | AQX Sports Analytics Data Bowl 4.0

TACTIX AI is an interactive football analytics dashboard that explores
what happens after teams lose possession. It uses StatsBomb Open Data
from the 2022 FIFA World Cup to investigate candidate possession-loss
events and subsequent opponent attacking outcomes.

## 🎯 Problem

Losing possession can expose a team to an opponent's attack. Coaches and
analysts need ways to investigate where candidate losses occur and what
happens during the following opponent possession.

TACTIX AI provides an exploratory, data-driven interface for examining
these patterns.

## 💡 Solution

TACTIX AI processes football event data and presents interactive
visualizations that help users explore candidate possession losses,
opponent possessions, and subsequent shots.

## ✨ Features

- Interactive dashboard built with Streamlit.
- Team, match, and event-indicator filters.
- Candidate possession-loss event analysis.
- Analysis of whether the next opponent possession contains a shot.
- Visual exploration of event locations.
- Match index and event-type coverage tables.
- Filtered data export to CSV.
- JSON validation summary.

## 📊 Dataset

**Source:** StatsBomb Open Data  
**Competition:** FIFA World Cup 2022  
**Matches processed:** 64  
**Events processed:** 234,637  
**Candidate transition records:** 10,942  
**Candidates followed by an opponent possession containing a shot:** 987

These are results from the current exploratory pipeline, not verified
counts of genuine turnovers or causal outcomes.

## 🧠 Methodology

1. Retrieve the World Cup 2022 match index.
2. Download the event data for each available match.
3. Identify candidate events such as dispossessions, miscontrols,
   explicitly unsuccessful passes, and unsuccessful dribbles.
4. Compare the candidate event's possession team with the team in the
   next possession.
5. Examine whether that subsequent opponent possession contains a shot.
6. Save the analysis reports and display them in the dashboard.

## 🛠️ Technology Stack

- Python
- Pandas
- Streamlit
- Plotly
- Requests
- StatsBomb Open Data

## 🚀 Run Locally

### Requirements

- Python 3.10 or newer
- Git
- Internet connection for downloading the dataset

### Installation

Clone the repository:

```bash
git clone https://github.com/mrnikhilsinha07/TACTIX-AI.git
cd TACTIX-AI
