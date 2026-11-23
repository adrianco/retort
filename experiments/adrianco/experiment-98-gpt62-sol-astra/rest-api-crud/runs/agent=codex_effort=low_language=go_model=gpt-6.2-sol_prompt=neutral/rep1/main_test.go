package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func testHandler(t *testing.T, path string) http.Handler {
	t.Helper()
	db, err := openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return newHandler(db)
}

func request(t *testing.T, handler http.Handler, method, path, body string, status int) *httptest.ResponseRecorder {
	t.Helper()
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, httptest.NewRequest(method, path, strings.NewReader(body)))
	if rec.Code != status {
		t.Fatalf("%s %s returned %d, want %d. Body: %s", method, path, rec.Code, status, rec.Body)
	}
	if status != http.StatusNoContent && rec.Header().Get("Content-Type") != "application/json" {
		t.Fatalf("expected JSON response to %s %s", method, path)
	}
	return rec
}

func decodeResponse[T any](t *testing.T, response *httptest.ResponseRecorder) T {
	t.Helper()
	var value T
	if err := json.Unmarshal(response.Body.Bytes(), &value); err != nil {
		t.Fatal(err)
	}
	return value
}

const sampleBook = `{"title":"Kindred","author":"Octavia E. Butler","year":1979,"isbn":"9780807083697"}`

func TestBookLifecycle(t *testing.T) {
	handler := testHandler(t, ":memory:")
	created := request(t, handler, "POST", "/books", sampleBook, 201)
	path := created.Header().Get("Location")
	if !strings.HasPrefix(path, "/books/") {
		t.Fatalf("unexpected Location: %q", path)
	}
	b := decodeResponse[book](t, created)
	if b.ID <= 0 || b.bookInput != (bookInput{"Kindred", "Octavia E. Butler", 1979, "9780807083697"}) {
		t.Fatalf("unexpected created book: %+v", b)
	}
	if got := decodeResponse[book](t, request(t, handler, "GET", path, "", 200)); got != b {
		t.Fatalf("read %+v, want %+v", got, b)
	}
	updated := decodeResponse[book](t, request(t, handler, "PUT", path,
		`{"title":"Beloved","author":"Toni Morrison","year":1987,"isbn":"9781400033416"}`, 200))
	if updated.ID != b.ID || updated.bookInput != (bookInput{"Beloved", "Toni Morrison", 1987, "9781400033416"}) {
		t.Fatalf("unexpected updated book: %+v", updated)
	}
	if got := decodeResponse[book](t, request(t, handler, "GET", path, "", 200)); got != updated {
		t.Fatalf("read %+v, want %+v", got, updated)
	}
	if deleted := request(t, handler, "DELETE", path, "", 204); deleted.Body.Len() != 0 {
		t.Fatalf("delete returned a body: %s", deleted.Body)
	}
	request(t, handler, "GET", path, "", 404)
	request(t, handler, "PUT", path, sampleBook, 404)
	request(t, handler, "DELETE", path, "", 404)
}

func TestListAndAuthorFilter(t *testing.T) {
	handler := testHandler(t, ":memory:")
	empty := decodeResponse[[]book](t, request(t, handler, "GET", "/books", "", 200))
	if empty == nil || len(empty) != 0 {
		t.Fatalf("expected an empty JSON array, got %#v", empty)
	}
	request(t, handler, "POST", "/books", sampleBook, 201)
	request(t, handler, "POST", "/books", `{"title":"Beloved","author":"Toni Morrison"}`, 201)
	all := decodeResponse[[]book](t, request(t, handler, "GET", "/books", "", 200))
	if len(all) != 2 {
		t.Fatalf("expected two books, got %+v", all)
	}
	filtered := decodeResponse[[]book](t, request(t, handler, "GET", "/books?author=Toni+Morrison", "", 200))
	if len(filtered) != 1 || filtered[0].Title != "Beloved" {
		t.Fatalf("unexpected filter result: %+v", filtered)
	}
}

func TestValidation(t *testing.T) {
	handler := testHandler(t, ":memory:")
	path := request(t, handler, "POST", "/books", sampleBook, 201).Header().Get("Location")
	for _, body := range []string{`{"author":"Author"}`, `{"title":"Title","author":" "}`, `{`, sampleBook + " {}"} {
		request(t, handler, "POST", "/books", body, 400)
		request(t, handler, "PUT", path, body, 400)
	}
	request(t, handler, "GET", "/books/xyz", "", 400)
	request(t, handler, "PATCH", path, "", 405)
	request(t, handler, "GET", "/unknown", "", 404)
	got := decodeResponse[book](t, request(t, handler, "GET", path, "", 200))
	if got.Title != "Kindred" {
		t.Fatalf("invalid update changed the book: %+v", got)
	}
}

func TestPersistenceAndHealth(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	db, err := openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	handler := newHandler(db)
	defer db.Close()
	location := request(t, handler, "POST", "/books", sampleBook, 201).Header().Get("Location")
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	request(t, handler, "GET", "/health", "", 503)

	handler = testHandler(t, path)
	health := decodeResponse[map[string]string](t, request(t, handler, "GET", "/health", "", 200))
	if health["status"] != "ok" {
		t.Fatalf("unexpected health response: %v", health)
	}
	b := decodeResponse[book](t, request(t, handler, "GET", location, "", 200))
	if b.Title != "Kindred" {
		t.Fatalf("unexpected persisted book: %+v", b)
	}
}
