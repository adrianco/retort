use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::path::Path;
use unicode_normalization::UnicodeNormalization;

pub type Result<T> = std::result::Result<T, Box<dyn Error + Send + Sync>>;

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct Match {
    pub competition: String,
    pub date: String,
    pub season: Option<i32>,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub home_team: String,
    pub away_team: String,
    pub home_goals: i32,
    pub away_goals: i32,
    pub stadium: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct Player {
    pub id: String,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: Option<i32>,
    pub potential: Option<i32>,
    pub club: String,
    pub position: String,
}

#[derive(Default, Clone)]
pub struct Database {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
}

#[derive(Default, Serialize)]
pub struct Record {
    pub matches: usize,
    pub wins: usize,
    pub draws: usize,
    pub losses: usize,
    pub goals_for: i32,
    pub goals_against: i32,
}

impl Database {
    pub fn load(data_dir: impl AsRef<Path>) -> Result<Self> {
        let d = data_dir.as_ref();
        let mut db = Self::default();
        db.load_standard(
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
        db.load_standard(
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
        db.load_standard(
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
        db.load_extended(&d.join("BR-Football-Dataset.csv"))?;
        db.load_historical(&d.join("novo_campeonato_brasileiro.csv"))?;
        db.load_players(&d.join("fifa_data.csv"))?;
        Ok(db)
    }
    #[allow(clippy::too_many_arguments)]
    fn load_standard(
        &mut self,
        path: &Path,
        competition: &str,
        date: &str,
        home: &str,
        away: &str,
        hg: &str,
        ag: &str,
        season: &str,
        extra: Option<&str>,
    ) -> Result<()> {
        let mut r = csv::Reader::from_path(path)?;
        let headers = r.headers()?.clone();
        for row in r.records() {
            let x = row?;
            self.matches.push(Match {
                competition: competition.into(),
                date: date_value(get(&headers, &x, date)),
                season: num(&get(&headers, &x, season)),
                round: extra.and_then(|e| {
                    let v = get(&headers, &x, e);
                    if e == "round" {
                        Some(v)
                    } else {
                        None
                    }
                }),
                stage: extra.and_then(|e| {
                    let v = get(&headers, &x, e);
                    if e == "stage" && !v.is_empty() {
                        Some(v)
                    } else {
                        None
                    }
                }),
                home_team: get(&headers, &x, home),
                away_team: get(&headers, &x, away),
                home_goals: num(&get(&headers, &x, hg)).unwrap_or(0),
                away_goals: num(&get(&headers, &x, ag)).unwrap_or(0),
                stadium: None,
            });
        }
        Ok(())
    }
    fn load_extended(&mut self, path: &Path) -> Result<()> {
        let mut r = csv::Reader::from_path(path)?;
        let h = r.headers()?.clone();
        for row in r.records() {
            let x = row?;
            self.matches.push(Match {
                competition: get(&h, &x, "tournament"),
                date: date_value(get(&h, &x, "date")),
                season: num(get(&h, &x, "date").get(0..4).unwrap_or("")),
                round: None,
                stage: None,
                home_team: get(&h, &x, "home"),
                away_team: get(&h, &x, "away"),
                home_goals: num(&get(&h, &x, "home_goal")).unwrap_or(0),
                away_goals: num(&get(&h, &x, "away_goal")).unwrap_or(0),
                stadium: None,
            });
        }
        Ok(())
    }
    fn load_historical(&mut self, path: &Path) -> Result<()> {
        let mut r = csv::Reader::from_path(path)?;
        let h = r.headers()?.clone();
        for row in r.records() {
            let x = row?;
            self.matches.push(Match {
                competition: "Brasileirão".into(),
                date: date_value(get(&h, &x, "Data")),
                season: num(&get(&h, &x, "Ano")),
                round: Some(get(&h, &x, "Rodada")),
                stage: None,
                home_team: get(&h, &x, "Equipe_mandante"),
                away_team: get(&h, &x, "Equipe_visitante"),
                home_goals: num(&get(&h, &x, "Gols_mandante")).unwrap_or(0),
                away_goals: num(&get(&h, &x, "Gols_visitante")).unwrap_or(0),
                stadium: some(get(&h, &x, "Arena")),
            });
        }
        Ok(())
    }
    fn load_players(&mut self, path: &Path) -> Result<()> {
        let mut r = csv::Reader::from_path(path)?;
        let h = r.headers()?.clone();
        for row in r.records() {
            let x = row?;
            self.players.push(Player {
                id: get(&h, &x, "ID"),
                name: get(&h, &x, "Name"),
                age: num(&get(&h, &x, "Age")),
                nationality: get(&h, &x, "Nationality"),
                overall: num(&get(&h, &x, "Overall")),
                potential: num(&get(&h, &x, "Potential")),
                club: get(&h, &x, "Club"),
                position: get(&h, &x, "Position"),
            });
        }
        Ok(())
    }
    #[allow(clippy::too_many_arguments)]
    pub fn find_matches(
        &self,
        team: Option<&str>,
        opponent: Option<&str>,
        competition: Option<&str>,
        season: Option<i32>,
        from: Option<&str>,
        to: Option<&str>,
        limit: usize,
    ) -> Vec<Match> {
        let mut v: Vec<_> = self
            .matches
            .iter()
            .filter(|m| {
                team.is_none_or(|q| same_team(&m.home_team, q) || same_team(&m.away_team, q))
            })
            .filter(|m| {
                opponent.is_none_or(|q| same_team(&m.home_team, q) || same_team(&m.away_team, q))
            })
            .filter(|m| competition.is_none_or(|q| contains(&m.competition, q)))
            .filter(|m| season.is_none_or(|s| m.season == Some(s)))
            .filter(|m| from.is_none_or(|d| m.date.as_str() >= d))
            .filter(|m| to.is_none_or(|d| m.date.as_str() <= d))
            .cloned()
            .collect();
        v.sort_by(|a, b| b.date.cmp(&a.date));
        v.truncate(limit);
        v
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
            .filter(|p| name.is_none_or(|q| contains(&p.name, q)))
            .filter(|p| nationality.is_none_or(|q| contains(&p.nationality, q)))
            .filter(|p| club.is_none_or(|q| contains(&p.club, q)))
            .filter(|p| position.is_none_or(|q| contains(&p.position, q)))
            .cloned()
            .collect();
        v.sort_by_key(|p| std::cmp::Reverse(p.overall.unwrap_or(0)));
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
        let mut r = Record::default();
        for m in self.find_matches(
            Some(team),
            None,
            competition,
            season,
            None,
            None,
            usize::MAX,
        ) {
            let home = same_team(&m.home_team, team);
            if venue == Some("home") && !home || venue == Some("away") && home {
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
        r
    }
    pub fn head_to_head(&self, a: &str, b: &str, season: Option<i32>) -> Value {
        let ms: Vec<_> = self
            .find_matches(Some(a), Some(b), None, season, None, None, usize::MAX)
            .into_iter()
            .filter(|m| {
                (same_team(&m.home_team, a) && same_team(&m.away_team, b))
                    || (same_team(&m.home_team, b) && same_team(&m.away_team, a))
            })
            .collect();
        let (mut aw, mut bw, mut draws) = (0, 0, 0);
        for m in &ms {
            if m.home_goals == m.away_goals {
                draws += 1
            } else {
                let winner = if m.home_goals > m.away_goals {
                    &m.home_team
                } else {
                    &m.away_team
                };
                if same_team(winner, a) {
                    aw += 1
                } else {
                    bw += 1
                }
            }
        }
        json!({"team_a":a,"team_b":b,"matches":ms,"team_a_wins":aw,"team_b_wins":bw,"draws":draws})
    }
    pub fn standings(&self, season: i32, competition: &str) -> Value {
        let mut t: BTreeMap<String, Record> = BTreeMap::new();
        // The historical Brasileirão CSV overlaps the modern Brasileirão CSV for
        // several seasons.  Search results deliberately retain both sources, but
        // a league table must count a fixture only once.
        let matches = self.find_matches(
            None,
            None,
            Some(competition),
            Some(season),
            None,
            None,
            usize::MAX,
        );
        // `stadium` is populated only by novo_campeonato_brasileiro.csv.  Its
        // 2003–2019 rows overlap the modern source from 2012 onwards and use
        // different club spellings, so fixture-key de-duplication alone cannot
        // merge every row. Prefer the modern source whenever it is available;
        // retain historical rows for the earlier seasons it uniquely covers.
        let modern_source_available = matches.iter().any(|m| m.stadium.is_none());
        let mut seen_fixtures = BTreeSet::new();
        for m in matches {
            if modern_source_available && m.stadium.is_some() {
                continue;
            }
            let fixture = (
                m.season,
                m.date.clone(),
                normalize(&m.home_team),
                normalize(&m.away_team),
            );
            if !seen_fixtures.insert(fixture) {
                continue;
            }
            for (team, gf, ga) in [
                (&m.home_team, m.home_goals, m.away_goals),
                (&m.away_team, m.away_goals, m.home_goals),
            ] {
                let r = t.entry(team.clone()).or_default();
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
        let mut v:Vec<_>=t.into_iter().map(|(team,r)|json!({"team":team,"points":r.wins*3+r.draws,"record":r,"goal_difference":r.goals_for-r.goals_against})).collect();
        v.sort_by(|a, b| {
            b["points"]
                .as_u64()
                .cmp(&a["points"].as_u64())
                .then_with(|| {
                    b["goal_difference"]
                        .as_i64()
                        .cmp(&a["goal_difference"].as_i64())
                })
        });
        json!(v)
    }
    pub fn statistics(&self, competition: Option<&str>, season: Option<i32>) -> Value {
        let m = self.find_matches(None, None, competition, season, None, None, usize::MAX);
        let n = m.len();
        let goals: i32 = m.iter().map(|x| x.home_goals + x.away_goals).sum();
        let biggest = m
            .iter()
            .max_by_key(|x| (x.home_goals - x.away_goals).abs())
            .cloned();
        json!({"matches":n,"goals":goals,"average_goals_per_match":if n==0{0.0}else{goals as f64/n as f64},"biggest_win":biggest})
    }
}
fn get(h: &csv::StringRecord, r: &csv::StringRecord, key: &str) -> String {
    h.iter()
        .position(|x| x.trim_start_matches('\u{feff}') == key)
        .and_then(|i| r.get(i))
        .unwrap_or("")
        .trim()
        .to_string()
}
fn num(s: &str) -> Option<i32> {
    s.trim()
        .parse()
        .ok()
        .or_else(|| s.trim().parse::<f64>().ok().map(|v| v as i32))
}
fn some(s: String) -> Option<String> {
    if s.is_empty() {
        None
    } else {
        Some(s)
    }
}
pub fn normalize(s: &str) -> String {
    s.nfd()
        .filter(|c| !unicode_normalization::char::is_combining_mark(*c))
        .collect::<String>()
        .to_lowercase()
        .replace(['-', '_'], " ")
        .split_whitespace()
        .filter(|w| {
            w.len() > 2
                && !matches!(
                    *w,
                    "sp" | "rj"
                        | "mg"
                        | "rs"
                        | "sc"
                        | "pr"
                        | "ba"
                        | "ce"
                        | "go"
                        | "pe"
                        | "df"
                        | "pa"
                        | "mt"
                        | "ms"
                        | "al"
                        | "am"
                        | "se"
                        | "pb"
                        | "rn"
                        | "es"
                        | "ma"
                        | "pi"
                        | "ac"
                        | "ro"
                        | "rr"
                        | "ap"
                        | "to"
                )
        })
        .collect::<Vec<_>>()
        .join(" ")
}
fn contains(value: &str, q: &str) -> bool {
    normalize(value).contains(&normalize(q))
}
fn same_team(a: &str, b: &str) -> bool {
    let a = normalize(a);
    let b = normalize(b);
    a == b || a.contains(&b) || b.contains(&a)
}
fn date_value(s: String) -> String {
    let p: Vec<_> = s.split('/').collect();
    if p.len() == 3 {
        format!("{}-{:0>2}-{:0>2}", p[2], p[1], p[0])
    } else {
        s.get(..10).unwrap_or(&s).to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    fn db() -> Database {
        Database {
            matches: vec![
                Match {
                    competition: "Brasileirão".into(),
                    date: "2023-09-03".into(),
                    season: Some(2023),
                    round: Some("22".into()),
                    stage: None,
                    home_team: "Flamengo-RJ".into(),
                    away_team: "Fluminense-RJ".into(),
                    home_goals: 2,
                    away_goals: 1,
                    stadium: None,
                },
                Match {
                    competition: "Brasileirão".into(),
                    date: "2023-09-10".into(),
                    season: Some(2023),
                    round: None,
                    stage: None,
                    home_team: "Palmeiras-SP".into(),
                    away_team: "Flamengo-RJ".into(),
                    home_goals: 0,
                    away_goals: 0,
                    stadium: None,
                },
            ],
            players: vec![Player {
                id: "1".into(),
                name: "Neymar Jr".into(),
                age: Some(31),
                nationality: "Brazil".into(),
                overall: Some(92),
                potential: Some(92),
                club: "PSG".into(),
                position: "LW".into(),
            }],
        }
    }
    #[test]
    fn normalizes_accents_and_state() {
        assert!(same_team("São Paulo-SP", "sao paulo"));
    }
    #[test]
    fn finds_head_to_head() {
        let x = db().head_to_head("Flamengo", "Fluminense", Some(2023));
        assert_eq!(x["team_a_wins"], 1);
        assert_eq!(x["matches"].as_array().unwrap().len(), 1)
    }
    #[test]
    fn calculates_home_record() {
        let r = db().team_record("Flamengo", Some(2023), None, Some("home"));
        assert_eq!((r.matches, r.wins, r.goals_for), (1, 1, 2));
    }
    #[test]
    fn player_search_is_case_and_accent_insensitive() {
        assert_eq!(
            db().search_players(Some("neymar"), Some("brazil"), None, None, 10)
                .len(),
            1
        )
    }
    #[test]
    fn all_datasets_load() {
        let p = Path::new(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        if fs::metadata(&p).is_ok() {
            let d = Database::load(p).unwrap();
            assert!(d.matches.len() > 20_000);
            assert!(d.players.len() > 18_000);
            let table = d.standings(2019, "Brasileirão");
            let rows = table.as_array().unwrap();
            assert_eq!(rows.len(), 20);
            assert!(rows.iter().all(|row| row["record"]["matches"] == 38));
        }
    }

    #[test]
    fn match_search_filters_team_date_season_and_competition() {
        let matches = db().find_matches(
            Some("Flamengo"),
            None,
            Some("brasileirao"),
            Some(2023),
            Some("2023-09-05"),
            Some("2023-09-30"),
            10,
        );
        assert_eq!(matches.len(), 1);
        assert_eq!(matches[0].home_team, "Palmeiras-SP");
    }

    #[test]
    fn standings_do_not_double_count_overlapping_fixtures() {
        let mut data = db();
        data.matches.push(Match {
            competition: "Brasileirão".into(),
            date: "2023-09-03".into(),
            season: Some(2023),
            round: Some("22".into()),
            stage: None,
            home_team: "Flamengo".into(),
            away_team: "Fluminense".into(),
            home_goals: 2,
            away_goals: 1,
            stadium: Some("Overlapping source row".into()),
        });

        let table = data.standings(2023, "Brasileirão");
        let flamengo = table
            .as_array()
            .unwrap()
            .iter()
            .find(|row| row["team"] == "Flamengo-RJ")
            .unwrap();
        assert_eq!(flamengo["record"]["matches"], 2);
        assert_eq!(flamengo["points"], 4);
    }

    #[test]
    fn statistics_calculates_goals_and_biggest_win() {
        let stats = db().statistics(Some("Brasileirão"), Some(2023));
        assert_eq!(stats["matches"], 2);
        assert_eq!(stats["goals"], 3);
        assert_eq!(stats["average_goals_per_match"], 1.5);
        assert_eq!(stats["biggest_win"]["home_team"], "Flamengo-RJ");
    }
}
