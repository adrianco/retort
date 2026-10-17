package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var req *http.Request
	if body == "" {
		req = httptest.NewRequest(method, path, nil)
	} else {
		req = httptest.NewRequest(method, path, bytes.NewBufferString(body))
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decodeBook(t *testing.T, rec *httptest.ResponseRecorder) Book {
	t.Helper()
	var b Book
	if err := json.Unmarshal(rec.Body.Bytes(), &b); err != nil {
		t.Fatalf("decode book: %v (body=%s)", err, rec.Body.String())
	}
	return b
}

func decodeError(t *testing.T, rec *httptest.ResponseRecorder) string {
	t.Helper()
	var m map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &m); err != nil {
		t.Fatalf("decode error body: %v (body=%s)", err, rec.Body.String())
	}
	s, _ := m["error"].(string)
	return s
}

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}`

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodGet, "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := rec.Body.String(); got != `{"status":"ok"}`+"\n" {
		t.Fatalf("body = %q", got)
	}
}

func TestBookCRUDLifecycle(t *testing.T) {
	h := newTestServer(t)

	// Create
	rec := do(t, h, http.MethodPost, "/books", dune)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body=%s", rec.Code, rec.Body.String())
	}
	created := decodeBook(t, rec)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Fatalf("Location = %q", loc)
	}

	// Get
	rec = do(t, h, http.MethodGet, "/books/1", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d", rec.Code)
	}
	if got := decodeBook(t, rec); got != created {
		t.Fatalf("get = %+v, want %+v", got, created)
	}

	// Update
	update := `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`
	rec = do(t, h, http.MethodPut, "/books/1", update)
	if rec.Code != http.StatusOK {
		t.Fatalf("update status = %d, body=%s", rec.Code, rec.Body.String())
	}
	updated := decodeBook(t, rec)
	if updated.Title != "Dune Messiah" || updated.Year != 1969 || updated.ISBN != "" {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	// Delete
	rec = do(t, h, http.MethodDelete, "/books/1", "")
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", rec.Code)
	}
	rec = do(t, h, http.MethodGet, "/books/1", "")
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want 404", rec.Code)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h := newTestServer(t)

	// Empty collection returns [] rather than null.
	rec := do(t, h, http.MethodGet, "/books", "")
	if rec.Code != http.StatusOK || rec.Body.String() != "[]\n" {
		t.Fatalf("empty list = %d %q", rec.Code, rec.Body.String())
	}

	do(t, h, http.MethodPost, "/books", dune)
	do(t, h, http.MethodPost, "/books", `{"title":"Emma","author":"Jane Austen","year":1815}`)
	do(t, h, http.MethodPost, "/books", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)

	rec = do(t, h, http.MethodGet, "/books", "")
	var all []Book
	json.Unmarshal(rec.Body.Bytes(), &all)
	if len(all) != 3 {
		t.Fatalf("list length = %d, want 3", len(all))
	}

	rec = do(t, h, http.MethodGet, "/books?author=Frank+Herbert", "")
	var herbert []Book
	json.Unmarshal(rec.Body.Bytes(), &herbert)
	if len(herbert) != 2 {
		t.Fatalf("author filter returned %d books, want 2", len(herbert))
	}
	for _, b := range herbert {
		if b.Author != "Frank Herbert" {
			t.Fatalf("filter leaked book by %q", b.Author)
		}
	}

	rec = do(t, h, http.MethodGet, "/books?author=Nobody", "")
	if rec.Body.String() != "[]\n" {
		t.Fatalf("no-match filter body = %q", rec.Body.String())
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestServer(t)

	tests := []struct {
		name       string
		body       string
		wantStatus int
	}{
		{"missing title", `{"author":"A"}`, http.StatusUnprocessableEntity},
		{"missing author", `{"title":"T"}`, http.StatusUnprocessableEntity},
		{"blank title is whitespace", `{"title":"   ","author":"A"}`, http.StatusUnprocessableEntity},
		{"year out of range", `{"title":"T","author":"A","year":-5}`, http.StatusUnprocessableEntity},
		{"bad isbn", `{"title":"T","author":"A","isbn":"abc"}`, http.StatusUnprocessableEntity},
		{"malformed json", `{"title":`, http.StatusBadRequest},
		{"unknown field", `{"title":"T","author":"A","pages":10}`, http.StatusBadRequest},
		{"empty body", ``, http.StatusBadRequest},
		{"wrong type", `{"title":"T","author":"A","year":"1990"}`, http.StatusBadRequest},
		{"trailing data", `{"title":"T","author":"A"}{}`, http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, http.MethodPost, "/books", tt.body)
			if rec.Code != tt.wantStatus {
				t.Fatalf("status = %d, want %d (body=%s)", rec.Code, tt.wantStatus, rec.Body.String())
			}
		})
	}

	// Field-level details are reported for validation failures.
	rec := do(t, h, http.MethodPost, "/books", `{}`)
	var body struct {
		Error   string            `json:"error"`
		Details map[string]string `json:"details"`
	}
	json.Unmarshal(rec.Body.Bytes(), &body)
	if body.Details["title"] == "" || body.Details["author"] == "" {
		t.Fatalf("expected title and author details, got %+v", body)
	}

	// Nothing was persisted by the failed requests.
	rec = do(t, h, http.MethodGet, "/books", "")
	if rec.Body.String() != "[]\n" {
		t.Fatalf("invalid requests persisted data: %s", rec.Body.String())
	}
}

func TestDuplicateISBNConflicts(t *testing.T) {
	h := newTestServer(t)
	if rec := do(t, h, http.MethodPost, "/books", dune); rec.Code != http.StatusCreated {
		t.Fatalf("first create = %d", rec.Code)
	}
	rec := do(t, h, http.MethodPost, "/books", dune)
	if rec.Code != http.StatusConflict {
		t.Fatalf("duplicate isbn status = %d, want 409", rec.Code)
	}

	// Books without an ISBN may coexist freely.
	noISBN := `{"title":"A","author":"B"}`
	if rec := do(t, h, http.MethodPost, "/books", noISBN); rec.Code != http.StatusCreated {
		t.Fatalf("no-isbn create 1 = %d", rec.Code)
	}
	if rec := do(t, h, http.MethodPost, "/books", noISBN); rec.Code != http.StatusCreated {
		t.Fatalf("no-isbn create 2 = %d", rec.Code)
	}
}

func TestIDHandling(t *testing.T) {
	h := newTestServer(t)

	for _, path := range []string{"/books/abc", "/books/0", "/books/-1"} {
		if rec := do(t, h, http.MethodGet, path, ""); rec.Code != http.StatusBadRequest {
			t.Fatalf("GET %s status = %d, want 400", path, rec.Code)
		}
	}
	if rec := do(t, h, http.MethodGet, "/books/999", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("GET missing status = %d, want 404", rec.Code)
	}
	if rec := do(t, h, http.MethodPut, "/books/999", dune); rec.Code != http.StatusNotFound {
		t.Fatalf("PUT missing status = %d, want 404", rec.Code)
	}
	if rec := do(t, h, http.MethodDelete, "/books/999", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("DELETE missing status = %d, want 404", rec.Code)
	}
}

func TestUpdateValidationAndISBNConflict(t *testing.T) {
	h := newTestServer(t)
	do(t, h, http.MethodPost, "/books", dune)
	do(t, h, http.MethodPost, "/books", `{"title":"Emma","author":"Jane Austen","isbn":"0141439580"}`)

	// Update must still satisfy required-field validation.
	if rec := do(t, h, http.MethodPut, "/books/1", `{"title":"","author":"X"}`); rec.Code != http.StatusUnprocessableEntity {
		t.Fatalf("invalid update status = %d, want 422", rec.Code)
	}
	// Moving an ISBN onto another book's ISBN is a conflict.
	rec := do(t, h, http.MethodPut, "/books/1", `{"title":"Dune","author":"Frank Herbert","isbn":"0141439580"}`)
	if rec.Code != http.StatusConflict {
		t.Fatalf("isbn-collision update status = %d, want 409", rec.Code)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	h := newTestServer(t)
	if rec := do(t, h, http.MethodPatch, "/books/1", ""); rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("PATCH status = %d, want 405", rec.Code)
	}
}

func TestErrorBodiesAreJSON(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodGet, "/books/404", "")
	if msg := decodeError(t, rec); msg != "book not found" {
		t.Fatalf("error message = %q", msg)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Fatalf("content-type = %q", ct)
	}
}
