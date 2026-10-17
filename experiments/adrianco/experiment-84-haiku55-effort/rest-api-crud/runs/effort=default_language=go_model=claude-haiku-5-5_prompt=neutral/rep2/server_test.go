package main

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

func newTestHandler(t *testing.T) http.Handler {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store).Handler()
}

func doRequest(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var reader io.Reader
	if body != "" {
		reader = strings.NewReader(body)
	}
	req := httptest.NewRequest(method, path, reader)
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func itoa(id int64) string {
	return strconv.FormatInt(id, 10)
}

func decodeBook(t *testing.T, rec *httptest.ResponseRecorder) Book {
	t.Helper()
	var b Book
	if err := json.Unmarshal(rec.Body.Bytes(), &b); err != nil {
		t.Fatalf("decode book %q: %v", rec.Body.String(), err)
	}
	return b
}

func assertStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d; body: %s", rec.Code, want, rec.Body.String())
	}
}

func TestBookLifecycle(t *testing.T) {
	h := newTestHandler(t)

	// Create
	rec := doRequest(t, h, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	assertStatus(t, rec, http.StatusCreated)
	created := decodeBook(t, rec)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("created book = %+v", created)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/"+itoa(created.ID) {
		t.Errorf("Location = %q", loc)
	}

	// Get
	rec = doRequest(t, h, http.MethodGet, "/books/"+itoa(created.ID), "")
	assertStatus(t, rec, http.StatusOK)
	if got := decodeBook(t, rec); got != created {
		t.Errorf("GET = %+v, want %+v", got, created)
	}

	// Update (PUT replaces the whole resource)
	rec = doRequest(t, h, http.MethodPut, "/books/"+itoa(created.ID),
		`{"title":"Dune Messiah","author":"Frank Herbert"}`)
	assertStatus(t, rec, http.StatusOK)
	updated := decodeBook(t, rec)
	if updated.Title != "Dune Messiah" || updated.Year != 0 || updated.ISBN != "" {
		t.Errorf("PUT result = %+v", updated)
	}

	// Delete
	rec = doRequest(t, h, http.MethodDelete, "/books/"+itoa(created.ID), "")
	assertStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("DELETE body = %q, want empty", rec.Body.String())
	}

	rec = doRequest(t, h, http.MethodGet, "/books/"+itoa(created.ID), "")
	assertStatus(t, rec, http.StatusNotFound)
	if !strings.Contains(rec.Body.String(), `"error"`) {
		t.Errorf("404 body is not a JSON error: %s", rec.Body.String())
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	h := newTestHandler(t)

	rec := doRequest(t, h, http.MethodGet, "/books", "")
	assertStatus(t, rec, http.StatusOK)
	if strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Errorf("empty list body = %q, want []", rec.Body.String())
	}

	for _, body := range []string{
		`{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin"}`,
		`{"title":"The Dispossessed","author":"Ursula K. Le Guin"}`,
		`{"title":"Dune","author":"Frank Herbert"}`,
	} {
		assertStatus(t, doRequest(t, h, http.MethodPost, "/books", body), http.StatusCreated)
	}

	var all []Book
	rec = doRequest(t, h, http.MethodGet, "/books", "")
	assertStatus(t, rec, http.StatusOK)
	if err := json.Unmarshal(rec.Body.Bytes(), &all); err != nil || len(all) != 3 {
		t.Fatalf("list all: %d books, err %v", len(all), err)
	}

	var filtered []Book
	rec = doRequest(t, h, http.MethodGet, "/books?author=Ursula+K.+Le+Guin", "")
	assertStatus(t, rec, http.StatusOK)
	if err := json.Unmarshal(rec.Body.Bytes(), &filtered); err != nil || len(filtered) != 2 {
		t.Fatalf("filtered list: %d books, err %v", len(filtered), err)
	}
	for _, b := range filtered {
		if b.Author != "Ursula K. Le Guin" {
			t.Errorf("filter leaked book by %q", b.Author)
		}
	}
}

func TestCreateBookValidation(t *testing.T) {
	h := newTestHandler(t)

	tests := []struct {
		name   string
		body   string
		status int
		field  string // expected key under "fields", if any
	}{
		{"empty object", `{}`, http.StatusBadRequest, "title"},
		{"missing author", `{"title":"Dune"}`, http.StatusBadRequest, "author"},
		{"blank title", `{"title":"  ","author":"Frank Herbert"}`, http.StatusBadRequest, "title"},
		{"bad isbn", `{"title":"Dune","author":"Frank Herbert","isbn":"123"}`, http.StatusBadRequest, "isbn"},
		{"malformed json", `{"title":`, http.StatusBadRequest, ""},
		{"unknown field", `{"title":"Dune","author":"Frank Herbert","pages":412}`, http.StatusBadRequest, ""},
		{"trailing content", `{"title":"Dune","author":"Frank Herbert"} {}`, http.StatusBadRequest, ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := doRequest(t, h, http.MethodPost, "/books", tt.body)
			assertStatus(t, rec, tt.status)
			var resp struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}
			if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil || resp.Error == "" {
				t.Fatalf("expected JSON error body, got %q (err %v)", rec.Body.String(), err)
			}
			if tt.field != "" {
				if _, ok := resp.Fields[tt.field]; !ok {
					t.Errorf("fields = %v, want key %q", resp.Fields, tt.field)
				}
			}
		})
	}

	// Nothing should have been stored.
	var all []Book
	rec := doRequest(t, h, http.MethodGet, "/books", "")
	json.Unmarshal(rec.Body.Bytes(), &all)
	if len(all) != 0 {
		t.Errorf("invalid requests stored %d books", len(all))
	}
}

func TestUpdateBookValidation(t *testing.T) {
	h := newTestHandler(t)
	rec := doRequest(t, h, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert"}`)
	created := decodeBook(t, rec)

	rec = doRequest(t, h, http.MethodPut, "/books/"+itoa(created.ID), `{"title":"Dune"}`)
	assertStatus(t, rec, http.StatusBadRequest)
	if !strings.Contains(rec.Body.String(), `"author"`) {
		t.Errorf("PUT validation body = %s, want author field error", rec.Body.String())
	}
}

func TestMissingOrInvalidIDs(t *testing.T) {
	h := newTestHandler(t)

	rec := doRequest(t, h, http.MethodGet, "/books/999", "")
	assertStatus(t, rec, http.StatusNotFound)
	rec = doRequest(t, h, http.MethodPut, "/books/999", `{"title":"X","author":"Y"}`)
	assertStatus(t, rec, http.StatusNotFound)
	rec = doRequest(t, h, http.MethodDelete, "/books/999", "")
	assertStatus(t, rec, http.StatusNotFound)

	for _, id := range []string{"abc", "0", "-1"} {
		rec = doRequest(t, h, http.MethodGet, "/books/"+id, "")
		assertStatus(t, rec, http.StatusBadRequest)
	}
}

func TestHealth(t *testing.T) {
	h := newTestHandler(t)
	rec := doRequest(t, h, http.MethodGet, "/health", "")
	assertStatus(t, rec, http.StatusOK)
	if !strings.Contains(rec.Body.String(), `"ok"`) {
		t.Errorf("health body = %s", rec.Body.String())
	}
}

func TestRoutingErrorsAreJSON(t *testing.T) {
	h := newTestHandler(t)

	rec := doRequest(t, h, http.MethodDelete, "/health", "")
	assertStatus(t, rec, http.StatusMethodNotAllowed)
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("405 Content-Type = %q", ct)
	}
	if allow := rec.Header().Get("Allow"); !strings.Contains(allow, "GET") {
		t.Errorf("405 Allow = %q, want it to list GET", allow)
	}
	if !strings.Contains(rec.Body.String(), `"method not allowed"`) {
		t.Errorf("405 body = %s", rec.Body.String())
	}

	rec = doRequest(t, h, http.MethodGet, "/nope", "")
	assertStatus(t, rec, http.StatusNotFound)
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("404 Content-Type = %q", ct)
	}
}
