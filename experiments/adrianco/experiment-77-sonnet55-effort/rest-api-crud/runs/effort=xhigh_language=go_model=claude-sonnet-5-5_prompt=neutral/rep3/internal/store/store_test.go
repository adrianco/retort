package store

import (
	"context"
	"errors"
	"path/filepath"
	"sync"
	"testing"

	"bookapi/internal/book"
)

func openTemp(t *testing.T) *Store {
	t.Helper()
	s, err := Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func TestCreateAndGet(t *testing.T) {
	s := openTemp(t)
	ctx := context.Background()

	created, err := s.Create(ctx, book.Input{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441172719"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("Create returned zero ID")
	}
	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got != created {
		t.Errorf("Get = %+v, want %+v", got, created)
	}
}

func TestGetMissing(t *testing.T) {
	s := openTemp(t)
	if _, err := s.Get(context.Background(), 42); !errors.Is(err, book.ErrNotFound) {
		t.Errorf("Get missing: err = %v, want ErrNotFound", err)
	}
}

func TestListFilterAndOrder(t *testing.T) {
	s := openTemp(t)
	ctx := context.Background()

	empty, err := s.List(ctx, "")
	if err != nil {
		t.Fatalf("List empty: %v", err)
	}
	if empty == nil || len(empty) != 0 {
		t.Errorf("empty List = %#v, want non-nil empty slice", empty)
	}

	for _, in := range []book.Input{
		{Title: "1984", Author: "George Orwell"},
		{Title: "Dune", Author: "Frank Herbert"},
		{Title: "Animal Farm", Author: "George Orwell"},
	} {
		if _, err := s.Create(ctx, in); err != nil {
			t.Fatalf("Create %q: %v", in.Title, err)
		}
	}

	all, err := s.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(all) != 3 || all[0].Title != "1984" || all[2].Title != "Animal Farm" {
		t.Errorf("List all = %+v, want 3 books in insertion order", all)
	}

	for _, filter := range []string{"George Orwell", "george orwell"} {
		got, err := s.List(ctx, filter)
		if err != nil {
			t.Fatalf("List(%q): %v", filter, err)
		}
		if len(got) != 2 || got[0].Title != "1984" || got[1].Title != "Animal Farm" {
			t.Errorf("List(%q) = %+v, want the two Orwell books", filter, got)
		}
	}

	// Filtering is an exact match, not a substring search.
	for _, filter := range []string{"Orwell", "Nobody"} {
		got, err := s.List(ctx, filter)
		if err != nil {
			t.Fatalf("List(%q): %v", filter, err)
		}
		if len(got) != 0 {
			t.Errorf("List(%q) = %+v, want none", filter, got)
		}
	}
}

func TestUpdate(t *testing.T) {
	s := openTemp(t)
	ctx := context.Background()
	created, _ := s.Create(ctx, book.Input{Title: "Old", Author: "Someone", Year: 1900, ISBN: "1"})

	updated, err := s.Update(ctx, created.ID, book.Input{Title: "New", Author: "Other", Year: 2001, ISBN: "2"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	want := book.Book{ID: created.ID, Title: "New", Author: "Other", Year: 2001, ISBN: "2"}
	if updated != want {
		t.Errorf("Update = %+v, want %+v", updated, want)
	}
	got, _ := s.Get(ctx, created.ID)
	if got != want {
		t.Errorf("Get after Update = %+v, want %+v", got, want)
	}

	if _, err := s.Update(ctx, created.ID+100, book.Input{Title: "x", Author: "y"}); !errors.Is(err, book.ErrNotFound) {
		t.Errorf("Update missing: err = %v, want ErrNotFound", err)
	}
}

func TestUpdateWithIdenticalValuesIsNotMissing(t *testing.T) {
	s := openTemp(t)
	ctx := context.Background()
	in := book.Input{Title: "Same", Author: "Same"}
	created, _ := s.Create(ctx, in)
	if _, err := s.Update(ctx, created.ID, in); err != nil {
		t.Errorf("no-op Update: %v", err)
	}
}

func TestDelete(t *testing.T) {
	s := openTemp(t)
	ctx := context.Background()
	created, _ := s.Create(ctx, book.Input{Title: "Gone", Author: "Soon"})

	if err := s.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := s.Get(ctx, created.ID); !errors.Is(err, book.ErrNotFound) {
		t.Errorf("Get after Delete: err = %v, want ErrNotFound", err)
	}
	if err := s.Delete(ctx, created.ID); !errors.Is(err, book.ErrNotFound) {
		t.Errorf("second Delete: err = %v, want ErrNotFound", err)
	}
}

func TestIDsAreNotReused(t *testing.T) {
	s := openTemp(t)
	ctx := context.Background()
	first, _ := s.Create(ctx, book.Input{Title: "A", Author: "A"})
	if err := s.Delete(ctx, first.ID); err != nil {
		t.Fatal(err)
	}
	second, _ := s.Create(ctx, book.Input{Title: "B", Author: "B"})
	if second.ID <= first.ID {
		t.Errorf("ID %d reused or went backwards after deleting %d", second.ID, first.ID)
	}
}

func TestPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	ctx := context.Background()

	s, err := Open(path)
	if err != nil {
		t.Fatal(err)
	}
	created, err := s.Create(ctx, book.Input{Title: "Durable", Author: "Disk"})
	if err != nil {
		t.Fatal(err)
	}
	if err := s.Close(); err != nil {
		t.Fatal(err)
	}

	s, err = Open(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer s.Close()
	got, err := s.Get(ctx, created.ID)
	if err != nil || got != created {
		t.Errorf("after reopen Get = %+v, %v; want %+v", got, err, created)
	}
}

func TestInMemory(t *testing.T) {
	s, err := Open(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	ctx := context.Background()
	created, err := s.Create(ctx, book.Input{Title: "Ephemeral", Author: "RAM"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := s.Get(ctx, created.ID); err != nil {
		t.Errorf("Get on in-memory store: %v", err)
	}
}

func TestPathWithSpecialCharacters(t *testing.T) {
	path := filepath.Join(t.TempDir(), "my books #1?.db")
	s, err := Open(path)
	if err != nil {
		t.Fatalf("Open(%q): %v", path, err)
	}
	defer s.Close()
	if _, err := s.Create(context.Background(), book.Input{Title: "T", Author: "A"}); err != nil {
		t.Errorf("Create: %v", err)
	}
}

func TestOpenRejectsEmptyPath(t *testing.T) {
	if _, err := Open(""); err == nil {
		t.Error("Open(\"\") succeeded, want error")
	}
}

func TestConcurrentWrites(t *testing.T) {
	s := openTemp(t)
	ctx := context.Background()

	const n = 25
	var wg sync.WaitGroup
	errs := make(chan error, n)
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, err := s.Create(ctx, book.Input{Title: "T", Author: "A"})
			errs <- err
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		if err != nil {
			t.Errorf("concurrent Create: %v", err)
		}
	}
	all, err := s.List(ctx, "")
	if err != nil || len(all) != n {
		t.Errorf("List = %d books, %v; want %d", len(all), err, n)
	}
}
