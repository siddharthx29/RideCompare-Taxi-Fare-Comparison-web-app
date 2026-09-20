import { Pool } from 'pg';
import dotenv from 'dotenv';

dotenv.config();

const connectionString = process.env.DATABASE_URL || 'postgresql://postgres:password@localhost:5432/ridecompare';

export const pool = new Pool({
  connectionString,
  ssl: process.env.NODE_ENV === 'production' && process.env.DATABASE_SSL === 'true'
    ? { rejectUnauthorized: false }
    : false
});

// Retry database connection on initial load
export async function connectWithRetry(retries = 5, delay = 2000): Promise<Pool> {
  for (let i = 0; i < retries; i++) {
    try {
      const client = await pool.connect();
      console.log('Successfully connected to PostgreSQL database!');
      client.release();
      return pool;
    } catch (err: any) {
      console.error(`❌ Database connection attempt ${i + 1} of ${retries} failed.`);
      console.error(`Error details: ${err.message || err}`);
      if (err.stack) {
        console.error(err.stack);
      }
      if (i < retries - 1) {
        console.log(`Retrying in ${delay / 1000}s...`);
        await new Promise(res => setTimeout(res, delay));
      }
    }
  }
  throw new Error(`Failed to establish database connection after ${retries} attempts.`);
}

