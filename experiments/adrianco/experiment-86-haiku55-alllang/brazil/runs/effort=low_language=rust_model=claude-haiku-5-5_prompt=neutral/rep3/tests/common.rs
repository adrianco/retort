//! Context: shared BDD fixtures. Builds a small in-memory dataset from inline
//! CSV text in the same column layout as the real Kaggle files, so scenarios
//! are deterministic and fast.

#![allow(dead_code)]

use brazilian_soccer_mcp::data::Dataset;

pub const BRASILEIRAO: &str = "\
datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round
2019-09-01 16:00:00,\"Flamengo-RJ\",RJ,\"Fluminense-RJ\",RJ,2,1,2019,20
2019-05-12 16:00:00,\"Fluminense-RJ\",RJ,\"Flamengo-RJ\",RJ,1,0,2019,8
2019-06-01 16:00:00,\"Palmeiras-SP\",SP,\"Corinthians-SP\",SP,3,0,2019,10
2019-06-08 16:00:00,\"Corinthians-SP\",SP,\"Palmeiras-SP\",SP,1,1,2019,11
2022-11-13 16:00:00,\"Palmeiras-SP\",SP,\"Santos-SP\",SP,NA,NA,2022,38
2022-04-10 16:00:00,\"Palmeiras-SP\",SP,\"Santos-SP\",SP,2,0,2022,6
2022-05-01 16:00:00,\"Santos-SP\",SP,\"Palmeiras-SP\",SP,1,1,2022,9
";

pub const CUP: &str = "\
round,datetime,home_team,away_team,home_goal,away_goal,season
\"final\",2019-12-11 17:00:00,\"Flamengo\",\"Athletico-PR\",2,1,2019
\"1\",2019-03-07 16:00:00,\"Boavista Sport Club (antigo Esporte Clube Barreira) - RJ\",\"América - MG\",0,0,2019
";

pub const LIBERTADORES: &str = "\
datetime,home_team,away_team,home_goal,away_goal,season,stage
2019-02-12 20:15:00,\"Nacional (URU)\",\"Barcelona-EQU\",2,2,2019,group stage
2019-04-16 22:00:00,\"Flamengo\",\"Barcelona-EQU\",4,0,2019,quarterfinals
";

/// Overlaps `BRASILEIRAO` (same fixture, different name spelling) and adds a
/// Serie B match that only this source provides.
pub const EXTENDED: &str = "\
tournament,home,home_goal,away_goal,away,date,time
Serie A,Flamengo,2.0,1.0,Fluminense,2019-09-01,16:00:00
Serie B,Vila Nova,1.0,0.0,Goias,2019-05-04,16:00:00
";

pub const HISTORICAL: &str = "\
ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,
";

pub const FIFA: &str = "\
,ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number
0,190871,Neymar Jr,26,Brazil,92,93,Paris Saint-Germain,LW,10
1,20801,Cristiano Ronaldo,33,Portugal,94,94,Juventus,ST,7
2,200,Gabriel Barbosa,22,Brazil,80,85,Flamengo,ST,9
3,300,Alisson,25,Brazil,89,89,Liverpool,GK,1
4,400,Lucas Pratto,28,Argentina,75,75,,ST,
";

/// The fixture dataset with every source loaded in the real-file order.
pub fn fixture() -> Dataset {
    let mut ds = Dataset::new();
    ds.add_brasileirao(BRASILEIRAO.as_bytes()).unwrap();
    ds.add_historical_brasileirao(HISTORICAL.as_bytes())
        .unwrap();
    ds.add_cup(CUP.as_bytes()).unwrap();
    ds.add_libertadores(LIBERTADORES.as_bytes()).unwrap();
    ds.add_extended(EXTENDED.as_bytes()).unwrap();
    ds.add_fifa(FIFA.as_bytes()).unwrap();
    ds
}
