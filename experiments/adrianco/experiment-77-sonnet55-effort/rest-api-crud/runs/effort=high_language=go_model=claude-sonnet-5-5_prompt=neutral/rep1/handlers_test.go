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
	store, err := NewStore(filepath.Join(t.TempDir(), "test.db"))
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

func mustCreate(t *testing.T, srv *httptest.Server, body string) Book {
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
	if resp.StatusCode != http.StatusOK || !strings.Contains(string(data), `"ok"`) {
		t.Fatalf("got %d %s", resp.StatusCode, data)
	}
}

func TestCreateAndGet(t *testing.T) {
	srv := newTestServer(t)
	b := mustCreate(t, srv, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if b.ID == 0 || b.Title != "Dune" || b.Year != 1965 || b.ISBN != "9780441013593" {
		t.Fatalf("unexpected book %+v", b)
	}
	resp, data := do(t, "GET", srv.URL+"/books/1", "")
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status %d", resp.StatusCode)
	}
	var got Book
	json.Unmarshal(data, &got)
	if got != b {
		t.Fatalf("got %+v want %+v", got, b)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)
	cases := map[string]string{
		"missing title":  `{"author":"A"}`,
		"blank title":    `{"title":"   ","author":"A"}`,
		"missing author": `{"title":"T"}`,
		"negative year":  `{"title":"T","author":"A","year":-1}`,
		"bad json":       `{not json`,
		"unknown field":  `{"title":"T","author":"A","foo":1}`,
		"empty body":     ``,
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
}

func TestListAndAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	resp, data := do(t, "GET", srv.URL+"/books", "")
	if resp.StatusCode != http.StatusOK || strings.TrimSpace(string(data)) != "[]" {
		t.Fatalf("empty list: %d %s", resp.StatusCode, data)
	}

	mustCreate(t, srv, `{"title":"Dune","author":"Frank Herbert"}`)
	mustCreate(t, srv, `{"title":"Emma","author":"Jane Austen"}`)
	mustCreate(t, srv, `{"title":"Persuasion","author":"Jane Austen"}`)

	var all, austen, none []Book
	_, data = do(t, "GET", srv.URL+"/books", "")
	json.Unmarshal(data, &all)
	_, data = do(t, "GET", srv.URL+"/books?author=Jane+Austen", "")
	json.Unmarshal(data, &austen)
	_, data = do(t, "GET", srv.URL+"/books?author=Nobody", "")
	json.Unmarshal(data, &none)

	if len(all) != 3 || len(austen) != 2 || len(none) != 0 {
		t.Fatalf("counts all=%d austen=%d none=%d", len(all), len(austen), len(none))
	}
}

func TestUpdate(t *testing.T) {
	srv := newTestServer(t)
	mustCreate(t, srv, `{"title":"Dune","author":"Frank Herbert","year":1965}`)

	resp, data := do(t, "PUT", srv.URL+"/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"x"}`)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status %d %s", resp.StatusCode, data)
	}
	var got Book
	_, data = do(t, "GET", srv.URL+"/books/1", "")
	json.Unmarshal(data, &got)
	if got.Title != "Dune Messiah" || got.Year != 1969 || got.ISBN != "x" {
		t.Fatalf("not updated: %+v", got)
	}

	resp, _ = do(t, "PUT", srv.URL+"/books/1", `{"title":"","author":"A"}`)
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("invalid update status %d", resp.StatusCode)
	}
	resp, _ = do(t, "PUT", srv.URL+"/books/99", `{"title":"T","author":"A"}`)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("missing update status %d", resp.StatusCode)
	}
}

func TestDelete(t *testing.T) {
	srv := newTestServer(t)
	mustCreate(t, srv, `{"title":"Dune","author":"Frank Herbert"}`)

	resp, _ := do(t, "DELETE", srv.URL+"/books/1", "")
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete status %d", resp.StatusCode)
	}
	resp, _ = do(t, "GET", srv.URL+"/books/1", "")
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("get after delete status %d", resp.StatusCode)
	}
	resp, _ = do(t, "DELETE", srv.URL+"/books/1", "")
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("second delete status %d", resp.StatusCode)
	}
}

func TestInvalidAndMissingID(t *testing.T) {
	srv := newTestServer(t)
	resp, _ := do(t, "GET", srv.URL+"/books/abc", "")
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("bad id status %d", resp.StatusCode)
	}
	resp, _ = do(t, "GET", srv.URL+"/books/42", "")
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("missing id status %d", resp.StatusCode)
	}
}
