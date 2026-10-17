package main

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

// newTestAPI starts the full HTTP stack against a fresh SQLite file.
func newTestAPI(t *testing.T) (*httptest.Server, *Store) {
	t.Helper()
	store := newTestStore(t)
	ts := httptest.NewServer(NewHandler(store))
	t.Cleanup(ts.Close)
	return ts, store
}

// do sends a request and returns the status code and raw body.
func do(t *testing.T, ts *httptest.Server, method, path, body string) (int, []byte) {
	t.Helper()
	req, err := http.NewRequest(method, ts.URL+path, strings.NewReader(body))
	if err != nil {
		t.Fatalf("NewRequest: %v", err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := ts.Client().Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, path, err)
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	return resp.StatusCode, b
}

func decodeBook(t *testing.T, b []byte) Book {
	t.Helper()
	var book Book
	if err := json.Unmarshal(b, &book); err != nil {
		t.Fatalf("decode book %s: %v", b, err)
	}
	return book
}

func decodeError(t *testing.T, b []byte) string {
	t.Helper()
	var body struct {
		Error string `json:"error"`
	}
	if err := json.Unmarshal(b, &body); err != nil {
		t.Fatalf("decode error body %s: %v", b, err)
	}
	return body.Error
}

func TestCreateAndGetBook(t *testing.T) {
	ts, _ := newTestAPI(t)

	status, body := do(t, ts, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-306-40615-7"}`)
	if status != http.StatusCreated {
		t.Fatalf("POST status = %d, body %s; want 201", status, body)
	}
	created := decodeBook(t, body)
	if created.ID == 0 || created.Title != "Dune" || created.Author != "Frank Herbert" ||
		created.Year != 1965 || created.ISBN != "978-0-306-40615-7" {
		t.Fatalf("POST body = %+v", created)
	}

	status, body = do(t, ts, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), "")
	if status != http.StatusOK {
		t.Fatalf("GET status = %d, body %s; want 200", status, body)
	}
	if got := decodeBook(t, body); got != created {
		t.Fatalf("GET body = %+v, want %+v", got, created)
	}
}

func TestCreateSetsLocationHeader(t *testing.T) {
	ts, _ := newTestAPI(t)

	resp, err := ts.Client().Post(ts.URL+"/books", "application/json",
		strings.NewReader(`{"title":"Dune","author":"Frank Herbert"}`))
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()

	book := decodeBook(t, mustReadAll(t, resp.Body))
	want := "/books/" + strconv.FormatInt(book.ID, 10)
	if got := resp.Header.Get("Location"); got != want {
		t.Fatalf("Location = %q, want %q", got, want)
	}
	if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
		t.Fatalf("Content-Type = %q, want application/json", ct)
	}
}

func TestCreateBookValidation(t *testing.T) {
	ts, _ := newTestAPI(t)

	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantField  string // expected key under "fields", if any
	}{
		{"missing title", `{"author":"Frank Herbert"}`, http.StatusUnprocessableEntity, "title"},
		{"missing author", `{"title":"Dune"}`, http.StatusUnprocessableEntity, "author"},
		{"blank title", `{"title":"   ","author":"Frank Herbert"}`, http.StatusUnprocessableEntity, "title"},
		{"invalid isbn", `{"title":"Dune","author":"Frank Herbert","isbn":"123"}`, http.StatusUnprocessableEntity, "isbn"},
		{"malformed json", `{"title":`, http.StatusBadRequest, ""},
		{"wrong json type", `["Dune"]`, http.StatusBadRequest, ""},
		{"trailing data", `{"title":"Dune","author":"Frank Herbert"} {}`, http.StatusBadRequest, ""},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, body := do(t, ts, http.MethodPost, "/books", tt.body)
			if status != tt.wantStatus {
				t.Fatalf("status = %d, body %s; want %d", status, body, tt.wantStatus)
			}
			if tt.wantField == "" {
				if decodeError(t, body) == "" {
					t.Fatalf("expected an error message, got %s", body)
				}
				return
			}
			var resp struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}
			if err := json.Unmarshal(body, &resp); err != nil {
				t.Fatalf("decode: %v", err)
			}
			if _, ok := resp.Fields[tt.wantField]; !ok {
				t.Fatalf("fields = %v, want key %q", resp.Fields, tt.wantField)
			}
		})
	}

	// Nothing should have been stored by the failed requests.
	status, body := do(t, ts, http.MethodGet, "/books", "")
	if status != http.StatusOK || strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("GET /books after failed creates = %d %s, want 200 []", status, body)
	}
}

func TestListBooksAndAuthorFilter(t *testing.T) {
	ts, _ := newTestAPI(t)

	status, body := do(t, ts, http.MethodGet, "/books", "")
	if status != http.StatusOK || strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("empty list = %d %s, want 200 []", status, body)
	}

	for _, b := range []string{
		`{"title":"Dune","author":"Frank Herbert"}`,
		`{"title":"Emma","author":"Jane Austen"}`,
		`{"title":"Children of Dune","author":"Frank Herbert"}`,
	} {
		if status, body := do(t, ts, http.MethodPost, "/books", b); status != http.StatusCreated {
			t.Fatalf("seed POST = %d %s", status, body)
		}
	}

	status, body = do(t, ts, http.MethodGet, "/books", "")
	if status != http.StatusOK {
		t.Fatalf("GET /books = %d", status)
	}
	var all []Book
	if err := json.Unmarshal(body, &all); err != nil || len(all) != 3 {
		t.Fatalf("GET /books = %s, want 3 books", body)
	}

	status, body = do(t, ts, http.MethodGet, "/books?author=frank+herbert", "")
	if status != http.StatusOK {
		t.Fatalf("GET /books?author = %d", status)
	}
	var filtered []Book
	if err := json.Unmarshal(body, &filtered); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("filtered = %s, want 2 Herbert books", body)
	}
	for _, b := range filtered {
		if b.Author != "Frank Herbert" {
			t.Errorf("filter returned book by %q", b.Author)
		}
	}
}

func TestGetBookErrors(t *testing.T) {
	ts, _ := newTestAPI(t)

	tests := []struct {
		name       string
		path       string
		wantStatus int
	}{
		{"unknown id", "/books/999", http.StatusNotFound},
		{"non-numeric id", "/books/abc", http.StatusBadRequest},
		{"zero id", "/books/0", http.StatusBadRequest},
		{"negative id", "/books/-1", http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, body := do(t, ts, http.MethodGet, tt.path, "")
			if status != tt.wantStatus {
				t.Fatalf("status = %d, body %s; want %d", status, body, tt.wantStatus)
			}
			if decodeError(t, body) == "" {
				t.Fatalf("expected JSON error message, got %s", body)
			}
		})
	}
}

func TestUpdateBook(t *testing.T) {
	ts, _ := newTestAPI(t)

	_, body := do(t, ts, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965}`)
	created := decodeBook(t, body)
	path := "/books/" + strconv.FormatInt(created.ID, 10)

	status, body := do(t, ts, http.MethodPut, path,
		`{"title":"Dune","author":"Frank Herbert","year":1966,"isbn":"0306406152"}`)
	if status != http.StatusOK {
		t.Fatalf("PUT status = %d, body %s; want 200", status, body)
	}
	updated := decodeBook(t, body)
	if updated.ID != created.ID || updated.Year != 1966 || updated.ISBN != "0306406152" {
		t.Fatalf("PUT body = %+v", updated)
	}

	status, body = do(t, ts, http.MethodGet, path, "")
	if status != http.StatusOK || decodeBook(t, body) != updated {
		t.Fatalf("GET after PUT = %d %s, want updated book", status, body)
	}

	status, body = do(t, ts, http.MethodPut, path, `{"title":"","author":"Frank Herbert"}`)
	if status != http.StatusUnprocessableEntity {
		t.Fatalf("PUT invalid status = %d, body %s; want 422", status, body)
	}

	status, body = do(t, ts, http.MethodPut, "/books/999", `{"title":"X","author":"Y"}`)
	if status != http.StatusNotFound {
		t.Fatalf("PUT unknown status = %d, body %s; want 404", status, body)
	}

	status, body = do(t, ts, http.MethodPut, "/books/abc", `{"title":"X","author":"Y"}`)
	if status != http.StatusBadRequest {
		t.Fatalf("PUT bad id status = %d, body %s; want 400", status, body)
	}
}

func TestDeleteBook(t *testing.T) {
	ts, _ := newTestAPI(t)

	_, body := do(t, ts, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert"}`)
	path := "/books/" + strconv.FormatInt(decodeBook(t, body).ID, 10)

	status, body := do(t, ts, http.MethodDelete, path, "")
	if status != http.StatusNoContent || len(body) != 0 {
		t.Fatalf("DELETE = %d %q, want 204 with empty body", status, body)
	}

	status, body = do(t, ts, http.MethodGet, path, "")
	if status != http.StatusNotFound {
		t.Fatalf("GET after DELETE = %d %s, want 404", status, body)
	}

	status, body = do(t, ts, http.MethodDelete, path, "")
	if status != http.StatusNotFound {
		t.Fatalf("second DELETE = %d %s, want 404", status, body)
	}
}

func TestHealthCheck(t *testing.T) {
	ts, store := newTestAPI(t)

	status, body := do(t, ts, http.MethodGet, "/health", "")
	if status != http.StatusOK {
		t.Fatalf("GET /health = %d %s, want 200", status, body)
	}
	var h map[string]string
	if err := json.Unmarshal(body, &h); err != nil || h["status"] != "ok" {
		t.Fatalf("GET /health body = %s, want status ok", body)
	}

	store.Close()
	status, body = do(t, ts, http.MethodGet, "/health", "")
	if status != http.StatusServiceUnavailable {
		t.Fatalf("GET /health with closed db = %d %s, want 503", status, body)
	}
}

func TestUnsupportedMethodIsRejected(t *testing.T) {
	ts, _ := newTestAPI(t)

	status, _ := do(t, ts, http.MethodPatch, "/books/1", `{}`)
	if status != http.StatusMethodNotAllowed {
		t.Fatalf("PATCH /books/1 = %d, want 405", status)
	}
}

func mustReadAll(t *testing.T, r io.Reader) []byte {
	t.Helper()
	b, err := io.ReadAll(r)
	if err != nil {
		t.Fatal(err)
	}
	return b
}
