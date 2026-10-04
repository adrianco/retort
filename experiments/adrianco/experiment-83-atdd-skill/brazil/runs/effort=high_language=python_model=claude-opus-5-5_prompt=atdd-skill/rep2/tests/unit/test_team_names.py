"""Unit tests: parsing raw team names and resolving questions to clubs (fine-grained cases the
acceptance specs deliberately leave to this level)."""
import pytest

from brazilian_soccer_mcp.teams import TeamNotFound, TeamRegistry, parse_name


@pytest.mark.parametrize("raw, base, qualifier", [
    ("Palmeiras-SP", "palmeiras", "SP"),
    ("Palmeiras - SP", "palmeiras", "SP"),
    ("Sociedade Esportiva Palmeiras", "palmeiras", "SP"),
    ("Sao Paulo", "sao paulo", None),
    ("São Paulo - SP", "sao paulo", "SP"),
    ("Atletico-PR", "athletico", "PR"),
    ("Athletico Paranaense - PR", "athletico", "PR"),
    ("Atlético Mineiro", "atletico", "MG"),
    ("Atletico Goianiense", "atletico", "GO"),
    ("Vasco Da Gama RJ", "vasco da gama", "RJ"),
    ("Barcelona-EQU", "barcelona", "EQU"),
    ("Nacional (URU)", "nacional", "URU"),
    ("C. R. B. - AL", "crb", "AL"),
    ("Fortaleza EC", "fortaleza", None),
    ("America FC (Minas Gerais)", "america", "MG"),
    ("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista", "RJ"),
    ("Colo-Colo", "colo colo", None),
    ("Paris Saint-Germain", "paris saint germain", None),
])
def test_parses_base_name_and_qualifier(raw, base, qualifier):
    assert parse_name(raw)[:2] == (base, qualifier)


def registry(*names, international=()):
    teams = TeamRegistry()
    for name in names + tuple(international):
        teams.observe(name)
    for name in names:
        teams.key_for(name)
    for name in international:
        teams.key_for(name, international=True)
    return teams


def test_a_bare_name_means_the_famous_club():
    teams = registry("Botafogo - RJ", "Botafogo - PB")
    assert teams.key_for("Botafogo") == "botafogo|RJ"


def test_a_bare_domestic_name_takes_its_only_known_state():
    teams = registry("Ituano - SP")
    assert teams.key_for("Ituano") == "ituano|SP"


def test_a_bare_international_name_does_not_borrow_a_brazilian_state():
    teams = registry("River Plate - SE", international=["River Plate"])
    assert teams.key_for("River Plate", international=True) == "river plate"
    assert teams.display("river plate|SE") == "River Plate-SE"


def test_questions_resolve_without_accents_or_suffixes():
    teams = registry("Grêmio - RS", "São Paulo - SP")
    assert teams.resolve("gremio") == "gremio|RS"
    assert teams.resolve("Sao Paulo FC") == "sao paulo|SP"


def test_unknown_teams_get_suggestions():
    teams = registry("Flamengo - RJ")
    with pytest.raises(TeamNotFound, match="Flamengo"):
        teams.resolve("Flamingo United")
