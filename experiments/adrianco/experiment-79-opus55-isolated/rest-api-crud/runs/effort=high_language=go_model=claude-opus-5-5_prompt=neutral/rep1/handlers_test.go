package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// newTestHandler returns the API handler backed by a fresh in-memory database.
func newTestHandler(t *testing.T) http.Handler {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewHandler(store)
}

// do sends a request to h and returns the recorded response.
func do(t *testing.T, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, target, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

// decode unmarshals the response body into v, failing the test on error.
func decode(t *testing.T, rec *httptest.ResponseRecorder, v any) {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	if err := json.Unmarshal(rec.Body.Bytes(), v); err != nil {
		t.Fatalf("decode response %q: %v", rec.Body.String(), err)
	}
}

// mustCreate posts a book and returns the stored record.
func mustCreate(t *testing.T, h http.Handler, body string) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", body)
	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /books = %d, want %d; body %s", rec.Code, http.StatusCreated, rec.Body)
	}
	var b Book
	decode(t, rec, &b)
	return b
}

func TestHealth(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodGet, "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /health = %d, want %d", rec.Code, http.StatusOK)
	}
	var got map[string]string
	decode(t, rec, &got)
	if got["status"] != "ok" {
		t.Errorf("status = %q, want %q", got["status"], "ok")
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestHandler(t)

	rec := do(t, h, http.MethodPost, "/books",
		`{"title":"  Dune ","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /books = %d, want %d; body %s", rec.Code, http.StatusCreated, rec.Body)
	}
	var created Book
	decode(t, rec, &created)

	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"}
	if created.ID <= 0 {
		t.Errorf("created ID = %d, want a positive ID", created.ID)
	}
	if created != want {
		t.Errorf("created = %+v, want %+v", created, want)
	}
	if loc, wantLoc := rec.Header().Get("Location"), fmt.Sprintf("/books/%d", created.ID); loc != wantLoc {
		t.Errorf("Location = %q, want %q", loc, wantLoc)
	}

	rec = do(t, h, http.MethodGet, fmt.Sprintf("/books/%d", created.ID), "")
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /books/{id} = %d, want %d", rec.Code, http.StatusOK)
	}
	var got Book
	decode(t, rec, &got)
	if got != want {
		t.Errorf("fetched = %+v, want %+v", got, want)
	}
}

func TestCreateBookOptionalFields(t *testing.T) {
	h := newTestHandler(t)

	got := mustCreate(t, h, `{"title":"Untitled","author":"Anon"}`)
	if got.Year != 0 || got.ISBN != "" {
		t.Errorf("got year %d isbn %q, want zero values", got.Year, got.ISBN)
	}
}

func TestCreateBookRejectsInvalidInput(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantFields []string
	}{
		{"missing title", `{"author":"Frank Herbert"}`, http.StatusBadRequest, []string{"title"}},
		{"missing author", `{"title":"Dune"}`, http.StatusBadRequest, []string{"author"}},
		{"missing both", `{}`, http.StatusBadRequest, []string{"title", "author"}},
		{"blank title", `{"title":"   ","author":"Frank Herbert"}`, http.StatusBadRequest, []string{"title"}},
		{"negative year", `{"title":"Dune","author":"Frank Herbert","year":-1}`, http.StatusBadRequest, []string{"year"}},
		{"wrong type", `{"title":"Dune","author":"Frank Herbert","year":"1965"}`, http.StatusBadRequest, nil},
		{"malformed JSON", `{"title":`, http.StatusBadRequest, nil},
		{"not an object", `["Dune"]`, http.StatusBadRequest, nil},
		{"empty body", ``, http.StatusBadRequest, nil},
		{"trailing data", `{"title":"Dune","author":"Frank Herbert"}{}`, http.StatusBadRequest, nil},
		{"body too large", `{"title":"` + strings.Repeat("a", maxBodyBytes) + `","author":"x"}`, http.StatusRequestEntityTooLarge, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newTestHandler(t)

			rec := do(t, h, http.MethodPost, "/books", tt.body)
			if rec.Code != tt.wantStatus {
				t.Fatalf("POST /books = %d, want %d; body %s", rec.Code, tt.wantStatus, rec.Body)
			}
			var got struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}
			decode(t, rec, &got)
			if got.Error == "" {
				t.Error("error message is empty")
			}
			if len(got.Fields) != len(tt.wantFields) {
				t.Errorf("fields = %v, want exactly %v", got.Fields, tt.wantFields)
			}
			for _, f := range tt.wantFields {
				if got.Fields[f] == "" {
					t.Errorf("fields = %v, want a problem reported for %q", got.Fields, f)
				}
			}

			// Nothing must have been stored.
			var books []Book
			decode(t, do(t, h, http.MethodGet, "/books", ""), &books)
			if len(books) != 0 {
				t.Errorf("rejected request stored %d book(s)", len(books))
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	h := newTestHandler(t)

	// An empty collection is an empty JSON array, not null.
	rec := do(t, h, http.MethodGet, "/books", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /books = %d, want %d", rec.Code, http.StatusOK)
	}
	if got := strings.TrimSpace(rec.Body.String()); got != "[]" {
		t.Errorf("empty list body = %s, want []", got)
	}

	dune := mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	emma := mustCreate(t, h, `{"title":"Emma","author":"Jane Austen","year":1815}`)
	messiah := mustCreate(t, h, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)

	tests := []struct {
		name   string
		target string
		want   []Book
	}{
		{"all", "/books", []Book{dune, emma, messiah}},
		{"empty filter", "/books?author=", []Book{dune, emma, messiah}},
		{"by author", "/books?author=Frank+Herbert", []Book{dune, messiah}},
		{"by author ignoring case", "/books?author=jane%20austen", []Book{emma}},
		{"partial name does not match", "/books?author=Frank", []Book{}},
		{"unknown author", "/books?author=Nobody", []Book{}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, http.MethodGet, tt.target, "")
			if rec.Code != http.StatusOK {
				t.Fatalf("GET %s = %d, want %d", tt.target, rec.Code, http.StatusOK)
			}
			var got []Book
			decode(t, rec, &got)
			if got == nil {
				t.Fatalf("GET %s returned null, want an array", tt.target)
			}
			if len(got) != len(tt.want) {
				t.Fatalf("GET %s = %+v, want %+v", tt.target, got, tt.want)
			}
			for i := range got {
				if got[i] != tt.want[i] {
					t.Errorf("book[%d] = %+v, want %+v", i, got[i], tt.want[i])
				}
			}
		})
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestHandler(t)
	created := mustCreate(t, h, `{"title":"Dune","author":"F. Herbert","year":1965,"isbn":"123"}`)
	path := fmt.Sprintf("/books/%d", created.ID)

	rec := do(t, h, http.MethodPut, path, `{"title":"Dune","author":"Frank Herbert","year":1966}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("PUT %s = %d, want %d; body %s", path, rec.Code, http.StatusOK, rec.Body)
	}
	// PUT replaces the whole record, so the omitted isbn is cleared.
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1966}
	var updated Book
	decode(t, rec, &updated)
	if updated != want {
		t.Errorf("updated = %+v, want %+v", updated, want)
	}

	var got Book
	decode(t, do(t, h, http.MethodGet, path, ""), &got)
	if got != want {
		t.Errorf("fetched after update = %+v, want %+v", got, want)
	}

	t.Run("invalid input leaves book unchanged", func(t *testing.T) {
		rec := do(t, h, http.MethodPut, path, `{"title":"","author":"Someone Else"}`)
		if rec.Code != http.StatusBadRequest {
			t.Fatalf("PUT %s = %d, want %d", path, rec.Code, http.StatusBadRequest)
		}
		var got Book
		decode(t, do(t, h, http.MethodGet, path, ""), &got)
		if got != want {
			t.Errorf("book after rejected update = %+v, want %+v", got, want)
		}
	})

	t.Run("unknown id", func(t *testing.T) {
		rec := do(t, h, http.MethodPut, "/books/9999", `{"title":"Dune","author":"Frank Herbert"}`)
		if rec.Code != http.StatusNotFound {
			t.Errorf("PUT /books/9999 = %d, want %d", rec.Code, http.StatusNotFound)
		}
	})
}

func TestDeleteBook(t *testing.T) {
	h := newTestHandler(t)
	keep := mustCreate(t, h, `{"title":"Emma","author":"Jane Austen"}`)
	gone := mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert"}`)
	path := fmt.Sprintf("/books/%d", gone.ID)

	rec := do(t, h, http.MethodDelete, path, "")
	if rec.Code != http.StatusNoContent {
		t.Fatalf("DELETE %s = %d, want %d", path, rec.Code, http.StatusNoContent)
	}
	if rec.Body.Len() != 0 {
		t.Errorf("DELETE body = %q, want empty", rec.Body)
	}

	if rec := do(t, h, http.MethodGet, path, ""); rec.Code != http.StatusNotFound {
		t.Errorf("GET %s after delete = %d, want %d", path, rec.Code, http.StatusNotFound)
	}
	if rec := do(t, h, http.MethodDelete, path, ""); rec.Code != http.StatusNotFound {
		t.Errorf("second DELETE %s = %d, want %d", path, rec.Code, http.StatusNotFound)
	}

	var books []Book
	decode(t, do(t, h, http.MethodGet, "/books", ""), &books)
	if len(books) != 1 || books[0] != keep {
		t.Errorf("remaining books = %+v, want only %+v", books, keep)
	}
}

func TestErrorResponses(t *testing.T) {
	tests := []struct {
		name       string
		method     string
		target     string
		wantStatus int
		wantAllow  string
	}{
		{"unknown book", http.MethodGet, "/books/9999", http.StatusNotFound, ""},
		{"non-numeric id", http.MethodGet, "/books/abc", http.StatusBadRequest, ""},
		{"zero id", http.MethodGet, "/books/0", http.StatusBadRequest, ""},
		{"negative id", http.MethodDelete, "/books/-1", http.StatusBadRequest, ""},
		{"unknown route", http.MethodGet, "/nope", http.StatusNotFound, ""},
		{"delete collection", http.MethodDelete, "/books", http.StatusMethodNotAllowed, "GET, HEAD, POST"},
		{"post to item", http.MethodPost, "/books/1", http.StatusMethodNotAllowed, "GET, HEAD, PUT, DELETE"},
		{"post to health", http.MethodPost, "/health", http.StatusMethodNotAllowed, "GET, HEAD"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newTestHandler(t)

			rec := do(t, h, tt.method, tt.target, "")
			if rec.Code != tt.wantStatus {
				t.Fatalf("%s %s = %d, want %d", tt.method, tt.target, rec.Code, tt.wantStatus)
			}
			if allow := rec.Header().Get("Allow"); allow != tt.wantAllow {
				t.Errorf("Allow = %q, want %q", allow, tt.wantAllow)
			}
			var got map[string]string
			decode(t, rec, &got)
			if got["error"] == "" {
				t.Errorf("body %s has no error message", rec.Body)
			}
		})
	}
}
