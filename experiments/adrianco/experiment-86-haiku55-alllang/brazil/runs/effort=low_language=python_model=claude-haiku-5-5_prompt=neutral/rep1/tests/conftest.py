# Context: Shared pytest fixtures. Builds a small, hand-checked copy of the six Kaggle files in a
# temp directory so behaviour tests are deterministic, and exposes the real data/kaggle set for
# the dataset-coverage tests. Tests follow Given/When/Then scenarios written as test names.

from pathlib import Path

import pytest

from brazilian_soccer_mcp.queries import SoccerKnowledgeBase

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_DATA_DIR = REPO_ROOT / "data" / "kaggle"

BRASILEIRAO_CSV = """datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round
2023-05-01 18:00:00,"Flamengo-RJ",RJ,"Fluminense-RJ",RJ,2,1,2023,1
2023-05-08 18:00:00,"Palmeiras-SP",SP,"Flamengo-RJ",RJ,0,0,2023,2
2023-05-15 18:00:00,"Fluminense-RJ",RJ,"Palmeiras-SP",SP,1,3,2023,3
2023-05-22 18:00:00,"Palmeiras-SP",SP,"Corinthians-SP",SP,2,0,2023,4
2023-05-29 18:00:00,"Corinthians-SP",SP,"Palmeiras-SP",SP,1,1,2023,5
2022-06-01 18:00:00,"Corinthians-SP",SP,"Flamengo-RJ",RJ,1,0,2022,1
2022-06-08 18:00:00,"Corinthians-SP",SP,"Palmeiras-SP",SP,3,1,2022,2
2022-06-15 18:00:00,"Corinthians-SP",SP,"Santos-SP",SP,0,2,2022,3
2022-06-22 18:00:00,"Atletico-MG",MG,"Flamengo-RJ",RJ,0,4,2022,4
2022-06-29 18:00:00,"Atletico-PR",PR,"Flamengo-RJ",RJ,1,1,2022,5
"""

HISTORICAL_CSV = """ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2010.01.0001,15/03/2010,2010,1,Palmeiras,Santos,1,0,SP,SP,Mandante,Pacaembu,
2010.01.0002,22/03/2010,2010,2,Santos,Palmeiras,NA,NA,SP,SP,Empate,Vila Belmiro,
"""

CUP_CSV = """"round","datetime","home_team","away_team","home_goal","away_goal","season"
"1",2023-06-10 16:00:00,"Flamengo - RJ","Sao Paulo - SP",2,1,2023
"""

LIBERTADORES_CSV = """datetime,home_team,away_team,home_goal,away_goal,season,stage
2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"
NA,"Boca Juniors","Toluca","1","2",2013,"group stage"
"""

BR_FOOTBALL_CSV = """tournament,home,home_goal,away_goal,away,date
Serie A,Santos,2.0,0.0,Cuiaba,2021-03-01
Serie A,Flamengo,2.0,1.0,Fluminense,2023-05-02
Serie B,Sport,1.0,1.0,Nautico,2023-04-01
"""

FIFA_CSV = """ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number
1,Neymar Jr,31,Brazil,92,92,Paris Saint-Germain,LW,10
2,Alisson,27,Brazil,89,91,Liverpool,GK,1
3,Casemiro,28,Brazil,89,89,Real Madrid,CDM,14
4,Gabriel Jesus,22,Brazil,85,90,Manchester City,ST,9
5,Lionel Messi,31,Argentina,94,94,FC Barcelona,RF,10
6,Gabigol,24,Brazil,80,85,Flamengo,ST,9
7,Everton Ribeiro,30,Brazil,80,80,Flamengo,CAM,7
8,Pedro,22,Brazil,78,84,Flamengo,ST,9
9,Pedro Henrique,20,Brazil,70,80,Sport Club do Recife,CB,4
"""


def write_sample_dataset(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "Brasileirao_Matches.csv": BRASILEIRAO_CSV,
        "novo_campeonato_brasileiro.csv": HISTORICAL_CSV,
        "Brazilian_Cup_Matches.csv": CUP_CSV,
        "Libertadores_Matches.csv": LIBERTADORES_CSV,
        "BR-Football-Dataset.csv": BR_FOOTBALL_CSV,
        "fifa_data.csv": FIFA_CSV,
    }
    for name, content in files.items():
        (data_dir / name).write_text(content, encoding="utf-8")
    return data_dir


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    return write_sample_dataset(tmp_path / "kaggle")


@pytest.fixture
def sample_kb(sample_dir: Path) -> SoccerKnowledgeBase:
    return SoccerKnowledgeBase.load(sample_dir)


@pytest.fixture(scope="session")
def real_kb() -> SoccerKnowledgeBase:
    return SoccerKnowledgeBase.load(REAL_DATA_DIR)
