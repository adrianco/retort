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
	srv := httptest.NewServer(NewHandler(store))
	t.Cleanup(func() {
		srv.Close()
		store.Close()
	})
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

func mustBook(t *testing.T, data []byte) Book {
	t.Helper()
	var b Book
	if err := json.Unmarshal(data, &b); err != nil {
		t.Fatalf("decode %q: %v", data, err)
	}
	return b
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	resp, body := do(t, "GET", srv.URL+"/health", "")
	if resp.StatusCode != 200 || !strings.Contains(string(body), `"ok"`) {
		t.Fatalf("got %d %s", resp.StatusCode, body)
	}
}

func TestCRUDLifecycle(t *testing.T) {
	srv := newTestServer(t)

	resp, body := do(t, "POST", srv.URL+"/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create: %d %s", resp.StatusCode, body)
	}
	created := mustBook(t, body)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := resp.Header.Get("Location"); loc != "/books/1" {
		t.Fatalf("Location = %q", loc)
	}

	resp, body = do(t, "GET", srv.URL+"/books/1", "")
	if resp.StatusCode != 200 || mustBook(t, body) != created {
		t.Fatalf("get: %d %s", resp.StatusCode, body)
	}

	resp, body = do(t, "PUT", srv.URL+"/books/1",
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"9780593098233"}`)
	if resp.StatusCode != 200 {
		t.Fatalf("update: %d %s", resp.StatusCode, body)
	}
	if b := mustBook(t, body); b.Title != "Dune Messiah" || b.Year != 1969 || b.ID != 1 {
		t.Fatalf("unexpected updated book: %+v", b)
	}
	_, body = do(t, "GET", srv.URL+"/books/1", "")
	if mustBook(t, body).Title != "Dune Messiah" {
		t.Fatalf("update not persisted: %s", body)
	}

	resp, _ = do(t, "DELETE", srv.URL+"/books/1", "")
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete: %d", resp.StatusCode)
	}
	resp, _ = do(t, "GET", srv.URL+"/books/1", "")
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("get after delete: %d", resp.StatusCode)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	resp, body := do(t, "GET", srv.URL+"/books", "")
	if resp.StatusCode != 200 || strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("empty list: %d %s", resp.StatusCode, body)
	}

	for _, b := range []string{
		`{"title":"A","author":"Alice"}`,
		`{"title":"B","author":"Bob"}`,
		`{"title":"C","author":"Alice"}`,
	} {
		if resp, body := do(t, "POST", srv.URL+"/books", b); resp.StatusCode != 201 {
			t.Fatalf("create: %d %s", resp.StatusCode, body)
		}
	}

	var all, alice, none []Book
	_, body = do(t, "GET", srv.URL+"/books", "")
	json.Unmarshal(body, &all)
	_, body = do(t, "GET", srv.URL+"/books?author=Alice", "")
	json.Unmarshal(body, &alice)
	resp, body = do(t, "GET", srv.URL+"/books?author=Nobody", "")
	json.Unmarshal(body, &none)

	if len(all) != 3 || len(alice) != 2 || len(none) != 0 {
		t.Fatalf("counts all=%d alice=%d none=%d", len(all), len(alice), len(none))
	}
	if strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("expected [] got %s", body)
	}
	for _, b := range alice {
		if b.Author != "Alice" {
			t.Fatalf("filter leaked %+v", b)
		}
	}
}

func TestValidation(t *testing.T) {
	srv := newTestServer(t)
	cases := map[string]string{
		"missing title":  `{"author":"X"}`,
		"blank title":    `{"title":"   ","author":"X"}`,
		"missing author": `{"title":"T"}`,
		"blank author":   `{"title":"T","author":""}`,
		"negative year":  `{"title":"T","author":"X","year":-1}`,
		"wrong type":     `{"title":"T","author":"X","year":"abc"}`,
		"malformed json": `{"title":`,
		"empty body":     ``,
		"unknown field":  `{"title":"T","author":"X","foo":1}`,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			resp, out := do(t, "POST", srv.URL+"/books", body)
			if resp.StatusCode != http.StatusBadRequest {
				t.Fatalf("POST: got %d %s", resp.StatusCode, out)
			}
			if !strings.Contains(string(out), `"error"`) {
				t.Fatalf("no error field: %s", out)
			}
		})
	}

	do(t, "POST", srv.URL+"/books", `{"title":"T","author":"X"}`)
	resp, _ := do(t, "PUT", srv.URL+"/books/1", `{"title":"","author":"X"}`)
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("PUT invalid: got %d", resp.StatusCode)
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	srv := newTestServer(t)
	body := `{"title":"T","author":"X"}`
	for _, tc := range []struct {
		method, path, body string
		want               int
	}{
		{"GET", "/books/99", "", 404},
		{"PUT", "/books/99", body, 404},
		{"DELETE", "/books/99", "", 404},
		{"GET", "/books/abc", "", 400},
		{"PUT", "/books/abc", body, 400},
		{"DELETE", "/books/0", "", 400},
	} {
		resp, out := do(t, tc.method, srv.URL+tc.path, tc.body)
		if resp.StatusCode != tc.want {
			t.Errorf("%s %s: got %d want %d (%s)", tc.method, tc.path, resp.StatusCode, tc.want, out)
		}
	}
}

func TestPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	s, err := NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	b := &Book{Title: "T", Author: "A"}
	if err := s.Create(b); err != nil {
		t.Fatal(err)
	}
	s.Close()

	s, err = NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	got, err := s.Get(b.ID)
	if err != nil || got.Title != "T" {
		t.Fatalf("got %+v, %v", got, err)
	}
}
