use std::io::Read;
use std::path::Path;

use crate::models::Player;

fn empty_as_none(value: &str) -> Option<String> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.to_string())
    }
}

#[derive(Debug, serde::Deserialize)]
struct FifaRecord {
    #[serde(rename = "ID")]
    id: i64,
    #[serde(rename = "Name")]
    name: String,
    #[serde(rename = "Age")]
    age: String,
    #[serde(rename = "Nationality")]
    nationality: String,
    #[serde(rename = "Overall")]
    overall: String,
    #[serde(rename = "Potential")]
    potential: String,
    #[serde(rename = "Club")]
    club: String,
    #[serde(rename = "Position")]
    position: String,
    #[serde(rename = "Jersey Number")]
    jersey_number: String,
    #[serde(rename = "Height")]
    height: String,
    #[serde(rename = "Weight")]
    weight: String,
}

pub fn load_fifa_players_from_reader<R: Read>(reader: R) -> anyhow::Result<Vec<Player>> {
    let mut rdr = csv::Reader::from_reader(reader);
    let mut players = Vec::new();
    for result in rdr.deserialize() {
        let record: FifaRecord = result?;
        players.push(Player {
            id: record.id,
            name: record.name,
            age: record.age.trim().parse().ok(),
            nationality: record.nationality,
            overall: record.overall.trim().parse().ok(),
            potential: record.potential.trim().parse().ok(),
            club: empty_as_none(&record.club),
            position: empty_as_none(&record.position),
            jersey_number: record.jersey_number.trim().parse().ok(),
            height: empty_as_none(&record.height),
            weight: empty_as_none(&record.weight),
        });
    }
    Ok(players)
}

pub fn load_fifa_players(path: &Path) -> anyhow::Result<Vec<Player>> {
    let file = std::fs::File::open(path)
        .map_err(|e| anyhow::anyhow!("failed to open {}: {e}", path.display()))?;
    load_fifa_players_from_reader(file)
}

#[cfg(test)]
mod tests {
    use super::*;

    const FIFA_FIXTURE: &str = ",ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From,Contract Valid Until,Height,Weight
0,192119,Gabriel Barbosa,23,url,Brazil,flag,79,85,Flamengo,logo,€20M,€65K,1800,Right,3,3,3,Medium/ Medium,Normal,Yes,ST,9,\"Jul 1, 2019\",,2023,5'9,159lbs
1,999999,L. Paredes,25,url,Argentina,flag,83,86,,logo,€30M,€75K,2000,Right,3,3,3,Medium/ Medium,Normal,Yes,CM,,\"Jan 1, 2019\",,2024,5'11,168lbs
";

    #[test]
    fn loads_fifa_players_from_reader() {
        let players = load_fifa_players_from_reader(FIFA_FIXTURE.as_bytes()).unwrap();
        assert_eq!(players.len(), 2);

        let gabigol = &players[0];
        assert_eq!(gabigol.id, 192119);
        assert_eq!(gabigol.name, "Gabriel Barbosa");
        assert_eq!(gabigol.age, Some(23));
        assert_eq!(gabigol.nationality, "Brazil");
        assert_eq!(gabigol.overall, Some(79));
        assert_eq!(gabigol.potential, Some(85));
        assert_eq!(gabigol.club.as_deref(), Some("Flamengo"));
        assert_eq!(gabigol.position.as_deref(), Some("ST"));
        assert_eq!(gabigol.jersey_number, Some(9));
        assert_eq!(gabigol.height.as_deref(), Some("5'9"));
        assert_eq!(gabigol.weight.as_deref(), Some("159lbs"));

        let paredes = &players[1];
        assert_eq!(paredes.club, None);
        assert_eq!(paredes.jersey_number, None);
    }
}
