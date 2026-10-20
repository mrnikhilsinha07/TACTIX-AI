from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
HEADERS = {"User-Agent": "TACTIX-AI-educational-research/0.2"}
TIMEOUT = 30
# 2022 FIFA World Cup: all matches in the competition/season match index.
COMPETITION_ID = 43
SEASON_ID = 106
COMPETITION_NAME = "FIFA World Cup"
SEASON_NAME = "2022"


def get_json(url: str) -> Any:
    response = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def name(value: Any) -> str:
    return value.get("name", "") if isinstance(value, dict) else ""


def event_type(event: dict) -> str:
    return name(event.get("type")) or "Unknown"


def team_name(event: dict) -> str:
    return name(event.get("team")) or "Unknown"


def possession_team(event: dict) -> str:
    # StatsBomb events may have possession_team, which is preferable to event team
    # when describing the team controlling a possession.
    return name(event.get("possession_team")) or team_name(event)


def location(event: dict) -> tuple[float | None, float | None]:
    value = event.get("location")
    if isinstance(value, list) and len(value) >= 2:
        try:
            return float(value[0]), float(value[1])
        except (TypeError, ValueError):
            pass
    return None, None


def turnover_indicator(event: dict) -> str | None:
    """Conservative candidate indicators; not every event proves a turnover."""
    kind = event_type(event)
    if kind in {"Dispossessed", "Miscontrol"}:
        return kind
    if kind == "Pass":
        outcome = name((event.get("pass") or {}).get("outcome"))
        # An explicit non-empty outcome other than success/completion indicates failure.
        if outcome and outcome.lower() not in {"complete", "success"}:
            return f"Incomplete pass: {outcome}"
    if kind == "Dribble":
        outcome = name((event.get("dribble") or {}).get("outcome"))
        if outcome and outcome.lower() not in {"complete", "success"}:
            return f"Unsuccessful dribble: {outcome}"
    return None


def is_opponent_possession(current_team: str, next_events: list[dict]) -> tuple[bool, str]:
    if not next_events:
        return False, ""
    next_team = possession_team(next_events[0])
    return bool(current_team and next_team and current_team != next_team), next_team


def main() -> None:
    print("TACTIX AI — improved transition validation")
    matches_url = f"{BASE}/matches/{COMPETITION_ID}/{SEASON_ID}.json"
    matches = get_json(matches_url)
    print(f"Found {len(matches)} matches for {COMPETITION_NAME} — {SEASON_NAME}.")

    match_rows: list[dict] = []
    event_counts = Counter()
    candidate_rows: list[dict] = []
    all_event_count = 0
    loaded_matches = 0
    errors: list[dict] = []

    for index, match in enumerate(matches, start=1):
        match_id = match.get("match_id")
        home_obj = match.get("home_team") or {}
        away_obj = match.get("away_team") or {}
        home = home_obj.get("home_team_name") or home_obj.get("name", "")
        away = away_obj.get("away_team_name") or away_obj.get("name", "")
        match_rows.append({
            "match_id": match_id,
            "match_date": match.get("match_date"),
            "home_team": home,
            "away_team": away,
            "home_score": match.get("home_score"),
            "away_score": match.get("away_score"),
        })
        try:
            events = get_json(f"{BASE}/events/{match_id}.json")
        except Exception as exc:
            errors.append({"match_id": match_id, "error": str(exc)})
            print(f"[{index}/{len(matches)}] Could not load match {match_id}: {exc}")
            continue

        loaded_matches += 1
        all_event_count += len(events)
        for event in events:
            event_counts[event_type(event)] += 1

        # Group source-ordered events by possession ID. We only analyze the next
        # possession if the possession team changes. This reduces false positives
        # compared with assuming every failed action is a confirmed turnover.
        possessions: dict[int, list[dict]] = {}
        for event in events:
            raw_possession = event.get("possession")
            if raw_possession is None:
                continue
            try:
                possessions.setdefault(int(raw_possession), []).append(event)
            except (TypeError, ValueError):
                continue

        possession_ids = sorted(possessions)
        next_possession_id = {
            possession_ids[i]: possession_ids[i + 1]
            for i in range(len(possession_ids) - 1)
        }

        for event in events:
            indicator = turnover_indicator(event)
            if not indicator:
                continue
            raw_current = event.get("possession")
            if raw_current is None:
                continue
            try:
                current_id = int(raw_current)
            except (TypeError, ValueError):
                continue

            following_id = next_possession_id.get(current_id)
            if following_id is None:
                continue

            current_team = possession_team(event)
            next_events = possessions.get(following_id, [])
            is_opponent, next_team = is_opponent_possession(current_team, next_events)
            if not is_opponent:
                continue

            shots = [e for e in next_events if event_type(e) == "Shot"]
            # A simple progression proxy: compare first available location in the
            # opponent's possession with the candidate loss location. It is not
            # an exact measure of progress because event locations and direction vary.
            loss_x, loss_y = location(event)
            next_x, next_y = location(next_events[0])
            minute = event.get("minute")
            second = event.get("second")
            game_state = "unknown"
            try:
                home_score = int(match.get("home_score") or 0)
                away_score = int(match.get("away_score") or 0)
                event_minute = int(minute or 0)
                # The current score fields are final scores, not score at event time.
                # Do not infer leading/trailing state from final score.
                if event_minute >= 0:
                    game_state = "not calculated (score-at-event unavailable)"
            except (TypeError, ValueError):
                pass

            candidate_rows.append({
                "match_id": match_id,
                "match_date": match.get("match_date"),
                "home_team": home,
                "away_team": away,
                "team_losing_possession": current_team,
                "opponent_next_possession": next_team,
                "loss_event_type": event_type(event),
                "loss_indicator": indicator,
                "minute": minute,
                "second": second,
                "loss_x": loss_x,
                "loss_y": loss_y,
                "next_possession_id": following_id,
                "opponent_possession_event_count": len(next_events),
                "opponent_possession_contains_shot": bool(shots),
                "opponent_shot_count": len(shots),
                "opponent_first_event": event_type(next_events[0]) if next_events else "Unknown",
                "next_possession_first_x": next_x,
                "next_possession_first_y": next_y,
                "game_state": game_state,
                "indicator_is_confirmed_turnover": False,
            })
        if index % 10 == 0 or index == len(matches):
            print(f"[{index}/{len(matches)}] processed; loaded event files: {loaded_matches}")
        time.sleep(0.05)

    pd.DataFrame(match_rows).to_csv(REPORTS / "sample_matches.csv", index=False)
    pd.DataFrame([{"event_type": k, "count": v} for k, v in event_counts.most_common()]).to_csv(
        REPORTS / "event_type_coverage.csv", index=False
    )
    candidates = pd.DataFrame(candidate_rows)
    candidates.to_csv(REPORTS / "transition_candidates.csv", index=False)

    summary = {
        "data_source": "StatsBomb Open Data",
        "competition": COMPETITION_NAME,
        "season": SEASON_NAME,
        "competition_id": COMPETITION_ID,
        "season_id": SEASON_ID,
        "matches_available": len(matches),
        "matches_with_events_loaded": loaded_matches,
        "total_events_loaded": all_event_count,
        "candidate_transition_rows": len(candidates),
        "candidate_rows_followed_by_opponent_possession_with_shot": int(
            candidates["opponent_possession_contains_shot"].sum()
        ) if not candidates.empty else 0,
        "download_errors": errors,
        "methodology": {
            "turnover_indicators": ["Dispossessed", "Miscontrol", "Pass with explicit unsuccessful outcome", "Dribble with explicit unsuccessful outcome"],
            "opponent_possession_check": "Candidate is retained only if the next possession's possession_team differs from the candidate event's possession team.",
            "limitations": [
                "These remain candidate indicators; the event itself does not always prove that possession changed at that instant.",
                "The next possession containing a shot is an association, not proof of causation.",
                "Exact pressing intensity and continuous player movement are not inferred.",
                "Score-at-event game state is not calculated because final score alone is insufficient.",
                "Location progression is not asserted as a metric in this version because direction and coordinate interpretation require additional validation."
            ]
        }
    }
    (REPORTS / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n--- IMPROVED VALIDATION SUMMARY ---")
    print(json.dumps(summary, indent=2))
    print(f"\nReports saved to: {REPORTS}")
    if errors:
        print(f"Warning: {len(errors)} match event files could not be loaded.")


if __name__ == "__main__":
    main()
