//! Core entities of the Brazilian soccer knowledge graph: dates, competitions,
//! data sources, teams, matches and players.

use serde::Serialize;
use std::fmt;

/// A calendar date. Hand-rolled so the crate stays dependency-light; the
/// datasets ship three different date spellings and all of them parse here.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Date {
    pub year: i32,
    pub month: u32,
    pub day: u32,
}

impl Date {
    pub fn new(year: i32, month: u32, day: u32) -> Option<Date> {
        if !(1..=12).contains(&month) || !(1..=31).contains(&day) {
            return None;
        }
        Some(Date { year, month, day })
    }

    /// Parses `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS` and `DD/MM/YYYY`.
    pub fn parse(raw: &str) -> Option<Date> {
        let trimmed = raw.trim().trim_matches('"');
        if trimmed.is_empty() {
            return None;
        }
        let date_part = trimmed.split_whitespace().next()?;
        if let Some((y, rest)) = date_part.split_once('-') {
            let (m, d) = rest.split_once('-')?;
            return Date::new(y.parse().ok()?, m.parse().ok()?, d.parse().ok()?);
        }
        if let Some((d, rest)) = date_part.split_once('/') {
            let (m, y) = rest.split_once('/')?;
            return Date::new(y.parse().ok()?, m.parse().ok()?, d.parse().ok()?);
        }
        None
    }

    /// Time-of-day component of a `YYYY-MM-DD HH:MM:SS` timestamp, if present.
    pub fn parse_time(raw: &str) -> Option<String> {
        let trimmed = raw.trim().trim_matches('"');
        let mut parts = trimmed.split_whitespace();
        parts.next()?;
        let time = parts.next()?;
        if time.contains(':') {
            Some(time.to_string())
        } else {
            None
        }
    }
}

impl fmt::Display for Date {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:04}-{:02}-{:02}", self.year, self.month, self.day)
    }
}

impl Serialize for Date {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(&self.to_string())
    }
}

/// Competitions represented across the datasets.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize)]
pub enum Competition {
    SerieA,
    SerieB,
    SerieC,
    CopaDoBrasil,
    Libertadores,
}

impl Competition {
    pub const ALL: [Competition; 5] = [
        Competition::SerieA,
        Competition::SerieB,
        Competition::SerieC,
        Competition::CopaDoBrasil,
        Competition::Libertadores,
    ];

    pub fn name(&self) -> &'static str {
        match self {
            Competition::SerieA => "Brasileirão Série A",
            Competition::SerieB => "Brasileirão Série B",
            Competition::SerieC => "Brasileirão Série C",
            Competition::CopaDoBrasil => "Copa do Brasil",
            Competition::Libertadores => "Copa Libertadores",
        }
    }

    /// Machine-friendly identifier used in tool arguments and JSON output.
    pub fn slug(&self) -> &'static str {
        match self {
            Competition::SerieA => "serie_a",
            Competition::SerieB => "serie_b",
            Competition::SerieC => "serie_c",
            Competition::CopaDoBrasil => "copa_do_brasil",
            Competition::Libertadores => "libertadores",
        }
    }

    /// Accepts English/Portuguese spellings, with or without accents.
    pub fn parse(raw: &str) -> Option<Competition> {
        let key = crate::normalize::simplify(raw);
        let compact = key.replace(' ', "");
        match compact.as_str() {
            "seriea"
            | "brasileirao"
            | "brasileiraoseriea"
            | "brasileiraoa"
            | "campeonato"
            | "campeonatobrasileiro"
            | "brazilianleague"
            | "a" => Some(Competition::SerieA),
            "serieb" | "brasileiraoserieb" | "b" => Some(Competition::SerieB),
            "seriec" | "brasileiraoseriec" | "c" => Some(Competition::SerieC),
            "copadobrasil" | "brazilcup" | "braziliancup" | "cup" | "copabrasil" => {
                Some(Competition::CopaDoBrasil)
            }
            "libertadores" | "copalibertadores" | "conmebollibertadores" => {
                Some(Competition::Libertadores)
            }
            _ => None,
        }
    }
}

impl fmt::Display for Competition {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.name())
    }
}

/// The CSV files backing the graph.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize)]
pub enum Source {
    Brasileirao,
    BrazilianCup,
    Libertadores,
    BrFootball,
    NovoBrasileirao,
    Fifa,
}

impl Source {
    pub const MATCH_SOURCES: [Source; 5] = [
        Source::Brasileirao,
        Source::BrazilianCup,
        Source::Libertadores,
        Source::BrFootball,
        Source::NovoBrasileirao,
    ];

    pub fn file_name(&self) -> &'static str {
        match self {
            Source::Brasileirao => "Brasileirao_Matches.csv",
            Source::BrazilianCup => "Brazilian_Cup_Matches.csv",
            Source::Libertadores => "Libertadores_Matches.csv",
            Source::BrFootball => "BR-Football-Dataset.csv",
            Source::NovoBrasileirao => "novo_campeonato_brasileiro.csv",
            Source::Fifa => "fifa_data.csv",
        }
    }

    pub fn label(&self) -> &'static str {
        match self {
            Source::Brasileirao => "Brasileirão Série A matches (Kaggle: ricardomattos05)",
            Source::BrazilianCup => "Copa do Brasil matches (Kaggle: ricardomattos05)",
            Source::Libertadores => "Copa Libertadores matches (Kaggle: ricardomattos05)",
            Source::BrFootball => "Extended match statistics (Kaggle: cuecacuela)",
            Source::NovoBrasileirao => "Historical Brasileirão 2003-2019 (Kaggle: macedojleo)",
            Source::Fifa => "FIFA player database (Kaggle: youssefelbadry10)",
        }
    }

    pub fn license(&self) -> &'static str {
        match self {
            Source::Brasileirao | Source::BrazilianCup | Source::Libertadores => "CC BY 4.0",
            Source::BrFootball => "CC0 Public Domain",
            Source::NovoBrasileirao => "CC BY 4.0",
            Source::Fifa => "Apache 2.0",
        }
    }

    /// Preference order when several files describe the same competition and
    /// season. The higher-priority file becomes the canonical record so
    /// aggregate statistics never double-count an overlapping fixture.
    pub fn priority_for(competition: Competition) -> &'static [Source] {
        match competition {
            Competition::SerieA => &[
                Source::Brasileirao,
                Source::NovoBrasileirao,
                Source::BrFootball,
            ],
            Competition::CopaDoBrasil => &[Source::BrazilianCup, Source::BrFootball],
            Competition::Libertadores => &[Source::Libertadores],
            Competition::SerieB | Competition::SerieC => &[Source::BrFootball],
        }
    }
}

impl fmt::Display for Source {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.file_name())
    }
}

/// Index of a team inside [`crate::graph::KnowledgeGraph::teams`].
pub type TeamId = usize;
/// Index of a match inside [`crate::graph::KnowledgeGraph::matches`].
pub type MatchId = usize;
/// Index of a player inside [`crate::graph::KnowledgeGraph::players`].
pub type PlayerId = usize;

/// A club, merged across every spelling found in the datasets.
#[derive(Debug, Clone, Serialize)]
pub struct Team {
    pub id: TeamId,
    /// Canonical key, e.g. `flamengo-RJ`.
    pub key: String,
    /// Preferred human-readable spelling, e.g. `Flamengo`.
    pub name: String,
    pub state: Option<String>,
    pub country: Option<String>,
    /// Every raw spelling observed, for provenance and lookup.
    pub aliases: Vec<String>,
}

impl Team {
    /// `Flamengo (RJ)` / `Nacional (URU)`. The qualifier is omitted when the
    /// name already carries it (`Botafogo-SP`).
    pub fn display(&self) -> String {
        let qualifier = self.state.as_deref().or(self.country.as_deref());
        match qualifier {
            Some(q) if !self.name.ends_with(q) => format!("{} ({})", self.name, q),
            _ => self.name.clone(),
        }
    }
}

/// Optional per-match statistics available only in `BR-Football-Dataset.csv`.
#[derive(Debug, Clone, Default, Serialize)]
pub struct MatchStats {
    pub home_corners: Option<f64>,
    pub away_corners: Option<f64>,
    pub home_shots: Option<f64>,
    pub away_shots: Option<f64>,
    pub home_attacks: Option<f64>,
    pub away_attacks: Option<f64>,
    pub total_corners: Option<f64>,
    pub half_time_home: Option<String>,
    pub half_time_away: Option<String>,
}

impl MatchStats {
    pub fn is_empty(&self) -> bool {
        self.home_corners.is_none()
            && self.home_shots.is_none()
            && self.home_attacks.is_none()
            && self.total_corners.is_none()
    }
}

/// Result of a played match, from the home team's point of view.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum Outcome {
    HomeWin,
    Draw,
    AwayWin,
}

/// A single fixture.
#[derive(Debug, Clone)]
pub struct Match {
    pub id: MatchId,
    pub competition: Competition,
    pub season: i32,
    pub date: Option<Date>,
    pub time: Option<String>,
    pub home: TeamId,
    pub away: TeamId,
    pub home_goals: Option<i32>,
    pub away_goals: Option<i32>,
    pub round: Option<String>,
    pub stage: Option<String>,
    pub venue: Option<String>,
    pub source: Source,
    /// False when a higher-priority source already covers this
    /// competition/season, i.e. the row is a duplicate view of the same
    /// fixture. Statistics use canonical rows only.
    pub canonical: bool,
    pub stats: Option<MatchStats>,
}

impl Match {
    pub fn played(&self) -> bool {
        self.home_goals.is_some() && self.away_goals.is_some()
    }

    pub fn outcome(&self) -> Option<Outcome> {
        match (self.home_goals, self.away_goals) {
            (Some(h), Some(a)) if h > a => Some(Outcome::HomeWin),
            (Some(h), Some(a)) if h < a => Some(Outcome::AwayWin),
            (Some(_), Some(_)) => Some(Outcome::Draw),
            _ => None,
        }
    }

    pub fn total_goals(&self) -> Option<i32> {
        match (self.home_goals, self.away_goals) {
            (Some(h), Some(a)) => Some(h + a),
            _ => None,
        }
    }

    pub fn goal_difference(&self) -> Option<i32> {
        match (self.home_goals, self.away_goals) {
            (Some(h), Some(a)) => Some((h - a).abs()),
            _ => None,
        }
    }

    pub fn involves(&self, team: TeamId) -> bool {
        self.home == team || self.away == team
    }

    /// The opponent of `team`, or `None` if the team did not play.
    pub fn opponent_of(&self, team: TeamId) -> Option<TeamId> {
        if self.home == team {
            Some(self.away)
        } else if self.away == team {
            Some(self.home)
        } else {
            None
        }
    }

    /// `(goals for, goals against)` from `team`'s perspective.
    pub fn goals_for(&self, team: TeamId) -> Option<(i32, i32)> {
        match (self.home_goals, self.away_goals) {
            (Some(h), Some(a)) if self.home == team => Some((h, a)),
            (Some(h), Some(a)) if self.away == team => Some((a, h)),
            _ => None,
        }
    }

    /// Round or stage label, whichever the source provides.
    pub fn phase(&self) -> Option<String> {
        match (&self.round, &self.stage) {
            (_, Some(stage)) => Some(stage.clone()),
            (Some(round), None) => Some(format!("Round {round}")),
            _ => None,
        }
    }
}

/// A FIFA-database player.
#[derive(Debug, Clone)]
pub struct Player {
    pub id: PlayerId,
    pub fifa_id: Option<i64>,
    pub name: String,
    pub age: Option<i32>,
    pub nationality: String,
    pub overall: i32,
    pub potential: i32,
    pub club: Option<String>,
    /// Resolved knowledge-graph team when the club also appears in match data.
    pub club_team: Option<TeamId>,
    pub position: Option<String>,
    pub jersey_number: Option<i32>,
    pub height: Option<String>,
    pub weight: Option<String>,
    pub value: Option<String>,
    pub wage: Option<String>,
    pub preferred_foot: Option<String>,
    /// Skill ratings aligned with [`ATTRIBUTE_NAMES`]; `0` means "not rated".
    pub attributes: Vec<u8>,
}

/// Skill columns kept from `fifa_data.csv`, in storage order.
pub const ATTRIBUTE_NAMES: [&str; 34] = [
    "Crossing",
    "Finishing",
    "HeadingAccuracy",
    "ShortPassing",
    "Volleys",
    "Dribbling",
    "Curve",
    "FKAccuracy",
    "LongPassing",
    "BallControl",
    "Acceleration",
    "SprintSpeed",
    "Agility",
    "Reactions",
    "Balance",
    "ShotPower",
    "Jumping",
    "Stamina",
    "Strength",
    "LongShots",
    "Aggression",
    "Interceptions",
    "Positioning",
    "Vision",
    "Penalties",
    "Composure",
    "Marking",
    "StandingTackle",
    "SlidingTackle",
    "GKDiving",
    "GKHandling",
    "GKKicking",
    "GKPositioning",
    "GKReflexes",
];

impl Player {
    pub fn attribute(&self, name: &str) -> Option<u8> {
        let idx = ATTRIBUTE_NAMES
            .iter()
            .position(|a| a.eq_ignore_ascii_case(name))?;
        self.attributes.get(idx).copied().filter(|v| *v > 0)
    }

    /// The `n` best-rated skills, for compact profile output.
    pub fn top_attributes(&self, n: usize) -> Vec<(&'static str, u8)> {
        let mut pairs: Vec<(&'static str, u8)> = ATTRIBUTE_NAMES
            .iter()
            .zip(self.attributes.iter())
            .filter(|(name, value)| **value > 0 && !name.starts_with("GK"))
            .map(|(name, value)| (*name, *value))
            .collect();
        pairs.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(b.0)));
        pairs.truncate(n);
        pairs
    }

    pub fn is_goalkeeper(&self) -> bool {
        self.position
            .as_deref()
            .map(|p| p.eq_ignore_ascii_case("GK"))
            .unwrap_or(false)
    }
}

/// Win/draw/loss tally used by every aggregate query.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
pub struct Record {
    pub matches: i32,
    pub wins: i32,
    pub draws: i32,
    pub losses: i32,
    pub goals_for: i32,
    pub goals_against: i32,
    pub clean_sheets: i32,
}

impl Record {
    /// Folds one played match into the tally, from the team's perspective.
    pub fn add(&mut self, goals_for: i32, goals_against: i32) {
        self.matches += 1;
        self.goals_for += goals_for;
        self.goals_against += goals_against;
        if goals_against == 0 {
            self.clean_sheets += 1;
        }
        match goals_for.cmp(&goals_against) {
            std::cmp::Ordering::Greater => self.wins += 1,
            std::cmp::Ordering::Equal => self.draws += 1,
            std::cmp::Ordering::Less => self.losses += 1,
        }
    }

    pub fn points(&self) -> i32 {
        self.wins * 3 + self.draws
    }

    pub fn goal_difference(&self) -> i32 {
        self.goals_for - self.goals_against
    }

    pub fn win_rate(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.wins as f64 * 100.0 / self.matches as f64
        }
    }

    pub fn points_per_match(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.points() as f64 / self.matches as f64
        }
    }

    pub fn goals_for_per_match(&self) -> f64 {
        if self.matches == 0 {
            0.0
        } else {
            self.goals_for as f64 / self.matches as f64
        }
    }

    pub fn merge(&mut self, other: &Record) {
        self.matches += other.matches;
        self.wins += other.wins;
        self.draws += other.draws;
        self.losses += other.losses;
        self.goals_for += other.goals_for;
        self.goals_against += other.goals_against;
        self.clean_sheets += other.clean_sheets;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_all_dataset_date_formats() {
        assert_eq!(Date::parse("2023-09-24"), Date::new(2023, 9, 24));
        assert_eq!(Date::parse("2012-05-19 18:30:00"), Date::new(2012, 5, 19));
        assert_eq!(Date::parse("29/03/2003"), Date::new(2003, 3, 29));
        assert_eq!(Date::parse(""), None);
        assert_eq!(Date::parse("not a date"), None);
        assert_eq!(
            Date::parse_time("2012-05-19 18:30:00").as_deref(),
            Some("18:30:00")
        );
        assert_eq!(Date::parse_time("2012-05-19"), None);
    }

    #[test]
    fn dates_sort_chronologically() {
        let mut dates = [
            Date::parse("2019-01-05").unwrap(),
            Date::parse("2003-12-31").unwrap(),
            Date::parse("2019-01-04").unwrap(),
        ];
        dates.sort();
        assert_eq!(dates[0].to_string(), "2003-12-31");
        assert_eq!(dates[2].to_string(), "2019-01-05");
    }

    #[test]
    fn competition_names_parse_loosely() {
        assert_eq!(Competition::parse("Brasileirão"), Some(Competition::SerieA));
        assert_eq!(Competition::parse("serie a"), Some(Competition::SerieA));
        assert_eq!(
            Competition::parse("Copa do Brasil"),
            Some(Competition::CopaDoBrasil)
        );
        assert_eq!(
            Competition::parse("libertadores"),
            Some(Competition::Libertadores)
        );
        assert_eq!(Competition::parse("premier league"), None);
    }

    #[test]
    fn record_tallies_points_and_rates() {
        let mut record = Record::default();
        record.add(2, 1); // win
        record.add(0, 0); // draw, clean sheet
        record.add(1, 3); // loss
        assert_eq!(record.wins, 1);
        assert_eq!(record.draws, 1);
        assert_eq!(record.losses, 1);
        assert_eq!(record.points(), 4);
        assert_eq!(record.clean_sheets, 1);
        assert_eq!(record.goal_difference(), -1);
        assert!((record.win_rate() - 33.333).abs() < 0.01);
    }
}
