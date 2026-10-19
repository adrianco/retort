package store

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
)

func openTestStore(t *testing.T) *Store {
	t.Helper()
	st, err := Open(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { st.Close() })
	return st
}

func TestStoreCreateAndGet(t *testing.T) {
	st := openTestStore(t)
	ctx := context.Background()

	created, err := st.Create(ctx, Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441172719"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("Create: expected non-zero ID")
	}

	got, err := st.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	want := created
	if got != want {
		t.Fatalf("Get = %+v, want %+v", got, want)
	}
}

func TestStoreGetMissing(t *testing.T) {
	st := openTestStore(t)
	_, err := st.Get(context.Background(), 999)
	if !errors.Is(err, ErrNotFound) {
		t.Fatalf("Get(missing) error = %v, want ErrNotFound", err)
	}
}

func TestStoreCreateAssignsSequentialIDs(t *testing.T) {
	st := openTestStore(t)
	ctx := context.Background()

	first, err := st.Create(ctx, Book{Title: "A", Author: "X"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	second, err := st.Create(ctx, Book{Title: "B", Author: "Y"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if second.ID != first.ID+1 {
		t.Fatalf("IDs not sequential: %d then %d", first.ID, second.ID)
	}
}

func TestStoreListAndFilter(t *testing.T) {
	st := openTestStore(t)
	ctx := context.Background()

	books := []Book{
		{Title: "Dune", Author: "Frank Herbert"},
		{Title: "Hyperion", Author: "Dan Simmons"},
		{Title: "Dune Messiah", Author: "Frank herbert"}, // different case
	}
	for _, b := range books {
		if _, err := st.Create(ctx, b); err != nil {
			t.Fatalf("Create: %v", err)
		}
	}

	all, err := st.List(ctx, "")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(all) != len(books) {
		t.Fatalf("List() returned %d books, want %d", len(all), len(books))
	}

	filtered, err := st.List(ctx, "frank herbert")
	if err != nil {
		t.Fatalf("List(author): %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("List(author=frank herbert) returned %d books, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Frank Herbert" && b.Author != "Frank herbert" {
			t.Fatalf("unexpected author in filtered list: %q", b.Author)
		}
	}

	none, err := st.List(ctx, "Nobody")
	if err != nil {
		t.Fatalf("List(nobody): %v", err)
	}
	if len(none) != 0 {
		t.Fatalf("List(nobody) returned %d books, want 0", len(none))
	}
}

func TestStoreUpdate(t *testing.T) {
	st := openTestStore(t)
	ctx := context.Background()

	created, err := st.Create(ctx, Book{Title: "Old Title", Author: "A. Author", Year: 1999})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}

	updated, err := st.Update(ctx, Book{ID: created.ID, Title: "New Title", Author: "A. Author", Year: 2000, ISBN: "123"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Title != "New Title" || updated.Year != 2000 || updated.ISBN != "123" {
		t.Fatalf("Update returned %+v, want updated fields", updated)
	}

	got, err := st.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get after update: %v", err)
	}
	if got.Title != "New Title" || got.Author != "A. Author" || got.Year != 2000 || got.ISBN != "123" {
		t.Fatalf("stored book after update = %+v, want updated values", got)
	}

	if _, err := st.Update(ctx, Book{ID: 424242, Title: "X", Author: "Y"}); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Update(missing) error = %v, want ErrNotFound", err)
	}
}

func TestStoreDelete(t *testing.T) {
	st := openTestStore(t)
	ctx := context.Background()

	created, err := st.Create(ctx, Book{Title: "Temp", Author: "T. Author"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}

	if err := st.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := st.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("Get after delete error = %v, want ErrNotFound", err)
	}
	if err := st.Delete(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Fatalf("second Delete error = %v, want ErrNotFound", err)
	}
}
