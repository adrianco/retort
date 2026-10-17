package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"strings"
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
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if body != "" {
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

const validBook = `{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0306406157"}`

func TestCreateAndGetBook(t *testing.T) {
	h := newTestServer(t)

	rec := do(t, h, http.MethodPost, "/books", validBook)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: status=%d body=%s", rec.Code, rec.Body.String())
	}
	created := decodeBook(t, rec)
	if created.ID == 0 || created.Title != "The Go Programming Language" || created.Year != 2015 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/"+strconv.FormatInt(created.ID, 10) {
		t.Errorf("Location header = %q", loc)
	}

	rec = do(t, h, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), "")
	if rec.Code != http.StatusOK {
		t.Fatalf("get: status=%d body=%s", rec.Code, rec.Body.String())
	}
	if got := decodeBook(t, rec); got != created {
		t.Fatalf("get mismatch: got %+v want %+v", got, created)
	}
}

func TestGetMissingBookReturns404(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodGet, "/books/999", "")
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status=%d want 404", rec.Code)
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	h := newTestServer(t)
	do(t, h, http.MethodPost, "/books", `{"title":"A","author":"Ursula K. Le Guin"}`)
	do(t, h, http.MethodPost, "/books", `{"title":"B","author":"Frank Herbert"}`)
	do(t, h, http.MethodPost, "/books", `{"title":"C","author":"ursula k. le guin"}`)

	rec := do(t, h, http.MethodGet, "/books", "")
	var all []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &all); err != nil || len(all) != 3 {
		t.Fatalf("list all: err=%v len=%d body=%s", err, len(all), rec.Body.String())
	}

	rec = do(t, h, http.MethodGet, "/books?author=Ursula+K.+Le+Guin", "")
	var filtered []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &filtered); err != nil {
		t.Fatalf("decode filtered: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("filtered len=%d want 2", len(filtered))
	}
	for _, b := range filtered {
		if !strings.EqualFold(b.Author, "Ursula K. Le Guin") {
			t.Errorf("unexpected author in filter result: %q", b.Author)
		}
	}

	rec = do(t, h, http.MethodGet, "/books?author=Nobody", "")
	if rec.Code != http.StatusOK || strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("empty filter: status=%d body=%s", rec.Code, rec.Body.String())
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestServer(t)
	created := decodeBook(t, do(t, h, http.MethodPost, "/books", validBook))

	rec := do(t, h, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10),
		`{"title":"Renamed","author":"Someone Else","year":2020,"isbn":""}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("update: status=%d body=%s", rec.Code, rec.Body.String())
	}
	updated := decodeBook(t, rec)
	if updated.ID != created.ID || updated.Title != "Renamed" || updated.Author != "Someone Else" || updated.ISBN != "" {
		t.Fatalf("unexpected update result: %+v", updated)
	}

	if got := decodeBook(t, do(t, h, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), "")); got != updated {
		t.Fatalf("persisted update mismatch: %+v", got)
	}

	rec = do(t, h, http.MethodPut, "/books/999", validBook)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("update missing: status=%d want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestServer(t)
	created := decodeBook(t, do(t, h, http.MethodPost, "/books", validBook))
	path := "/books/" + strconv.FormatInt(created.ID, 10)

	if rec := do(t, h, http.MethodDelete, path, ""); rec.Code != http.StatusNoContent {
		t.Fatalf("delete: status=%d want 204", rec.Code)
	}
	if rec := do(t, h, http.MethodGet, path, ""); rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete: status=%d want 404", rec.Code)
	}
	if rec := do(t, h, http.MethodDelete, path, ""); rec.Code != http.StatusNotFound {
		t.Fatalf("second delete: status=%d want 404", rec.Code)
	}
}

func TestValidationErrors(t *testing.T) {
	h := newTestServer(t)

	tests := []struct {
		name   string
		body   string
		fields []string
	}{
		{"missing title and author", `{"year":2000}`, []string{"title", "author"}},
		{"blank title", `{"title":"   ","author":"X"}`, []string{"title"}},
		{"bad year", `{"title":"T","author":"A","year":12}`, []string{"year"}},
		{"bad isbn", `{"title":"T","author":"A","isbn":"123"}`, []string{"isbn"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, http.MethodPost, "/books", tt.body)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("status=%d want 400 (body=%s)", rec.Code, rec.Body.String())
			}
			var eb errorBody
			if err := json.Unmarshal(rec.Body.Bytes(), &eb); err != nil {
				t.Fatalf("decode error body: %v", err)
			}
			for _, f := range tt.fields {
				if _, ok := eb.Details[f]; !ok {
					t.Errorf("expected detail for field %q, got %v", f, eb.Details)
				}
			}
		})
	}
}

func TestMalformedRequests(t *testing.T) {
	h := newTestServer(t)

	cases := map[string]string{
		"not json":         `{"title":`,
		"unknown field":    `{"title":"T","author":"A","pages":10}`,
		"trailing content": `{"title":"T","author":"A"} {"x":1}`,
		"wrong type":       `{"title":"T","author":"A","year":"nineteen"}`,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			rec := do(t, h, http.MethodPost, "/books", body)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("status=%d want 400 (body=%s)", rec.Code, rec.Body.String())
			}
		})
	}

	if rec := do(t, h, http.MethodGet, "/books/abc", ""); rec.Code != http.StatusBadRequest {
		t.Errorf("non-numeric id: status=%d want 400", rec.Code)
	}
	if rec := do(t, h, http.MethodGet, "/books/0", ""); rec.Code != http.StatusBadRequest {
		t.Errorf("zero id: status=%d want 400", rec.Code)
	}
}

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodGet, "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("health: status=%d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), `"ok"`) {
		t.Errorf("health body = %s", rec.Body.String())
	}
}

func TestDataPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	h := NewServer(store)
	created := decodeBook(t, do(t, h, http.MethodPost, "/books", validBook))
	store.Close()

	store2, err := OpenStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer store2.Close()
	rec := do(t, NewServer(store2), http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), "")
	if rec.Code != http.StatusOK {
		t.Fatalf("after reopen: status=%d", rec.Code)
	}
	if got := decodeBook(t, rec); got != created {
		t.Fatalf("after reopen mismatch: %+v", got)
	}
}

func TestValidateISBN(t *testing.T) {
	valid := []string{"0306406152", "155404295X", "978-0-306-40615-7", "9780306406157", "0-306-40615-2"}
	invalid := []string{"0306406153", "978030640615", "abcdefghij", "155404295x1", "12345678X0"}

	for _, s := range valid {
		if !validISBN(s) {
			t.Errorf("validISBN(%q) = false, want true", s)
		}
	}
	for _, s := range invalid {
		if validISBN(s) {
			t.Errorf("validISBN(%q) = true, want false", s)
		}
	}
}
