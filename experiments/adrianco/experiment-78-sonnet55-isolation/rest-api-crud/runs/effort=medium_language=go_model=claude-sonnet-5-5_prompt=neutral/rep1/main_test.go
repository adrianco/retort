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
	srv := httptest.NewServer((&API{s}).routes())
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
		t.Fatalf("got %d", resp.StatusCode)
	}
}

func TestCRUD(t *testing.T) {
	srv := newServer(t)
	resp, body := do(t, "POST", srv.URL+"/books", `{"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}`)
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
	if resp.StatusCode != 200 || !strings.Contains(string(body), "Herbert") {
		t.Fatalf("get: %d %s", resp.StatusCode, body)
	}
	resp, body = do(t, "PUT", url, `{"title":"Dune Messiah","author":"Herbert","year":1969,"isbn":"456"}`)
	if resp.StatusCode != 200 || !strings.Contains(string(body), "Messiah") {
		t.Fatalf("update: %d %s", resp.StatusCode, body)
	}
	resp, _ = do(t, "DELETE", url, "")
	if resp.StatusCode != 204 {
		t.Fatalf("delete: %d", resp.StatusCode)
	}
	resp, _ = do(t, "GET", url, "")
	if resp.StatusCode != 404 {
		t.Fatalf("after delete: %d", resp.StatusCode)
	}
	resp, _ = do(t, "DELETE", url, "")
	if resp.StatusCode != 404 {
		t.Fatalf("second delete: %d", resp.StatusCode)
	}
}

func TestValidation(t *testing.T) {
	srv := newServer(t)
	for _, body := range []string{`{"author":"A"}`, `{"title":"T"}`, `{"title":"  ","author":"A"}`, `not json`, `{"title":"T","author":"A","year":-1}`} {
		resp, _ := do(t, "POST", srv.URL+"/books", body)
		if resp.StatusCode != 400 {
			t.Errorf("%q: got %d", body, resp.StatusCode)
		}
	}
	resp, _ := do(t, "PUT", srv.URL+"/books/99", `{"title":"T","author":"A"}`)
	if resp.StatusCode != 404 {
		t.Errorf("put missing: %d", resp.StatusCode)
	}
	resp, _ = do(t, "GET", srv.URL+"/books/abc", "")
	if resp.StatusCode != 400 {
		t.Errorf("bad id: %d", resp.StatusCode)
	}
}

func TestListAuthorFilter(t *testing.T) {
	srv := newServer(t)
	for _, b := range []string{`{"title":"A","author":"X"}`, `{"title":"B","author":"Y"}`, `{"title":"C","author":"X"}`} {
		do(t, "POST", srv.URL+"/books", b)
	}
	var all, xs []Book
	_, body := do(t, "GET", srv.URL+"/books", "")
	json.Unmarshal(body, &all)
	_, body = do(t, "GET", srv.URL+"/books?author=X", "")
	json.Unmarshal(body, &xs)
	if len(all) != 3 || len(xs) != 2 {
		t.Fatalf("all=%d xs=%d", len(all), len(xs))
	}
	_, body = do(t, "GET", srv.URL+"/books?author=Nobody", "")
	if strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("expected empty array, got %s", body)
	}
}
