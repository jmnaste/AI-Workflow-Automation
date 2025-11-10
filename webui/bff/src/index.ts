import express from 'express';
import cookieParser from 'cookie-parser';
import cors from 'cors';
import pino from 'pino';
import pinoHttp from 'pino-http';
import healthRouter from './routes/health.js';
import authRouter from './routes/auth.js';

const app = express();
const port = process.env.PORT || 3001;

// Logger setup
const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: process.env.NODE_ENV !== 'production' ? {
    target: 'pino-pretty',
    options: {
      colorize: true,
      translateTime: 'SYS:standard',
      ignore: 'pid,hostname',
    },
  } : undefined,
});

// Middleware
app.use(pinoHttp({ logger }));
app.use(express.json());
app.use(cookieParser());

// CORS - same origin only (Nginx serves both UI and proxies to BFF)
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:5173',
  credentials: true,
}));

// Routes
app.use('/bff/health', healthRouter);
app.use('/bff/auth', authRouter);

// Error handler
app.use((err: Error, req: express.Request, res: express.Response, _next: express.NextFunction) => {
  logger.error({ err, req: req.url }, 'Unhandled error');
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'production' ? 'An error occurred' : err.message,
  });
});

// Start server
const server = app.listen(port, () => {
  logger.info(`BFF server listening on port ${port}`);
  logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
  logger.info(`API base: ${process.env.API_BASE_URL || 'http://api:8000'}`);
  logger.info(`Auth base: ${process.env.AUTH_BASE_URL || 'http://auth:8000'}`);
});

server.on('error', (error) => {
  logger.error({ error }, 'Server error');
  process.exit(1);
});

process.on('uncaughtException', (error) => {
  logger.error({ error }, 'Uncaught exception');
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  logger.error({ reason }, 'Unhandled rejection');
  process.exit(1);
});

process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  server.close(() => {
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully');
  server.close(() => {
    process.exit(0);
  });
});

export default app;
