import express from 'express';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import dotenv from 'dotenv';
import path from 'path';
import fs from 'fs';
import apiRouter from './routes/api';
import { connectWithRetry } from './db/pool';
import { setupDatabase } from './db/setup';

// Load environment variables from .env file
dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Security: Disable X-Powered-By header
app.disable('x-powered-by');

// Security Headers Middleware
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  next();
});

// Setup Secure CORS Middleware
const allowedOrigins = process.env.ALLOWED_ORIGINS
  ? process.env.ALLOWED_ORIGINS.split(',').map(o => o.trim())
  : [
      'https://taxi-fare-comparison-web-app.onrender.com',
      'https://ridecompare.onrender.com',
      'http://localhost:5173',
      'http://localhost:8080',
      'http://localhost:3000',
      'https://taxi.teamnexterp.com',
      'http://taxi.teamnexterp.com'
    ];

app.use(cors({
  origin: (origin, callback) => {
    if (!origin) {
      return callback(null, true);
    }

    const isAllowed = allowedOrigins.includes(origin) || 
      origin.endsWith('.teamnexterp.com') || 
      origin === 'https://teamnexterp.com' ||
      origin.endsWith('.onrender.com');

    if (isAllowed) {
      callback(null, true);
    } else {
      callback(null, false); // Reject without throwing an unhandled exception
    }
  },
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true
}));

// Payload limit protection against DoS
app.use(express.json({ limit: '1mb' }));

// Request/Response Logger Middleware
app.use((req, res, next) => {
  const start = Date.now();
  console.log(`[Incoming Request] ${req.method} ${req.originalUrl}`);
  if (req.query && Object.keys(req.query).length > 0) {
    console.log(`[Query Parameters]`, req.query);
  }
  if (req.body && Object.keys(req.body).length > 0) {
    console.log(`[Request Payload]`, req.body);
  }
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`[Response Status] ${req.method} ${req.originalUrl} | Status: ${res.statusCode} | Duration: ${duration}ms`);
  });
  next();
});

// Express rate limiter to secure backend routes from abuse
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per window
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests from this IP. Please try again after 15 minutes.' }
});

// Apply rate limiter to API routes
app.use('/api', apiLimiter);

// Bind API Routes
app.use('/api', apiRouter);

/**
 * Formats the server uptime into a human-readable string (hh:mm:ss)
 */
function getFormattedUptime(): string {
  const uptimeSeconds = process.uptime();
  const hrs = Math.floor(uptimeSeconds / 3600);
  const mins = Math.floor((uptimeSeconds % 3600) / 60);
  const secs = Math.floor(uptimeSeconds % 60);
  
  const pad = (num: number) => num.toString().padStart(2, '0');
  return `${pad(hrs)}h ${pad(mins)}m ${pad(secs)}s`;
}

// GET /health - Enhanced health-check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'healthy',
    uptime: getFormattedUptime(),
    timestamp: new Date().toISOString()
  });
});

// Resolve the path to the React frontend production build if it exists.
// Checks multiple potential locations to ensure compatibility with dev, production, and Docker environments.
const FRONTEND_DIST_PATH = process.env.FRONTEND_DIST_PATH || [
  path.join(__dirname, '../../frontend/dist'),
  path.join(process.cwd(), '../frontend/dist'),
  path.join(process.cwd(), 'frontend/dist'),
  path.join(__dirname, '../frontend/dist')
].find(p => fs.existsSync(p)) || '';

if (FRONTEND_DIST_PATH) {
  console.log(`[Static Files] Serving production React build from: ${FRONTEND_DIST_PATH}`);
  
  // Serve static files from React build directory
  app.use(express.static(FRONTEND_DIST_PATH));

  // Serve index.html specifically for the root URL
  app.get('/', (req, res, next) => {
    const indexPath = path.join(FRONTEND_DIST_PATH, 'index.html');
    if (fs.existsSync(indexPath)) {
      res.sendFile(indexPath);
    } else {
      next();
    }
  });

  // Client-side routing wildcard: fallback to index.html for SPA router support (excluding API and health routes)
  app.get('*', (req, res, next) => {
    if (req.path.startsWith('/api') || req.path.startsWith('/health')) {
      return next();
    }
    const indexPath = path.join(FRONTEND_DIST_PATH, 'index.html');
    if (fs.existsSync(indexPath)) {
      res.sendFile(indexPath);
    } else {
      next();
    }
  });
} else {
  console.log('[Static Files] React frontend production build directory not found. Root path will serve API status JSON.');
  
  // GET / - Root route displays professional JSON status when React frontend dist is not built
  app.get('/', (req, res) => {
    res.status(200).json({
      status: "success",
      message: "RideCompare API is running successfully",
      version: "1.0.0"
    });
  });
}

// Global Error Handler Middleware using TypeScript best practices
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error(`[Error Log] Unhandled error during ${req.method} ${req.originalUrl}:`);
  if (err instanceof Error) {
    console.error(err.stack);
  } else {
    console.error(err);
  }
  
  const statusCode = err.status || err.statusCode || 500;
  const message = err.message || 'An unexpected database or server error occurred';
  
  res.status(statusCode).json({
    status: 'error',
    message: message,
    // Exclude stack trace in production to prevent leaking sensitive internals
    ...(process.env.NODE_ENV !== 'production' && { stack: err.stack })
  });
});

// Launch server after connecting to PostgreSQL DB
async function startServer() {
  try {
    // Run database migrations before starting the application
    await setupDatabase(false);

    await connectWithRetry();
    app.listen(PORT, () => {
      console.log(`RideCompare backend listening on port ${PORT} in ${process.env.NODE_ENV || 'development'} mode.`);
    });
  } catch (error: any) {
    console.error('❌ FATAL: Database connection could not be established or migrations failed. Server startup aborted.');
    console.error(error.message || error);
    process.exit(1);
  }
}

startServer();

