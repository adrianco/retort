package dsl

import "brsoccer/acceptance/driver"

// Datasets is the part of the language about the data the server holds.
type Datasets struct {
	ctx    *context
	driver driver.SoccerDriver
}

func (d *Datasets) Describe() {
	d.ctx.t.Helper()
	d.driver.DescribeDatasets()
}

// ConfirmLoaded checks that each named dataset is loaded and has records.
func (d *Datasets) ConfirmLoaded(datasets ...string) {
	d.ctx.t.Helper()
	d.driver.ConfirmDatasetsLoaded(datasets)
}

// Assistant is the part of the language about the LLM assistant that
// uses the server to answer questions.
type Assistant struct {
	ctx    *context
	driver driver.SoccerDriver
}

func (a *Assistant) DiscoverCapabilities() {
	a.ctx.t.Helper()
	a.driver.DiscoverCapabilities()
}

// ConfirmCanAnswer checks that the assistant was offered each kind of question.
func (a *Assistant) ConfirmCanAnswer(kinds ...string) {
	a.ctx.t.Helper()
	a.driver.ConfirmCapabilities(kinds)
}

// ConfirmAnswerReads checks that the answer handed to the assistant
// contains the given line of text.
func (a *Assistant) ConfirmAnswerReads(line string) {
	a.ctx.t.Helper()
	a.driver.ConfirmAnswerContains(line)
}
