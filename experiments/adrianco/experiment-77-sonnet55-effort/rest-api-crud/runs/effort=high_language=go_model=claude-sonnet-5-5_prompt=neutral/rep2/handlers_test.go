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
	store, err := OpenStore(filepath.Join(t.TempDir(), "test.db"))
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
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, body %s", resp.StatusCode, body)
	}
	var m map[string]string
	json.Unmarshal(body, &m)
	if m["status"] != "ok" {
		t.Errorf("status field = %q", m["status"])
	}
}

func TestCRUDLifecycle(t *testing.T) {
	srv := newTestServer(t)

	resp, body := do(t, "POST", srv.URL+"/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d, body %s", resp.StatusCode, body)
	}
	created := mustBook(t, body)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 || created.ISBN != "9780441172719" {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := resp.Header.Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q", loc)
	}
	url := srv.URL + "/books/1"

	resp, body = do(t, "GET", url, "")
	if resp.StatusCode != http.StatusOK || mustBook(t, body) != created {
		t.Fatalf("get: %d %s", resp.StatusCode, body)
	}

	resp, body = do(t, "PUT", url,
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"9780441172696"}`)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("update status = %d, body %s", resp.StatusCode, body)
	}
	if got := mustBook(t, body); got.ID != created.ID || got.Title != "Dune Messiah" || got.Year != 1969 {
		t.Fatalf("unexpected updated book: %+v", got)
	}
	_, body = do(t, "GET", url, "")
	if mustBook(t, body).Title != "Dune Messiah" {
		t.Errorf("update not persisted: %s", body)
	}

	resp, _ = do(t, "DELETE", url, "")
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete status = %d", resp.StatusCode)
	}
	resp, _ = do(t, "GET", url, "")
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("get after delete = %d", resp.StatusCode)
	}
	resp, _ = do(t, "DELETE", url, "")
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("second delete = %d", resp.StatusCode)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	resp, body := do(t, "GET", srv.URL+"/books", "")
	if resp.StatusCode != http.StatusOK || strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("empty list: %d %s", resp.StatusCode, body)
	}

	for _, s := range []string{
		`{"title":"A","author":"Ann Author"}`,
		`{"title":"B","author":"Bob Writer"}`,
		`{"title":"C","author":"Ann Author"}`,
	} {
		if resp, body := do(t, "POST", srv.URL+"/books", s); resp.StatusCode != http.StatusCreated {
			t.Fatalf("create: %d %s", resp.StatusCode, body)
		}
	}

	var all []Book
	_, body = do(t, "GET", srv.URL+"/books", "")
	json.Unmarshal(body, &all)
	if len(all) != 3 {
		t.Fatalf("len(all) = %d", len(all))
	}

	var filtered []Book
	_, body = do(t, "GET", srv.URL+"/books?author=Ann+Author", "")
	json.Unmarshal(body, &filtered)
	if len(filtered) != 2 || filtered[0].Title != "A" || filtered[1].Title != "C" {
		t.Fatalf("filtered = %+v", filtered)
	}

	_, body = do(t, "GET", srv.URL+"/books?author=Nobody", "")
	if strings.TrimSpace(string(body)) != "[]" {
		t.Errorf("no-match list = %s", body)
	}
}

func TestValidation(t *testing.T) {
	srv := newTestServer(t)
	tests := []struct {
		name, body string
		want       int
	}{
		{"missing title", `{"author":"X"}`, http.StatusUnprocessableEntity},
		{"missing author", `{"title":"X"}`, http.StatusUnprocessableEntity},
		{"blank title", `{"title":"   ","author":"X"}`, http.StatusUnprocessableEntity},
		{"negative year", `{"title":"T","author":"X","year":-5}`, http.StatusUnprocessableEntity},
		{"bad json", `{"title":`, http.StatusBadRequest},
		{"wrong type", `{"title":5,"author":"X"}`, http.StatusBadRequest},
		{"empty body", ``, http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			resp, body := do(t, "POST", srv.URL+"/books", tt.body)
			if resp.StatusCode != tt.want {
				t.Errorf("POST status = %d, want %d (%s)", resp.StatusCode, tt.want, body)
			}
			if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
				t.Errorf("Content-Type = %q", ct)
			}
		})
	}

	// Validation also applies to PUT.
	do(t, "POST", srv.URL+"/books", `{"title":"T","author":"A"}`)
	resp, _ := do(t, "PUT", srv.URL+"/books/1", `{"title":"","author":"A"}`)
	if resp.StatusCode != http.StatusUnprocessableEntity {
		t.Errorf("PUT invalid status = %d", resp.StatusCode)
	}
	// Nothing invalid should have been stored.
	_, body := do(t, "GET", srv.URL+"/books", "")
	var all []Book
	json.Unmarshal(body, &all)
	if len(all) != 1 {
		t.Errorf("books stored = %d, want 1", len(all))
	}
}

func TestBadAndMissingIDs(t *testing.T) {
	srv := newTestServer(t)
	for _, id := range []string{"abc", "0", "-1"} {
		resp, _ := do(t, "GET", srv.URL+"/books/"+id, "")
		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("GET %s = %d, want 400", id, resp.StatusCode)
		}
	}
	resp, _ := do(t, "GET", srv.URL+"/books/999", "")
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("GET missing = %d", resp.StatusCode)
	}
	resp, _ = do(t, "PUT", srv.URL+"/books/999", `{"title":"T","author":"A"}`)
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("PUT missing = %d", resp.StatusCode)
	}
}

func TestPersistence(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persist.db")
	s1, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	b, err := s1.Create(Book{Title: "T", Author: "A", Year: 2000})
	if err != nil {
		t.Fatal(err)
	}
	s1.Close()

	s2, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s2.Close()
	got, err := s2.Get(b.ID)
	if err != nil || got != b {
		t.Fatalf("Get after reopen = %+v, %v", got, err)
	}
}
