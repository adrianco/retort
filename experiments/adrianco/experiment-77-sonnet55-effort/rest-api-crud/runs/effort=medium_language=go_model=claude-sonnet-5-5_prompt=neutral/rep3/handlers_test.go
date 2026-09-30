package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newServer(t *testing.T) *httptest.Server {
	t.Helper()
	s, err := NewStore(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	srv := httptest.NewServer(NewHandler(s))
	t.Cleanup(func() { srv.Close(); s.Close() })
	return srv
}

func do(t *testing.T, method, url, body string) (*http.Response, []byte) {
	t.Helper()
	req, _ := http.NewRequest(method, url, strings.NewReader(body))
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var buf strings.Builder
	b := make([]byte, 4096)
	for {
		n, err := resp.Body.Read(b)
		buf.Write(b[:n])
		if err != nil {
			break
		}
	}
	return resp, []byte(buf.String())
}

func TestHealth(t *testing.T) {
	srv := newServer(t)
	resp, _ := do(t, "GET", srv.URL+"/health", "")
	if resp.StatusCode != 200 {
		t.Fatalf("status %d", resp.StatusCode)
	}
}

func TestCRUD(t *testing.T) {
	srv := newServer(t)

	resp, body := do(t, "POST", srv.URL+"/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}`)
	if resp.StatusCode != 201 {
		t.Fatalf("create: %d %s", resp.StatusCode, body)
	}
	var b Book
	json.Unmarshal(body, &b)
	if b.ID == 0 || b.Title != "Dune" {
		t.Fatalf("bad book %+v", b)
	}
	url := srv.URL + "/books/1"

	resp, body = do(t, "GET", url, "")
	if resp.StatusCode != 200 || !strings.Contains(string(body), "Frank Herbert") {
		t.Fatalf("get: %d %s", resp.StatusCode, body)
	}

	resp, body = do(t, "PUT", url, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"456"}`)
	if resp.StatusCode != 200 || !strings.Contains(string(body), "Dune Messiah") {
		t.Fatalf("update: %d %s", resp.StatusCode, body)
	}

	resp, _ = do(t, "DELETE", url, "")
	if resp.StatusCode != 204 {
		t.Fatalf("delete: %d", resp.StatusCode)
	}
	resp, _ = do(t, "GET", url, "")
	if resp.StatusCode != 404 {
		t.Fatalf("get after delete: %d", resp.StatusCode)
	}
	resp, _ = do(t, "DELETE", url, "")
	if resp.StatusCode != 404 {
		t.Fatalf("second delete: %d", resp.StatusCode)
	}
}

func TestValidation(t *testing.T) {
	srv := newServer(t)
	cases := []string{
		`{"author":"A"}`,
		`{"title":"T"}`,
		`{"title":"  ","author":"A"}`,
		`not json`,
		`{"title":"T","author":"A","year":-5}`,
	}
	for _, c := range cases {
		if resp, _ := do(t, "POST", srv.URL+"/books", c); resp.StatusCode != 400 {
			t.Errorf("%q: got %d, want 400", c, resp.StatusCode)
		}
	}
	if resp, _ := do(t, "PUT", srv.URL+"/books/1", `{"title":"T","author":"A"}`); resp.StatusCode != 404 {
		t.Errorf("put missing: got %d", resp.StatusCode)
	}
	if resp, _ := do(t, "GET", srv.URL+"/books/abc", ""); resp.StatusCode != 400 {
		t.Errorf("bad id: got %d", resp.StatusCode)
	}
}

func TestListFilter(t *testing.T) {
	srv := newServer(t)
	for _, b := range []string{
		`{"title":"A","author":"X"}`, `{"title":"B","author":"Y"}`, `{"title":"C","author":"X"}`,
	} {
		do(t, "POST", srv.URL+"/books", b)
	}
	count := func(u string) int {
		_, body := do(t, "GET", u, "")
		var bs []Book
		if err := json.Unmarshal(body, &bs); err != nil {
			t.Fatal(err)
		}
		return len(bs)
	}
	if n := count(srv.URL + "/books"); n != 3 {
		t.Errorf("all: %d", n)
	}
	if n := count(srv.URL + "/books?author=X"); n != 2 {
		t.Errorf("filter: %d", n)
	}
	if n := count(srv.URL + "/books?author=Nobody"); n != 0 {
		t.Errorf("none: %d", n)
	}
}
