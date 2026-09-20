import { Client } from 'pg';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { URL } from 'url';

dotenv.config();

const dbUrl = process.env.DATABASE_URL || 'postgresql://postgres:password@localhost:5432/ridecompare';

function getSystemDbUrl(url: string): string {
  try {
    const parsed = new URL(url);
    parsed.pathname = '/postgres';
    return parsed.toString();
  } catch (err) {
    throw new Error(`Failed to parse DATABASE_URL: ${url}`);
  }
}

function getDatabaseName(url: string): string {
  try {
    const parsed = new URL(url);
    return parsed.pathname.replace('/', '');
  } catch (err) {
    throw new Error(`Failed to extract database name from DATABASE_URL: ${url}`);
  }
}

async function checkPostgresAvailability(retries = 10, delay = 2000): Promise<boolean> {
  const parsedUrl = new URL(dbUrl);
  console.log(`Checking PostgreSQL availability at ${parsedUrl.hostname}:${parsedUrl.port || '5432'}...`);
  
  for (let i = 0; i < retries; i++) {
    const client = new Client({ connectionString: dbUrl });
    try {
      await client.connect();
      await client.end();
      console.log('✅ PostgreSQL server is available and accepting connections.');
      return true;
    } catch (err: any) {
      console.log(`[Attempt ${i + 1}/${retries}] PostgreSQL not available yet: ${err.message}. Retrying in ${delay / 1000}s...`);
      await new Promise(res => setTimeout(res, delay));
    }
  }
  return false;
}

async function ensureDatabaseExists() {
  const targetDb = getDatabaseName(dbUrl);
  const systemDbUrl = getSystemDbUrl(dbUrl);

  console.log(`Verifying target database "${targetDb}" exists...`);
  const client = new Client({ connectionString: systemDbUrl });
  
  try {
    await client.connect();
    
    const res = await client.query(
      'SELECT 1 FROM pg_database WHERE datname = $1',
      [targetDb]
    );
    
    if (res.rowCount === 0) {
      console.log(`Database "${targetDb}" does not exist. Creating database "${targetDb}"...`);
      // CREATE DATABASE cannot run in a transaction, run it on the client
      await client.query(`CREATE DATABASE ${targetDb}`);
      console.log(`✅ Database "${targetDb}" created successfully.`);
    } else {
      console.log(`Database "${targetDb}" already exists.`);
    }
  } catch (err: any) {
    console.error(`❌ Error verifying or creating database: ${err.message}`);
    throw err;
  } finally {
    await client.end();
  }
}

async function runMigrations() {
  const targetDb = getDatabaseName(dbUrl);
  console.log(`Connecting to database "${targetDb}" to execute migrations...`);
  const client = new Client({ connectionString: dbUrl });
  
  try {
    await client.connect();

    // Ensure migrations table exists
    await client.query(`
      CREATE TABLE IF NOT EXISTS schema_migrations (
        id SERIAL PRIMARY KEY,
        migration_name VARCHAR(255) UNIQUE NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    const migrationsDir = path.join(__dirname, 'migrations');
    if (!fs.existsSync(migrationsDir)) {
      throw new Error(`Migrations directory not found at: ${migrationsDir}`);
    }

    const files = fs.readdirSync(migrationsDir)
      .filter(file => file.endsWith('.sql'))
      .sort();

    if (files.length === 0) {
      console.log('No migration scripts (.sql) found.');
      return;
    }

    for (const file of files) {
      const checkRes = await client.query(
        'SELECT 1 FROM schema_migrations WHERE migration_name = $1',
        [file]
      );

      if (checkRes.rowCount === 0) {
        console.log(`Applying migration "${file}"...`);
        const sql = fs.readFileSync(path.join(migrationsDir, file), 'utf8');
        
        await client.query('BEGIN');
        try {
          // Execute migration SQL commands
          await client.query(sql);
          // Log applied migration
          await client.query(
            'INSERT INTO schema_migrations (migration_name) VALUES ($1)',
            [file]
          );
          await client.query('COMMIT');
          console.log(`✅ Migration "${file}" applied successfully.`);
        } catch (err: any) {
          await client.query('ROLLBACK');
          console.error(`❌ Migration "${file}" failed! Transaction rolled back.`);
          throw err;
        }
      } else {
        console.log(`Migration "${file}" already applied.`);
      }
    }
  } catch (err: any) {
    console.error(`❌ Error during migration runner: ${err.message}`);
    throw err;
  } finally {
    await client.end();
  }
}

export async function setupDatabase(exitOnCompletion = false) {
  console.log('====================================================');
  console.log('         RideCompare Database Setup & Migrator       ');
  console.log('====================================================');
  
  try {
    const isAvailable = await checkPostgresAvailability(10, 2000);
    if (!isAvailable) {
      console.error('❌ FATAL: PostgreSQL server is offline or unreachable.');
      console.error('Please verify PostgreSQL is running before launching RideCompare.');
      if (exitOnCompletion) {
        process.exit(1);
      } else {
        throw new Error('PostgreSQL server is offline or unreachable.');
      }
    }

    try {
      await ensureDatabaseExists();
    } catch (dbErr: any) {
      console.warn('⚠️ Could not verify or create target database (this is expected on managed hostings like Render). Proceeding to run migrations directly on target database...');
    }

    await runMigrations();
    
    console.log('====================================================');
    console.log('✅ Database setup and migrations completed successfully!');
    console.log('====================================================');
    if (exitOnCompletion) process.exit(0);
  } catch (err: any) {
    console.error('❌ FATAL: Database setup failed:');
    console.error(err.stack || err.message || err);
    if (exitOnCompletion) {
      process.exit(1);
    } else {
      throw err;
    }
  }
}

// Run automatically if this script is executed directly via CLI
const isDirectRun = require.main === module || 
  (process.argv[1] && (process.argv[1].endsWith('setup.ts') || process.argv[1].endsWith('setup.js')));

if (isDirectRun) {
  setupDatabase(true);
}

