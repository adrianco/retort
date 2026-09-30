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
	ts := httptest.NewServer(NewHandler(store))
	t.Cleanup(func() { ts.Close(); store.Close() })
	return ts
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

func mustCreate(t *testing.T, ts *httptest.Server, body string) Book {
	t.Helper()
	resp, data := do(t, "POST", ts.URL+"/books", body)
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
	ts := newTestServer(t)
	resp, data := do(t, "GET", ts.URL+"/health", "")
	if resp.StatusCode != 200 || !strings.Contains(string(data), `"ok"`) {
		t.Fatalf("got %d %s", resp.StatusCode, data)
	}
}

func TestCreateAndGet(t *testing.T) {
	ts := newTestServer(t)
	b := mustCreate(t, ts, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if b.ID == 0 || b.Title != "Dune" || b.Year != 1965 {
		t.Fatalf("unexpected book %+v", b)
	}
	resp, data := do(t, "GET", ts.URL+"/books/1", "")
	if resp.StatusCode != 200 {
		t.Fatalf("status %d", resp.StatusCode)
	}
	var got Book
	json.Unmarshal(data, &got)
	if got != b {
		t.Fatalf("got %+v want %+v", got, b)
	}
}

func TestCreateValidation(t *testing.T) {
	ts := newTestServer(t)
	cases := map[string]struct {
		body   string
		status int
	}{
		"missing title":  {`{"author":"A"}`, 422},
		"missing author": {`{"title":"T"}`, 422},
		"blank title":    {`{"title":"   ","author":"A"}`, 422},
		"negative year":  {`{"title":"T","author":"A","year":-1}`, 422},
		"malformed json": {`{"title":`, 400},
		"unknown field":  {`{"title":"T","author":"A","foo":1}`, 400},
		"wrong type":     {`{"title":5,"author":"A"}`, 400},
		"trailing data":  {`{"title":"T","author":"A"}{}`, 400},
		"valid minimal":  {`{"title":"T","author":"A"}`, 201},
	}
	for name, c := range cases {
		t.Run(name, func(t *testing.T) {
			resp, data := do(t, "POST", ts.URL+"/books", c.body)
			if resp.StatusCode != c.status {
				t.Fatalf("got %d want %d: %s", resp.StatusCode, c.status, data)
			}
			if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
				t.Fatalf("content-type %q", ct)
			}
		})
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	resp, data := do(t, "GET", ts.URL+"/books", "")
	if resp.StatusCode != 200 || strings.TrimSpace(string(data)) != "[]" {
		t.Fatalf("empty list: %d %s", resp.StatusCode, data)
	}

	mustCreate(t, ts, `{"title":"Dune","author":"Frank Herbert"}`)
	mustCreate(t, ts, `{"title":"Emma","author":"Jane Austen"}`)
	mustCreate(t, ts, `{"title":"Persuasion","author":"Jane Austen"}`)

	var all []Book
	_, data = do(t, "GET", ts.URL+"/books", "")
	json.Unmarshal(data, &all)
	if len(all) != 3 {
		t.Fatalf("want 3 books, got %d", len(all))
	}

	var austen []Book
	_, data = do(t, "GET", ts.URL+"/books?author=jane%20austen", "")
	json.Unmarshal(data, &austen)
	if len(austen) != 2 {
		t.Fatalf("want 2 books by Austen, got %d", len(austen))
	}

	var none []Book
	_, data = do(t, "GET", ts.URL+"/books?author=Nobody", "")
	json.Unmarshal(data, &none)
	if none == nil || len(none) != 0 {
		t.Fatalf("want empty non-nil list, got %v (%s)", none, data)
	}
}

func TestUpdate(t *testing.T) {
	ts := newTestServer(t)
	b := mustCreate(t, ts, `{"title":"Dun","author":"F. Herbert","year":1965}`)

	resp, data := do(t, "PUT", ts.URL+"/books/1", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}`)
	if resp.StatusCode != 200 {
		t.Fatalf("status %d: %s", resp.StatusCode, data)
	}
	var got Book
	json.Unmarshal(data, &got)
	if got.ID != b.ID || got.Title != "Dune" || got.ISBN != "123" {
		t.Fatalf("unexpected %+v", got)
	}

	if resp, _ := do(t, "PUT", ts.URL+"/books/1", `{"title":"","author":"x"}`); resp.StatusCode != 422 {
		t.Fatalf("invalid update status %d", resp.StatusCode)
	}
	if resp, _ := do(t, "PUT", ts.URL+"/books/99", `{"title":"a","author":"b"}`); resp.StatusCode != 404 {
		t.Fatalf("missing update status %d", resp.StatusCode)
	}
}

func TestDelete(t *testing.T) {
	ts := newTestServer(t)
	mustCreate(t, ts, `{"title":"Dune","author":"Frank Herbert"}`)

	if resp, _ := do(t, "DELETE", ts.URL+"/books/1", ""); resp.StatusCode != 204 {
		t.Fatalf("delete status %d", resp.StatusCode)
	}
	if resp, _ := do(t, "GET", ts.URL+"/books/1", ""); resp.StatusCode != 404 {
		t.Fatalf("get after delete status %d", resp.StatusCode)
	}
	if resp, _ := do(t, "DELETE", ts.URL+"/books/1", ""); resp.StatusCode != 404 {
		t.Fatalf("second delete status %d", resp.StatusCode)
	}
}

func TestBadAndMissingID(t *testing.T) {
	ts := newTestServer(t)
	for _, id := range []string{"abc", "0", "-3"} {
		if resp, _ := do(t, "GET", ts.URL+"/books/"+id, ""); resp.StatusCode != 400 {
			t.Fatalf("id %q: status %d", id, resp.StatusCode)
		}
	}
	if resp, _ := do(t, "GET", ts.URL+"/books/42", ""); resp.StatusCode != 404 {
		t.Fatalf("status %d", resp.StatusCode)
	}
}

func TestPersistsOnDisk(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	s1, err := NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := s1.Create(Book{Title: "Dune", Author: "Frank Herbert"}); err != nil {
		t.Fatal(err)
	}
	s1.Close()

	s2, err := NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s2.Close()
	books, err := s2.List("")
	if err != nil || len(books) != 1 || books[0].Title != "Dune" {
		t.Fatalf("got %v, %v", books, err)
	}
}
