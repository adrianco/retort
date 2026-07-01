def test_given_running_service_when_health_checked_then_status_is_ok(client):
    # Given a running service
    # When the health check endpoint is called
    response = client.get("/health")

    # Then the response indicates the service is healthy
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
