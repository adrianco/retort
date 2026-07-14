"""BDD step definitions for Health Check feature."""
from pytest_bdd import scenarios, given, when, then

scenarios("health.feature")


@given("the service is running")
def _():
    pass


@when("I send a GET request to /health")
def _(app_client, scenario_data):
    scenario_data["response"] = app_client.get("/health")


@then("the response status is 200")
def _(scenario_data):
    assert scenario_data["response"].status_code == 200


@then("the response body contains status ok")
def _(scenario_data):
    data = scenario_data["response"].get_json()
    assert data["status"] == "ok"
