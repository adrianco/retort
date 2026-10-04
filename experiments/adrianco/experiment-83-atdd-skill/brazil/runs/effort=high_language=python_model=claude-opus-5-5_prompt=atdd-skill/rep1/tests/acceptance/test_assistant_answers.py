"""What a connected AI assistant experiences: discoverable capabilities and readable answers."""


def test_should_offer_every_category_of_question_to_an_assistant(assistant):
    assistant.discover_capabilities()

    assistant.confirm_can_answer("matches", "teams", "players", "competitions", "statistics")


def test_should_answer_in_readable_text(archive, assistant):
    archive.has_match("Flamengo 2-1 Fluminense", date="2023-09-03", season=2023, league_round=22)

    assistant.ask_for_matches_between("Flamengo", "Fluminense")

    assistant.confirm_answer_reads("2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)")


def test_should_explain_when_it_does_not_know_a_team(archive, assistant):
    archive.has_match("Flamengo 2-1 Fluminense")

    assistant.ask_for_record_of("Real Madrid")

    assistant.confirm_answer_explains("No matches found for team 'Real Madrid'")
