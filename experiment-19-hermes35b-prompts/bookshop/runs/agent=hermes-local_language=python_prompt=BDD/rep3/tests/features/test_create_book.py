"""BDD step definitions for Create Book feature."""
from pytest_bdd import scenarios, given, when, then

scenarios("create_book.feature")


@given("the service is running")
def _():
    pass


@when("I create a book with the title The Great Gatsby and author F. Scott Fitzgerald")
def _(app_client, scenario_data):
    resp = app_client.post("/books", json={
        "title": "The Great Gatsby", "author": "F. Scott Fitzgerald"
    })
    scenario_data["response"] = resp
    if resp.status_code == 201:
        scenario_data["book_id"] = resp.get_json()["id"]


@when("I create a book with the title 1984 and author George Orwell and year 1949 and isbn 978-0451524935")
def _(app_client, scenario_data):
    resp = app_client.post("/books", json={
        "title": "1984", "author": "George Orwell",
        "year": 1949, "isbn": "978-0451524935"
    })
    scenario_data["response"] = resp
    if resp.status_code == 201:
        scenario_data["book_id"] = resp.get_json()["id"]


@when("I create a book with missing title")
def _(app_client, scenario_data):
    resp = app_client.post("/books", json={"author": "Some Author"})
    scenario_data["response"] = resp


@when("I create a book with missing author")
def _(app_client, scenario_data):
    resp = app_client.post("/books", json={"title": "Some Title"})
    scenario_data["response"] = resp


@then("the response status is 201")
def _(scenario_data):
    assert scenario_data["response"].status_code == 201


@then("the response body contains the book data")
def _(scenario_data):
    data = scenario_data["response"].get_json()
    assert "id" in data
    assert "title" in data
    assert "author" in data


@then("the created book has a generated id")
def _(scenario_data):
    data = scenario_data["response"].get_json()
    assert data["id"] is not None


@then("the response status is 400")
def _(scenario_data):
    assert scenario_data["response"].status_code == 400


@then("the book year is 1949")
def _(scenario_data):
    data = scenario_data["response"].get_json()
    assert data["year"] == 1949


@then("the book isbn is 978-0451524935")
def _(scenario_data):
    data = scenario_data["response"].get_json()
    assert data["isbn"] == "978-0451524935"
