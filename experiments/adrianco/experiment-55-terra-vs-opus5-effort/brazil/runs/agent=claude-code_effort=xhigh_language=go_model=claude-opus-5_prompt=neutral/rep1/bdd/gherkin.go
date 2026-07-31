// Package bdd runs the Gherkin feature files in ../features against the MCP
// server.
//
// The specification asks for behaviour-driven scenarios, so the acceptance
// criteria live in plain Given/When/Then English that a non-programmer can read
// and review, and this package is the machinery that executes them. It contains
// a small Gherkin subset parser (Feature, Background, Scenario, Given/When/Then/
// And/But) and a step registry that binds each sentence to Go code.
//
// A scenario whose sentence has no matching step definition fails the test run,
// which keeps the feature files and the step implementations honest with each
// other.
package bdd

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

// Step is one Given/When/Then line.
type Step struct {
	Keyword string // Given, When or Then, with And/But resolved to the previous keyword
	Text    string
	Line    int
}

// Scenario is a named list of steps.
type Scenario struct {
	Name  string
	Steps []Step
	Line  int
}

// Feature is one .feature file.
type Feature struct {
	Name        string
	Description []string
	Background  []Step
	Scenarios   []Scenario
	Path        string
}

var (
	featureRe    = regexp.MustCompile(`^Feature:\s*(.*)$`)
	backgroundRe = regexp.MustCompile(`^Background:\s*$`)
	scenarioRe   = regexp.MustCompile(`^Scenario:\s*(.*)$`)
	stepRe       = regexp.MustCompile(`^(Given|When|Then|And|But)\s+(.*)$`)
)

// ParseFeature reads one .feature file.
func ParseFeature(path string) (*Feature, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	f := &Feature{Path: path}
	// section is where subsequent steps go: "background", "scenario" or "".
	section := ""
	lastKeyword := "Given"
	for i, raw := range strings.Split(string(data), "\n") {
		line := strings.TrimSpace(raw)
		lineNo := i + 1
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		switch {
		case featureRe.MatchString(line):
			f.Name = featureRe.FindStringSubmatch(line)[1]
			section = ""
		case backgroundRe.MatchString(line):
			section, lastKeyword = "background", "Given"
		case scenarioRe.MatchString(line):
			f.Scenarios = append(f.Scenarios, Scenario{Name: scenarioRe.FindStringSubmatch(line)[1], Line: lineNo})
			section, lastKeyword = "scenario", "Given"
		case stepRe.MatchString(line):
			m := stepRe.FindStringSubmatch(line)
			keyword, text := m[1], strings.TrimSpace(m[2])
			if keyword == "And" || keyword == "But" {
				keyword = lastKeyword
			}
			lastKeyword = keyword
			step := Step{Keyword: keyword, Text: text, Line: lineNo}
			switch section {
			case "background":
				f.Background = append(f.Background, step)
			case "scenario":
				last := len(f.Scenarios) - 1
				if last < 0 {
					return nil, fmt.Errorf("%s:%d: step outside a scenario", path, lineNo)
				}
				f.Scenarios[last].Steps = append(f.Scenarios[last].Steps, step)
			default:
				return nil, fmt.Errorf("%s:%d: step before any Scenario or Background", path, lineNo)
			}
		default:
			if section == "" {
				f.Description = append(f.Description, line)
			}
		}
	}
	if f.Name == "" {
		return nil, fmt.Errorf("%s: no Feature: line", path)
	}
	if len(f.Scenarios) == 0 {
		return nil, fmt.Errorf("%s: no scenarios", path)
	}
	return f, nil
}

// ParseDir reads every .feature file in a directory, sorted by name.
func ParseDir(dir string) ([]*Feature, error) {
	paths, err := filepath.Glob(filepath.Join(dir, "*.feature"))
	if err != nil {
		return nil, err
	}
	if len(paths) == 0 {
		return nil, fmt.Errorf("no .feature files in %s", dir)
	}
	sort.Strings(paths)
	features := make([]*Feature, 0, len(paths))
	for _, p := range paths {
		f, err := ParseFeature(p)
		if err != nil {
			return nil, err
		}
		features = append(features, f)
	}
	return features, nil
}

// AllSteps returns a scenario's steps with the feature background prepended.
func (f *Feature) AllSteps(s Scenario) []Step {
	steps := make([]Step, 0, len(f.Background)+len(s.Steps))
	steps = append(steps, f.Background...)
	steps = append(steps, s.Steps...)
	return steps
}

// StepFunc implements one step. args holds the captured placeholder values in
// the order they appear in the pattern.
type StepFunc func(w *World, args []string) error

// Registry maps step sentences to implementations.
type Registry struct {
	defs []definition
}

type definition struct {
	pattern string
	re      *regexp.Regexp
	fn      StepFunc
	used    bool
}

// placeholderRe finds the {string}, {int} and {word} placeholders in a pattern.
var placeholderRe = regexp.MustCompile(`\{(string|int|word)\}`)

// Step registers an implementation. The pattern is plain English with
// placeholders: {string} matches a quoted value, {int} a number and {word} a
// bare token.
func (r *Registry) Step(pattern string, fn StepFunc) {
	var b strings.Builder
	b.WriteString("^")
	last := 0
	for _, loc := range placeholderRe.FindAllStringSubmatchIndex(pattern, -1) {
		b.WriteString(regexp.QuoteMeta(pattern[last:loc[0]]))
		switch pattern[loc[2]:loc[3]] {
		case "string":
			b.WriteString(`"([^"]*)"`)
		case "int":
			b.WriteString(`(-?\d+)`)
		case "word":
			b.WriteString(`(\S+)`)
		}
		last = loc[1]
	}
	b.WriteString(regexp.QuoteMeta(pattern[last:]))
	b.WriteString("$")
	r.defs = append(r.defs, definition{pattern: pattern, re: regexp.MustCompile(b.String())})
	r.defs[len(r.defs)-1].fn = fn
}

// ErrNoStepDefinition reports a sentence the registry cannot execute.
type ErrNoStepDefinition struct{ Step Step }

func (e *ErrNoStepDefinition) Error() string {
	return fmt.Sprintf("no step definition matches %q (line %d)", e.Step.Text, e.Step.Line)
}

// Execute runs one step against the world.
func (r *Registry) Execute(w *World, step Step) error {
	for i := range r.defs {
		if m := r.defs[i].re.FindStringSubmatch(step.Text); m != nil {
			r.defs[i].used = true
			return r.defs[i].fn(w, m[1:])
		}
	}
	return &ErrNoStepDefinition{Step: step}
}

// UnusedPatterns lists step definitions that no scenario exercised, so dead step
// code is visible rather than silently accumulating.
func (r *Registry) UnusedPatterns() []string {
	var out []string
	for _, d := range r.defs {
		if !d.used {
			out = append(out, d.pattern)
		}
	}
	sort.Strings(out)
	return out
}
