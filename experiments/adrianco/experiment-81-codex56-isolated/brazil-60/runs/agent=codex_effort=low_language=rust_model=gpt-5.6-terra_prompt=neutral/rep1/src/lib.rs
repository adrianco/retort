use csv::StringRecord;
use serde::Serialize;
use std::{
    collections::{BTreeMap, HashSet},
    error::Error,
    path::Path,
};

#[derive(Clone, Debug, Serialize)]
pub struct Match {
    pub date: String,
    pub competition: String,
    pub season: Option<i32>,
    pub round: Option<String>,
    pub home: String,
    pub away: String,
    pub home_goals: i32,
    pub away_goals: i32,
}
#[derive(Clone, Debug, Serialize)]
pub struct Player {
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: Option<i32>,
    pub potential: Option<i32>,
    pub club: String,
    pub position: String,
}
#[derive(Clone, Debug, Serialize, Default)]
pub struct Record {
    pub matches: usize,
    pub wins: usize,
    pub draws: usize,
    pub losses: usize,
    pub goals_for: i32,
    pub goals_against: i32,
    pub win_rate: f64,
}
#[derive(Clone, Debug, Serialize, Default)]
pub struct AggregateStats {
    pub matches: usize,
    pub total_goals: i32,
    pub average_goals_per_match: f64,
    pub home_wins: usize,
    pub draws: usize,
    pub away_wins: usize,
    pub home_win_rate: f64,
    pub biggest_wins: Vec<Match>,
}
#[derive(Default)]
pub struct Database {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

fn field<'a>(headers: &StringRecord, row: &'a StringRecord, name: &str) -> &'a str {
    headers
        .iter()
        .position(|h| h.trim_start_matches('\u{feff}').eq_ignore_ascii_case(name))
        .and_then(|i| row.get(i))
        .unwrap_or("")
        .trim()
}
fn int(s: &str) -> Option<i32> {
    s.trim()
        .parse()
        .ok()
        .or_else(|| s.trim().parse::<f64>().ok().map(|n| n as i32))
}
pub fn normalize_team(s: &str) -> String {
    let lower = s
        .trim()
        .to_lowercase()
        .replace('ã', "a")
        .replace('á', "a")
        .replace('à', "a")
        .replace('â', "a")
        .replace('é', "e")
        .replace('ê', "e")
        .replace('í', "i")
        .replace('ó', "o")
        .replace('ô', "o")
        .replace('õ', "o")
        .replace('ú', "u")
        .replace('ç', "c");
    // Preserve state information long enough to disambiguate the two
    // Atléticos before generic state-suffix removal below.
    if lower.ends_with("-pr") && (lower.starts_with("atletico") || lower.starts_with("athletico")) {
        return "athletico paranaense".into();
    }
    if lower.ends_with("-mg") && lower.starts_with("atletico") {
        return "atletico mineiro".into();
    }
    if lower.ends_with("-mg") && lower.starts_with("america") {
        return "america mineiro".into();
    }
    let base = lower
        .rsplit_once('-')
        .filter(|(_, suffix)| suffix.len() == 2 && suffix.chars().all(|c| c.is_ascii_alphabetic()))
        .map(|(x, _)| x)
        .unwrap_or(&lower);
    let cleaned: String = base
        .chars()
        .map(|c| {
            if c.is_alphanumeric() || c.is_whitespace() {
                c
            } else {
                ' '
            }
        })
        .collect();
    let normalized = cleaned
        .replace("sport club ", "")
        .replace("football club", "")
        .replace("esporte clube", "")
        .replace("clube de regatas", "")
        .replace("fc", "")
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ");
    // These are the same clubs under the abbreviations used by the sources.
    match normalized.as_str() {
        "atletico"
        | "atletico pr"
        | "atletico paranaense"
        | "athletico"
        | "athletico paranaense" => "athletico paranaense".into(),
        "atletico mg" | "atletico mineiro" => "atletico mineiro".into(),
        "america mg" | "america mineiro" => "america mineiro".into(),
        "botafogo rj" => "botafogo".into(),
        "vasco da gama" | "vasco da gama rj" => "vasco".into(),
        "ec bahia" | "esporte clube bahia" => "bahia".into(),
        other => other.into(),
    }
}
fn canonical_date(s: &str) -> String {
    let s = s.trim();
    if let Some((d, m, y)) = s
        .split('/')
        .collect::<Vec<_>>()
        .as_slice()
        .get(0..3)
        .and_then(|x| Some((x[0], x[1], x[2])))
    {
        return format!("{y}-{m:0>2}-{d:0>2}");
    };
    s.get(0..10).unwrap_or(s).to_string()
}
fn canonical_competition(s: &str) -> String {
    let key = s.to_lowercase();
    if key.contains("serie a") || key.contains("brasileir") {
        "Brasileirão".into()
    } else if key.contains("copa do brasil") {
        "Copa do Brasil".into()
    } else if key.contains("libertadores") {
        "Libertadores".into()
    } else {
        s.into()
    }
}

// Days since a fixed epoch.  This deliberately avoids a date crate while still
// treating month/year boundaries correctly when feeds differ by UTC offset.
fn date_day(date: &str) -> Option<i64> {
    let mut it = date.split('-');
    let (y, m, d) = (
        it.next()?.parse::<i64>().ok()?,
        it.next()?.parse::<i64>().ok()?,
        it.next()?.parse::<i64>().ok()?,
    );
    if !(1..=12).contains(&m) || !(1..=31).contains(&d) {
        return None;
    }
    let y = y - if m <= 2 { 1 } else { 0 };
    let era = if y >= 0 { y } else { y - 399 } / 400;
    let yoe = y - era * 400;
    let mp = m + if m > 2 { -3 } else { 9 };
    let doy = (153 * mp + 2) / 5 + d - 1;
    Some(era * 146097 + yoe * 365 + yoe / 4 - yoe / 100 + doy)
}
impl Database {
    pub fn load(dir: impl AsRef<Path>) -> Result<Self, Box<dyn Error>> {
        let d = dir.as_ref();
        let mut db = Self::default();
        db.load_matches(
            &d.join("Brasileirao_Matches.csv"),
            "Brasileirão",
            "datetime",
            "home_team",
            "away_team",
            "home_goal",
            "away_goal",
            "season",
            Some("round"),
        )?;
        db.load_matches(
            &d.join("Brazilian_Cup_Matches.csv"),
            "Copa do Brasil",
            "datetime",
            "home_team",
            "away_team",
            "home_goal",
            "away_goal",
            "season",
            Some("round"),
        )?;
        db.load_matches(
            &d.join("Libertadores_Matches.csv"),
            "Libertadores",
            "datetime",
            "home_team",
            "away_team",
            "home_goal",
            "away_goal",
            "season",
            Some("stage"),
        )?;
        db.load_matches(
            &d.join("BR-Football-Dataset.csv"),
            "Extended statistics",
            "date",
            "home",
            "away",
            "home_goal",
            "away_goal",
            "",
            Some("tournament"),
        )?;
        db.load_matches(
            &d.join("novo_campeonato_brasileiro.csv"),
            "Brasileirão historical",
            "Data",
            "Equipe_mandante",
            "Equipe_visitante",
            "Gols_mandante",
            "Gols_visitante",
            "Ano",
            Some("Rodada"),
        )?;
        let mut r = csv::ReaderBuilder::new()
            .flexible(true)
            .from_path(d.join("fifa_data.csv"))?;
        let h = r.headers()?.clone();
        for row in r.records().flatten() {
            db.players.push(Player {
                name: field(&h, &row, "Name").into(),
                age: int(field(&h, &row, "Age")),
                nationality: field(&h, &row, "Nationality").into(),
                overall: int(field(&h, &row, "Overall")),
                potential: int(field(&h, &row, "Potential")),
                club: field(&h, &row, "Club").into(),
                position: field(&h, &row, "Position").into(),
            });
        }
        db.deduplicate_matches();
        Ok(db)
    }

    /// Reconcile overlapping Kaggle feeds.  The dedicated competition files
    /// are loaded first and therefore win; the extended and historical feeds
    /// fill gaps only.  A one-day tolerance accounts for local versus UTC
    /// kick-off dates in the source files.
    fn deduplicate_matches(&mut self) {
        let mut unique: Vec<Match> = Vec::with_capacity(self.matches.len());
        let mut seen = HashSet::with_capacity(self.matches.len());
        'candidate: for m in self.matches.drain(..) {
            let day = date_day(&m.date);
            let base = format!(
                "{}\u{1f}{:?}\u{1f}{}\u{1f}{}",
                m.competition,
                m.season,
                normalize_team(&m.home),
                normalize_team(&m.away),
                // Scores are intentionally not part of the key.  A few
                // overlapping feeds disagree on corrections, but still
                // describe the same fixture.
            );
            if let Some(day) = day {
                for candidate_day in day - 1..=day + 1 {
                    if seen.contains(&format!("{base}\u{1f}{candidate_day}")) {
                        continue 'candidate;
                    }
                }
                seen.insert(format!("{base}\u{1f}{day}"));
            } else {
                // Malformed dates cannot be safely reconciled by proximity.
                // Retain one exact-date fixture instead.
                let key = format!("{base}\u{1f}{}", m.date);
                if !seen.insert(key) {
                    continue;
                }
            }
            unique.push(m);
        }
        self.matches = unique;
    }
    fn load_matches(
        &mut self,
        path: &Path,
        competition: &str,
        date: &str,
        home: &str,
        away: &str,
        hg: &str,
        ag: &str,
        season: &str,
        round: Option<&str>,
    ) -> Result<(), Box<dyn Error>> {
        let mut r = csv::ReaderBuilder::new().flexible(true).from_path(path)?;
        let h = r.headers()?.clone();
        for row in r.records().flatten() {
            if let (Some(x), Some(y)) = (int(field(&h, &row, hg)), int(field(&h, &row, ag))) {
                let raw_date = field(&h, &row, date);
                self.matches.push(Match {
                    date: canonical_date(raw_date),
                    competition: if competition == "Extended statistics" {
                        canonical_competition(field(&h, &row, "tournament"))
                    } else {
                        canonical_competition(competition)
                    },
                    season: int(field(&h, &row, season))
                        .or_else(|| raw_date.get(0..4).and_then(|x| x.parse().ok())),
                    round: round
                        .map(|x| field(&h, &row, x).to_string())
                        .filter(|x| !x.is_empty()),
                    home: field(&h, &row, home).into(),
                    away: field(&h, &row, away).into(),
                    home_goals: x,
                    away_goals: y,
                });
            }
        }
        Ok(())
    }
    pub fn search_matches(
        &self,
        team: Option<&str>,
        opponent: Option<&str>,
        competition: Option<&str>,
        season: Option<i32>,
        from: Option<&str>,
        to: Option<&str>,
        limit: usize,
    ) -> Vec<Match> {
        let t = team.map(normalize_team);
        let o = opponent.map(normalize_team);
        let mut v: Vec<_> = self
            .matches
            .iter()
            .filter(|m| {
                t.as_ref().map_or(true, |q| {
                    normalize_team(&m.home).contains(q) || normalize_team(&m.away).contains(q)
                }) && o.as_ref().map_or(true, |q| {
                    normalize_team(&m.home).contains(q) || normalize_team(&m.away).contains(q)
                }) && competition.map_or(true, |q| {
                    m.competition.to_lowercase().contains(&q.to_lowercase())
                }) && season.map_or(true, |q| m.season == Some(q))
                    && from.map_or(true, |q| m.date >= canonical_date(q))
                    && to.map_or(true, |q| m.date <= canonical_date(q))
            })
            .cloned()
            .collect();
        v.sort_by(|a, b| b.date.cmp(&a.date));
        v.truncate(limit);
        v
    }
    pub fn team_record(
        &self,
        team: &str,
        season: Option<i32>,
        competition: Option<&str>,
        venue: Option<&str>,
    ) -> Record {
        let q = normalize_team(team);
        let mut r = Record::default();
        for m in &self.matches {
            let home = normalize_team(&m.home).contains(&q);
            let away = normalize_team(&m.away).contains(&q);
            if !(home || away)
                || season.map_or(false, |x| m.season != Some(x))
                || competition.map_or(false, |x| {
                    !m.competition.to_lowercase().contains(&x.to_lowercase())
                })
                || venue.map_or(false, |v| v == "home" && !home || v == "away" && !away)
            {
                continue;
            }
            let (gf, ga) = if home {
                (m.home_goals, m.away_goals)
            } else {
                (m.away_goals, m.home_goals)
            };
            r.matches += 1;
            r.goals_for += gf;
            r.goals_against += ga;
            if gf > ga {
                r.wins += 1
            } else if gf == ga {
                r.draws += 1
            } else {
                r.losses += 1
            }
        }
        r.win_rate = if r.matches == 0 {
            0.0
        } else {
            r.wins as f64 * 100.0 / r.matches as f64
        };
        r
    }
    pub fn standings(&self, season: i32, competition: &str) -> Vec<(String, Record, i32)> {
        let mut all: BTreeMap<String, Record> = BTreeMap::new();
        for m in &self.matches {
            if m.season != Some(season)
                || !m
                    .competition
                    .to_lowercase()
                    .contains(&competition.to_lowercase())
            {
                continue;
            }
            for (team, gf, ga) in [
                (&m.home, m.home_goals, m.away_goals),
                (&m.away, m.away_goals, m.home_goals),
            ] {
                // The key must be canonical: otherwise Flamengo-RJ and
                // Flamengo (or Atlético-PR/Athletico Paranaense) become
                // separate table rows.
                let r = all.entry(normalize_team(team)).or_default();
                r.matches += 1;
                r.goals_for += gf;
                r.goals_against += ga;
                if gf > ga {
                    r.wins += 1
                } else if gf == ga {
                    r.draws += 1
                } else {
                    r.losses += 1
                }
            }
        }
        let mut v: Vec<_> = all
            .into_iter()
            .map(|(t, r)| {
                let p = r.wins as i32 * 3 + r.draws as i32;
                (t, r, p)
            })
            .collect();
        v.sort_by(|a, b| {
            b.2.cmp(&a.2)
                .then((b.1.goals_for - b.1.goals_against).cmp(&(a.1.goals_for - a.1.goals_against)))
                .then(b.1.goals_for.cmp(&a.1.goals_for))
        });
        v
    }
    pub fn aggregate_stats(
        &self,
        competition: Option<&str>,
        season: Option<i32>,
        biggest_wins_limit: usize,
    ) -> AggregateStats {
        let mut stats = AggregateStats::default();
        let mut matches: Vec<Match> = self
            .matches
            .iter()
            .filter(|m| {
                season.map_or(true, |year| m.season == Some(year))
                    && competition.map_or(true, |q| {
                        m.competition.to_lowercase().contains(&q.to_lowercase())
                    })
            })
            .cloned()
            .collect();
        for m in &matches {
            stats.matches += 1;
            stats.total_goals += m.home_goals + m.away_goals;
            if m.home_goals > m.away_goals {
                stats.home_wins += 1;
            } else if m.home_goals == m.away_goals {
                stats.draws += 1;
            } else {
                stats.away_wins += 1;
            }
        }
        if stats.matches > 0 {
            stats.average_goals_per_match = stats.total_goals as f64 / stats.matches as f64;
            stats.home_win_rate = stats.home_wins as f64 * 100.0 / stats.matches as f64;
        }
        matches.sort_by(|a, b| {
            (b.home_goals - b.away_goals)
                .abs()
                .cmp(&(a.home_goals - a.away_goals).abs())
                .then_with(|| b.date.cmp(&a.date))
        });
        matches.truncate(biggest_wins_limit);
        stats.biggest_wins = matches;
        stats
    }
    pub fn search_players(
        &self,
        name: Option<&str>,
        nationality: Option<&str>,
        club: Option<&str>,
        position: Option<&str>,
        limit: usize,
    ) -> Vec<Player> {
        let mut v: Vec<_> = self
            .players
            .iter()
            .filter(|p| {
                name.map_or(true, |x| p.name.to_lowercase().contains(&x.to_lowercase()))
                    && nationality.map_or(true, |x| p.nationality.eq_ignore_ascii_case(x))
                    && club.map_or(true, |x| p.club.to_lowercase().contains(&x.to_lowercase()))
                    && position.map_or(true, |x| p.position.eq_ignore_ascii_case(x))
            })
            .cloned()
            .collect();
        v.sort_by_key(|p| std::cmp::Reverse(p.overall.unwrap_or(0)));
        v.truncate(limit);
        v
    }
    pub fn head_to_head_records(
        &self,
        team: &str,
        opponent: &str,
        season: Option<i32>,
    ) -> (Record, Record) {
        let a = normalize_team(team);
        let b = normalize_team(opponent);
        let (mut ar, mut br) = (Record::default(), Record::default());
        for m in &self.matches {
            let ah = normalize_team(&m.home).contains(&a);
            let bh = normalize_team(&m.home).contains(&b);
            let aa = normalize_team(&m.away).contains(&a);
            let ba = normalize_team(&m.away).contains(&b);
            if season.map_or(false, |x| m.season != Some(x)) || !((ah && ba) || (bh && aa)) {
                continue;
            }
            let (a_g, a_o, b_g, b_o) = if ah {
                (m.home_goals, m.away_goals, m.away_goals, m.home_goals)
            } else {
                (m.away_goals, m.home_goals, m.home_goals, m.away_goals)
            };
            for (r, g, o) in [(&mut ar, a_g, a_o), (&mut br, b_g, b_o)] {
                r.matches += 1;
                r.goals_for += g;
                r.goals_against += o;
                if g > o {
                    r.wins += 1
                } else if g == o {
                    r.draws += 1
                } else {
                    r.losses += 1
                };
                r.win_rate = r.wins as f64 * 100.0 / r.matches as f64
            }
        }
        (ar, br)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn normalizes_variations() {
        assert_eq!(normalize_team("São Paulo-SP"), "sao paulo");
        assert_eq!(normalize_team("Flamengo-RJ"), "flamengo");
    }
    #[test]
    fn record_counts_results() {
        let mut d = Database::default();
        d.matches = vec![
            Match {
                date: "2023-01-01".into(),
                competition: "X".into(),
                season: Some(2023),
                round: None,
                home: "Palmeiras-SP".into(),
                away: "A".into(),
                home_goals: 2,
                away_goals: 0,
            },
            Match {
                date: "2023-01-02".into(),
                competition: "X".into(),
                season: Some(2023),
                round: None,
                home: "A".into(),
                away: "Palmeiras".into(),
                home_goals: 1,
                away_goals: 1,
            },
        ];
        let r = d.team_record("Palmeiras", Some(2023), None, None);
        assert_eq!((r.matches, r.wins, r.draws, r.goals_for), (2, 1, 1, 3));
    }
    #[test]
    fn loads_all_provided_data_and_finds_records() {
        let d = Database::load("data/kaggle").unwrap();
        // Five feeds overlap substantially; fixture reconciliation keeps each
        // match once while still loading every supplied file.
        assert!(d.matches.len() > 10_000);
        assert!(d.players.len() > 18_000);
        assert!(!d
            .search_matches(Some("Flamengo"), None, None, None, None, None, 5)
            .is_empty());
        assert!(!d
            .search_players(Some("Neymar"), None, None, None, 5)
            .is_empty());
    }
    #[test]
    fn standings_reconcile_sources_and_team_variants() {
        let d = Database::load("data/kaggle").unwrap();
        let table = d.standings(2019, "Brasileirão");
        assert_eq!(table.len(), 20);
        let flamengo = table
            .iter()
            .find(|(team, _, _)| team == "flamengo")
            .unwrap();
        assert_eq!(
            (
                flamengo.1.matches,
                flamengo.1.wins,
                flamengo.1.draws,
                flamengo.1.losses,
                flamengo.2
            ),
            (38, 28, 6, 4, 90)
        );
    }
    #[test]
    fn aggregate_statistics_are_calculated() {
        let mut d = Database::default();
        d.matches = vec![
            Match {
                date: "2020-01-01".into(),
                competition: "X".into(),
                season: Some(2020),
                round: None,
                home: "A".into(),
                away: "B".into(),
                home_goals: 3,
                away_goals: 1,
            },
            Match {
                date: "2020-01-02".into(),
                competition: "X".into(),
                season: Some(2020),
                round: None,
                home: "B".into(),
                away: "A".into(),
                home_goals: 0,
                away_goals: 0,
            },
        ];
        let s = d.aggregate_stats(Some("X"), Some(2020), 1);
        assert_eq!(
            (s.matches, s.total_goals, s.home_wins, s.draws),
            (2, 4, 1, 1)
        );
        assert_eq!(s.biggest_wins[0].home_goals, 3);
    }
    #[test]
    fn query_filters_and_head_to_head_cover_match_and_player_lookups() {
        let mut d = Database::default();
        d.matches = vec![
            Match {
                date: "2023-06-01".into(),
                competition: "Brasileirão".into(),
                season: Some(2023),
                round: Some("1".into()),
                home: "Flamengo-RJ".into(),
                away: "Fluminense-RJ".into(),
                home_goals: 2,
                away_goals: 1,
            },
            Match {
                date: "2022-06-01".into(),
                competition: "Copa do Brasil".into(),
                season: Some(2022),
                round: Some("final".into()),
                home: "Fluminense".into(),
                away: "Flamengo".into(),
                home_goals: 0,
                away_goals: 0,
            },
        ];
        d.players.push(Player {
            name: "Gabriel Barbosa".into(),
            age: Some(26),
            nationality: "Brazil".into(),
            overall: Some(83),
            potential: Some(84),
            club: "Flamengo".into(),
            position: "ST".into(),
        });
        let matches = d.search_matches(
            Some("Flamengo"),
            Some("Fluminense"),
            Some("Brasileirão"),
            Some(2023),
            Some("2023-01-01"),
            Some("2023-12-31"),
            10,
        );
        assert_eq!(matches.len(), 1);
        let (flamengo, _fluminense) = d.head_to_head_records("Flamengo", "Fluminense", None);
        assert_eq!((flamengo.matches, flamengo.wins, flamengo.draws), (2, 1, 1));
        let players = d.search_players(
            Some("Gabriel"),
            Some("Brazil"),
            Some("Flamengo"),
            Some("ST"),
            10,
        );
        assert_eq!(players[0].overall, Some(83));
    }
}
