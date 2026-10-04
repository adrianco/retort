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

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode %q: %v", rec.Body.String(), err)
	}
	return v
}

func mustCreate(t *testing.T, h http.Handler, body string) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", body)
	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /books = %d, want 201; body %s", rec.Code, rec.Body)
	}
	return decode[Book](t, rec)
}

func TestHealth(t *testing.T) {
	h := newTestHandler(t)
	rec := do(t, h, http.MethodGet, "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := decode[map[string]string](t, rec); got["status"] != "ok" {
		t.Errorf("body = %v, want status ok", got)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201; body %s", rec.Code, rec.Body)
	}
	created := decode[Book](t, rec)
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}
	if created.ID <= 0 || created != want {
		t.Errorf("created = %+v, want %+v with positive ID", created, want)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	rec = do(t, h, http.MethodGet, "/books/1", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("GET status = %d, want 200", rec.Code)
	}
	if got := decode[Book](t, rec); got != want {
		t.Errorf("got = %+v, want %+v", got, want)
	}
}

func TestCreateValidation(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantFields []string
	}{
		{"missing title", `{"author":"A"}`, 400, []string{"title"}},
		{"missing author", `{"title":"T"}`, 400, []string{"author"}},
		{"missing both", `{}`, 400, []string{"title", "author"}},
		{"blank title", `{"title":"   ","author":"A"}`, 400, []string{"title"}},
		{"negative year", `{"title":"T","author":"A","year":-1}`, 400, []string{"year"}},
		{"malformed JSON", `{"title":`, 400, nil},
		{"empty body", ``, 400, nil},
		{"wrong type", `{"title":"T","author":"A","year":"1999"}`, 400, nil},
		{"trailing data", `{"title":"T","author":"A"}{}`, 400, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newTestHandler(t)
			rec := do(t, h, http.MethodPost, "/books", tt.body)
			if rec.Code != tt.wantStatus {
				t.Fatalf("status = %d, want %d; body %s", rec.Code, tt.wantStatus, rec.Body)
			}
			resp := decode[errorResponse](t, rec)
			if resp.Error == "" {
				t.Error("error message is empty")
			}
			if len(resp.Details) != len(tt.wantFields) {
				t.Errorf("details = %v, want fields %v", resp.Details, tt.wantFields)
			}
			for _, f := range tt.wantFields {
				if resp.Details[f] == "" {
					t.Errorf("details missing field %q: %v", f, resp.Details)
				}
			}

			// Nothing should have been stored.
			list := decode[[]Book](t, do(t, h, http.MethodGet, "/books", ""))
			if len(list) != 0 {
				t.Errorf("rejected request stored a book: %+v", list)
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodGet, "/books", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty list body = %s, want []", body)
	}

	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	mustCreate(t, h, `{"title":"Emma","author":"Jane Austen","year":1815}`)
	mustCreate(t, h, `{"title":"Persuasion","author":"Jane Austen","year":1817}`)

	titles := func(path string) []string {
		t.Helper()
		rec := do(t, h, http.MethodGet, path, "")
		if rec.Code != http.StatusOK {
			t.Fatalf("GET %s = %d, want 200", path, rec.Code)
		}
		var out []string
		for _, b := range decode[[]Book](t, rec) {
			out = append(out, b.Title)
		}
		return out
	}

	tests := []struct {
		path string
		want string
	}{
		{"/books", "Dune,Emma,Persuasion"},
		{"/books?author=Jane+Austen", "Emma,Persuasion"},
		{"/books?author=jane+austen", "Emma,Persuasion"},
		{"/books?author=Frank+Herbert", "Dune"},
		{"/books?author=Jane", ""},
		{"/books?author=Nobody", ""},
	}
	for _, tt := range tests {
		if got := strings.Join(titles(tt.path), ","); got != tt.want {
			t.Errorf("GET %s titles = %q, want %q", tt.path, got, tt.want)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}`)

	rec := do(t, h, http.MethodPut, "/books/1",
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"456"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body %s", rec.Code, rec.Body)
	}
	want := Book{ID: 1, Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969, ISBN: "456"}
	if got := decode[Book](t, rec); got != want {
		t.Errorf("response = %+v, want %+v", got, want)
	}
	if got := decode[Book](t, do(t, h, http.MethodGet, "/books/1", "")); got != want {
		t.Errorf("stored = %+v, want %+v", got, want)
	}

	// Invalid updates are rejected and leave the book untouched.
	rec = do(t, h, http.MethodPut, "/books/1", `{"title":"","author":"Frank Herbert"}`)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("invalid update status = %d, want 400", rec.Code)
	}
	if got := decode[Book](t, do(t, h, http.MethodGet, "/books/1", "")); got != want {
		t.Errorf("after invalid update = %+v, want %+v", got, want)
	}

	rec = do(t, h, http.MethodPut, "/books/99", `{"title":"T","author":"A"}`)
	if rec.Code != http.StatusNotFound {
		t.Errorf("update missing status = %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert"}`)

	rec := do(t, h, http.MethodDelete, "/books/1", "")
	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want 204", rec.Code)
	}
	if rec.Body.Len() != 0 {
		t.Errorf("204 response has body %q", rec.Body)
	}
	if rec := do(t, h, http.MethodGet, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("GET after delete = %d, want 404", rec.Code)
	}
	if rec := do(t, h, http.MethodDelete, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("second delete = %d, want 404", rec.Code)
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodGet, "/books/42", "")
	if rec.Code != http.StatusNotFound {
		t.Errorf("missing book status = %d, want 404", rec.Code)
	}
	if resp := decode[errorResponse](t, rec); resp.Error == "" {
		t.Error("404 has no error message")
	}

	for _, id := range []string{"abc", "0", "-1", "1.5"} {
		for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
			rec := do(t, h, method, "/books/"+id, `{"title":"T","author":"A"}`)
			if rec.Code != http.StatusBadRequest {
				t.Errorf("%s /books/%s = %d, want 400", method, id, rec.Code)
			}
		}
	}

	if rec := do(t, h, http.MethodPatch, "/books/1", ""); rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("PATCH status = %d, want 405", rec.Code)
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
		t.Fatalf("reopen: %v", err)
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
