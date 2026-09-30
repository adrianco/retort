package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	ts := httptest.NewServer(newHandler(store))
	t.Cleanup(func() { ts.Close(); store.Close() })
	return ts
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
	ts := newTestServer(t)
	resp, _ := do(t, "GET", ts.URL+"/health", "")
	if resp.StatusCode != 200 {
		t.Fatalf("status %d", resp.StatusCode)
	}
}

func TestCRUD(t *testing.T) {
	ts := newTestServer(t)
	resp, body := do(t, "POST", ts.URL+"/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}`)
	if resp.StatusCode != 201 {
		t.Fatalf("create: %d %s", resp.StatusCode, body)
	}
	var b Book
	json.Unmarshal(body, &b)
	if b.ID == 0 || b.Title != "Dune" {
		t.Fatalf("bad book %+v", b)
	}
	u := ts.URL + "/books/1"

	resp, body = do(t, "GET", u, "")
	if resp.StatusCode != 200 || !strings.Contains(string(body), "Frank Herbert") {
		t.Fatalf("get: %d %s", resp.StatusCode, body)
	}

	resp, body = do(t, "PUT", u, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"456"}`)
	if resp.StatusCode != 200 || !strings.Contains(string(body), "Dune Messiah") {
		t.Fatalf("update: %d %s", resp.StatusCode, body)
	}

	resp, _ = do(t, "DELETE", u, "")
	if resp.StatusCode != 204 {
		t.Fatalf("delete: %d", resp.StatusCode)
	}
	resp, _ = do(t, "GET", u, "")
	if resp.StatusCode != 404 {
		t.Fatalf("get after delete: %d", resp.StatusCode)
	}
	resp, _ = do(t, "DELETE", u, "")
	if resp.StatusCode != 404 {
		t.Fatalf("delete missing: %d", resp.StatusCode)
	}
}

func TestValidation(t *testing.T) {
	ts := newTestServer(t)
	for name, body := range map[string]string{
		"no title":    `{"author":"A"}`,
		"no author":   `{"title":"T"}`,
		"blank title": `{"title":"  ","author":"A"}`,
		"bad json":    `{`,
		"neg year":    `{"title":"T","author":"A","year":-1}`,
	} {
		if resp, _ := do(t, "POST", ts.URL+"/books", body); resp.StatusCode != 400 {
			t.Errorf("%s: status %d", name, resp.StatusCode)
		}
	}
	if resp, _ := do(t, "PUT", ts.URL+"/books/99", `{"title":"T","author":"A"}`); resp.StatusCode != 404 {
		t.Errorf("update missing: %d", resp.StatusCode)
	}
	if resp, _ := do(t, "GET", ts.URL+"/books/abc", ""); resp.StatusCode != 400 {
		t.Errorf("bad id: %d", resp.StatusCode)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	ts := newTestServer(t)
	resp, body := do(t, "GET", ts.URL+"/books", "")
	if resp.StatusCode != 200 || strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("empty list: %d %s", resp.StatusCode, body)
	}
	do(t, "POST", ts.URL+"/books", `{"title":"A1","author":"Alice"}`)
	do(t, "POST", ts.URL+"/books", `{"title":"A2","author":"Alice"}`)
	do(t, "POST", ts.URL+"/books", `{"title":"B1","author":"Bob"}`)

	var all, alice []Book
	_, body = do(t, "GET", ts.URL+"/books", "")
	json.Unmarshal(body, &all)
	_, body = do(t, "GET", ts.URL+"/books?author=Alice", "")
	json.Unmarshal(body, &alice)
	if len(all) != 3 || len(alice) != 2 {
		t.Fatalf("all=%d alice=%d", len(all), len(alice))
	}
}
