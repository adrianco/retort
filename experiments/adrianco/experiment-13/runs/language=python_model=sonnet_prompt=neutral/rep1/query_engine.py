from __future__ import annotations

from typing import Optional

import pandas as pd

from data_loader import DataLoader, normalize_team


class QueryEngine:
    """Provides query methods over the loaded soccer datasets."""

    def __init__(self, loader: DataLoader):
        self.loader = loader

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _filter_team(self, df: pd.DataFrame, team: str) -> pd.DataFrame:
        norm = normalize_team(team)
        mask = df["home_team_norm"].str.contains(norm, regex=False, na=False) | df[
            "away_team_norm"
        ].str.contains(norm, regex=False, na=False)
        return df[mask]

    def _filter_competition(self, df: pd.DataFrame, competition: str) -> pd.DataFrame:
        low = competition.lower()
        return df[df["competition"].str.lower().str.contains(low, na=False)]

    @staticmethod
    def _fmt_row(row: pd.Series) -> str:
        date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "Unknown"
        hg = int(row["home_goal"]) if pd.notna(row["home_goal"]) else "?"
        ag = int(row["away_goal"]) if pd.notna(row["away_goal"]) else "?"
        ri = row["round_info"]
        ri_part = f" ({ri})" if ri and ri not in ("", "nan") else ""
        yr = f" [{row['season']}]" if pd.notna(row["season"]) else ""
        return f"  {date_str}: {row['home_team']} {hg}-{ag} {row['away_team']} | {row['competition']}{ri_part}{yr}"

    # ------------------------------------------------------------------ #
    # Public query methods                                                 #
    # ------------------------------------------------------------------ #

    def search_matches(
        self,
        team: Optional[str] = None,
        opponent: Optional[str] = None,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20,
    ) -> str:
        """Search matches with optional filters. Returns formatted results."""
        df = self.loader.all_matches.copy()

        if team:
            df = self._filter_team(df, team)
        if opponent:
            df = self._filter_team(df, opponent)
        if competition:
            df = self._filter_competition(df, competition)
        if season:
            df = df[df["season"] == season]
        if date_from:
            df = df[df["date"] >= pd.to_datetime(date_from, errors="coerce")]
        if date_to:
            df = df[df["date"] <= pd.to_datetime(date_to, errors="coerce")]

        df = df.sort_values("date", ascending=False)
        total = len(df)
        shown = min(total, limit)
        df = df.head(limit)

        if df.empty:
            return "No matches found matching the criteria."

        lines = [f"Found {total} matches (showing {shown}):"]
        lines.extend(self._fmt_row(row) for _, row in df.iterrows())
        return "\n".join(lines)

    def head_to_head(
        self,
        team1: str,
        team2: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """Head-to-head record and recent matches between two teams."""
        df = self.loader.all_matches.copy()
        n1 = normalize_team(team1)
        n2 = normalize_team(team2)

        mask = (
            df["home_team_norm"].str.contains(n1, regex=False, na=False)
            & df["away_team_norm"].str.contains(n2, regex=False, na=False)
        ) | (
            df["home_team_norm"].str.contains(n2, regex=False, na=False)
            & df["away_team_norm"].str.contains(n1, regex=False, na=False)
        )
        df = df[mask]

        if competition:
            df = self._filter_competition(df, competition)
        if season:
            df = df[df["season"] == season]

        total = len(df)
        if total == 0:
            return f"No matches found between {team1} and {team2}."

        valid = df.dropna(subset=["home_goal", "away_goal"])

        t1_wins = (
            (
                valid["home_team_norm"].str.contains(n1, regex=False, na=False)
                & (valid["home_goal"] > valid["away_goal"])
            )
            | (
                valid["away_team_norm"].str.contains(n1, regex=False, na=False)
                & (valid["away_goal"] > valid["home_goal"])
            )
        ).sum()

        t2_wins = (
            (
                valid["home_team_norm"].str.contains(n2, regex=False, na=False)
                & (valid["home_goal"] > valid["away_goal"])
            )
            | (
                valid["away_team_norm"].str.contains(n2, regex=False, na=False)
                & (valid["away_goal"] > valid["home_goal"])
            )
        ).sum()

        draws = (valid["home_goal"] == valid["away_goal"]).sum()

        lines = [
            f"Head-to-Head: {team1} vs {team2}",
            f"Total matches: {total}",
            f"{team1} wins: {t1_wins} | Draws: {draws} | {team2} wins: {t2_wins}",
            "",
            f"Recent matches (showing {min(total, limit)}):",
        ]
        for _, row in df.sort_values("date", ascending=False).head(limit).iterrows():
            lines.append(self._fmt_row(row))
        return "\n".join(lines)

    def get_team_record(
        self,
        team: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        home_away: str = "all",
    ) -> str:
        """Win/loss/draw record for a team with optional filters."""
        df = self.loader.all_matches.copy()
        norm = normalize_team(team)

        if competition:
            df = self._filter_competition(df, competition)
        if season:
            df = df[df["season"] == season]

        home_df = df[
            df["home_team_norm"].str.contains(norm, regex=False, na=False)
        ].dropna(subset=["home_goal", "away_goal"])
        away_df = df[
            df["away_team_norm"].str.contains(norm, regex=False, na=False)
        ].dropna(subset=["home_goal", "away_goal"])

        if home_away == "home":
            away_df = pd.DataFrame(columns=away_df.columns)
        elif home_away == "away":
            home_df = pd.DataFrame(columns=home_df.columns)

        if len(home_df) + len(away_df) == 0:
            return f"No matches found for {team}."

        def stats(hdf, adf):
            hw = (hdf["home_goal"] > hdf["away_goal"]).sum() if len(hdf) else 0
            hd = (hdf["home_goal"] == hdf["away_goal"]).sum() if len(hdf) else 0
            hl = (hdf["home_goal"] < hdf["away_goal"]).sum() if len(hdf) else 0
            hgf = hdf["home_goal"].sum() if len(hdf) else 0
            hga = hdf["away_goal"].sum() if len(hdf) else 0
            aw = (adf["away_goal"] > adf["home_goal"]).sum() if len(adf) else 0
            ad = (adf["away_goal"] == adf["home_goal"]).sum() if len(adf) else 0
            al = (adf["away_goal"] < adf["home_goal"]).sum() if len(adf) else 0
            agf = adf["away_goal"].sum() if len(adf) else 0
            aga = adf["home_goal"].sum() if len(adf) else 0
            return (hw, hd, hl, hgf, hga, aw, ad, al, agf, aga)

        hw, hd, hl, hgf, hga, aw, ad, al, agf, aga = stats(home_df, away_df)
        tw = int(hw + aw)
        td = int(hd + ad)
        tl = int(hl + al)
        tgf = int(hgf + agf)
        tga = int(hga + aga)
        total = tw + td + tl
        wr = 100 * tw / total if total else 0

        display = team
        if len(home_df):
            display = home_df.iloc[0]["home_team"]
        elif len(away_df):
            display = away_df.iloc[0]["away_team"]

        lines = [f"Record for {display}:"]
        if competition:
            lines.append(f"Competition: {competition}")
        if season:
            lines.append(f"Season: {season}")
        if home_away != "all":
            lines.append(f"Filter: {home_away} games only")
        lines += [
            "",
            f"Total Matches: {total}",
            f"Wins: {tw} | Draws: {td} | Losses: {tl}",
            f"Win Rate: {wr:.1f}%",
            f"Goals For: {tgf} | Goals Against: {tga} | GD: {tgf - tga:+d}",
        ]
        if home_away == "all":
            lines += [
                "",
                f"Home: {int(hw)}W/{int(hd)}D/{int(hl)}L | GF: {int(hgf)} GA: {int(hga)}",
                f"Away: {int(aw)}W/{int(ad)}D/{int(al)}L | GF: {int(agf)} GA: {int(aga)}",
            ]
        return "\n".join(lines)

    def get_standings(
        self,
        season: int,
        competition: str = "Brasileirão",
    ) -> str:
        """Calculate league standings from match results for a given season."""
        df = self.loader.all_matches.copy()
        df = df[df["season"] == season]
        df = self._filter_competition(df, competition)

        # For Brasileirão, avoid double-counting overlapping sources (2012-2019).
        # Normalize to ASCII before comparing so accented input ("Brasileirão") matches too.
        comp_norm = normalize_team(competition)  # → "brasileirao"
        if "brasileiro" in comp_norm or comp_norm in ("serie a", "brasileirao"):
            if "brasileirao" in df["source"].values:
                df = df[df["source"] == "brasileirao"]
            elif "historico" in df["source"].values:
                df = df[df["source"] == "historico"]

        df = df.dropna(subset=["home_goal", "away_goal"])

        if df.empty:
            return f"No match data found for {season} {competition}."

        teams: dict[str, dict] = {}

        def update(name: str, gf: int, ga: int, result: str) -> None:
            if name not in teams:
                teams[name] = {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
            t = teams[name]
            t["P"] += 1
            t["GF"] += gf
            t["GA"] += ga
            if result == "W":
                t["W"] += 1
                t["Pts"] += 3
            elif result == "D":
                t["D"] += 1
                t["Pts"] += 1
            else:
                t["L"] += 1

        for _, row in df.iterrows():
            hg, ag = int(row["home_goal"]), int(row["away_goal"])
            if hg > ag:
                update(row["home_team"], hg, ag, "W")
                update(row["away_team"], ag, hg, "L")
            elif hg < ag:
                update(row["home_team"], hg, ag, "L")
                update(row["away_team"], ag, hg, "W")
            else:
                update(row["home_team"], hg, ag, "D")
                update(row["away_team"], ag, hg, "D")

        table = sorted(
            teams.items(),
            key=lambda x: (x[1]["Pts"], x[1]["GF"] - x[1]["GA"], x[1]["GF"]),
            reverse=True,
        )

        header = f"{'Pos':>3} | {'Team':<30} | {'P':>3} | {'W':>3} | {'D':>3} | {'L':>3} | {'GF':>4} | {'GA':>4} | {'GD':>4} | {'Pts':>4}"
        lines = [
            f"{season} {competition} Standings (calculated from match data):",
            header,
            "-" * len(header),
        ]
        for pos, (name, s) in enumerate(table, 1):
            gd = s["GF"] - s["GA"]
            lines.append(
                f"{pos:>3} | {name:<30} | {s['P']:>3} | {s['W']:>3} | {s['D']:>3} | {s['L']:>3} |"
                f" {s['GF']:>4} | {s['GA']:>4} | {gd:>+4} | {s['Pts']:>4}"
            )
        return "\n".join(lines)

    def search_players(
        self,
        name: Optional[str] = None,
        nationality: Optional[str] = None,
        club: Optional[str] = None,
        position: Optional[str] = None,
        min_overall: Optional[int] = None,
        max_overall: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """Search FIFA player database with optional filters."""
        df = self.loader.fifa.copy()

        if name:
            n = normalize_team(name)
            df = df[df["name_norm"].str.contains(n, regex=False, na=False)]
        if nationality:
            n = normalize_team(nationality)
            df = df[df["nationality_norm"].str.contains(n, regex=False, na=False)]
        if club:
            n = normalize_team(club)
            df = df[df["club_norm"].str.contains(n, regex=False, na=False)]
        if position:
            df = df[df["Position"].str.upper().str.contains(position.upper(), na=False)]
        if min_overall is not None:
            df = df[df["Overall"] >= min_overall]
        if max_overall is not None:
            df = df[df["Overall"] <= max_overall]

        df = df.sort_values("Overall", ascending=False)
        total = len(df)
        shown = min(total, limit)
        df = df.head(limit)

        if df.empty:
            return "No players found matching the criteria."

        lines = [f"Found {total} players (showing {shown}):"]
        for i, (_, row) in enumerate(df.iterrows(), 1):
            overall = int(row["Overall"]) if pd.notna(row["Overall"]) else "?"
            potential = int(row["Potential"]) if pd.notna(row["Potential"]) else "?"
            age = int(row["Age"]) if pd.notna(row["Age"]) else "?"
            lines.append(
                f"  {i:>2}. {row['Name']} | Overall: {overall} | Potential: {potential} |"
                f" Age: {age} | Pos: {row.get('Position', '?')} |"
                f" Club: {row.get('Club', '?')} | Nationality: {row.get('Nationality', '?')}"
            )
        return "\n".join(lines)

    def get_statistics(
        self,
        stat_type: str,
        competition: Optional[str] = None,
        season: Optional[int] = None,
        limit: int = 10,
    ) -> str:
        """
        Aggregate statistics. stat_type options:
          goals_per_match, biggest_wins, best_home_record, best_away_record, top_teams_goals
        """
        df = self.loader.all_matches.copy()
        df = df.dropna(subset=["home_goal", "away_goal"])

        if competition:
            df = self._filter_competition(df, competition)
        if season:
            df = df[df["season"] == season]

        if df.empty:
            return "No data found for the given criteria."

        st = stat_type.lower()

        if st == "goals_per_match":
            total = len(df)
            avg = (df["home_goal"] + df["away_goal"]).mean()
            home_wr = (df["home_goal"] > df["away_goal"]).mean() * 100
            draw_r = (df["home_goal"] == df["away_goal"]).mean() * 100
            away_wr = (df["home_goal"] < df["away_goal"]).mean() * 100
            lines = ["Match Statistics:"]
            if competition:
                lines.append(f"Competition: {competition}")
            if season:
                lines.append(f"Season: {season}")
            lines += [
                f"Total Matches: {total:,}",
                f"Average Goals per Match: {avg:.2f}",
                f"Home Win Rate: {home_wr:.1f}%",
                f"Draw Rate: {draw_r:.1f}%",
                f"Away Win Rate: {away_wr:.1f}%",
            ]
            return "\n".join(lines)

        elif st == "biggest_wins":
            df = df.copy()
            df["goal_diff"] = (df["home_goal"] - df["away_goal"]).abs()
            df = df.sort_values(
                ["goal_diff", "home_goal", "away_goal"], ascending=[False, False, False]
            ).head(limit)
            lines = ["Biggest wins (by goal difference):"]
            if competition:
                lines.append(f"Competition: {competition}")
            if season:
                lines.append(f"Season: {season}")
            lines.append("")
            for i, (_, row) in enumerate(df.iterrows(), 1):
                date_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "Unknown"
                hg, ag = int(row["home_goal"]), int(row["away_goal"])
                diff = int(row["goal_diff"])
                yr = f" {row['season']}" if pd.notna(row["season"]) else ""
                lines.append(
                    f"  {i:>2}. {date_str}: {row['home_team']} {hg}-{ag} {row['away_team']}"
                    f" (diff: {diff}) | {row['competition']}{yr}"
                )
            return "\n".join(lines)

        elif st in ("best_home_record", "best_away_record"):
            is_home = st == "best_home_record"
            team_col = "home_team" if is_home else "away_team"
            win_mask = (df["home_goal"] > df["away_goal"]) if is_home else (df["away_goal"] > df["home_goal"])
            draw_mask = df["home_goal"] == df["away_goal"]
            loss_mask = ~win_mask & ~draw_mask

            grp = df.groupby(team_col)
            records = []
            for team_name, g in grp:
                p = len(g)
                if p < 5:
                    continue
                w = win_mask[g.index].sum()
                d = draw_mask[g.index].sum()
                l = loss_mask[g.index].sum()
                records.append((team_name, p, int(w), int(d), int(l), 100 * w / p))

            records.sort(key=lambda x: (x[5], x[2]), reverse=True)
            records = records[:limit]
            label = "Home" if is_home else "Away"
            lines = [f"Best {label} Records:"]
            lines.append(
                f"{'Rank':>4} | {'Team':<30} | {'P':>3} | {'W':>3} | {'D':>3} | {'L':>3} | {'Win%':>6}"
            )
            lines.append("-" * 62)
            for i, (name, p, w, d, l, wr) in enumerate(records, 1):
                lines.append(f"  {i:>2} | {name:<30} | {p:>3} | {w:>3} | {d:>3} | {l:>3} | {wr:>5.1f}%")
            return "\n".join(lines)

        elif st == "top_teams_goals":
            home_g = df.groupby("home_team")["home_goal"].sum()
            away_g = df.groupby("away_team")["away_goal"].sum()
            all_teams = set(home_g.index) | set(away_g.index)
            rows = sorted(
                [
                    (t, int(home_g.get(t, 0) + away_g.get(t, 0)), int(home_g.get(t, 0)), int(away_g.get(t, 0)))
                    for t in all_teams
                ],
                key=lambda x: x[1],
                reverse=True,
            )[:limit]
            lines = ["Top Goal-Scoring Teams:"]
            lines.append(f"{'Rank':>4} | {'Team':<30} | {'Total':>6} | {'Home':>5} | {'Away':>5}")
            lines.append("-" * 58)
            for i, (name, total, home, away) in enumerate(rows, 1):
                lines.append(f"  {i:>2} | {name:<30} | {total:>6} | {home:>5} | {away:>5}")
            return "\n".join(lines)

        return (
            f"Unknown stat_type '{stat_type}'. "
            "Available: goals_per_match, biggest_wins, best_home_record, best_away_record, top_teams_goals"
        )
