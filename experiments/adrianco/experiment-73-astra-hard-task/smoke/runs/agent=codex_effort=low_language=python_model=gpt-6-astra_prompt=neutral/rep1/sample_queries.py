"""Natural-language examples and equivalent tool calls for an MCP-connected LLM.

The host LLM performs language interpretation and keeps follow-up context. These
examples are also executed by test_soccer.py against the actual datasets.
"""
SAMPLE_QUERIES = [
    ('Show me all Flamengo vs Fluminense matches', 'head_to_head', {'team': 'Flamengo', 'opponent': 'Fluminense'}),
    ('What matches did Palmeiras play in 2023?', 'matches', {'filters': {'team': 'Palmeiras', 'season': 2023}}),
    ('Find all Copa do Brasil finals', 'matches', {'filters': {'competition': 'Copa do Brasil', 'stage': 'final'}}),
    ("What is Corinthians’ home record in 2022?", 'team_stats', {'team': 'Corinthians', 'filters': {'venue': 'home', 'season': 2022}}),
    ('Which team scored the most goals in Serie A 2023?', 'analysis', {'filters': {'competition': 'Serie A', 'season': 2023}, 'limit': 1}),
    ('Compare Palmeiras and Santos head-to-head', 'head_to_head', {'team': 'Palmeiras', 'opponent': 'Santos'}),
    ('Find all Brazilian players in the dataset', 'players', {'nationality': 'Brazil'}),
    ('Who are the highest-rated players at Flamengo?', 'players', {'club': 'Flamengo'}),
    ('Show me all forwards from São Paulo FC', 'players', {'club': 'São Paulo FC', 'position': 'forward'}),
    ('Who led the calculated 2019 Brasileirão table?', 'standings', {'competition': 'Brasileirão', 'season': 2019}),
    ('Show the 2018 Copa Libertadores bracket data', 'competition_info', {'competition': 'Libertadores', 'season': 2018}),
    ('Which teams occupied the bottom positions in 2020?', 'standings', {'competition': 'Serie A', 'season': 2020}),
    ("What’s the average goals per match in the Brasileirão?", 'analysis', {'filters': {'competition': 'Brasileirão'}}),
    ('Which team has the best away record?', 'analysis', {}),
    ('Show me the biggest wins in the dataset', 'analysis', {}),
    ('When did Flamengo last play Corinthians?', 'head_to_head', {'team': 'Flamengo', 'opponent': 'Corinthians', 'limit': 1}),
    ('Who is Neymar?', 'players', {'name': 'Neymar'}),
    ('Which players play for Flamengo in the FIFA snapshot?', 'players', {'club': 'Flamengo'}),
    ('Show me all derbies in 2023', 'matches', {'filters': {'derbies': True, 'season': 2023}}),
    ('What competitions has Palmeiras played in?', 'team_info', {'team': 'Palmeiras'}),
    ('Which team has the best home record?', 'analysis', {}),
    ('Who are the top Brazilian players?', 'players', {'nationality': 'Brazilian', 'limit': 10}),
    ('Compare the 2018 and 2019 seasons', 'compare_seasons', {'seasons': [2018, 2019]}),
    ('Find matches played in September 2023', 'matches', {'filters': {'start_date': '2023-09-01', 'end_date': '2023-09-30'}}),
    ('Show Palmeiras away matches in the Copa do Brasil', 'matches', {'filters': {'team': 'Palmeiras', 'venue': 'away', 'competition': 'Copa do Brasil'}}),
    ('Show Corinthians relationships in the knowledge graph', 'graph', {'entity': 'Corinthians'}),
    ('Which datasets and licenses support these answers?', 'coverage', {}),
]
