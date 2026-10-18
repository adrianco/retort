package org.brazilsoccer.mcp;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Small RFC-4180-style reader; datasets contain quoted commas and UTF-8 text. */
final class Csv {
  static List<Map<String,String>> read(Path file) throws IOException {
    try (Reader r = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
      List<List<String>> rows = new ArrayList<>(); List<String> row = new ArrayList<>(); StringBuilder cell = new StringBuilder();
      boolean quoted=false; int c;
      while ((c=r.read()) != -1) { char ch=(char)c;
        if (ch=='\"') { if (quoted && r.markSupported()) { quoted=false; } else quoted=!quoted; }
        else if (ch==',' && !quoted) { row.add(cell.toString()); cell.setLength(0); }
        else if ((ch=='\n' || ch=='\r') && !quoted) { if (ch=='\r') continue; row.add(cell.toString()); cell.setLength(0); rows.add(row); row=new ArrayList<>(); }
        else cell.append(ch);
      }
      if (cell.length()>0 || !row.isEmpty()) { row.add(cell.toString()); rows.add(row); }
      if (rows.isEmpty()) return List.of();
      List<String> header=rows.remove(0); if (!header.isEmpty()) header.set(0, header.get(0).replace("\uFEFF", ""));
      List<Map<String,String>> out=new ArrayList<>();
      for (List<String> values: rows) { if (values.size()==1 && values.get(0).isBlank()) continue; Map<String,String> m=new LinkedHashMap<>(); for(int i=0;i<header.size();i++) m.put(header.get(i), i<values.size()?values.get(i):""); out.add(m); }
      return out;
    }
  }
}
