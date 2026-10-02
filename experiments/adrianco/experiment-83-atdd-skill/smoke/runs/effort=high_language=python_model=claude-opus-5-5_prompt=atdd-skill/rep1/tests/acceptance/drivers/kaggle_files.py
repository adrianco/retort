"""
Protocol driver (layer 3) for the system's external data source: the
Kaggle CSV files.

Writes synthetic facts in exactly the layout of each provided file —
column names, date formats ("2012-05-19 18:30:00", "29/03/2003"), state
suffixes and float-valued goals — so the system under test reads them
through the same path it uses for the real data.
"""

import csv
import datetime
import re
from pathlib import Path

FILES = {
    "Brasileirao_Matches.csv": ["datetime", "home_team", "home_team_state", "away_team", "away_team_state",
                                "home_goal", "away_goal", "season", "round"],
    "Brazilian_Cup_Matches.csv": ["round", "datetime", "home_team", "away_team", "home_goal", "away_goal", "season"],
    "Libertadores_Matches.csv": ["datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "stage"],
    "BR-Football-Dataset.csv": ["tournament", "home", "home_goal", "away_goal", "away", "home_corner",
                                "away_corner", "home_attack", "away_attack", "home_shots", "away_shots", "time",
                                "date", "ht_diff", "at_diff", "ht_result", "at_result", "total_corners"],
    "novo_campeonato_brasileiro.csv": ["ID", "Data", "Ano", "Rodada", "Equipe_mandante", "Equipe_visitante",
                                       "Gols_mandante", "Gols_visitante", "Mandante_UF", "Visitante_UF",
                                       "Vencedor", "Arena", "OBS"],
    "fifa_data.csv": ["", "ID", "Name", "Age", "Nationality", "Overall", "Potential", "Club", "Value", "Wage",
                      "Preferred Foot", "Position", "Jersey Number", "Height", "Weight", "Crossing", "Finishing",
                      "Dribbling", "ShortPassing", "SprintSpeed", "StandingTackle", "GKDiving"],
}


class KaggleFiles:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self._rows = {name: [] for name in FILES}

    def add_brasileirao_match(self, home, away, home_goals, away_goals, date, season, round):
        self._rows["Brasileirao_Matches.csv"].append(
            [f"{date} 16:00:00", home, _state(home), away, _state(away), _or_na(home_goals), _or_na(away_goals),
             season, round])

    def add_historical_brasileirao_match(self, home, away, home_goals, away_goals, date, season, round):
        winner = "Mandante" if home_goals > away_goals else "Visitante" if away_goals > home_goals else "Empate"
        match_id = f"{season}.{round:02d}.{len(self._rows['novo_campeonato_brasileiro.csv']) + 1:04d}"
        self._rows["novo_campeonato_brasileiro.csv"].append(
            [match_id, _brazilian_date(date), season, round, home, away, home_goals, away_goals,
             _state(home), _state(away), winner, "Arena", ""])

    def add_copa_do_brasil_match(self, home, away, home_goals, away_goals, date, season, round):
        self._rows["Brazilian_Cup_Matches.csv"].append(
            [round, f"{date} 21:30:00", home, away, home_goals, away_goals, season])

    def add_libertadores_match(self, home, away, home_goals, away_goals, date, season, stage):
        self._rows["Libertadores_Matches.csv"].append(
            [f"{date} 21:30:00", home, away, home_goals, away_goals, season, stage])

    def add_extended_stats_match(self, home, away, home_goals, away_goals, date, tournament, corners, shots):
        diff = home_goals - away_goals
        result = {True: "WON", False: "LOST"}
        home_result = "DRAW" if diff == 0 else result[diff > 0]
        away_result = "DRAW" if diff == 0 else result[diff < 0]
        self._rows["BR-Football-Dataset.csv"].append(
            [tournament, home, float(home_goals), float(away_goals), away, float(corners[0]), float(corners[1]),
             80.0, 80.0, float(shots[0]), float(shots[1]), "20:00:00", date, float(diff), float(-diff),
             home_result, away_result, float(sum(corners))])

    def add_fifa_player(self, name, nationality, club, overall, position, age):
        rows = self._rows["fifa_data.csv"]
        rows.append([len(rows), 900000 + len(rows), name, age, nationality, overall, overall + 3, club,
                     "€10M", "€20K", "Right", position, 10, "5'10", "160lbs", 60, 60, 60, 60, 60, 60, 10])

    def write(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        for name, header in FILES.items():
            with open(self.directory / name, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(header)
                writer.writerows(self._rows[name])


def _or_na(goals):
    return "NA" if goals is None else goals


def _state(team):
    match = re.search(r"-\s*([A-Z]{2})$", team)
    return match.group(1) if match else ""


def _brazilian_date(iso_date):
    return datetime.date.fromisoformat(iso_date).strftime("%d/%m/%Y")
