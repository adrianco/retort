package books;

import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.sun.net.httpserver.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public final class BookServer implements AutoCloseable {
    private final HttpServer server;
    private final BookStore store;
    private static final ObjectMapper JSON = new ObjectMapper();

    public BookServer(int port, BookStore store) throws IOException {
        this.store=store; server=HttpServer.create(new InetSocketAddress(port),0); server.createContext("/",this::handle);
    }
    public void start(){server.start();}
    public int port(){return server.getAddress().getPort();}
    @Override public void close(){server.stop(0);}
    private void handle(HttpExchange exchange)throws IOException {
        try {
            String path=exchange.getRequestURI().getPath(), method=exchange.getRequestMethod();
            if(path.equals("/health") && method.equals("GET")){send(exchange,200,Map.of("status","ok"));return;}
            if(path.equals("/books") && method.equals("GET")){String author=query(exchange.getRequestURI()).get("author");send(exchange,200,store.list(author));return;}
            if(path.equals("/books") && method.equals("POST")){JsonNode body=readBody(exchange); BookInput input=parse(body); if(input.error!=null){sendError(exchange,400,input.error);return;} send(exchange,201,store.create(input.title,input.author,input.year,input.isbn));return;}
            if(path.startsWith("/books/")) {
                long id; try{id=Long.parseLong(path.substring("/books/".length()));if(id<1)throw new NumberFormatException();}catch(NumberFormatException e){sendError(exchange,400,"Invalid book ID");return;}
                if(method.equals("GET")){Optional<Book> b=store.find(id);if(b.isEmpty())sendError(exchange,404,"Book not found");else send(exchange,200,b.get());return;}
                if(method.equals("PUT")){BookInput in=parse(readBody(exchange));if(in.error!=null){sendError(exchange,400,in.error);return;}Optional<Book>b=store.update(id,in.title,in.author,in.year,in.isbn);if(b.isEmpty())sendError(exchange,404,"Book not found");else send(exchange,200,b.get());return;}
                if(method.equals("DELETE")){if(store.delete(id))send(exchange,204,null);else sendError(exchange,404,"Book not found");return;}
            }
            sendError(exchange,404,"Not found");
        } catch(JsonProcessingException | IllegalArgumentException e){sendError(exchange,400,"Invalid JSON request");}
        catch(Exception e){sendError(exchange,500,"Internal server error");}
    }
    private static JsonNode readBody(HttpExchange e)throws IOException{return JSON.readTree(e.getRequestBody());}
    private static BookInput parse(JsonNode n){
        if(n==null||!n.isObject())return BookInput.error("Request body must be a JSON object");
        JsonNode t=n.get("title"),a=n.get("author");if(t==null||!t.isTextual()||t.asText().isBlank())return BookInput.error("Title is required");if(a==null||!a.isTextual()||a.asText().isBlank())return BookInput.error("Author is required");
        Integer year=null;JsonNode y=n.get("year");if(y!=null&&!y.isNull()){if(!y.canConvertToInt())return BookInput.error("Year must be an integer");year=y.intValue();}
        JsonNode i=n.get("isbn");if(i!=null&&!i.isNull()&&!i.isTextual())return BookInput.error("ISBN must be a string");
        return new BookInput(t.asText().trim(),a.asText().trim(),year,i==null||i.isNull()?null:i.asText(),null);
    }
    private static Map<String,String> query(URI uri){Map<String,String> result=new HashMap<>();String q=uri.getRawQuery();if(q!=null)for(String part:q.split("&")){String[]kv=part.split("=",2);try{result.put(URLDecoder.decode(kv[0],StandardCharsets.UTF_8),URLDecoder.decode(kv.length>1?kv[1]:"",StandardCharsets.UTF_8));}catch(IllegalArgumentException ignored){}}return result;}
    private static void sendError(HttpExchange e,int status,String message)throws IOException{ObjectNode n=JSON.createObjectNode();n.put("error",message);send(e,status,n);}
    private static void send(HttpExchange e,int status,Object body)throws IOException{if(status==204){e.sendResponseHeaders(status,-1);e.close();return;}byte[] bytes=JSON.writeValueAsBytes(body);e.getResponseHeaders().set("Content-Type","application/json; charset=utf-8");e.sendResponseHeaders(status,bytes.length);try(OutputStream out=e.getResponseBody()){out.write(bytes);}}
    private record BookInput(String title,String author,Integer year,String isbn,String error){static BookInput error(String e){return new BookInput(null,null,null,null,e);}}
    public static void main(String[]args)throws Exception{int port=Integer.parseInt(System.getenv().getOrDefault("PORT","8080"));String db=System.getenv().getOrDefault("BOOKS_DB","books.db");BookServer app=new BookServer(port,new BookStore(db));app.start();System.out.println("Book API listening on http://localhost:"+app.port());}
}
