import express from 'express';

const app = express();
const port = 3001;

app.get('/test', (req, res) => {
  res.json({ message: 'It works!' });
});

const server = app.listen(port, '0.0.0.0', () => {
  console.log(`Test server running on port ${port}`);
});

server.on('error', (err) => {
  console.error('Server error:', err);
});

server.on('listening', () => {
  console.log('Server is now listening');
  const addr = server.address();
  console.log('Address:', addr);
});
