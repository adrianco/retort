"""Shared fixtures.

Two datasets are available to tests:

* ``graph`` - the real Kaggle data, loaded once per test session (~0.6s), used
  for behaviour tests with known-good answers such as the 2019 Brasileirão.
* ``synthetic_graph`` - a handful of rows written to a temporary directory, used
  where the assertion is about loading rules (de-duplication, encodings, date
  formats) rather than about football.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brazilian_soccer.graph import KnowledgeGraph, load_graph  # noqa: E402
from brazilian_soccer.loader import load_dataset  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "kaggle"


@pytest.fixture(scope="session")
def graph() -> KnowledgeGraph:
    """The knowledge graph built from the real datasets."""
    return load_graph(DATA_DIR)


@pytest.fixture(scope="session")
def dataset():
    """The loaded dataset (teams, matches, players) from the real files."""
    return load_dataset(DATA_DIR)


# --------------------------------------------------------------------------- #
# Synthetic data
# --------------------------------------------------------------------------- #

SYNTHETIC_FILES = {
    "Brasileirao_Matches.csv": (
        '"datetime","home_team","home_team_state","away_team","away_team_state",'
        '"home_goal","away_goal","season","round"\n'
        '2019-05-05 16:00:00,"Flamengo-RJ","RJ","Sao Paulo-SP","SP",2,1,2019,1\n'
        '2019-08-10 16:00:00,"Sao Paulo-SP","SP","Flamengo-RJ","RJ",0,0,2019,20\n'
        '2019-05-06 18:00:00,"Gremio-RS","RS","Atletico-MG","MG",3,0,2019,1\n'
        '2019-08-11 18:00:00,"Atletico-MG","MG","Gremio-RS","RS",1,1,2019,20\n'
    ),
    # Same two Flamengo fixtures, spelled differently, plus an extra season.
    "novo_campeonato_brasileiro.csv": (
        "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,"
        "Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS\n"
        "2019.01.0001,05/05/2019,2019,1,Flamengo,São Paulo,2,1,RJ,SP,Mandante,"
        "Maracanã,\n"
        "2019.20.0002,10/08/2019,2019,20,São Paulo,Flamengo,0,0,SP,RJ,Empate,"
        "Morumbi,\n"
        "2005.01.0003,29/03/2005,2005,1,Grêmio,Atlético-MG,1,2,RS,MG,Visitante,"
        "Olímpico,\n"
    ),
    "Brazilian_Cup_Matches.csv": (
        '"round","datetime","home_team","away_team","home_goal","away_goal",'
        '"season"\n'
        '"1",2019-03-06 20:30:00,"Flamengo - RJ","América - MG",1,0,2019\n'
        '"2",2019-04-10 20:30:00,"Grêmio - RS","Flamengo - RJ",2,2,2019\n'
    ),
    "Libertadores_Matches.csv": (
        '"datetime","home_team","away_team","home_goal","away_goal","season",'
        '"stage"\n'
        '2019-03-05 21:30:00,"Flamengo","Nacional (URU)","3","1",2019,'
        '"group stage"\n'
        '2019-11-23 17:00:00,"Flamengo","River Plate","2","1",2019,"final"\n'
        ',"Palmeiras","Boca Juniors","-","-",,"final"\n'
    ),
    # Overlaps the Brasileirão file (adds shot data) and adds a Série B match.
    "BR-Football-Dataset.csv": (
        "tournament,home,home_goal,away_goal,away,home_corner,away_corner,"
        "home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,"
        "at_diff,ht_result,at_result,total_corners\n"
        "Serie A,Flamengo,2.0,1.0,Sao Paulo,5.0,3.0,110.0,90.0,12.0,7.0,"
        "16:00:00,2019-05-05,1.0,-1.0,WON,LOST,8.0\n"
        "Serie B,Ceara,1.0,0.0,Vitoria,4.0,2.0,80.0,70.0,9.0,5.0,"
        "19:00:00,2019-06-01,1.0,-1.0,WON,LOST,6.0\n"
        # A January match belongs to the previous season.
        "Serie B,Vitoria,2.0,2.0,Ceara,3.0,3.0,75.0,75.0,8.0,8.0,"
        "19:00:00,2020-01-15,0.0,0.0,DRAW,DRAW,6.0\n"
    ),
    "fifa_data.csv": (
        ",ID,Name,Age,Nationality,Overall,Potential,Club,Value,Wage,"
        "Preferred Foot,Position,Jersey Number,Height,Weight,Finishing,"
        "Dribbling\n"
        "0,1001,Ronaldinho,32,Brazil,88,88,Flamengo,€20M,€100K,Right,CAM,10,"
        "5'11,176lbs,85,94\n"
        "1,1002,João Silva,21,Brazil,70,84,Grêmio,€3M,€10K,Left,ST,9,"
        "6'0,170lbs,72,68\n"
        "2,1003,A. Keeper,29,Argentina,74,76,Boca Juniors,€5M,€20K,Right,GK,1,"
        "6'3,190lbs,20,30\n"
    ),
}


@pytest.fixture(scope="session")
def synthetic_data_dir(tmp_path_factory) -> Path:
    """A directory holding small, hand-written versions of the six files."""
    directory = tmp_path_factory.mktemp("synthetic_kaggle")
    for name, content in SYNTHETIC_FILES.items():
        (directory / name).write_text(content, encoding="utf-8")
    return directory


@pytest.fixture(scope="session")
def synthetic_dataset(synthetic_data_dir):
    return load_dataset(synthetic_data_dir)


@pytest.fixture(scope="session")
def synthetic_graph(synthetic_dataset) -> KnowledgeGraph:
    return KnowledgeGraph(synthetic_dataset)
