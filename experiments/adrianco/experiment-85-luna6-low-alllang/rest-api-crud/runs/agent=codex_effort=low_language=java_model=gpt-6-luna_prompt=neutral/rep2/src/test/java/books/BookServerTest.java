package books;

import com.fasterxml.jackson.databind.*;
import org.junit.jupiter.api.*;
import java.net.*;
import java.net.http.*;
import java.nio.file.*;
import static org.junit.jupiter.api.Assertions.*;

class BookServerTest {
    private BookServer server; private HttpClient client; private ObjectMapper mapper=new ObjectMapper();
    @BeforeEach void start() throws Exception { Path db=Files.createTempFile("books-test",".db"); server=new BookServer(0,new BookStore(db.toString()));server.start();client=HttpClient.newHttpClient(); }
    @AfterEach void stop(){server.close();}
    private HttpResponse<String> request(String method,String path,String body)throws Exception {var b=HttpRequest.newBuilder(URI.create("http://localhost:"+server.port()+path));if(body!=null)b.header("Content-Type","application/json");return client.send(b.method(method,body==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(body)).build(),HttpResponse.BodyHandlers.ofString());}
    @Test void healthEndpointReturnsOk()throws Exception{var r=request("GET","/health",null);assertEquals(200,r.statusCode());assertEquals("ok",mapper.readTree(r.body()).get("status").asText());}
    @Test void createReadAndFilterBooks()throws Exception{var created=request("POST","/books","{\"title\":\"Dune\",\"author\":\"Frank Herbert\",\"year\":1965,\"isbn\":\"123\"}");assertEquals(201,created.statusCode());long id=mapper.readTree(created.body()).get("id").asLong();assertEquals(200,request("GET","/books/"+id,null).statusCode());assertEquals(1,mapper.readTree(request("GET","/books?author=Frank%20Herbert",null).body()).size());assertEquals(0,mapper.readTree(request("GET","/books?author=Other",null).body()).size());}
    @Test void validationUpdateAndDelete()throws Exception{assertEquals(400,request("POST","/books","{\"author\":\"A\"}").statusCode());var c=request("POST","/books","{\"title\":\"Old\",\"author\":\"A\"}");long id=mapper.readTree(c.body()).get("id").asLong();assertEquals(200,request("PUT","/books/"+id,"{\"title\":\"New\",\"author\":\"A\"}").statusCode());assertEquals("New",mapper.readTree(request("GET","/books/"+id,null).body()).get("title").asText());assertEquals(204,request("DELETE","/books/"+id,null).statusCode());assertEquals(404,request("GET","/books/"+id,null).statusCode());}
}
