//! Dataset loading.
//!
//! Each bundled CSV uses a different column layout, so there is a dedicated
//! parser per file. All match files feed a single deduplicated [`Database`]
//! `matches` collection; the FIFA file populates `players`.
//!
//! Deduplication matters because `BR-Football-Dataset.csv` (Série A 2014-2023)
//! overlaps the dedicated Brasileirão files. Matches are keyed by
//! `(competition, season, home, away)` so the same fixture loaded from two
//! files collapses to one, keeping calculated standings correct.

use crate::models::{parse_date, Competition, Match, Player};
use crate::normalize;
use std::collections::HashSet;
use std::io::Read;
use std::path::Path;

/// In-memory knowledge base over all datasets.
#[derive(Debug, Default)]
pub struct Database {
    pub matches: Vec<Match>,
    pub players: Vec<Player>,
    seen: HashSet<String>,
}

/// Map header names to their column index.
fn header_index(headers: &csv::StringRecord) -> std::collections::HashMap<String, usize> {
    headers
        .iter()
        .enumerate()
        .map(|(i, h)| (h.trim().to_string(), i))
        .collect()
}

fn field<'a>(
    rec: &'a csv::StringRecord,
    idx: &std::collections::HashMap<String, usize>,
    name: &str,
) -> Option<&'a str> {
    idx.get(name).and_then(|&i| rec.get(i)).map(|s| s.trim())
}

/// Parse a goal count that may be written as `"2"` or `"1.0"`.
fn parse_goal(raw: &str) -> Option<u32> {
    let s = raw.trim();
    if s.is_empty() {
        return None;
    }
    if let Ok(v) = s.parse::<u32>() {
        return Some(v);
    }
    s.parse::<f64>().ok().filter(|v| v.is_finite()).map(|v| v.round() as u32)
}

fn parse_season(raw: &str) -> Option<i32> {
    raw.trim().parse::<i32>().ok()
}

impl Database {
    pub fn new() -> Self {
        Database::default()
    }

    /// Insert a match unless an equivalent one (same competition, season and
    /// ordered team pairing) was already loaded from another file.
    fn push_match(&mut self, m: Match) {
        let key = format!(
            "{}|{}|{}|{}",
            m.competition.display_name(),
            m.season,
            m.home_key(),
            m.away_key()
        );
        if self.seen.insert(key) {
            self.matches.push(m);
        }
    }

    fn reader<R: Read>(rdr: R) -> csv::Reader<R> {
        csv::ReaderBuilder::new().flexible(true).from_reader(rdr)
    }

    /// Brasileirão Série A (`Brasileirao_Matches.csv`).
    pub fn load_brasileirao<R: Read>(&mut self, rdr: R) -> usize {
        self.load_generic_matches(rdr, Competition::Brasileirao, "datetime", "round", None)
    }

    /// Copa do Brasil (`Brazilian_Cup_Matches.csv`).
    pub fn load_cup<R: Read>(&mut self, rdr: R) -> usize {
        self.load_generic_matches(rdr, Competition::CopaDoBrasil, "datetime", "round", None)
    }

    /// Copa Libertadores (`Libertadores_Matches.csv`).
    pub fn load_libertadores<R: Read>(&mut self, rdr: R) -> usize {
        self.load_generic_matches(rdr, Competition::Libertadores, "datetime", "round", Some("stage"))
    }

    /// Shared parser for the three `home_team`/`away_team` files.
    fn load_generic_matches<R: Read>(
        &mut self,
        rdr: R,
        comp: Competition,
        date_col: &str,
        round_col: &str,
        stage_col: Option<&str>,
    ) -> usize {
        let mut reader = Self::reader(rdr);
        let headers = match reader.headers() {
            Ok(h) => h.clone(),
            Err(_) => return 0,
        };
        let idx = header_index(&headers);
        let mut count = 0;
        for rec in reader.records().flatten() {
            let (home, away) = match (field(&rec, &idx, "home_team"), field(&rec, &idx, "away_team"))
            {
                (Some(h), Some(a)) if !h.is_empty() && !a.is_empty() => (h, a),
                _ => continue,
            };
            let hg = field(&rec, &idx, "home_goal").and_then(parse_goal);
            let ag = field(&rec, &idx, "away_goal").and_then(parse_goal);
            let season = field(&rec, &idx, "season").and_then(parse_season);
            let (hg, ag, season) = match (hg, ag, season) {
                (Some(h), Some(a), Some(s)) => (h, a, s),
                _ => continue,
            };
            let m = Match {
                competition: comp.clone(),
                home_team: normalize::display_name(home),
                away_team: normalize::display_name(away),
                home_goal: hg,
                away_goal: ag,
                season,
                date: field(&rec, &idx, date_col).and_then(parse_date),
                round: field(&rec, &idx, round_col)
                    .filter(|s| !s.is_empty())
                    .map(|s| s.to_string()),
                stage: stage_col
                    .and_then(|c| field(&rec, &idx, c))
                    .filter(|s| !s.is_empty())
                    .map(|s| s.to_string()),
            };
            self.push_match(m);
            count += 1;
        }
        count
    }

    /// Extended statistics (`BR-Football-Dataset.csv`).
    pub fn load_br_football<R: Read>(&mut self, rdr: R) -> usize {
        let mut reader = Self::reader(rdr);
        let headers = match reader.headers() {
            Ok(h) => h.clone(),
            Err(_) => return 0,
        };
        let idx = header_index(&headers);
        let mut count = 0;
        for rec in reader.records().flatten() {
            let (home, away) = match (field(&rec, &idx, "home"), field(&rec, &idx, "away")) {
                (Some(h), Some(a)) if !h.is_empty() && !a.is_empty() => (h, a),
                _ => continue,
            };
            let hg = field(&rec, &idx, "home_goal").and_then(parse_goal);
            let ag = field(&rec, &idx, "away_goal").and_then(parse_goal);
            let date = field(&rec, &idx, "date").and_then(parse_date);
            let (hg, ag) = match (hg, ag) {
                (Some(h), Some(a)) => (h, a),
                _ => continue,
            };
            // Derive the season year from the ISO date.
            let season = date
                .as_deref()
                .and_then(|d| d.get(0..4))
                .and_then(parse_season);
            let season = match season {
                Some(s) => s,
                None => continue,
            };
            let comp = field(&rec, &idx, "tournament")
                .map(Competition::from_tournament)
                .unwrap_or(Competition::Other("Unknown".into()));
            let m = Match {
                competition: comp,
                home_team: normalize::display_name(home),
                away_team: normalize::display_name(away),
                home_goal: hg,
                away_goal: ag,
                season,
                date,
                round: None,
                stage: None,
            };
            self.push_match(m);
            count += 1;
        }
        count
    }

    /// Historical Brasileirão 2003-2019 (`novo_campeonato_brasileiro.csv`).
    pub fn load_novo<R: Read>(&mut self, rdr: R) -> usize {
        let mut reader = Self::reader(rdr);
        let headers = match reader.headers() {
            Ok(h) => h.clone(),
            Err(_) => return 0,
        };
        let idx = header_index(&headers);
        let mut count = 0;
        for rec in reader.records().flatten() {
            let (home, away) = match (
                field(&rec, &idx, "Equipe_mandante"),
                field(&rec, &idx, "Equipe_visitante"),
            ) {
                (Some(h), Some(a)) if !h.is_empty() && !a.is_empty() => (h, a),
                _ => continue,
            };
            let hg = field(&rec, &idx, "Gols_mandante").and_then(parse_goal);
            let ag = field(&rec, &idx, "Gols_visitante").and_then(parse_goal);
            let season = field(&rec, &idx, "Ano").and_then(parse_season);
            let (hg, ag, season) = match (hg, ag, season) {
                (Some(h), Some(a), Some(s)) => (h, a, s),
                _ => continue,
            };
            let m = Match {
                competition: Competition::Brasileirao,
                home_team: normalize::display_name(home),
                away_team: normalize::display_name(away),
                home_goal: hg,
                away_goal: ag,
                season,
                date: field(&rec, &idx, "Data").and_then(parse_date),
                round: field(&rec, &idx, "Rodada")
                    .filter(|s| !s.is_empty())
                    .map(|s| s.to_string()),
                stage: None,
            };
            self.push_match(m);
            count += 1;
        }
        count
    }

    /// FIFA player database (`fifa_data.csv`).
    pub fn load_fifa<R: Read>(&mut self, rdr: R) -> usize {
        let mut reader = Self::reader(rdr);
        let headers = match reader.headers() {
            Ok(h) => h.clone(),
            Err(_) => return 0,
        };
        let idx = header_index(&headers);
        let mut count = 0;
        for rec in reader.records().flatten() {
            let id = match field(&rec, &idx, "ID").and_then(|s| s.parse::<u64>().ok()) {
                Some(v) => v,
                None => continue,
            };
            let name = match field(&rec, &idx, "Name").filter(|s| !s.is_empty()) {
                Some(n) => n.to_string(),
                None => continue,
            };
            let player = Player {
                id,
                name,
                age: field(&rec, &idx, "Age").and_then(|s| s.parse().ok()),
                nationality: field(&rec, &idx, "Nationality").unwrap_or("").to_string(),
                overall: field(&rec, &idx, "Overall").and_then(|s| s.parse().ok()),
                potential: field(&rec, &idx, "Potential").and_then(|s| s.parse().ok()),
                club: field(&rec, &idx, "Club").unwrap_or("").to_string(),
                position: field(&rec, &idx, "Position").unwrap_or("").to_string(),
            };
            self.players.push(player);
            count += 1;
        }
        count
    }

    /// Load every dataset from a directory containing the bundled CSV files.
    pub fn load_from_dir(dir: impl AsRef<Path>) -> std::io::Result<Database> {
        let dir = dir.as_ref();
        let mut db = Database::new();
        let open = |name: &str| std::fs::File::open(dir.join(name));

        // Load the authoritative dedicated files first so they win on dedup.
        if let Ok(f) = open("Brasileirao_Matches.csv") {
            db.load_brasileirao(f);
        }
        if let Ok(f) = open("novo_campeonato_brasileiro.csv") {
            db.load_novo(f);
        }
        if let Ok(f) = open("Brazilian_Cup_Matches.csv") {
            db.load_cup(f);
        }
        if let Ok(f) = open("Libertadores_Matches.csv") {
            db.load_libertadores(f);
        }
        if let Ok(f) = open("BR-Football-Dataset.csv") {
            db.load_br_football(f);
        }
        if let Ok(f) = open("fifa_data.csv") {
            db.load_fifa(f);
        }
        Ok(db)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_goal_formats() {
        assert_eq!(parse_goal("2"), Some(2));
        assert_eq!(parse_goal("1.0"), Some(1));
        assert_eq!(parse_goal("3.0"), Some(3));
        assert_eq!(parse_goal(""), None);
        assert_eq!(parse_goal("x"), None);
    }

    #[test]
    fn loads_brasileirao_rows() {
        let csv = "\"datetime\",\"home_team\",\"home_team_state\",\"away_team\",\"away_team_state\",\"home_goal\",\"away_goal\",\"season\",\"round\"\n\
2019-10-27 16:00:00,\"Flamengo-RJ\",\"RJ\",\"Grêmio-RS\",\"RS\",5,0,2019,30\n";
        let mut db = Database::new();
        let n = db.load_brasileirao(csv.as_bytes());
        assert_eq!(n, 1);
        assert_eq!(db.matches.len(), 1);
        let m = &db.matches[0];
        assert_eq!(m.home_team, "Flamengo");
        assert_eq!(m.away_team, "Grêmio");
        assert_eq!(m.home_goal, 5);
        assert_eq!(m.competition, Competition::Brasileirao);
        assert_eq!(m.season, 2019);
        assert_eq!(m.date.as_deref(), Some("2019-10-27"));
        assert_eq!(m.round.as_deref(), Some("30"));
    }

    #[test]
    fn loads_libertadores_with_quoted_goals_and_stage() {
        let csv = "\"datetime\",\"home_team\",\"away_team\",\"home_goal\",\"away_goal\",\"season\",\"stage\"\n\
2013-02-12 20:15:00,\"Nacional (URU)\",\"Barcelona-EQU\",\"2\",\"2\",2013,\"group stage\"\n";
        let mut db = Database::new();
        db.load_libertadores(csv.as_bytes());
        let m = &db.matches[0];
        assert_eq!(m.home_team, "Nacional");
        assert_eq!(m.away_team, "Barcelona");
        assert_eq!(m.home_goal, 2);
        assert_eq!(m.stage.as_deref(), Some("group stage"));
    }

    #[test]
    fn loads_br_football_floats_and_classifies() {
        let csv = "tournament,home,home_goal,away_goal,away,date\n\
Serie A,Flamengo,3.0,1.0,Santos,2019-05-01\n\
Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2023-09-24\n";
        let mut db = Database::new();
        let n = db.load_br_football(csv.as_bytes());
        assert_eq!(n, 2);
        assert_eq!(db.matches[0].competition, Competition::Brasileirao);
        assert_eq!(db.matches[0].home_goal, 3);
        assert_eq!(db.matches[0].season, 2019);
        assert_eq!(db.matches[1].competition, Competition::CopaDoBrasil);
    }

    #[test]
    fn loads_novo_brazilian_dates() {
        let csv = "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS\n\
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,\n";
        let mut db = Database::new();
        db.load_novo(csv.as_bytes());
        let m = &db.matches[0];
        assert_eq!(m.home_team, "Guarani");
        assert_eq!(m.away_team, "Vasco");
        assert_eq!(m.home_goal, 4);
        assert_eq!(m.season, 2003);
        assert_eq!(m.date.as_deref(), Some("2003-03-29"));
        assert_eq!(m.competition, Competition::Brasileirao);
    }

    #[test]
    fn loads_fifa_players() {
        let csv = ",ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Position\n\
0,158023,L. Messi,31,url,Argentina,flag,94,94,FC Barcelona,RF\n\
1,20801,Neymar Jr,27,url,Brazil,flag,92,93,Paris Saint-Germain,LW\n";
        let mut db = Database::new();
        let n = db.load_fifa(csv.as_bytes());
        assert_eq!(n, 2);
        let p = &db.players[1];
        assert_eq!(p.name, "Neymar Jr");
        assert_eq!(p.nationality, "Brazil");
        assert_eq!(p.overall, Some(92));
        assert_eq!(p.club, "Paris Saint-Germain");
        assert_eq!(p.position, "LW");
    }

    #[test]
    fn deduplicates_overlapping_matches() {
        // Same fixture present in the dedicated file and in BR-Football.
        let dedicated = "\"datetime\",\"home_team\",\"home_team_state\",\"away_team\",\"away_team_state\",\"home_goal\",\"away_goal\",\"season\",\"round\"\n\
2019-05-01 16:00:00,\"Flamengo-RJ\",\"RJ\",\"Santos-SP\",\"SP\",3,1,2019,5\n";
        let brf = "tournament,home,home_goal,away_goal,away,date\n\
Serie A,Flamengo,3.0,1.0,Santos,2019-05-01\n";
        let mut db = Database::new();
        db.load_brasileirao(dedicated.as_bytes());
        db.load_br_football(brf.as_bytes());
        // Only the first (dedicated) copy is kept.
        assert_eq!(db.matches.len(), 1);
        assert_eq!(db.matches[0].round.as_deref(), Some("5"));
    }
}
