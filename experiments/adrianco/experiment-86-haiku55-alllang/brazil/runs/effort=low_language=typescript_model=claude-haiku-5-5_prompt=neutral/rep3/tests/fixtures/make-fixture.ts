/*
 * Context: Writes a tiny, hand-checked copy of the six dataset files into a temp directory so
 * the arithmetic in query tests can be verified exactly. Mirrors the real column layouts.
 */
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export function makeFixtureDir(): string {
  const dir = mkdtempSync(join(tmpdir(), 'bsm-fixture-'));
  writeFileSync(join(dir, 'Brasileirao_Matches.csv'), [
    '"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"',
    '2019-04-01 16:00:00,"Palmeiras-SP","SP","Santos-SP","SP",2,0,2019,1',
    '2019-04-02 16:00:00,"Santos-SP","SP","Palmeiras-SP","SP",1,1,2019,2',
    '2019-04-03 16:00:00,"Flamengo-RJ","RJ","Palmeiras-SP","SP",0,1,2019,3',
    '2019-04-04 16:00:00,"Palmeiras-SP","SP","Flamengo-RJ","RJ",,,2019,4',
    '2023-05-01 16:00:00,"Palmeiras-SP","SP","Flamengo-RJ","RJ",3,1,2023,1',
    '',
  ].join('\n'));
  writeFileSync(join(dir, 'novo_campeonato_brasileiro.csv'), [
    'ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS',
    // Duplicate of the Palmeiras-Santos match 2-0 from the Brasileirão file (must be de-duplicated)
    '2019.01.0001,01/04/2019,2019,1,Palmeiras,Santos,2,0,SP,SP,Mandante,Allianz,',
    '2019.01.0002,02/04/2019,2019,1,Santos,Palmeiras,1,1,SP,SP,Empate,Vila,',
    '',
  ].join('\n'));
  writeFileSync(join(dir, 'Brazilian_Cup_Matches.csv'), [
    '"round","datetime","home_team","away_team","home_goal","away_goal","season"',
    '"Final",2019-11-20 16:00:00,"Flamengo","Palmeiras",1,0,2019',
    '',
  ].join('\n'));
  writeFileSync(join(dir, 'Libertadores_Matches.csv'), [
    '"datetime","home_team","away_team","home_goal","away_goal","season","stage"',
    '2019-02-12 20:15:00,"Nacional (URU)","Flamengo","2","2",2019,"group stage"',
    '',
  ].join('\n'));
  writeFileSync(join(dir, 'BR-Football-Dataset.csv'), [
    'tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners',
    'Serie A,Palmeiras,2.0,0.0,Santos,1.0,1.0,1.0,1.0,1.0,1.0,16:00:00,2019-04-01,0.0,0.0,DRAW,DRAW,2.0',
    'Serie B,Palmeiras,1.0,1.0,Santos,1.0,1.0,1.0,1.0,1.0,1.0,16:00:00,2019-04-10,0.0,0.0,DRAW,DRAW,2.0',
    '',
  ].join('\n'));
  writeFileSync(join(dir, 'fifa_data.csv'), [
    '﻿,ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Preferred Foot,Height,Weight,Crossing,Finishing,Value,Wage',
    '0,1,Neymar Jr,26,Brazil,92,93,Paris Saint-Germain,LW,10,Right,5\'9,150lbs,80,90,€100M,€300K',
    '1,2,Gabriel Barbosa,21,Brazil,85,88,Flamengo,ST,9,Right,5\'8,150lbs,70,88+2,€40M,€100K',
    '2,3,Diego Alves,31,Brazil,84,84,Flamengo,GK,1,Right,6\'0,170lbs,20,10,€20M,€80K',
    '3,4,Lionel Foo,30,Argentina,80,80,Santos,CAM,8,Left,5\'7,140lbs,60,70,€10M,€50K',
    '',
  ].join('\n'));
  return dir;
}
