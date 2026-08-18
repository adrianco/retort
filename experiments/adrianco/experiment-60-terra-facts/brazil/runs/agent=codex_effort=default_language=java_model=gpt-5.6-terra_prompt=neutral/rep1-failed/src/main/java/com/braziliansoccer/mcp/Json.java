package com.braziliansoccer.mcp;

import java.util.*;

/** Minimal JSON parser/writer for line-delimited JSON-RPC on standard input/output. */
final class Json {
    private Json() {}
    static Object parse(String text) { return new Parser(text).value(); }
    @SuppressWarnings("unchecked") static Map<String,Object> object(Object value) { return value instanceof Map<?,?> map ? (Map<String,Object>) map : Map.of(); }
    static String stringify(Object value) {
        if (value == null) return "null"; if (value instanceof String s) return '"' + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r") + '"';
        if (value instanceof Number || value instanceof Boolean) return value.toString();
        if (value instanceof Map<?,?> map) return map.entrySet().stream().map(e -> stringify(String.valueOf(e.getKey()))+":"+stringify(e.getValue())).collect(java.util.stream.Collectors.joining(",","{","}"));
        if (value instanceof Collection<?> values) return values.stream().map(Json::stringify).collect(java.util.stream.Collectors.joining(",","[","]"));
        return stringify(String.valueOf(value));
    }
    private static final class Parser { private final String s; private int i; Parser(String s){this.s=s;} Object value(){ws(); if(i>=s.length())return null; char c=s.charAt(i); if(c=='{')return obj();if(c=='[')return array();if(c=='\"')return string();if(s.startsWith("true",i)){i+=4;return true;}if(s.startsWith("false",i)){i+=5;return false;}if(s.startsWith("null",i)){i+=4;return null;} return number();} Map<String,Object> obj(){Map<String,Object> out=new LinkedHashMap<>(); i++;ws();while(i<s.length()&&s.charAt(i)!='}') {String k=string();ws();i++;Object v=value();out.put(k,v);ws();if(i<s.length()&&s.charAt(i)==','){i++;ws();}}i++;return out;} List<Object> array(){List<Object>out=new ArrayList<>();i++;ws();while(i<s.length()&&s.charAt(i)!=']'){out.add(value());ws();if(i<s.length()&&s.charAt(i)==','){i++;ws();}}i++;return out;}String string(){StringBuilder b=new StringBuilder();i++;while(i<s.length()&&s.charAt(i)!='\"'){char c=s.charAt(i++);if(c=='\\'&&i<s.length()){char e=s.charAt(i++);b.append(switch(e){case 'n'->'\n';case 'r'->'\r';case 't'->'\t';default->e;});}else b.append(c);}i++;return b.toString();}Number number(){int p=i;while(i<s.length()&&"-+.0123456789eE".indexOf(s.charAt(i))>=0)i++;String n=s.substring(p,i);return n.contains(".")?Double.valueOf(n):Long.valueOf(n);}void ws(){while(i<s.length()&&Character.isWhitespace(s.charAt(i)))i++;} }
}
