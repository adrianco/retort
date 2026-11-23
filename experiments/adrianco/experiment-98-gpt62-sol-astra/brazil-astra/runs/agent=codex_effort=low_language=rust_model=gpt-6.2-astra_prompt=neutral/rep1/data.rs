use rusqlite::{functions::FunctionFlags, params, Connection};
use serde_json::Value;
use std::{error::Error, path::Path};
pub type Result<T> = std::result::Result<T, Box<dyn Error>>;
pub fn fold(s: &str) -> String {
    s.trim()
        .to_lowercase()
        .chars()
        .map(|c| match c {
            'á' | 'à' | 'ã' | 'â' | 'ä' => 'a',
            'é' | 'ê' | 'è' | 'ë' => 'e',
            'í' | 'ì' | 'ï' => 'i',
            'ó' | 'ô' | 'õ' | 'ò' | 'ö' => 'o',
            'ú' | 'ü' | 'ù' => 'u',
            'ç' => 'c',
            'ñ' => 'n',
            c => c,
        })
        .collect()
}
pub fn team(s: &str) -> String {
    let name = fold(s).replace(" - ", "-");
    let states = "ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to";
    let (base, state) = name
        .rsplit_once(['-', ' '])
        .filter(|(_, t)| states.split_whitespace().any(|st| st == *t))
        .unwrap_or((&name, ""));
    if matches!(base, "atletico" | "athletico" | "america" | "botafogo") && !state.is_empty() {
        return format!("{}-{}", base.replace("athletico", "atletico"), state);
    }
    match base {
        "clube de regatas do flamengo" | "cr flamengo" => "flamengo",
        "sport club corinthians paulista" | "sc corinthians" => "corinthians",
        "sao paulo fc" | "sao paulo futebol clube" => "sao paulo",
        "sociedade esportiva palmeiras" => "palmeiras",
        "fortaleza fc" | "fortaleza esporte clube" => "fortaleza",
        "santa cruz fc" => "santa cruz",
        "santos fc" => "santos",
        "fluminense fc" => "fluminense",
        "atletico mineiro" | "clube atletico mineiro" => "atletico-mg",
        "athletico" | "atletico paranaense" | "athletico paranaense" => "atletico-pr",
        "atletico goianiense" => "atletico-go",
        "america mineiro" => "america-mg",
        "botafogo" => "botafogo-rj",
        "vasco da gama" | "cr vasco da gama" => "vasco",
        "sport recife" | "sport club do recife" => "sport",
        "ec bahia" => "bahia",
        "ec juventude" => "juventude",
        "nautico capibaribe" => "nautico",
        "red bull bragantino" | "rb bragantino" => "bragantino",
        s => s,
    }
    .into()
}
fn date(s: &str) -> Option<String> {
    let d = s.split_whitespace().next()?;
    if let Some((day, rest)) = d.split_once('/') {
        let (month, year) = rest.split_once('/')?;
        Some(format!("{year}-{month:0>2}-{day:0>2}"))
    } else {
        (d.len() == 10).then(|| d.to_owned())
    }
}
pub const FILES: [&str; 6] = [
    "Brasileirao_Matches.csv",
    "Brazilian_Cup_Matches.csv",
    "Libertadores_Matches.csv",
    "novo_campeonato_brasileiro.csv",
    "BR-Football-Dataset.csv",
    "fifa_data.csv",
];
pub fn load(dir: &Path) -> Result<Connection> {
    let mut db = Connection::open_in_memory()?;
    for (name, f) in [("team_key", team as fn(&str) -> String), ("fold", fold)] {
        db.create_scalar_function(
            name,
            1,
            FunctionFlags::SQLITE_DETERMINISTIC | FunctionFlags::SQLITE_UTF8,
            move |ctx| Ok(f(ctx.get_raw(0).as_str().unwrap_or(""))),
        )?;
    }
    let tx = db.transaction()?;
    tx.execute_batch("CREATE TABLE records(id INTEGER PRIMARY KEY,source TEXT,competition TEXT,date TEXT,season INTEGER,round TEXT,stage TEXT,home TEXT,away TEXT,home_goal INTEGER,away_goal INTEGER,fixture INTEGER,attributes TEXT);
 CREATE TABLE matches(id INTEGER PRIMARY KEY,competition TEXT,date TEXT,season INTEGER,round TEXT,stage TEXT,home TEXT,away TEXT,home_goal INTEGER,away_goal INTEGER,derby INTEGER);
 CREATE INDEX provenance ON records(fixture,source); CREATE INDEX pairing ON matches(competition,home,away);
 CREATE TABLE players(id INTEGER PRIMARY KEY,name TEXT,age INTEGER,nationality TEXT,overall INTEGER,potential INTEGER,club TEXT,club_key TEXT,position TEXT,attributes TEXT);")?;
    for (i, file) in FILES.iter().enumerate() {
        let mut rdr = csv::Reader::from_path(dir.join(file))?;
        let headers = rdr.headers()?.clone();
        for row in rdr.records() {
            let row = row?;
            let attrs: Value = headers
                .iter()
                .zip(row.iter())
                .filter(|(h, _)| !h.is_empty())
                .map(|(k, v)| (k.to_owned(), Value::from(v)))
                .collect();
            let get = |key: &str| attrs[key].as_str().unwrap_or("");
            if i == 5 {
                tx.prepare_cached("INSERT INTO players VALUES(?,?,?,?,?,?,?,?,?,?)")?
                    .execute(params![
                        get("ID"),
                        get("Name"),
                        get("Age"),
                        get("Nationality"),
                        get("Overall"),
                        get("Potential"),
                        get("Club"),
                        team(get("Club")),
                        get("Position"),
                        attrs.to_string()
                    ])?;
                continue;
            }
            let (dt, h, a, hg, ag, yr, rnd) = match i {
                3 => (
                    "Data",
                    "Equipe_mandante",
                    "Equipe_visitante",
                    "Gols_mandante",
                    "Gols_visitante",
                    "Ano",
                    "Rodada",
                ),
                4 => ("date", "home", "away", "home_goal", "away_goal", "", ""),
                _ => (
                    "datetime",
                    "home_team",
                    "away_team",
                    "home_goal",
                    "away_goal",
                    "season",
                    "round",
                ),
            };
            let d = date(get(dt));
            let home = team(get(h));
            let away = team(get(a));
            let comp = match i {
                0 | 3 => "Serie A",
                1 => "Copa do Brasil",
                2 => "Libertadores",
                _ => get("tournament"),
            };
            let year = get(yr)
                .parse::<i32>()
                .ok()
                .or_else(|| d.as_ref()?.get(..4)?.parse().ok());
            let goal = |k| get(k).parse::<f64>().ok().map(|n| n as i32);
            let stage = match (i, year, get(rnd)) {
                (1, Some(2012), "6")
                | (1, Some(2016), "7")
                | (1, Some(2013..=2015 | 2017..=2020), "8") => "final",
                _ => get("stage"),
            };
            // League clubs meet once per home orientation per season. Extended rows
            // lack a season, so use a nearby date (also handles overnight kickoffs).
            let existing: Option<i64> = tx
                .prepare_cached(
                    "SELECT min(id) FROM matches
                 WHERE competition=?1 AND home=?2 AND away=?3 AND (
                   date=?4 OR (?5=4 AND abs(julianday(date)-julianday(?4))<=1)
                   OR (season=?6 AND (?5=3 OR (?5=4 AND home_goal IS NULL))
                       AND EXISTS (SELECT 1 FROM records r WHERE r.fixture=matches.id
                                   AND r.source='Brasileirao_Matches.csv')))",
                )?
                .query_row(params![comp, home, away, d, i, year], |r| r.get(0))?;
            let id = if let Some(id) = existing {
                tx.prepare_cached(
                    "UPDATE matches SET date=CASE WHEN home_goal IS NULL AND ?1 IS NOT NULL
                       THEN coalesce(?3,date) ELSE date END,
                       home_goal=coalesce(home_goal,?1), away_goal=coalesce(away_goal,?2)
                     WHERE id=?4",
                )?
                .execute(params![goal(hg), goal(ag), d, id])?;
                id
            } else {
                let derby = rivals(&home, &away);
                tx.prepare_cached("INSERT INTO matches VALUES(NULL,?,?,?,?,?,?,?,?,?,?)")?
                    .execute(params![
                        comp,
                        d,
                        year,
                        get(rnd),
                        stage,
                        home,
                        away,
                        goal(hg),
                        goal(ag),
                        derby
                    ])?;
                tx.last_insert_rowid()
            };
            tx.prepare_cached("INSERT INTO records VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?,?)")?
                .execute(params![
                    file,
                    comp,
                    d,
                    year,
                    get(rnd),
                    stage,
                    home,
                    away,
                    goal(hg),
                    goal(ag),
                    id,
                    attrs.to_string()
                ])?;
        }
    }
    tx.execute_batch(include_str!("views.sql"))?;
    tx.commit()?;
    Ok(db)
}
fn rivals(a: &str, b: &str) -> bool {
    let groups: &[&[&str]] = &[
        &["flamengo", "fluminense", "vasco", "botafogo-rj"],
        &["corinthians", "palmeiras", "santos", "sao paulo"],
        &["gremio", "internacional"],
        &["cruzeiro", "atletico-mg"],
        &["bahia", "vitoria"],
        &["ceara", "fortaleza"],
        &["atletico-pr", "coritiba"],
    ];
    a != b && groups.iter().any(|g| g.contains(&a) && g.contains(&b))
}
