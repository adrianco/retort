"""Tests for the CSV data loaders."""
import textwrap

import pytest

from brazilian_soccer import data_loader as dl


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(p)


class TestLoadBrasileirao:
    def test_loads_and_normalizes(self, tmp_path):
        path = _write(tmp_path, "Brasileirao_Matches.csv", '''\
            "datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
            2019-04-27 21:00:00,"Flamengo-RJ","RJ","Cruzeiro-MG","MG",3,1,2019,1
            ''')
        matches = dl.load_brasileirao(path)
        assert len(matches) == 1
        m = matches[0]
        assert m.competition == "Brasileirão Série A"
        assert m.home_team == "Flamengo"
        assert m.away_team == "Cruzeiro"
        assert m.home_score == 3 and m.away_score == 1
        assert m.season == 2019
        assert m.date == "2019-04-27"
        assert m.round == "1"
        assert m.home_key == "flamengo rj"  # key retains state suffix


class TestLoadCup:
    def test_loads_copa_do_brasil(self, tmp_path):
        path = _write(tmp_path, "Brazilian_Cup_Matches.csv", '''\
            "round","datetime","home_team","away_team","home_goal","away_goal","season"
            "1",2012-03-07 16:00:00,"Boavista - RJ","América - MG",0,0,2012
            ''')
        matches = dl.load_cup(path)
        assert len(matches) == 1
        m = matches[0]
        assert m.competition == "Copa do Brasil"
        assert m.away_team == "América"
        assert m.home_score == 0 and m.away_score == 0
        assert m.season == 2012


class TestLoadLibertadores:
    def test_loads_with_stage(self, tmp_path):
        path = _write(tmp_path, "Libertadores_Matches.csv", '''\
            "datetime","home_team","away_team","home_goal","away_goal","season","stage"
            2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"
            ''')
        matches = dl.load_libertadores(path)
        m = matches[0]
        assert m.competition == "Copa Libertadores"
        assert m.home_team == "Nacional"
        assert m.away_team == "Barcelona"
        assert m.stage == "group stage"
        assert m.home_score == 2 and m.away_score == 2


class TestLoadBrFootball:
    def test_maps_tournament_and_derives_season(self, tmp_path):
        path = _write(tmp_path, "BR-Football-Dataset.csv", '''\
            tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
            Serie A,Flamengo,2.0,1.0,Vasco,5.0,3.0,90.0,80.0,10.0,6.0,16:00:00,2023-11-01,1.0,-1.0,WON,LOST,8.0
            Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0
            ''')
        matches = dl.load_br_football(path)
        assert len(matches) == 2
        sa = matches[0]
        assert sa.competition == "Brasileirão Série A"
        assert sa.home_team == "Flamengo" and sa.away_team == "Vasco"
        assert sa.home_score == 2 and sa.away_score == 1
        assert sa.season == 2023
        assert sa.date == "2023-11-01"
        assert matches[1].competition == "Copa do Brasil"


class TestLoadNovo:
    def test_parses_brazilian_date_and_winner(self, tmp_path):
        path = _write(tmp_path, "novo_campeonato_brasileiro.csv", '''\
            ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
            2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,
            ''')
        matches = dl.load_novo(path)
        m = matches[0]
        assert m.competition == "Brasileirão Série A"
        assert m.home_team == "Guarani" and m.away_team == "Vasco"
        assert m.home_score == 4 and m.away_score == 2
        assert m.season == 2003
        assert m.date == "2003-03-29"
        assert m.round == "1"


class TestLoadPlayers:
    def test_loads_fifa_players(self, tmp_path):
        # Header carries a BOM and a leading unnamed index column.
        path = _write(tmp_path, "fifa_data.csv", '''\
            ﻿,ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From,Contract Valid Until,Height,Weight
            0,190871,Neymar Jr,26,p.png,Brazil,f.png,92,93,Paris Saint-Germain,l.png,€118.5M,€290K,2143,Right,5,5,5,High/ Medium,Neymar,Yes,LW,10,"Jul 1 2017",,2022,5'9,150lbs
            ''')
        players = dl.load_players(path)
        assert len(players) == 1
        p = players[0]
        assert p.name == "Neymar Jr"
        assert p.nationality == "Brazil"
        assert p.overall == 92
        assert p.club == "Paris Saint-Germain"
        assert p.position == "LW"
        assert p.age == 26


class TestLoadAll:
    def test_dedupes_overlapping_serie_a_matches(self, tmp_path):
        # Same match present in both Serie A sources -> must collapse to one.
        _write(tmp_path, "Brasileirao_Matches.csv", '''\
            "datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
            2019-04-27 21:00:00,"Flamengo-RJ","RJ","Cruzeiro-MG","MG",3,1,2019,1
            ''')
        _write(tmp_path, "novo_campeonato_brasileiro.csv", '''\
            ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
            2019.01.0004,27/04/2019,2019,1,Flamengo,Cruzeiro,3,1,RJ,MG,Mandante,Maracanã,
            ''')
        matches = dl.load_all_matches(str(tmp_path))
        assert len(matches) == 1

    def test_picks_authoritative_source_despite_date_and_name_drift(self, tmp_path):
        # Real data: the same Serie A season appears in multiple sources with
        # off-by-one dates and team-name spelling drift. Signature dedup can't
        # collapse those, so the loader must pick ONE source per (comp, season).
        _write(tmp_path, "Brasileirao_Matches.csv", '''\
            "datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
            2019-05-26 16:00:00,"Flamengo-RJ","RJ","Athletico-PR","PR",3,2,2019,6
            ''')
        _write(tmp_path, "BR-Football-Dataset.csv", '''\
            tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
            Serie A,Flamengo,3.0,2.0,Atletico Paranaense,5.0,3.0,90.0,80.0,10.0,6.0,16:00:00,2019-05-27,1.0,-1.0,WON,LOST,8.0
            ''')
        matches = dl.load_all_matches(str(tmp_path))
        # Only the higher-priority Brasileirao_Matches row survives.
        assert len(matches) == 1
        assert matches[0].source == "Brasileirao_Matches.csv"

    def test_keeps_seasons_only_present_in_lower_priority_source(self, tmp_path):
        # BR-Football is the sole source of Serie B -> must be kept.
        _write(tmp_path, "Brasileirao_Matches.csv", '''\
            "datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
            2019-05-26 16:00:00,"Flamengo-RJ","RJ","Santos-SP","SP",1,0,2019,6
            ''')
        _write(tmp_path, "BR-Football-Dataset.csv", '''\
            tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
            Serie B,Guarani,2.0,0.0,Cruzeiro,5.0,3.0,90.0,80.0,10.0,6.0,16:00:00,2019-07-27,1.0,-1.0,WON,LOST,8.0
            ''')
        matches = dl.load_all_matches(str(tmp_path))
        comps = {m.competition for m in matches}
        assert comps == {"Brasileirão Série A", "Brasileirão Série B"}

    def test_missing_files_are_skipped(self, tmp_path):
        _write(tmp_path, "Libertadores_Matches.csv", '''\
            "datetime","home_team","away_team","home_goal","away_goal","season","stage"
            2013-02-12 20:15:00,"Nacional (URU)","Barcelona-EQU","2","2",2013,"group stage"
            ''')
        matches = dl.load_all_matches(str(tmp_path))
        assert len(matches) == 1
        assert matches[0].competition == "Copa Libertadores"
