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
	return NewHandler(store)
}

// do sends a request to h and decodes a JSON response body into out (if non-nil).
func do(t *testing.T, h http.Handler, method, target, body string, out any) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, target, strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if out != nil {
		if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
			t.Fatalf("%s %s: Content-Type = %q, want application/json", method, target, ct)
		}
		if err := json.Unmarshal(rec.Body.Bytes(), out); err != nil {
			t.Fatalf("%s %s: decode %q: %v", method, target, rec.Body.String(), err)
		}
	}
	return rec
}

func mustCreate(t *testing.T, h http.Handler, body string) Book {
	t.Helper()
	var b Book
	if rec := do(t, h, "POST", "/books", body, &b); rec.Code != http.StatusCreated {
		t.Fatalf("POST /books = %d, want 201: %s", rec.Code, rec.Body.String())
	}
	return b
}

func TestHealth(t *testing.T) {
	h := newTestHandler(t)
	var got map[string]string
	rec := do(t, h, "GET", "/health", "", &got)
	if rec.Code != http.StatusOK || got["status"] != "ok" {
		t.Fatalf("GET /health = %d %v, want 200 status=ok", rec.Code, got)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestHandler(t)

	var created Book
	rec := do(t, h, "POST", "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`, &created)
	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /books = %d, want 201: %s", rec.Code, rec.Body.String())
	}
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}
	if created.ID < 1 || created != want {
		t.Fatalf("created = %+v, want %+v with positive ID", created, want)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	var got Book
	if rec := do(t, h, "GET", "/books/1", "", &got); rec.Code != http.StatusOK {
		t.Fatalf("GET /books/1 = %d, want 200", rec.Code)
	}
	if got != want {
		t.Errorf("got = %+v, want %+v", got, want)
	}
}

func TestCreateBookValidation(t *testing.T) {
	h := newTestHandler(t)

	tests := []struct {
		name       string
		body       string
		wantFields []string
	}{
		{"missing title", `{"author":"Frank Herbert"}`, []string{"title"}},
		{"missing author", `{"title":"Dune"}`, []string{"author"}},
		{"blank title and author", `{"title":"  ","author":""}`, []string{"title", "author"}},
		{"negative year", `{"title":"Dune","author":"Frank Herbert","year":-1}`, []string{"year"}},
		{"malformed JSON", `{"title":`, nil},
		{"wrong type", `{"title":"Dune","author":"Frank Herbert","year":"1965"}`, nil},
		{"empty body", ``, nil},
		{"trailing data", `{"title":"Dune","author":"Frank Herbert"}{}`, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got errorResponse
			rec := do(t, h, "POST", "/books", tt.body, &got)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400: %s", rec.Code, rec.Body.String())
			}
			if got.Error == "" {
				t.Error("error message is empty")
			}
			if len(got.Fields) != len(tt.wantFields) {
				t.Errorf("fields = %v, want keys %v", got.Fields, tt.wantFields)
			}
			for _, f := range tt.wantFields {
				if got.Fields[f] == "" {
					t.Errorf("fields = %v, missing %q", got.Fields, f)
				}
			}
		})
	}

	// Nothing invalid should have been stored.
	var books []Book
	do(t, h, "GET", "/books", "", &books)
	if len(books) != 0 {
		t.Errorf("books after invalid creates = %+v, want none", books)
	}
}

func TestListBooks(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, "GET", "/books", "", nil)
	if rec.Code != http.StatusOK || strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("empty list = %d %q, want 200 []", rec.Code, rec.Body.String())
	}

	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	mustCreate(t, h, `{"title":"Emma","author":"Jane Austen","year":1815}`)
	mustCreate(t, h, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)

	tests := []struct {
		target string
		want   []string
	}{
		{"/books", []string{"Dune", "Emma", "Dune Messiah"}},
		{"/books?author=Frank+Herbert", []string{"Dune", "Dune Messiah"}},
		{"/books?author=jane%20austen", []string{"Emma"}},
		{"/books?author=Frank", []string{}},
		{"/books?author=", []string{"Dune", "Emma", "Dune Messiah"}},
	}
	for _, tt := range tests {
		t.Run(tt.target, func(t *testing.T) {
			var books []Book
			if rec := do(t, h, "GET", tt.target, "", &books); rec.Code != http.StatusOK {
				t.Fatalf("status = %d, want 200", rec.Code)
			}
			titles := []string{}
			for _, b := range books {
				titles = append(titles, b.Title)
			}
			if strings.Join(titles, "|") != strings.Join(tt.want, "|") {
				t.Errorf("titles = %v, want %v", titles, tt.want)
			}
		})
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"F. Herbert","year":1965,"isbn":"123"}`)

	var updated Book
	rec := do(t, h, "PUT", "/books/1", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`, &updated)
	if rec.Code != http.StatusOK {
		t.Fatalf("PUT /books/1 = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	want := Book{ID: 1, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}
	if updated != want {
		t.Errorf("updated = %+v, want %+v", updated, want)
	}

	var got Book
	do(t, h, "GET", "/books/1", "", &got)
	if got != want {
		t.Errorf("after update got = %+v, want %+v", got, want)
	}

	if rec := do(t, h, "PUT", "/books/1", `{"title":"","author":"Frank Herbert"}`, &errorResponse{}); rec.Code != http.StatusBadRequest {
		t.Errorf("PUT invalid = %d, want 400", rec.Code)
	}
	do(t, h, "GET", "/books/1", "", &got)
	if got != want {
		t.Errorf("after rejected update got = %+v, want %+v", got, want)
	}

	if rec := do(t, h, "PUT", "/books/99", `{"title":"X","author":"Y"}`, &errorResponse{}); rec.Code != http.StatusNotFound {
		t.Errorf("PUT missing = %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert"}`)

	rec := do(t, h, "DELETE", "/books/1", "", nil)
	if rec.Code != http.StatusNoContent || rec.Body.Len() != 0 {
		t.Fatalf("DELETE /books/1 = %d %q, want 204 with empty body", rec.Code, rec.Body.String())
	}
	if rec := do(t, h, "GET", "/books/1", "", &errorResponse{}); rec.Code != http.StatusNotFound {
		t.Errorf("GET after delete = %d, want 404", rec.Code)
	}
	if rec := do(t, h, "DELETE", "/books/1", "", &errorResponse{}); rec.Code != http.StatusNotFound {
		t.Errorf("second DELETE = %d, want 404", rec.Code)
	}
}

func TestBookIDErrors(t *testing.T) {
	h := newTestHandler(t)

	tests := []struct {
		method, target, body string
		want                 int
	}{
		{"GET", "/books/42", "", http.StatusNotFound},
		{"GET", "/books/abc", "", http.StatusBadRequest},
		{"GET", "/books/0", "", http.StatusBadRequest},
		{"PUT", "/books/abc", `{"title":"X","author":"Y"}`, http.StatusBadRequest},
		{"DELETE", "/books/-1", "", http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(tt.method+" "+tt.target, func(t *testing.T) {
			var got errorResponse
			rec := do(t, h, tt.method, tt.target, tt.body, &got)
			if rec.Code != tt.want {
				t.Errorf("status = %d, want %d", rec.Code, tt.want)
			}
			if got.Error == "" {
				t.Error("error message is empty")
			}
		})
	}

	if rec := do(t, h, "PATCH", "/books/1", "", nil); rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("PATCH /books/1 = %d, want 405", rec.Code)
	}
}

func TestStorePersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := NewStore(path)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	created, err := store.Create(t.Context(), Book{Title: "Dune", Author: "Frank Herbert", Year: 1965})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	store, err = NewStore(path)
	if err != nil {
		t.Fatalf("reopen NewStore: %v", err)
	}
	defer store.Close()
	got, err := store.Get(t.Context(), created.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("got = %+v, want %+v", got, created)
	}
}
