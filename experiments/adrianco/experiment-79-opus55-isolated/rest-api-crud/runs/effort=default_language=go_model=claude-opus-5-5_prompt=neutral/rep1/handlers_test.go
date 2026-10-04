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
		t.Fatalf("create status = %d, body = %s", rec.Code, rec.Body.String())
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
		t.Fatalf("status = %d, want 201; body = %s", rec.Code, rec.Body.String())
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
		t.Fatalf("get status = %d, want 200", rec.Code)
	}
	if got := decode[Book](t, rec); got != want {
		t.Errorf("got = %+v, want %+v", got, want)
	}
}

func TestCreateOptionalFieldsOmitted(t *testing.T) {
	h := newTestHandler(t)
	b := mustCreate(t, h, `{"title":"  Untitled  ","author":"Anon"}`)
	if b.Title != "Untitled" || b.Year != 0 || b.ISBN != "" {
		t.Errorf("book = %+v, want trimmed title and zero-valued year/isbn", b)
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
		{"null author", `{"title":"T","author":null}`, 400, []string{"author"}},
		{"negative year", `{"title":"T","author":"A","year":-1}`, 400, []string{"year"}},
		{"year wrong type", `{"title":"T","author":"A","year":"1999"}`, 400, nil},
		{"malformed json", `{"title":`, 400, nil},
		{"empty body", ``, 400, nil},
		{"trailing data", `{"title":"T","author":"A"}{}`, 400, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newTestHandler(t)
			rec := do(t, h, http.MethodPost, "/books", tt.body)
			if rec.Code != tt.wantStatus {
				t.Fatalf("status = %d, want %d; body = %s", rec.Code, tt.wantStatus, rec.Body.String())
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
			if books := decode[[]Book](t, do(t, h, http.MethodGet, "/books", "")); len(books) != 0 {
				t.Errorf("books stored after invalid create: %v", books)
			}
		})
	}
}

func TestCreateBodyTooLarge(t *testing.T) {
	h := newTestHandler(t)
	body := `{"title":"` + strings.Repeat("x", maxBodyBytes) + `","author":"A"}`
	rec := do(t, h, http.MethodPost, "/books", body)
	if rec.Code != http.StatusRequestEntityTooLarge {
		t.Errorf("status = %d, want 413", rec.Code)
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

	if books := decode[[]Book](t, do(t, h, http.MethodGet, "/books", "")); len(books) != 3 {
		t.Errorf("len = %d, want 3", len(books))
	}

	for _, q := range []string{"Jane+Austen", "jane%20austen"} {
		books := decode[[]Book](t, do(t, h, http.MethodGet, "/books?author="+q, ""))
		if len(books) != 2 || books[0].Title != "Emma" || books[1].Title != "Persuasion" {
			t.Errorf("author=%s: got %+v, want Emma and Persuasion", q, books)
		}
	}

	// The filter is an exact match, not a substring or pattern match.
	for _, q := range []string{"Jane", "%25", "Nobody"} {
		rec := do(t, h, http.MethodGet, "/books?author="+q, "")
		if body := strings.TrimSpace(rec.Body.String()); rec.Code != 200 || body != "[]" {
			t.Errorf("author=%s: status = %d, body = %s, want 200 []", q, rec.Code, body)
		}
	}
}

func TestAuthorFilterIsNotInjectable(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert"}`)
	rec := do(t, h, http.MethodGet, "/books?author=x'%20OR%20'1'='1", "")
	if books := decode[[]Book](t, rec); rec.Code != 200 || len(books) != 0 {
		t.Errorf("status = %d, books = %v, want 200 and no books", rec.Code, books)
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"F. Herbert","year":1965,"isbn":"123"}`)

	rec := do(t, h, http.MethodPut, "/books/1", `{"title":"Dune","author":"Frank Herbert","year":1966}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body = %s", rec.Code, rec.Body.String())
	}
	// PUT replaces the whole resource, so the omitted isbn is cleared.
	want := Book{ID: 1, Title: "Dune", Author: "Frank Herbert", Year: 1966}
	if got := decode[Book](t, rec); got != want {
		t.Errorf("response = %+v, want %+v", got, want)
	}
	if got := decode[Book](t, do(t, h, http.MethodGet, "/books/1", "")); got != want {
		t.Errorf("stored = %+v, want %+v", got, want)
	}

	rec = do(t, h, http.MethodPut, "/books/1", `{"title":"","author":"Frank Herbert"}`)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("invalid update status = %d, want 400", rec.Code)
	}
	if got := decode[Book](t, do(t, h, http.MethodGet, "/books/1", "")); got != want {
		t.Errorf("book changed by invalid update: %+v", got)
	}

	rec = do(t, h, http.MethodPut, "/books/99", `{"title":"T","author":"A"}`)
	if rec.Code != http.StatusNotFound {
		t.Errorf("missing update status = %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestHandler(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert"}`)

	rec := do(t, h, http.MethodDelete, "/books/1", "")
	if rec.Code != http.StatusNoContent || rec.Body.Len() != 0 {
		t.Fatalf("status = %d, body = %q, want 204 with empty body", rec.Code, rec.Body.String())
	}
	if rec := do(t, h, http.MethodGet, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("get after delete status = %d, want 404", rec.Code)
	}
	if rec := do(t, h, http.MethodDelete, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("second delete status = %d, want 404", rec.Code)
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodGet, "/books/42", "")
	if rec.Code != http.StatusNotFound {
		t.Errorf("status = %d, want 404", rec.Code)
	}
	if resp := decode[errorResponse](t, rec); resp.Error == "" {
		t.Error("error message is empty")
	}

	for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
		for _, id := range []string{"abc", "0", "-1", "1.5"} {
			rec := do(t, h, method, "/books/"+id, `{"title":"T","author":"A"}`)
			if rec.Code != http.StatusBadRequest {
				t.Errorf("%s /books/%s status = %d, want 400", method, id, rec.Code)
			}
		}
	}
}

func TestMethodNotAllowed(t *testing.T) {
	h := newTestHandler(t)
	if rec := do(t, h, http.MethodPatch, "/books/1", `{}`); rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want 405", rec.Code)
	}
}

func TestDataPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := NewStore(path)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	mustCreate(t, NewHandler(store), `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	store, err = NewStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer store.Close()
	got := decode[Book](t, do(t, NewHandler(store), http.MethodGet, "/books/1", ""))
	if got.Title != "Dune" || got.Year != 1965 {
		t.Errorf("after reopen = %+v, want Dune (1965)", got)
	}
}
