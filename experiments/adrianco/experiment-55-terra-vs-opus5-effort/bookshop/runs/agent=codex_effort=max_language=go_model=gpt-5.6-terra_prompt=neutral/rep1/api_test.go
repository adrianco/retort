package main

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"testing"
)

func newTestAPI(t *testing.T) http.Handler {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore() error = %v", err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Errorf("Close() error = %v", err)
		}
	})
	return NewAPI(store)
}

func doJSONRequest(t *testing.T, handler http.Handler, method, target string, body string) *httptest.ResponseRecorder {
	t.Helper()
	request := httptest.NewRequest(method, target, bytes.NewBufferString(body))
	if body != "" {
		request.Header.Set("Content-Type", "application/json")
	}
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, request)
	return recorder
}

func decodeResponse[T any](t *testing.T, recorder *httptest.ResponseRecorder) T {
	t.Helper()
	var value T
	if err := json.NewDecoder(recorder.Body).Decode(&value); err != nil {
		t.Fatalf("decode JSON response %q: %v", recorder.Body.String(), err)
	}
	return value
}

func TestBookCRUD(t *testing.T) {
	api := newTestAPI(t)

	createdResponse := doJSONRequest(t, api, http.MethodPost, "/books", `{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"9780441478125"}`)
	if createdResponse.Code != http.StatusCreated {
		t.Fatalf("POST /books status = %d, want %d; body=%s", createdResponse.Code, http.StatusCreated, createdResponse.Body.String())
	}
	created := decodeResponse[Book](t, createdResponse)
	if created.ID == 0 || created.Title != "The Left Hand of Darkness" || created.Author != "Ursula K. Le Guin" {
		t.Fatalf("created book = %#v, want assigned ID and supplied fields", created)
	}

	getResponse := doJSONRequest(t, api, http.MethodGet, "/books/"+itoa(created.ID), "")
	if getResponse.Code != http.StatusOK {
		t.Fatalf("GET /books/{id} status = %d, want %d", getResponse.Code, http.StatusOK)
	}
	if got := decodeResponse[Book](t, getResponse); got != created {
		t.Fatalf("GET /books/{id} = %#v, want %#v", got, created)
	}

	updatedResponse := doJSONRequest(t, api, http.MethodPut, "/books/"+itoa(created.ID), `{"title":"The Dispossessed","author":"Ursula K. Le Guin","year":1974,"isbn":"9780061054884"}`)
	if updatedResponse.Code != http.StatusOK {
		t.Fatalf("PUT /books/{id} status = %d, want %d; body=%s", updatedResponse.Code, http.StatusOK, updatedResponse.Body.String())
	}
	updated := decodeResponse[Book](t, updatedResponse)
	if updated.ID != created.ID || updated.Title != "The Dispossessed" || updated.Year != 1974 {
		t.Fatalf("updated book = %#v, want replacement values", updated)
	}

	deleteResponse := doJSONRequest(t, api, http.MethodDelete, "/books/"+itoa(created.ID), "")
	if deleteResponse.Code != http.StatusNoContent {
		t.Fatalf("DELETE /books/{id} status = %d, want %d", deleteResponse.Code, http.StatusNoContent)
	}
	if body, _ := io.ReadAll(deleteResponse.Result().Body); len(body) != 0 {
		t.Fatalf("DELETE /books/{id} body = %q, want empty", body)
	}

	missingResponse := doJSONRequest(t, api, http.MethodGet, "/books/"+itoa(created.ID), "")
	if missingResponse.Code != http.StatusNotFound {
		t.Fatalf("GET deleted book status = %d, want %d", missingResponse.Code, http.StatusNotFound)
	}
}

func TestListBooksCanFilterByAuthor(t *testing.T) {
	api := newTestAPI(t)

	for _, payload := range []string{
		`{"title":"A Wizard of Earthsea","author":"Ursula K. Le Guin","year":1968,"isbn":"9780547773742"}`,
		`{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}`,
		`{"title":"The Tombs of Atuan","author":"Ursula K. Le Guin","year":1971,"isbn":"9781442459913"}`,
	} {
		response := doJSONRequest(t, api, http.MethodPost, "/books", payload)
		if response.Code != http.StatusCreated {
			t.Fatalf("POST /books status = %d, want %d; body=%s", response.Code, http.StatusCreated, response.Body.String())
		}
	}

	response := doJSONRequest(t, api, http.MethodGet, "/books?author=Ursula%20K.%20Le%20Guin", "")
	if response.Code != http.StatusOK {
		t.Fatalf("GET /books?author=... status = %d, want %d", response.Code, http.StatusOK)
	}
	books := decodeResponse[[]Book](t, response)
	if len(books) != 2 {
		t.Fatalf("filtered books length = %d, want 2; books=%#v", len(books), books)
	}
	for _, book := range books {
		if book.Author != "Ursula K. Le Guin" {
			t.Fatalf("filtered book author = %q, want Ursula K. Le Guin", book.Author)
		}
	}
}

func TestBookValidationAndNotFoundResponses(t *testing.T) {
	api := newTestAPI(t)

	for _, payload := range []string{
		`{"author":"Anonymous","year":2024}`,
		`{"title":"Untitled","author":"   "}`,
		`{"title":"Bad Year","author":"Author","year":-1}`,
		`{"title":"Unexpected","author":"Author","extra":true}`,
	} {
		response := doJSONRequest(t, api, http.MethodPost, "/books", payload)
		if response.Code != http.StatusBadRequest {
			t.Fatalf("POST invalid book %s status = %d, want %d; body=%s", payload, response.Code, http.StatusBadRequest, response.Body.String())
		}
	}

	response := doJSONRequest(t, api, http.MethodPut, "/books/999", `{"title":"Missing","author":"Nobody"}`)
	if response.Code != http.StatusNotFound {
		t.Fatalf("PUT missing book status = %d, want %d; body=%s", response.Code, http.StatusNotFound, response.Body.String())
	}

	response = doJSONRequest(t, api, http.MethodGet, "/books/not-a-number", "")
	if response.Code != http.StatusBadRequest {
		t.Fatalf("GET invalid ID status = %d, want %d; body=%s", response.Code, http.StatusBadRequest, response.Body.String())
	}
}

func TestHealth(t *testing.T) {
	api := newTestAPI(t)
	response := doJSONRequest(t, api, http.MethodGet, "/health", "")
	if response.Code != http.StatusOK {
		t.Fatalf("GET /health status = %d, want %d", response.Code, http.StatusOK)
	}
	status := decodeResponse[map[string]string](t, response)
	if status["status"] != "ok" {
		t.Fatalf("health response = %#v, want status=ok", status)
	}
}

func itoa(value int64) string {
	return strconv.FormatInt(value, 10)
}
