package dsl

import (
	"testing"
	"time"

	"brsoccer/acceptance/drivers"
)

// Datasets is the language for asking what data the system holds.
type Datasets struct {
	t      *testing.T
	driver drivers.SystemDriver
}

func (d *Datasets) List() {
	d.t.Helper()
	d.driver.ListDatasets()
}

func (d *Datasets) ConfirmLoaded(dataset string, facts ...string) {
	d.t.Helper()
	d.driver.ConfirmDatasetLoaded(dataset, NewParams(d.t, facts...).Expectations())
}

// Fan is the person asking the questions; it covers expectations about the
// experience of asking, rather than the content of any answer.
type Fan struct {
	t      *testing.T
	driver drivers.SystemDriver
}

func (f *Fan) ConfirmAnsweredWithin(args ...string) {
	f.t.Helper()
	p := NewParams(f.t, args...)
	f.driver.ConfirmAnsweredWithin(time.Duration(p.Int("seconds", 2)) * time.Second)
}
