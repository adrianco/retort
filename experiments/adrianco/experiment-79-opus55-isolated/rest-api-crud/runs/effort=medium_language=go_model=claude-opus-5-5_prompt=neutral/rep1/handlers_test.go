package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func newTestHandler(t *testing.T) http.Handler {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store).Handler()
}

// do sends a request to h and decodes the JSON response body into out (if
// non-nil), returning the recorded response.
func do(t *testing.T, h http.Handler, method, path, body string, out any) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if rec.Body.Len() > 0 {
		if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
			t.Errorf("%s %s: Content-Type = %q, want application/json", method, path, ct)
		}
	}
	if out != nil {
		if err := json.Unmarshal(rec.Body.Bytes(), out); err != nil {
			t.Fatalf("%s %s: decode body %q: %v", method, path, rec.Body.String(), err)
		}
	}
	return rec
}

func mustCreate(t *testing.T, h http.Handler, body string) Book {
	t.Helper()
	var b Book
	if rec := do(t, h, http.MethodPost, "/books", body, &b); rec.Code != http.StatusCreated {
		t.Fatalf("create: status = %d, body = %s", rec.Code, rec.Body.String())
	}
	return b
}

func TestHealth(t *testing.T) {
	h := newTestHandler(t)
	var got map[string]string
	rec := do(t, h, http.MethodGet, "/health", "", &got)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got["status"] != "ok" {
		t.Errorf("status field = %q, want ok", got["status"])
	}
}

func TestCreateAndGet(t *testing.T) {
	h := newTestHandler(t)

	var created Book
	rec := do(t, h, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`, &created)
	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201; body = %s", rec.Code, rec.Body.String())
	}
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}
	if created.ID <= 0 || created != want {
		t.Errorf("created = %+v, want %+v with positive ID", created, want)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	var got Book
	rec = do(t, h, http.MethodGet, "/books/1", "", &got)
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d, want 200", rec.Code)
	}
	if got != created {
		t.Errorf("got = %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantFields []string
	}{
		{"missing title", `{"author":"A"}`, http.StatusBadRequest, []string{"title"}},
		{"missing author", `{"title":"T"}`, http.StatusBadRequest, []string{"author"}},
		{"missing both", `{}`, http.StatusBadRequest, []string{"title", "author"}},
		{"blank title", `{"title":"   ","author":"A"}`, http.StatusBadRequest, []string{"title"}},
		{"negative year", `{"title":"T","author":"A","year":-1}`, http.StatusBadRequest, []string{"year"}},
		{"year too large", `{"title":"T","author":"A","year":10000}`, http.StatusBadRequest, []string{"year"}},
		{"malformed json", `{"title":`, http.StatusBadRequest, nil},
		{"empty body", ``, http.StatusBadRequest, nil},
		{"wrong type", `{"title":"T","author":"A","year":"1965"}`, http.StatusBadRequest, nil},
		{"trailing data", `{"title":"T","author":"A"}{}`, http.StatusBadRequest, nil},
		{"not an object", `[]`, http.StatusBadRequest, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newTestHandler(t)
			var got struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}
			rec := do(t, h, http.MethodPost, "/books", tt.body, &got)
			if rec.Code != tt.wantStatus {
				t.Fatalf("status = %d, want %d; body = %s", rec.Code, tt.wantStatus, rec.Body.String())
			}
			if got.Error == "" {
				t.Error("error message is empty")
			}
			if len(got.Fields) != len(tt.wantFields) {
				t.Errorf("fields = %v, want keys %v", got.Fields, tt.wantFields)
			}
			for _, f := range tt.wantFields {
				if got.Fields[f] == "" {
					t.Errorf("fields[%q] missing; got %v", f, got.Fields)
				}
			}

			// Nothing should have been stored.
			var books []Book
			do(t, h, http.MethodGet, "/books", "", &books)
			if len(books) != 0 {
				t.Errorf("rejected request stored %d book(s)", len(books))
			}
		})
	}
}

func TestCreateTrimsWhitespace(t *testing.T) {
	h := newTestHandler(t)
	b := mustCreate(t, h, `{"title":"  Dune ","author":" Frank Herbert  ","isbn":" 123 "}`)
	if b.Title != "Dune" || b.Author != "Frank Herbert" || b.ISBN != "123" {
		t.Errorf("got %+v, want trimmed fields", b)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h := newTestHandler(t)

	var books []Book
	rec := do(t, h, http.MethodGet, "/books", "", &books)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := strings.TrimSpace(rec.Body.String()); got != "[]" {
		t.Errorf("empty list body = %s, want []", got)
	}

	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	mustCreate(t, h, `{"title":"Emma","author":"Jane Austen","year":1815}`)
	mustCreate(t, h, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)

	do(t, h, http.MethodGet, "/books", "", &books)
	if len(books) != 3 {
		t.Fatalf("len = %d, want 3", len(books))
	}
	if books[0].Title != "Dune" || books[1].Title != "Emma" || books[2].Title != "Dune Messiah" {
		t.Errorf("books not in insertion order: %+v", books)
	}

	do(t, h, http.MethodGet, "/books?author=Frank+Herbert", "", &books)
	if len(books) != 2 {
		t.Fatalf("filtered len = %d, want 2: %+v", len(books), books)
	}
	for _, b := range books {
		if b.Author != "Frank Herbert" {
			t.Errorf("unexpected author in filtered list: %+v", b)
		}
	}

	do(t, h, http.MethodGet, "/books?author=jane%20austen", "", &books)
	if len(books) != 1 || books[0].Title != "Emma" {
		t.Errorf("case-insensitive filter = %+v, want just Emma", books)
	}

	rec = do(t, h, http.MethodGet, "/books?author=Nobody", "", &books)
	if rec.Code != http.StatusOK || len(books) != 0 {
		t.Errorf("unknown author: status = %d, books = %+v; want 200 and none", rec.Code, books)
	}

	// The filter value is data, not SQL.
	do(t, h, http.MethodGet, "/books?author=%27+OR+1%3D1+--", "", &books)
	if len(books) != 0 {
		t.Errorf("injection-style filter matched %d book(s)", len(books))
	}
}

func TestUpdate(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"111"}`)
	other := mustCreate(t, h, `{"title":"Emma","author":"Jane Austen","year":1815}`)

	var updated Book
	rec := do(t, h, http.MethodPut, "/books/1",
		`{"title":"Dune (Revised)","author":"F. Herbert","year":1966,"isbn":"222"}`, &updated)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body = %s", rec.Code, rec.Body.String())
	}
	want := Book{ID: 1, Title: "Dune (Revised)", Author: "F. Herbert", Year: 1966, ISBN: "222"}
	if updated != want {
		t.Errorf("updated = %+v, want %+v", updated, want)
	}

	var got Book
	do(t, h, http.MethodGet, "/books/1", "", &got)
	if got != want {
		t.Errorf("persisted = %+v, want %+v", got, want)
	}

	do(t, h, http.MethodGet, "/books/2", "", &got)
	if got != other {
		t.Errorf("unrelated book changed: %+v, want %+v", got, other)
	}

	// An ID in the body must not override the one in the path.
	do(t, h, http.MethodPut, "/books/1", `{"id":2,"title":"X","author":"Y"}`, &updated)
	if updated.ID != 1 {
		t.Errorf("ID after update = %d, want 1", updated.ID)
	}
}

func TestUpdateErrors(t *testing.T) {
	h := newTestHandler(t)
	orig := mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965}`)

	if rec := do(t, h, http.MethodPut, "/books/1", `{"title":"","author":"A"}`, nil); rec.Code != http.StatusBadRequest {
		t.Errorf("invalid update: status = %d, want 400", rec.Code)
	}
	if rec := do(t, h, http.MethodPut, "/books/1", `not json`, nil); rec.Code != http.StatusBadRequest {
		t.Errorf("malformed update: status = %d, want 400", rec.Code)
	}
	if rec := do(t, h, http.MethodPut, "/books/99", `{"title":"T","author":"A"}`, nil); rec.Code != http.StatusNotFound {
		t.Errorf("missing book: status = %d, want 404", rec.Code)
	}
	if rec := do(t, h, http.MethodPut, "/books/abc", `{"title":"T","author":"A"}`, nil); rec.Code != http.StatusBadRequest {
		t.Errorf("bad id: status = %d, want 400", rec.Code)
	}

	var got Book
	do(t, h, http.MethodGet, "/books/1", "", &got)
	if got != orig {
		t.Errorf("book changed by failed updates: %+v, want %+v", got, orig)
	}
}

func TestDelete(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert"}`)
	mustCreate(t, h, `{"title":"Emma","author":"Jane Austen"}`)

	rec := do(t, h, http.MethodDelete, "/books/1", "", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want 204", rec.Code)
	}
	if rec.Body.Len() != 0 {
		t.Errorf("204 response has body %q", rec.Body.String())
	}

	if rec := do(t, h, http.MethodGet, "/books/1", "", nil); rec.Code != http.StatusNotFound {
		t.Errorf("get after delete: status = %d, want 404", rec.Code)
	}
	if rec := do(t, h, http.MethodDelete, "/books/1", "", nil); rec.Code != http.StatusNotFound {
		t.Errorf("second delete: status = %d, want 404", rec.Code)
	}

	var books []Book
	do(t, h, http.MethodGet, "/books", "", &books)
	if len(books) != 1 || books[0].Title != "Emma" {
		t.Errorf("remaining books = %+v, want just Emma", books)
	}
}

func TestNotFoundAndBadIDs(t *testing.T) {
	h := newTestHandler(t)
	tests := []struct {
		method, path string
		want         int
	}{
		{http.MethodGet, "/books/1", http.StatusNotFound},
		{http.MethodDelete, "/books/1", http.StatusNotFound},
		{http.MethodGet, "/books/abc", http.StatusBadRequest},
		{http.MethodGet, "/books/0", http.StatusBadRequest},
		{http.MethodGet, "/books/-1", http.StatusBadRequest},
		{http.MethodDelete, "/books/1.5", http.StatusBadRequest},
		{http.MethodGet, "/books/99999999999999999999", http.StatusBadRequest},
		{http.MethodGet, "/nope", http.StatusNotFound},
		{http.MethodPatch, "/books/1", http.StatusMethodNotAllowed},
		{http.MethodDelete, "/books", http.StatusMethodNotAllowed},
		{http.MethodPost, "/health", http.StatusMethodNotAllowed},
	}
	for _, tt := range tests {
		t.Run(tt.method+" "+tt.path, func(t *testing.T) {
			var got map[string]string
			rec := do(t, h, tt.method, tt.path, "", &got)
			if rec.Code != tt.want {
				t.Errorf("status = %d, want %d", rec.Code, tt.want)
			}
			if got["error"] == "" {
				t.Errorf("body = %s, want JSON with an error message", rec.Body.String())
			}
		})
	}
}

func TestBodyTooLarge(t *testing.T) {
	h := newTestHandler(t)
	body := `{"title":"` + strings.Repeat("a", maxBodyBytes) + `","author":"A"}`
	if rec := do(t, h, http.MethodPost, "/books", body, nil); rec.Code != http.StatusRequestEntityTooLarge {
		t.Errorf("status = %d, want 413", rec.Code)
	}
}

func TestPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := NewStore(path)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	created := mustCreate(t, NewServer(store).Handler(), `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	store, err = NewStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer store.Close()

	var got Book
	rec := do(t, NewServer(store).Handler(), http.MethodGet, "/books/1", "", &got)
	if rec.Code != http.StatusOK || got != created {
		t.Errorf("after reopen: status = %d, book = %+v; want 200 and %+v", rec.Code, got, created)
	}
}
