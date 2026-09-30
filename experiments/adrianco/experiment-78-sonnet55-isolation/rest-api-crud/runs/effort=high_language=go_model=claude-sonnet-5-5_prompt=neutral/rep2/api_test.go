package main

import (
	"encoding/json"
	"io"
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
		t.Fatal(err)
	}
	srv := httptest.NewServer((&API{store: store}).Handler())
	t.Cleanup(func() { srv.Close(); store.Close() })
	return srv
}

func do(t *testing.T, method, url, body string) (*http.Response, []byte) {
	t.Helper()
	req, err := http.NewRequest(method, url, strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatal(err)
	}
	return resp, data
}

func createBook(t *testing.T, srv *httptest.Server, body string) Book {
	t.Helper()
	resp, data := do(t, "POST", srv.URL+"/books", body)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create: status %d body %s", resp.StatusCode, data)
	}
	var b Book
	if err := json.Unmarshal(data, &b); err != nil {
		t.Fatal(err)
	}
	return b
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	resp, data := do(t, "GET", srv.URL+"/health", "")
	if resp.StatusCode != 200 || !strings.Contains(string(data), `"ok"`) {
		t.Fatalf("got %d %s", resp.StatusCode, data)
	}
}

func TestCreateAndGet(t *testing.T) {
	srv := newTestServer(t)
	b := createBook(t, srv, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if b.ID == 0 || b.Title != "Dune" || b.Year != 1965 {
		t.Fatalf("unexpected book %+v", b)
	}
	resp, data := do(t, "GET", srv.URL+"/books/1", "")
	if resp.StatusCode != 200 {
		t.Fatalf("status %d", resp.StatusCode)
	}
	var got Book
	json.Unmarshal(data, &got)
	if got != b {
		t.Fatalf("got %+v want %+v", got, b)
	}
}

func TestValidation(t *testing.T) {
	srv := newTestServer(t)
	cases := map[string]string{
		"missing title":  `{"author":"A"}`,
		"blank title":    `{"title":"  ","author":"A"}`,
		"missing author": `{"title":"T"}`,
		"bad year":       `{"title":"T","author":"A","year":-5}`,
		"invalid json":   `{nope`,
		"wrong type":     `{"title":5,"author":"A"}`,
		"trailing data":  `{"title":"T","author":"A"} {}`,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			resp, data := do(t, "POST", srv.URL+"/books", body)
			if resp.StatusCode != http.StatusBadRequest {
				t.Fatalf("status %d body %s", resp.StatusCode, data)
			}
			if !strings.Contains(string(data), `"error"`) {
				t.Fatalf("no error field: %s", data)
			}
		})
	}
	// Updates are validated too.
	createBook(t, srv, `{"title":"T","author":"A"}`)
	if resp, _ := do(t, "PUT", srv.URL+"/books/1", `{"title":"","author":"A"}`); resp.StatusCode != 400 {
		t.Fatalf("PUT status %d", resp.StatusCode)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, `{"title":"Dune","author":"Frank Herbert"}`)
	createBook(t, srv, `{"title":"Emma","author":"Jane Austen"}`)
	createBook(t, srv, `{"title":"Persuasion","author":"Jane Austen"}`)

	list := func(query string) []Book {
		resp, data := do(t, "GET", srv.URL+"/books"+query, "")
		if resp.StatusCode != 200 {
			t.Fatalf("status %d", resp.StatusCode)
		}
		var books []Book
		if err := json.Unmarshal(data, &books); err != nil {
			t.Fatal(err)
		}
		return books
	}
	if n := len(list("")); n != 3 {
		t.Fatalf("all: got %d", n)
	}
	if n := len(list("?author=Jane+Austen")); n != 2 {
		t.Fatalf("filtered: got %d", n)
	}
	if books := list("?author=Nobody"); books == nil || len(books) != 0 {
		t.Fatalf("expected empty non-nil list, got %#v", books)
	}
}

func TestUpdateAndDelete(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, `{"title":"Old","author":"A","year":2000}`)

	resp, data := do(t, "PUT", srv.URL+"/books/1", `{"title":"New","author":"B","year":2001,"isbn":"X"}`)
	if resp.StatusCode != 200 {
		t.Fatalf("PUT status %d %s", resp.StatusCode, data)
	}
	_, data = do(t, "GET", srv.URL+"/books/1", "")
	var got Book
	json.Unmarshal(data, &got)
	if got.Title != "New" || got.Author != "B" || got.Year != 2001 || got.ISBN != "X" {
		t.Fatalf("not updated: %+v", got)
	}

	if resp, _ := do(t, "DELETE", srv.URL+"/books/1", ""); resp.StatusCode != 204 {
		t.Fatalf("DELETE status %d", resp.StatusCode)
	}
	if resp, _ := do(t, "GET", srv.URL+"/books/1", ""); resp.StatusCode != 404 {
		t.Fatalf("GET after delete status %d", resp.StatusCode)
	}
	if resp, _ := do(t, "DELETE", srv.URL+"/books/1", ""); resp.StatusCode != 404 {
		t.Fatalf("second DELETE status %d", resp.StatusCode)
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	srv := newTestServer(t)
	for _, tc := range []struct {
		method, path, body string
		want               int
	}{
		{"GET", "/books/42", "", 404},
		{"PUT", "/books/42", `{"title":"T","author":"A"}`, 404},
		{"DELETE", "/books/42", "", 404},
		{"GET", "/books/abc", "", 400},
		{"PUT", "/books/0", `{"title":"T","author":"A"}`, 400},
	} {
		resp, _ := do(t, tc.method, srv.URL+tc.path, tc.body)
		if resp.StatusCode != tc.want {
			t.Errorf("%s %s: got %d want %d", tc.method, tc.path, resp.StatusCode, tc.want)
		}
	}
}

func TestPersistenceAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	s1, err := NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := s1.Create(Book{Title: "Persisted", Author: "A"}); err != nil {
		t.Fatal(err)
	}
	s1.Close()

	s2, err := NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s2.Close()
	books, err := s2.List("")
	if err != nil || len(books) != 1 || books[0].Title != "Persisted" {
		t.Fatalf("got %v, %v", books, err)
	}
}
