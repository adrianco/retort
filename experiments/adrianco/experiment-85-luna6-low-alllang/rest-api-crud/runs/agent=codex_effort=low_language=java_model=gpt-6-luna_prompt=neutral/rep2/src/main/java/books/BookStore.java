package books;

import java.sql.*;
import java.util.*;

public final class BookStore {
    private final String url;

    public BookStore(String databasePath) {
        this.url = "jdbc:sqlite:" + databasePath;
        try (Connection connection = connect(); Statement statement = connection.createStatement()) {
            statement.executeUpdate("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)");
        } catch (SQLException e) { throw new IllegalStateException("Could not initialize database", e); }
    }

    private Connection connect() throws SQLException { return DriverManager.getConnection(url); }

    public Book create(String title, String author, Integer year, String isbn) {
        try (Connection c = connect(); PreparedStatement p = c.prepareStatement("INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)", Statement.RETURN_GENERATED_KEYS)) {
            p.setString(1,title); p.setString(2,author); if(year == null) p.setNull(3,Types.INTEGER); else p.setInt(3,year); p.setString(4,isbn); p.executeUpdate();
            try (ResultSet keys = p.getGeneratedKeys()) { return new Book(keys.next()?keys.getLong(1):lastId(c),title,author,year,isbn); }
        } catch(SQLException e) { throw new IllegalStateException("Could not create book",e); }
    }
    private long lastId(Connection c) throws SQLException { try(Statement s=c.createStatement(); ResultSet r=s.executeQuery("SELECT last_insert_rowid()")){r.next();return r.getLong(1);} }

    public List<Book> list(String author) {
        String sql = author == null || author.isBlank() ? "SELECT * FROM books ORDER BY id" : "SELECT * FROM books WHERE lower(author)=lower(?) ORDER BY id";
        try(Connection c=connect(); PreparedStatement p=c.prepareStatement(sql)) { if(!sql.contains("lower(author)")) {} else p.setString(1,author); try(ResultSet r=p.executeQuery()){List<Book> out=new ArrayList<>();while(r.next())out.add(read(r));return out;} }
        catch(SQLException e){throw new IllegalStateException("Could not list books",e);}
    }
    public Optional<Book> find(long id) { try(Connection c=connect();PreparedStatement p=c.prepareStatement("SELECT * FROM books WHERE id=?")){p.setLong(1,id);try(ResultSet r=p.executeQuery()){return r.next()?Optional.of(read(r)):Optional.empty();}}catch(SQLException e){throw new IllegalStateException("Could not find book",e);} }
    public Optional<Book> update(long id,String title,String author,Integer year,String isbn) {
        try(Connection c=connect();PreparedStatement p=c.prepareStatement("UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?")){p.setString(1,title);p.setString(2,author);if(year==null)p.setNull(3,Types.INTEGER);else p.setInt(3,year);p.setString(4,isbn);p.setLong(5,id);if(p.executeUpdate()==0)return Optional.empty();return find(id);}catch(SQLException e){throw new IllegalStateException("Could not update book",e);}
    }
    public boolean delete(long id){try(Connection c=connect();PreparedStatement p=c.prepareStatement("DELETE FROM books WHERE id=?")){p.setLong(1,id);return p.executeUpdate()>0;}catch(SQLException e){throw new IllegalStateException("Could not delete book",e);}}
    private Book read(ResultSet r)throws SQLException{int y=r.getInt("year");Integer year=r.wasNull()?null:y;return new Book(r.getLong("id"),r.getString("title"),r.getString("author"),year,r.getString("isbn"));}
}
