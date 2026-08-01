use anyhow::{Context, Result};
use chrono::{Datelike, NaiveDate};
use csv::StringRecord;
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, path::Path};
use unicode_normalization::{char::is_combining_mark, UnicodeNormalization};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Match {
    pub date: Option<NaiveDate>,
    pub home: String,
    pub away: String,
    pub home_goals: i32,
    pub away_goals: i32,
    pub competition: String,
    pub season: Option<i32>,
    pub round: Option<String>,
    pub stage: Option<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Player {
    pub id: Option<String>,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: Option<i32>,
    pub potential: Option<i32>,
    pub club: String,
    pub position: String,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct Record {
    pub matches: usize,
    pub wins: usize,
    pub draws: usize,
    pub losses: usize,
    pub goals_for: i32,
    pub goals_against: i32,
}
impl Record {
    pub fn points(&self) -> i32 {
        (self.wins * 3 + self.draws) as i32
    }
    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 * 100.0 / self.matches as f64
        }
    }
}
#[derive(Debug, Clone, Serialize)]
pub struct Standing {
    pub team: String,
    #[serde(flatten)]
    pub record: Record,
    pub points: i32,
}
#[derive(Debug, Clone, Default)]
pub struct Database {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

pub fn normalize(value: &str) -> String {
    let lower: String = value
        .nfd()
        .filter(|c| !is_combining_mark(*c))
        .collect::<String>()
        .to_lowercase();
    let mut s = lower
        .replace("&", " and ")
        .replace("-sp", "")
        .replace("-rj", "")
        .replace("-mg", "")
        .replace("-rs", "")
        .replace("-pr", "")
        .replace("-sc", "")
        .replace("-pe", "")
        .replace("-ba", "")
        .replace("-ce", "")
        .replace("-go", "")
        .replace("-df", "")
        .replace("-es", "")
        .replace("-pa", "");
    s = s
        .chars()
        .map(|c| if c.is_alphanumeric() { c } else { ' ' })
        .collect();
    let words: Vec<&str> = s
        .split_whitespace()
        .filter(|w| {
            !matches!(
                *w,
                "fc" | "sc" | "cr" | "club" | "esporte" | "sport" | "futebol" | "paulista"
            )
        })
        .collect();
    words.join(" ")
}
fn same_team(a: &str, b: &str) -> bool {
    let a = normalize(a);
    let b = normalize(b);
    a == b || (!a.is_empty() && !b.is_empty() && (a.contains(&b) || b.contains(&a)))
}
fn same_competition(actual: &str, requested: &str) -> bool {
    let actual = normalize(actual);
    let requested = normalize(requested);
    actual.contains(&requested)
        || requested.contains(&actual)
        || (requested.contains("brasileirao") && actual.contains("serie a"))
}
fn date(value: &str) -> Option<NaiveDate> {
    ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"]
        .iter()
        .find_map(|f| NaiveDate::parse_from_str(value.trim(), f).ok())
}
fn int(value: Option<&str>) -> i32 {
    value
        .unwrap_or("")
        .trim()
        .parse::<f64>()
        .map(|x| x as i32)
        .unwrap_or(0)
}
fn field<'a>(h: &StringRecord, r: &'a StringRecord, name: &str) -> Option<&'a str> {
    h.iter()
        .position(|x| x.trim_start_matches('\u{feff}').eq_ignore_ascii_case(name))
        .and_then(|i| r.get(i))
}
fn read_csv(path: &Path) -> Result<(StringRecord, Vec<StringRecord>)> {
    let mut rd = csv::ReaderBuilder::new()
        .flexible(true)
        .from_path(path)
        .with_context(|| format!("reading {}", path.display()))?;
    let h = rd.headers()?.clone();
    Ok((h, rd.records().filter_map(Result::ok).collect()))
}
impl Database {
    pub fn load_from_dir(dir: impl AsRef<Path>) -> Result<Self> {
        let d = dir.as_ref();
        let mut db = Self::default();
        db.load_matches(
            &d.join("Brasileirao_Matches.csv"),
            "Brasileirão",
            &[
                ("datetime", "date"),
                ("home_team", "home"),
                ("away_team", "away"),
                ("home_goal", "hg"),
                ("away_goal", "ag"),
                ("season", "season"),
                ("round", "round"),
            ],
        )?;
        db.load_matches(
            &d.join("Brazilian_Cup_Matches.csv"),
            "Copa do Brasil",
            &[
                ("datetime", "date"),
                ("home_team", "home"),
                ("away_team", "away"),
                ("home_goal", "hg"),
                ("away_goal", "ag"),
                ("season", "season"),
                ("round", "round"),
            ],
        )?;
        db.load_matches(
            &d.join("Libertadores_Matches.csv"),
            "Libertadores",
            &[
                ("datetime", "date"),
                ("home_team", "home"),
                ("away_team", "away"),
                ("home_goal", "hg"),
                ("away_goal", "ag"),
                ("season", "season"),
                ("stage", "stage"),
            ],
        )?;
        db.load_matches(
            &d.join("BR-Football-Dataset.csv"),
            "",
            &[
                ("date", "date"),
                ("home", "home"),
                ("away", "away"),
                ("home_goal", "hg"),
                ("away_goal", "ag"),
                ("tournament", "competition"),
            ],
        )?;
        db.load_matches(
            &d.join("novo_campeonato_brasileiro.csv"),
            "Brasileirão",
            &[
                ("Data", "date"),
                ("Equipe_mandante", "home"),
                ("Equipe_visitante", "away"),
                ("Gols_mandante", "hg"),
                ("Gols_visitante", "ag"),
                ("Ano", "season"),
                ("Rodada", "round"),
            ],
        )?;
        db.load_players(&d.join("fifa_data.csv"))?;
        Ok(db)
    }
    fn load_matches(
        &mut self,
        path: &Path,
        default_comp: &str,
        _mapping: &[(&str, &str)],
    ) -> Result<()> {
        let (h, rows) = read_csv(path)?;
        for r in rows {
            let get = |n| field(&h, &r, n).unwrap_or("");
            let home = get("home_team");
            let home = if home.is_empty() { get("home") } else { home };
            let home = if home.is_empty() {
                get("Equipe_mandante")
            } else {
                home
            };
            let away = get("away_team");
            let away = if away.is_empty() { get("away") } else { away };
            let away = if away.is_empty() {
                get("Equipe_visitante")
            } else {
                away
            };
            if home.is_empty() || away.is_empty() {
                continue;
            };
            let raw_date = {
                let x = get("datetime");
                if x.is_empty() {
                    get("date")
                } else {
                    x
                }
            };
            let raw_date = if raw_date.is_empty() {
                get("Data")
            } else {
                raw_date
            };
            let hg = {
                let x = field(&h, &r, "home_goal");
                if x.is_some() {
                    int(x)
                } else {
                    int(field(&h, &r, "Gols_mandante"))
                }
            };
            let ag = {
                let x = field(&h, &r, "away_goal");
                if x.is_some() {
                    int(x)
                } else {
                    int(field(&h, &r, "Gols_visitante"))
                }
            };
            let season: Option<i32> = {
                let x = get("season");
                if x.is_empty() {
                    get("Ano")
                } else {
                    x
                }
            }
            .parse()
            .ok();
            let season = season.or_else(|| date(raw_date).map(|d| d.year()));
            let comp = {
                let x = get("tournament");
                if x.is_empty() {
                    default_comp.to_string()
                } else {
                    x.to_string()
                }
            };
            self.matches.push(Match {
                date: date(raw_date),
                home: home.into(),
                away: away.into(),
                home_goals: hg,
                away_goals: ag,
                competition: comp,
                season,
                round: field(&h, &r, "round")
                    .or_else(|| field(&h, &r, "Rodada"))
                    .filter(|x| !x.is_empty())
                    .map(str::to_string),
                stage: field(&h, &r, "stage")
                    .filter(|x| !x.is_empty())
                    .map(str::to_string),
            });
        }
        Ok(())
    }
    fn load_players(&mut self, path: &Path) -> Result<()> {
        let (h, rows) = read_csv(path)?;
        for r in rows {
            let g = |n| field(&h, &r, n).unwrap_or("");
            let name = g("Name");
            if !name.is_empty() {
                self.players.push(Player {
                    id: Some(g("ID").to_string()).filter(|x| !x.is_empty()),
                    name: name.into(),
                    age: g("Age").parse().ok(),
                    nationality: g("Nationality").into(),
                    overall: g("Overall").parse().ok(),
                    potential: g("Potential").parse().ok(),
                    club: g("Club").into(),
                    position: g("Position").into(),
                });
            }
        }
        Ok(())
    }
    pub fn matches(
        &self,
        team: Option<&str>,
        opponent: Option<&str>,
        competition: Option<&str>,
        season: Option<i32>,
        from: Option<NaiveDate>,
        to: Option<NaiveDate>,
        limit: usize,
    ) -> Vec<Match> {
        let mut v: Vec<_> = self
            .matches
            .iter()
            .filter(|m| {
                team.map_or(true, |t| same_team(&m.home, t) || same_team(&m.away, t))
                    && opponent.map_or(true, |t| same_team(&m.home, t) || same_team(&m.away, t))
                    && competition.map_or(true, |c| same_competition(&m.competition, c))
                    && season.map_or(true, |s| m.season == Some(s))
                    && from.map_or(true, |d| m.date.map_or(false, |x| x >= d))
                    && to.map_or(true, |d| m.date.map_or(false, |x| x <= d))
            })
            .cloned()
            .collect();
        v.sort_by_key(|m| std::cmp::Reverse(m.date));
        v.truncate(limit);
        v
    }
    pub fn team_record(
        &self,
        team: &str,
        season: Option<i32>,
        competition: Option<&str>,
        home_only: bool,
    ) -> Record {
        let mut out = Record::default();
        for m in self.matches(
            Some(team),
            None,
            competition,
            season,
            None,
            None,
            usize::MAX,
        ) {
            let home = same_team(&m.home, team);
            if home_only && !home {
                continue;
            }
            let (gf, ga) = if home {
                (m.home_goals, m.away_goals)
            } else {
                (m.away_goals, m.home_goals)
            };
            out.matches += 1;
            out.goals_for += gf;
            out.goals_against += ga;
            if gf > ga {
                out.wins += 1
            } else if gf < ga {
                out.losses += 1
            } else {
                out.draws += 1
            }
        }
        out
    }
    pub fn head_to_head(
        &self,
        a: &str,
        b: &str,
        season: Option<i32>,
        competition: Option<&str>,
    ) -> (Record, Record) {
        let ms = self.matches(
            Some(a),
            Some(b),
            competition,
            season,
            None,
            None,
            usize::MAX,
        );
        let mut ar = Record::default();
        let mut br = Record::default();
        for m in ms {
            let ah = same_team(&m.home, a);
            let (ag, bg) = if ah {
                (m.home_goals, m.away_goals)
            } else {
                (m.away_goals, m.home_goals)
            };
            for (r, gf, ga) in [(&mut ar, ag, bg), (&mut br, bg, ag)] {
                r.matches += 1;
                r.goals_for += gf;
                r.goals_against += ga;
                if gf > ga {
                    r.wins += 1
                } else if gf < ga {
                    r.losses += 1
                } else {
                    r.draws += 1
                }
            }
        }
        (ar, br)
    }
    pub fn standings(&self, season: i32, competition: Option<&str>) -> Vec<Standing> {
        let mut map: BTreeMap<String, Record> = BTreeMap::new();
        for m in self.matches(
            None,
            None,
            competition,
            Some(season),
            None,
            None,
            usize::MAX,
        ) {
            for (name, gf, ga) in [
                (&m.home, m.home_goals, m.away_goals),
                (&m.away, m.away_goals, m.home_goals),
            ] {
                let r = map.entry(name.clone()).or_default();
                r.matches += 1;
                r.goals_for += gf;
                r.goals_against += ga;
                if gf > ga {
                    r.wins += 1
                } else if gf < ga {
                    r.losses += 1
                } else {
                    r.draws += 1
                }
            }
        }
        let mut v: Vec<_> = map
            .into_iter()
            .map(|(team, record)| Standing {
                points: record.points(),
                team,
                record,
            })
            .collect();
        v.sort_by(|a, b| {
            b.points
                .cmp(&a.points)
                .then(
                    (b.record.goals_for - b.record.goals_against)
                        .cmp(&(a.record.goals_for - a.record.goals_against)),
                )
                .then(b.record.goals_for.cmp(&a.record.goals_for))
        });
        v
    }
    pub fn players(
        &self,
        name: Option<&str>,
        nationality: Option<&str>,
        club: Option<&str>,
        position: Option<&str>,
        limit: usize,
    ) -> Vec<Player> {
        let mut p: Vec<_> = self
            .players
            .iter()
            .filter(|p| {
                name.map_or(true, |x| normalize(&p.name).contains(&normalize(x)))
                    && nationality
                        .map_or(true, |x| normalize(&p.nationality).contains(&normalize(x)))
                    && club.map_or(true, |x| normalize(&p.club).contains(&normalize(x)))
                    && position.map_or(true, |x| normalize(&p.position).contains(&normalize(x)))
            })
            .cloned()
            .collect();
        p.sort_by_key(|p| std::cmp::Reverse(p.overall.unwrap_or(0)));
        p.truncate(limit);
        p
    }
}
pub fn format_match(m: &Match) -> String {
    format!(
        "{}: {} {}-{} {} ({})",
        m.date
            .map(|d| d.to_string())
            .unwrap_or_else(|| "unknown date".into()),
        m.home,
        m.home_goals,
        m.away_goals,
        m.away,
        m.competition
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn normalizes_accents_and_suffixes() {
        assert!(same_team("São Paulo FC", "Sao Paulo-SP"));
        assert!(same_team(
            "Sport Club Corinthians Paulista",
            "Corinthians-SP"
        ));
        assert!(same_competition("Serie A", "Brasileirão"));
    }
    #[test]
    fn record_and_head_to_head() {
        let mut d = Database::default();
        d.matches = vec![
            Match {
                date: None,
                home: "Flamengo-RJ".into(),
                away: "Fluminense-RJ".into(),
                home_goals: 2,
                away_goals: 1,
                competition: "Brasileirão".into(),
                season: Some(2023),
                round: None,
                stage: None,
            },
            Match {
                date: None,
                home: "Fluminense".into(),
                away: "Flamengo".into(),
                home_goals: 0,
                away_goals: 0,
                competition: "Brasileirão".into(),
                season: Some(2023),
                round: None,
                stage: None,
            },
        ];
        let r = d.team_record("Flamengo", Some(2023), None, false);
        assert_eq!((r.matches, r.wins, r.draws, r.goals_for), (2, 1, 1, 2));
        let (a, b) = d.head_to_head("Flamengo", "Fluminense", None, None);
        assert_eq!((a.wins, b.losses), (1, 1));
    }

    #[test]
    fn loads_all_provided_sources() {
        let db = Database::load_from_dir("data/kaggle").expect("provided data loads");
        assert!(db.matches.len() > 20_000);
        assert!(db.players.len() > 18_000);
        assert!(!db
            .matches(Some("Flamengo"), None, None, Some(2023), None, None, 5)
            .is_empty());
    }
}
