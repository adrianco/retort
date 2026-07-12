import { expect } from 'chai';
import request from 'supertest';
import express from 'express';
import bodyParser from 'body-parser';
import bookRoutes from '../routes/bookRoutes';
import { Database } from '../db/database';

const db = new Database();

describe('Book API', function() {
    this.timeout(5000);
    
    let app: express.Application;
    
    before(async function() {
        await db.init();
        
        app = express();
        app.use(bodyParser.json());
        app.use('/', bookRoutes);
        
        // Clean the database before tests
        await db.db.exec('DELETE FROM books');
    });
    
    after(async function() {
        await db.close();
    });
    
    it('should create a new book', async function() {
        const res = await request(app)
            .post('/books')
            .send({
                title: 'The Great Gatsby',
                author: 'F. Scott Fitzgerald',
                year: 1925,
                isbn: '9780743273565'
            });
        
        expect(res.status).to.equal(201);
        expect(res.body).to.have.property('id');
        expect(res.body.title).to.equal('The Great Gatsby');
        expect(res.body.author).to.equal('F. Scott Fitzgerald');
    });
    
    it('should get all books', async function() {
        const res = await request(app)
            .get('/books');
        
        expect(res.status).to.equal(200);
        expect(res.body).to.be.an('array');
    });
    
    it('should filter books by author', async function() {
        // First, add another book by a different author
        await request(app)
            .post('/books')
            .send({
                title: '1984',
                author: 'George Orwell',
                year: 1949,
                isbn: '9780451524935'
            });
        
        const res = await request(app)
            .get('/books')
            .query({ author: 'F. Scott Fitzgerald' });
        
        expect(res.status).to.equal(200);
        expect(res.body).to.be.an('array');
        expect(res.body.length).to.equal(1);
        expect(res.body[0].author).to.equal('F. Scott Fitzgerald');
    });
    
    it('should get a single book by ID', async function() {
        const createRes = await request(app)
            .post('/books')
            .send({
                title: 'To Kill a Mockingbird',
                author: 'Harper Lee',
                year: 1960,
                isbn: '9780061120084'
            });
        
        const bookId = createRes.body.id;
        
        const res = await request(app)
            .get(`/books/${bookId}`);
        
        expect(res.status).to.equal(200);
        expect(res.body.id).to.equal(bookId);
        expect(res.body.title).to.equal('To Kill a Mockingbird');
    });
    
    it('should update a book', async function() {
        const createRes = await request(app)
            .post('/books')
            .send({
                title: 'The Catcher in the Rye',
                author: 'J.D. Salinger',
                year: 1951,
                isbn: '9780316769488'
            });
        
        const bookId = createRes.body.id;
        
        const res = await request(app)
            .put(`/books/${bookId}`)
            .send({
                title: 'Updated Title',
                author: 'Updated Author',
                year: 2020,
                isbn: 'updated-isbn'
            });
        
        expect(res.status).to.equal(200);
        
        // Verify the update
        const getRes = await request(app)
            .get(`/books/${bookId}`);
        
        expect(getRes.body.title).to.equal('Updated Title');
        expect(getRes.body.author).to.equal('Updated Author');
    });
    
    it('should delete a book', async function() {
        const createRes = await request(app)
            .post('/books')
            .send({
                title: 'Delete Me',
                author: 'Test Author',
                year: 2020,
                isbn: 'test-isbn'
            });
        
        const bookId = createRes.body.id;
        
        const res = await request(app)
            .delete(`/books/${bookId}`);
        
        expect(res.status).to.equal(200);
        
        // Verify deletion
        const getRes = await request(app)
            .get(`/books/${bookId}`);
        
        expect(getRes.status).to.equal(404);
    });
});
