package com.brazilsoccer.mcp;

import java.io.*;import java.nio.charset.StandardCharsets;import java.nio.file.*;import java.util.*;

/** Small RFC-4180-style reader; datasets contain quoted commas and UTF-8 text. */
final class Csv {
  static List<Map<String,String>> read(Path file) throws IOException {
    try (Reader r = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
      List<List<String>> rows = parse(r); if (rows.isEmpty()) return List.of();
      List<String> header = rows.remove(0); if (!header.isEmpty()) header.set(0, header.get(0).replace("\uFEFF", ""));
      List<Map<String,String>> result = new ArrayList<>();
      for (List<String> row: rows) { if (row.stream().allMatch(String::isEmpty)) continue; Map<String,String> m=new LinkedHashMap<>(); for(int i=0;i<header.size();i++)m.put(header.get(i),i<row.size()?row.get(i):""); result.add(m); }
      return result;
    }
  }
  private static List<List<String>> parse(Reader input) throws IOException {
    List<List<String>> rows=new ArrayList<>(); List<String> row=new ArrayList<>(); StringBuilder cell=new StringBuilder(); boolean quote=false; int c;
    while((c=input.read())!=-1){ char ch=(char)c; if(quote){if(ch=='\"'){input.mark(1);int next=input.read();if(next=='\"')cell.append('\"');else{quote=false;if(next!=-1)input.reset();}}else cell.append(ch);}else if(ch=='\"')quote=true;else if(ch==','){row.add(cell.toString().trim());cell.setLength(0);}else if(ch=='\n'){row.add(cell.toString().trim());cell.setLength(0);rows.add(row);row=new ArrayList<>();}else if(ch!='\r')cell.append(ch); }
    if(quote) throw new IOException("Unclosed quote in CSV"); if(!row.isEmpty()||cell.length()>0){row.add(cell.toString().trim());rows.add(row);} return rows;
  }
}
