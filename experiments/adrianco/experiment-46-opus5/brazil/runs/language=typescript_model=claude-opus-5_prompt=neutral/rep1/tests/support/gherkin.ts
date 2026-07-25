/**
 * A minimal Gherkin parser.
 *
 * The specification asks for BDD scenarios, so the `.feature` files in
 * `tests/features` are the real test definitions rather than prose copied into
 * test names. This parser covers the subset those files use: Feature,
 * Background, Scenario, Scenario Outline with an Examples table, `#` comments
 * and `And`/`But` continuations. Anything richer (tags, doc strings, data
 * tables on steps) is out of scope and reported as an error rather than
 * silently ignored.
 */

export type StepKeyword = 'Given' | 'When' | 'Then';

export interface Step {
  keyword: StepKeyword;
  text: string;
  line: number;
}

export interface Scenario {
  name: string;
  steps: Step[];
  line: number;
}

export interface Feature {
  name: string;
  description: string;
  background: Step[];
  scenarios: Scenario[];
}

const CONTINUATIONS = new Set(['And', 'But', '*']);

export function parseFeature(source: string, file = '<feature>'): Feature {
  const feature: Feature = { name: '', description: '', background: [], scenarios: [] };
  const descriptionLines: string[] = [];

  // Where subsequent steps land: the background, the current scenario, or
  // nothing yet (steps before any section are an error).
  let target: Step[] | undefined;
  let outline: { name: string; steps: Step[] } | undefined;
  let previousKeyword: StepKeyword | undefined;

  const lines = source.split('\n');
  for (let index = 0; index < lines.length; index++) {
    const raw = lines[index]!;
    const line = raw.trim();
    const lineNumber = index + 1;

    if (line === '' || line.startsWith('#')) continue;

    // Tags and Rules parse as free text in the description region, so without
    // this they would be silently dropped there and rejected elsewhere -- and
    // someone marking a scenario `@skip` would see it run anyway.
    if (line.startsWith('@') || /^Rule:/.test(line)) {
      throw new Error(`${file}:${lineNumber}: "${line}" is not supported by this parser`);
    }

    // Longest keywords first: "Examples" must not be consumed as "Example".
    const section = /^(Feature|Background|Scenario Outline|Scenario Template|Scenarios|Scenario|Examples|Example):\s*(.*)$/.exec(line);
    if (section) {
      const keyword = section[1]!;
      const title = section[2]!.trim();

      if (keyword === 'Feature') {
        feature.name = title;
        target = undefined;
        continue;
      }
      if (keyword === 'Background') {
        feature.background = [];
        target = feature.background;
        previousKeyword = undefined;
        continue;
      }
      if (keyword === 'Examples' || keyword === 'Scenarios') {
        if (!outline) throw new Error(`${file}:${lineNumber}: Examples without a Scenario Outline`);
        const { rows, next } = readTable(lines, index + 1, file);
        for (const row of rows) {
          feature.scenarios.push({
            name: interpolate(outline.name, row),
            line: lineNumber,
            steps: outline.steps.map((step) => ({ ...step, text: interpolate(step.text, row) })),
          });
        }
        index = next - 1;
        outline = undefined;
        target = undefined;
        continue;
      }

      // Scenario / Scenario Outline / Example
      if (keyword === 'Scenario Outline' || keyword === 'Scenario Template') {
        outline = { name: title, steps: [] };
        target = outline.steps;
      } else {
        const scenario: Scenario = { name: title, steps: [], line: lineNumber };
        feature.scenarios.push(scenario);
        target = scenario.steps;
        outline = undefined;
      }
      previousKeyword = undefined;
      continue;
    }

    const step = /^(Given|When|Then|And|But|\*)\s+(.*)$/.exec(line);
    if (step) {
      if (!target) throw new Error(`${file}:${lineNumber}: step outside a Scenario or Background`);
      const word = step[1]!;
      let keyword: StepKeyword;
      if (CONTINUATIONS.has(word)) {
        if (!previousKeyword) throw new Error(`${file}:${lineNumber}: "${word}" with no preceding step`);
        keyword = previousKeyword;
      } else {
        keyword = word as StepKeyword;
      }
      previousKeyword = keyword;
      target.push({ keyword, text: step[2]!.trim(), line: lineNumber });
      continue;
    }

    if (feature.name && feature.scenarios.length === 0 && !target) {
      descriptionLines.push(line);
      continue;
    }

    throw new Error(`${file}:${lineNumber}: could not parse "${line}"`);
  }

  if (outline) throw new Error(`${file}: Scenario Outline "${outline.name}" has no Examples table`);
  feature.description = descriptionLines.join('\n');
  return feature;
}

function readTable(
  lines: string[],
  start: number,
  file: string,
): { rows: Array<Record<string, string>>; next: number } {
  let index = start;
  const cells: string[][] = [];

  while (index < lines.length) {
    const line = lines[index]!.trim();
    if (line === '' || line.startsWith('#')) {
      index++;
      continue;
    }
    if (!line.startsWith('|')) break;
    cells.push(splitRow(line));
    index++;
  }

  const header = cells.shift();
  if (!header) throw new Error(`${file}:${start}: Examples table has no header row`);

  const rows = cells.map((row) => {
    const record: Record<string, string> = {};
    header.forEach((name, position) => {
      record[name] = row[position] ?? '';
    });
    return record;
  });

  return { rows, next: index };
}

function splitRow(line: string): string[] {
  return line
    .slice(1, line.endsWith('|') ? -1 : undefined)
    .split('|')
    .map((cell) => cell.trim());
}

/** Replace `<name>` placeholders from an Examples row. */
function interpolate(text: string, row: Record<string, string>): string {
  return text.replace(/<([^<>]+)>/g, (whole, name: string) =>
    Object.prototype.hasOwnProperty.call(row, name) ? row[name]! : whole,
  );
}
