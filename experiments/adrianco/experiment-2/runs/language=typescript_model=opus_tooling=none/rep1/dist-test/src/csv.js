import { readFileSync } from "node:fs";
export function parseCSV(content) {
    // Strip BOM
    if (content.charCodeAt(0) === 0xfeff)
        content = content.slice(1);
    const rows = [];
    let cur = [];
    let field = "";
    let inQuotes = false;
    for (let i = 0; i < content.length; i++) {
        const ch = content[i];
        if (inQuotes) {
            if (ch === '"') {
                if (content[i + 1] === '"') {
                    field += '"';
                    i++;
                }
                else {
                    inQuotes = false;
                }
            }
            else {
                field += ch;
            }
        }
        else {
            if (ch === '"') {
                inQuotes = true;
            }
            else if (ch === ",") {
                cur.push(field);
                field = "";
            }
            else if (ch === "\r") {
                // ignore
            }
            else if (ch === "\n") {
                cur.push(field);
                field = "";
                rows.push(cur);
                cur = [];
            }
            else {
                field += ch;
            }
        }
    }
    if (field.length > 0 || cur.length > 0) {
        cur.push(field);
        rows.push(cur);
    }
    if (rows.length === 0)
        return [];
    const headers = rows[0].map((h) => h.trim());
    const out = [];
    for (let i = 1; i < rows.length; i++) {
        const r = rows[i];
        if (r.length === 1 && r[0] === "")
            continue;
        const obj = {};
        for (let j = 0; j < headers.length; j++) {
            obj[headers[j]] = r[j] ?? "";
        }
        out.push(obj);
    }
    return out;
}
export function readCSV(path) {
    return parseCSV(readFileSync(path, "utf8"));
}
