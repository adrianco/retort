import { Match, Player, TeamStats, DataStore } from "./types.js";
export declare function searchMatches(data: DataStore, opts: {
    team?: string;
    homeTeam?: string;
    awayTeam?: string;
    opponent?: string;
    competition?: string;
    season?: number;
    dateFrom?: string;
    dateTo?: string;
    limit?: number;
}): Match[];
export declare function getTeamStats(data: DataStore, team: string, opts?: {
    competition?: string;
    season?: number;
    homeOnly?: boolean;
    awayOnly?: boolean;
}): TeamStats;
export declare function getHeadToHead(data: DataStore, team1: string, team2: string, opts?: {
    competition?: string;
    season?: number;
}): {
    team1Stats: TeamStats;
    team2Stats: TeamStats;
    matches: Match[];
};
export declare function searchPlayers(data: DataStore, opts: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    minOverall?: number;
    maxOverall?: number;
    sortBy?: string;
    limit?: number;
}): Player[];
export declare function getStandings(data: DataStore, season: number, competition?: string): TeamStats[];
export declare function getStatistics(data: DataStore, opts?: {
    competition?: string;
    season?: number;
    team?: string;
}): {
    totalMatches: number;
    totalGoals: number;
    avgGoalsPerMatch: number;
    homeWins: number;
    awayWins: number;
    draws: number;
    homeWinRate: number;
    awayWinRate: number;
    drawRate: number;
    biggestWins: Match[];
};
//# sourceMappingURL=queries.d.ts.map