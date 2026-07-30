"""Filtering, sorting and paging on ``GET /books``."""

from __future__ import annotations

import pytest

from bookapi.repository import _order_by


def titles(response):
    return [book["title"] for book in response.get_json()]


def test_author_filter_returns_only_that_authors_books(client, library):
    response = client.get("/books?author=Chinua Achebe")

    assert response.status_code == 200
    assert titles(response) == ["Things Fall Apart", "No Longer at Ease"]
    assert response.headers["X-Total-Count"] == "2"


@pytest.mark.parametrize("author", ["chinua achebe", "CHINUA ACHEBE", "Chinua ACHEBE"])
def test_author_filter_ignores_case(client, library, author):
    assert len(client.get(f"/books?author={author}").get_json()) == 2


def test_author_filter_ignores_surrounding_whitespace(client, library):
    assert len(client.get("/books?author=%20Chinua%20Achebe%20").get_json()) == 2


def test_author_filter_with_no_match_returns_an_empty_list(client, library):
    response = client.get("/books?author=Nobody At All")

    assert response.status_code == 200
    assert response.get_json() == []
    assert response.headers["X-Total-Count"] == "0"


def test_author_filter_is_a_whole_name_match_not_a_substring(client, library):
    assert client.get("/books?author=Achebe").get_json() == []


def test_empty_author_filter_is_treated_as_no_filter(client, library):
    assert len(client.get("/books?author=").get_json()) == 3


def test_case_insensitivity_covers_ascii_only(client):
    """A documented limitation, pinned so it cannot change unnoticed.

    Both filters fold case through SQLite built-ins - LIKE for title, COLLATE
    NOCASE for author - and neither touches non-ASCII letters.  Matching "emile"
    to "Émile" would need a custom Unicode collation.
    """
    client.post("/books", json={"title": "Émile", "author": "Émile Zola"})

    # Exact-case queries work for any script.
    assert len(client.get("/books?title=%C3%89mile").get_json()) == 1
    assert len(client.get("/books?author=%C3%89mile%20Zola").get_json()) == 1
    # ASCII letters fold.
    assert len(client.get("/books?author=%C3%89MILE%20ZOLA").get_json()) == 1
    # The accented letter does not.
    assert client.get("/books?title=%C3%A9mile").get_json() == []
    assert client.get("/books?author=%C3%A9mile%20zola").get_json() == []


def test_title_filter_matches_substrings_case_insensitively(client, library):
    assert titles(client.get("/books?title=fall")) == ["Things Fall Apart"]
    assert len(client.get("/books?title=a").get_json()) == 3


def test_title_filter_treats_wildcards_literally(client, library):
    """Asserting only that a wildcard finds nothing would also hold if the escape
    were dropped, so this pins the positive case: '%' must match a real '%'."""
    client.post("/books", json={"title": "100% Pure", "author": "A"})
    client.post("/books", json={"title": "Cost_Benefit", "author": "A"})

    assert titles(client.get("/books?title=%25")) == ["100% Pure"]
    assert titles(client.get("/books?title=_")) == ["Cost_Benefit"]
    # An unescaped '_' is LIKE's single-character wildcard and would match all 5.
    assert len(client.get("/books").get_json()) == 5


def test_year_filter(client, library):
    assert titles(client.get("/books?year=1960")) == ["No Longer at Ease"]
    assert client.get("/books?year=1900").get_json() == []


def test_filters_combine(client, library):
    assert titles(client.get("/books?author=Chinua Achebe&year=1958")) == [
        "Things Fall Apart"
    ]
    assert client.get("/books?author=Chinua Achebe&year=1969").get_json() == []


def test_default_order_is_by_id(client, library):
    assert [b["id"] for b in client.get("/books").get_json()] == [
        b["id"] for b in library
    ]


def test_sort_by_column(client, library):
    assert titles(client.get("/books?sort=title")) == [
        "No Longer at Ease",
        "The Left Hand of Darkness",
        "Things Fall Apart",
    ]
    assert titles(client.get("/books?sort=-year")) == [
        "The Left Hand of Darkness",
        "No Longer at Ease",
        "Things Fall Apart",
    ]


def test_text_sorting_ignores_case(client):
    """The data is picked so binary and case-insensitive order actually differ.

    SQLite's default collation compares bytes, so every capital letter sorts
    ahead of every lowercase one: "Banana" (0x42) would come before "apple"
    (0x61).  Case-insensitively, "apple" comes first.
    """
    for title in ("apple", "Banana"):
        client.post("/books", json={"title": title, "author": "A"})

    assert titles(client.get("/books?sort=title")) == ["apple", "Banana"]
    assert titles(client.get("/books?sort=-title")) == ["Banana", "apple"]


def test_author_sorting_ignores_case(client):
    for author in ("achebe", "Zola"):
        client.post("/books", json={"title": f"by {author}", "author": author})

    response = client.get("/books?sort=author")

    assert [b["author"] for b in response.get_json()] == ["achebe", "Zola"]


def test_sort_on_an_unknown_column_is_rejected(client, library):
    response = client.get("/books?sort=isbn")

    assert response.status_code == 400
    assert "sort" in response.get_json()["details"]


@pytest.mark.parametrize("sort", ["--title", "-+title", "title-", "id;drop", "id 1"])
def test_malformed_sort_values_are_rejected(client, library, sort):
    """Only one leading '-' or '+' is a direction prefix; the rest must be an
    exact column name, which is what keeps the ORDER BY interpolation safe."""
    response = client.get(f"/books?sort={sort}")

    assert response.status_code == 400
    assert "sort" in response.get_json()["details"]


@pytest.mark.parametrize("sort", ["id", "-id", "+id"])
def test_direction_prefixes_are_accepted(client, library, sort):
    assert client.get(f"/books?sort={sort}").status_code == 200


def test_blank_sort_falls_back_to_the_default(client, library):
    assert titles(client.get("/books?sort=")) == titles(client.get("/books"))


def test_limit_and_offset_page_through_results(client, library):
    first = client.get("/books?limit=2")
    assert len(first.get_json()) == 2
    # X-Total-Count reports every match, not just this page.
    assert first.headers["X-Total-Count"] == "3"

    second = client.get("/books?limit=2&offset=2")
    assert len(second.get_json()) == 1
    assert second.headers["X-Total-Count"] == "3"

    assert titles(first) + titles(second) == titles(client.get("/books"))


def test_offset_without_limit_skips_from_the_front(client, library):
    assert titles(client.get("/books?offset=1")) == titles(client.get("/books"))[1:]


def test_offset_past_the_end_returns_an_empty_page(client, library):
    response = client.get("/books?offset=99")

    assert response.status_code == 200
    assert response.get_json() == []
    assert response.headers["X-Total-Count"] == "3"


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=-1", "limit=abc", "limit=99999", "offset=-1", "year=x"]
)
def test_invalid_query_parameters_are_rejected(client, query):
    response = client.get(f"/books?{query}")

    assert response.status_code == 400
    assert response.get_json()["code"] == "validation_error"


def test_the_order_by_clause_always_carries_an_id_tiebreaker():
    """A white-box test on purpose.

    SQLite's sorter happens to preserve scan order for equal keys, so removing
    the explicit ``, id`` from ORDER BY leaves every black-box paging assertion
    green while quietly downgrading stable paging from guaranteed to incidental.
    Asserting on the generated SQL is the only way to pin the intent.
    """
    assert _order_by("author", False) == "ORDER BY author COLLATE NOCASE ASC, id ASC"
    assert _order_by("year", True) == "ORDER BY year DESC, id DESC"
    assert _order_by("id", False) == "ORDER BY id ASC, id ASC"


def test_paging_covers_every_row_once_when_the_sort_key_ties(client):
    """Every row shares one author, so ``id`` is the only thing separating them.
    Paging must therefore hand back id order with no gaps and no repeats."""
    created = [
        client.post(
            "/books", json={"title": f"Book {index}", "author": "Same Author"}
        ).get_json()["id"]
        for index in range(5)
    ]

    paged = []
    for offset in (0, 2, 4):
        page = client.get(f"/books?sort=author&limit=2&offset={offset}").get_json()
        paged.extend(book["id"] for book in page)

    assert paged == created


def test_descending_sort_also_breaks_ties_by_id(client):
    created = [
        client.post("/books", json={"title": "Same", "author": "A"}).get_json()["id"]
        for _ in range(4)
    ]

    ids = [b["id"] for b in client.get("/books?sort=-title").get_json()]

    assert ids == sorted(created, reverse=True)


@pytest.mark.parametrize("offset", [2**63, 2**63 + 1, 10**25])
def test_offset_beyond_sqlites_integer_range_is_a_400_not_a_crash(client, offset):
    """An offset this large cannot be bound as a SQLite parameter; unbounded, it
    reached the driver and raised OverflowError as a 500."""
    response = client.get(f"/books?offset={offset}")

    assert response.status_code == 400
    assert response.get_json()["details"] == {
        "offset": f"must be between 0 and {2**63 - 1}"
    }


def test_the_largest_bindable_offset_is_accepted(client, library):
    response = client.get(f"/books?offset={2**63 - 1}")

    assert response.status_code == 200
    assert response.get_json() == []
