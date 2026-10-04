"""Head-to-head comparisons and traditional derbies."""


def test_should_count_wins_and_draws_for_each_side(archive, rivalries):
    archive.has_match("Palmeiras 2-0 Santos")
    archive.has_match("Santos 1-0 Palmeiras")
    archive.has_match("Palmeiras 3-1 Santos")
    archive.has_match("Santos 2-2 Palmeiras")

    rivalries.compare("Palmeiras", "Santos")

    rivalries.confirm_head_to_head(Palmeiras=2, Santos=1, draws=1)


def test_should_total_the_goals_each_side_scored(archive, rivalries):
    archive.has_match("Palmeiras 2-0 Santos")
    archive.has_match("Santos 1-0 Palmeiras")

    rivalries.compare("Palmeiras", "Santos")

    rivalries.confirm_goals(Palmeiras=2, Santos=1)


def test_should_name_a_traditional_derby(archive, rivalries):
    archive.has_match("Flamengo 2-1 Fluminense")

    rivalries.compare("Flamengo", "Fluminense")

    rivalries.confirm_derby_name("Fla-Flu")


def test_should_find_all_derbies_played_in_a_season(archive, rivalries):
    archive.has_match("Grêmio 1-1 Internacional", season=2023)
    archive.has_match("Corinthians 2-1 Palmeiras", season=2023)
    archive.has_match("Grêmio 3-0 Bahia", season=2023)
    archive.has_match("Corinthians 1-0 Palmeiras", season=2022)

    rivalries.find_derbies(season=2023)

    rivalries.confirm_derbies("Grêmio 1-1 Internacional", "Corinthians 2-1 Palmeiras")


def test_should_say_how_many_more_derbies_there_are_beyond_those_listed(archive, assistant):
    archive.has_matches("Grêmio 1-1 Internacional", "Internacional 2-0 Grêmio", "Bahia 0-0 Vitória", season=2023)

    assistant.ask_for_derbies(season=2023, at_most=1)

    assistant.confirm_answer_reads("(2 more derbies in dataset)")
