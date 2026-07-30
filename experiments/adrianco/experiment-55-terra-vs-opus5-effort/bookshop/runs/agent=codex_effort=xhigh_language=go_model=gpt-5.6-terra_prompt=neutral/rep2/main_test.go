package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	db, err := OpenDatabase(fmt.Sprintf("file:%s?mode=memory&cache=shared", strings.ReplaceAll(t.Name(), "/", "_")))
	if err != nil {
		t.Fatalf("OpenDatabase() error = %v", err)
	}
	db.SetMaxOpenConns(1)
	t.Cleanup(func() { db.Close() })
	return NewServer(db)
}

func request(t *testing.T, handler http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, req)
	return response
}

func decodeResponse[T any](t *testing.T, response *httptest.ResponseRecorder) T {
	t.Helper()
	var value T
	if err := json.NewDecoder(response.Body).Decode(&value); err != nil {
		t.Fatalf("decode response: %v; body: %s", err, response.Body.String())
	}
	return value
}

func TestCreateAndGetBook(t *testing.T) {
	handler := newTestServer(t)
	createdResponse := request(t, handler, http.MethodPost, "/books", `{"title":" Kindred ","author":"Octavia E. Butler","year":1979,"isbn":"978-0807083697"}`)
	if createdResponse.Code != http.StatusCreated {
		t.Fatalf("POST /books status = %d, want %d; body: %s", createdResponse.Code, http.StatusCreated, createdResponse.Body)
	}
	created := decodeResponse[Book](t, createdResponse)
	if created.ID < 1 || created.Title != "Kindred" || created.Author != "Octavia E. Butler" || created.Year != 1979 {
		t.Fatalf("created book = %#v, want saved book with normalized title", created)
	}

	gotResponse := request(t, handler, http.MethodGet, fmt.Sprintf("/books/%d", created.ID), "")
	if gotResponse.Code != http.StatusOK {
		t.Fatalf("GET /books/{id} status = %d, want %d", gotResponse.Code, http.StatusOK)
	}
	got := decodeResponse[Book](t, gotResponse)
	if got != created {
		t.Fatalf("GET /books/{id} = %#v, want %#v", got, created)
	}
}

func TestListCanFilterByAuthor(t *testing.T) {
	handler := newTestServer(t)
	for _, body := range []string{
		`{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"1"}`,
		`{"title":"Parable of the Sower","author":"Octavia E. Butler","year":1993,"isbn":"2"}`,
		`{"title":"A Wizard of Earthsea","author":"Ursula K. Le Guin","year":1968,"isbn":"3"}`,
	} {
		response := request(t, handler, http.MethodPost, "/books", body)
		if response.Code != http.StatusCreated {
			t.Fatalf("POST /books status = %d, want %d", response.Code, http.StatusCreated)
		}
	}

	response := request(t, handler, http.MethodGet, "/books?author=Octavia%20E.%20Butler", "")
	if response.Code != http.StatusOK {
		t.Fatalf("GET /books?author= status = %d, want %d", response.Code, http.StatusOK)
	}
	books := decodeResponse[[]Book](t, response)
	if len(books) != 2 || books[0].Title != "Kindred" || books[1].Title != "Parable of the Sower" {
		t.Fatalf("filtered books = %#v, want two Butler books in insertion order", books)
	}
}

func TestUpdateThenDeleteBook(t *testing.T) {
	handler := newTestServer(t)
	created := decodeResponse[Book](t, request(t, handler, http.MethodPost, "/books", `{"title":"Draft","author":"Author"}`))
	path := fmt.Sprintf("/books/%d", created.ID)

	updatedResponse := request(t, handler, http.MethodPut, path, `{"title":"Final","author":"New Author","year":2024,"isbn":"updated"}`)
	if updatedResponse.Code != http.StatusOK {
		t.Fatalf("PUT /books/{id} status = %d, want %d; body: %s", updatedResponse.Code, http.StatusOK, updatedResponse.Body)
	}
	updated := decodeResponse[Book](t, updatedResponse)
	if updated.Title != "Final" || updated.Author != "New Author" || updated.Year != 2024 || updated.ISBN != "updated" {
		t.Fatalf("updated book = %#v, want replacement values", updated)
	}

	deletedResponse := request(t, handler, http.MethodDelete, path, "")
	if deletedResponse.Code != http.StatusNoContent {
		t.Fatalf("DELETE /books/{id} status = %d, want %d", deletedResponse.Code, http.StatusNoContent)
	}
	notFoundResponse := request(t, handler, http.MethodGet, path, "")
	if notFoundResponse.Code != http.StatusNotFound {
		t.Fatalf("GET after DELETE status = %d, want %d", notFoundResponse.Code, http.StatusNotFound)
	}
}

func TestValidationAndHealth(t *testing.T) {
	handler := newTestServer(t)
	invalid := request(t, handler, http.MethodPost, "/books", `{"title":"","author":"Writer"}`)
	if invalid.Code != http.StatusBadRequest {
		t.Fatalf("POST invalid book status = %d, want %d", invalid.Code, http.StatusBadRequest)
	}
	errorBody := decodeResponse[map[string]string](t, invalid)
	if errorBody["error"] != "title is required" {
		t.Fatalf("validation response = %#v", errorBody)
	}

	health := request(t, handler, http.MethodGet, "/health", "")
	if health.Code != http.StatusOK {
		t.Fatalf("GET /health status = %d, want %d", health.Code, http.StatusOK)
	}
	if got := decodeResponse[map[string]string](t, health)["status"]; got != "ok" {
		t.Fatalf("health status = %q, want ok", got)
	}
}
