package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	ts := httptest.NewServer(NewHandler(store))
	t.Cleanup(func() {
		ts.Close()
		store.Close()
	})
	return ts
}

// do sends a request and decodes the JSON response body into out (if non-nil).
func do(t *testing.T, method, url, body string, out any) *http.Response {
	t.Helper()
	req, err := http.NewRequest(method, url, strings.NewReader(body))
	if err != nil {
		t.Fatalf("NewRequest: %v", err)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, url, err)
	}
	defer resp.Body.Close()
	if out != nil {
		if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
			t.Errorf("%s %s: Content-Type = %q, want application/json", method, url, ct)
		}
		if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
			t.Fatalf("%s %s: decode response: %v", method, url, err)
		}
	}
	return resp
}

func wantStatus(t *testing.T, resp *http.Response, want int) {
	t.Helper()
	if resp.StatusCode != want {
		t.Fatalf("%s %s: status = %d, want %d", resp.Request.Method, resp.Request.URL.Path, resp.StatusCode, want)
	}
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)
	var got map[string]string
	resp := do(t, "GET", ts.URL+"/health", "", &got)
	wantStatus(t, resp, http.StatusOK)
	if got["status"] != "ok" {
		t.Errorf("status = %q, want ok", got["status"])
	}
}

func TestBookCRUD(t *testing.T) {
	ts := newTestServer(t)

	var created Book
	resp := do(t, "POST", ts.URL+"/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`, &created)
	wantStatus(t, resp, http.StatusCreated)
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"}
	if created.ID == 0 || created != want {
		t.Fatalf("created = %+v, want %+v with non-zero ID", created, want)
	}
	if loc := resp.Header.Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	var got Book
	resp = do(t, "GET", ts.URL+"/books/1", "", &got)
	wantStatus(t, resp, http.StatusOK)
	if got != created {
		t.Errorf("get = %+v, want %+v", got, created)
	}

	var updated Book
	resp = do(t, "PUT", ts.URL+"/books/1",
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"9780441172696"}`, &updated)
	wantStatus(t, resp, http.StatusOK)
	want = Book{ID: 1, Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969, ISBN: "9780441172696"}
	if updated != want {
		t.Errorf("updated = %+v, want %+v", updated, want)
	}
	do(t, "GET", ts.URL+"/books/1", "", &got)
	if got != want {
		t.Errorf("get after update = %+v, want %+v", got, want)
	}

	resp = do(t, "DELETE", ts.URL+"/books/1", "", nil)
	wantStatus(t, resp, http.StatusNoContent)

	resp = do(t, "GET", ts.URL+"/books/1", "", nil)
	wantStatus(t, resp, http.StatusNotFound)
}

func TestListBooksAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	var books []Book
	resp := do(t, "GET", ts.URL+"/books", "", &books)
	wantStatus(t, resp, http.StatusOK)
	if books == nil || len(books) != 0 {
		t.Fatalf("empty list = %#v, want [] (not null)", books)
	}

	for _, body := range []string{
		`{"title":"Dune","author":"Frank Herbert","year":1965}`,
		`{"title":"Emma","author":"Jane Austen","year":1815}`,
		`{"title":"Persuasion","author":"Jane Austen","year":1817}`,
	} {
		wantStatus(t, do(t, "POST", ts.URL+"/books", body, nil), http.StatusCreated)
	}

	do(t, "GET", ts.URL+"/books", "", &books)
	if len(books) != 3 {
		t.Fatalf("list returned %d books, want 3", len(books))
	}

	do(t, "GET", ts.URL+"/books?author=Jane+Austen", "", &books)
	if len(books) != 2 || books[0].Title != "Emma" || books[1].Title != "Persuasion" {
		t.Errorf("filtered list = %+v, want Emma and Persuasion", books)
	}

	do(t, "GET", ts.URL+"/books?author=jane+austen", "", &books)
	if len(books) != 2 {
		t.Errorf("case-insensitive filter returned %d books, want 2", len(books))
	}

	do(t, "GET", ts.URL+"/books?author=Nobody", "", &books)
	if len(books) != 0 {
		t.Errorf("filter for unknown author returned %d books, want 0", len(books))
	}
}

func TestValidation(t *testing.T) {
	ts := newTestServer(t)
	wantStatus(t, do(t, "POST", ts.URL+"/books", `{"title":"Dune","author":"Frank Herbert"}`, nil), http.StatusCreated)

	tests := []struct {
		name   string
		body   string
		status int
		fields []string
	}{
		{"missing title", `{"author":"A"}`, http.StatusUnprocessableEntity, []string{"title"}},
		{"missing author", `{"title":"T"}`, http.StatusUnprocessableEntity, []string{"author"}},
		{"blank title and author", `{"title":"  ","author":""}`, http.StatusUnprocessableEntity, []string{"title", "author"}},
		{"negative year", `{"title":"T","author":"A","year":-1}`, http.StatusUnprocessableEntity, []string{"year"}},
		{"malformed JSON", `{"title":`, http.StatusBadRequest, nil},
		{"wrong type", `{"title":"T","author":"A","year":"1965"}`, http.StatusBadRequest, nil},
		{"unknown field", `{"title":"T","author":"A","pages":3}`, http.StatusBadRequest, nil},
		{"empty body", ``, http.StatusBadRequest, nil},
	}
	for _, target := range []struct{ method, path string }{{"POST", "/books"}, {"PUT", "/books/1"}} {
		for _, tc := range tests {
			t.Run(target.method+" "+tc.name, func(t *testing.T) {
				var got struct {
					Error  string            `json:"error"`
					Fields map[string]string `json:"fields"`
				}
				resp := do(t, target.method, ts.URL+target.path, tc.body, &got)
				wantStatus(t, resp, tc.status)
				if got.Error == "" {
					t.Error("error message is empty")
				}
				if len(got.Fields) != len(tc.fields) {
					t.Errorf("fields = %v, want keys %v", got.Fields, tc.fields)
				}
				for _, f := range tc.fields {
					if got.Fields[f] == "" {
						t.Errorf("missing validation error for field %q", f)
					}
				}
			})
		}
	}

	// Rejected requests must not have modified anything.
	var books []Book
	do(t, "GET", ts.URL+"/books", "", &books)
	if len(books) != 1 || books[0].Title != "Dune" {
		t.Errorf("books after rejected requests = %+v, want only the original Dune", books)
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	ts := newTestServer(t)
	valid := `{"title":"T","author":"A"}`

	tests := []struct {
		method, path, body string
		status             int
	}{
		{"GET", "/books/999", "", http.StatusNotFound},
		{"PUT", "/books/999", valid, http.StatusNotFound},
		{"DELETE", "/books/999", "", http.StatusNotFound},
		{"GET", "/books/abc", "", http.StatusBadRequest},
		{"PUT", "/books/abc", valid, http.StatusBadRequest},
		{"DELETE", "/books/0", "", http.StatusBadRequest},
	}
	for _, tc := range tests {
		t.Run(tc.method+" "+tc.path, func(t *testing.T) {
			var got map[string]string
			resp := do(t, tc.method, ts.URL+tc.path, tc.body, &got)
			wantStatus(t, resp, tc.status)
			if got["error"] == "" {
				t.Error("error message is empty")
			}
		})
	}

	resp := do(t, "PATCH", ts.URL+"/books/1", valid, nil)
	wantStatus(t, resp, http.StatusMethodNotAllowed)
}

func TestStorePersistsToFile(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := NewStore(path)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	b := Book{Title: "Dune", Author: "Frank Herbert", Year: 1965}
	if err := store.Create(t.Context(), &b); err != nil {
		t.Fatalf("Create: %v", err)
	}
	store.Close()

	store, err = NewStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer store.Close()
	got, err := store.Get(t.Context(), b.ID)
	if err != nil {
		t.Fatalf("Get after reopen: %v", err)
	}
	if got != b {
		t.Errorf("after reopen = %+v, want %+v", got, b)
	}
}
