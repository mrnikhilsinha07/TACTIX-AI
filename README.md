# TACTIX AI — Improved Transition Validation

This package replaces `src/validate_statsbomb.py` with a more conservative event-based transition analysis.

## Install location
Copy `src\validate_statsbomb.py` into:
`D:\TACTIX_AI_Data_Validation\src\validate_statsbomb.py`

Overwrite the old file when Windows asks.

## Run
From PowerShell in `D:\TACTIX_AI_Data_Validation`:

```powershell
.\.venv\Scripts\python.exe src\validate_statsbomb.py
```

This now processes all matches listed for the 2022 FIFA World Cup competition/season, not just the first eight. It may take several minutes.

## What changed
- Loads the full World Cup 2022 match list.
- Uses possession IDs and possession-team changes to filter candidate indicators.
- Keeps clear limitations in the summary.
- Does not infer score-at-event game state from final scores.
- Writes updated reports to the existing `reports` folder.

Back up the existing script if you want to preserve the initial version.
