#!/usr/bin/env node

/**
 * Script to generate TypeScript types from FastAPI OpenAPI schema
 *
 * This script can be run automatically in your development workflow
 * to keep frontend types in sync with backend changes.
 * Run this script in `package.json` scripts section:
 *
 * "scripts": {
 *   "sync-types": "node scripts/generate-types.cjs && prettier --write types/server/server-types.ts"
 * }
 */

const { execSync } = require('child_process');
const fs = require('fs');

// Configuration
const API_URL = process.env.API_URL || 'http://localhost:8000';
const OUTPUT_FILE = './types/server/server-types.ts';
const FORCE_MODE = process.argv.includes('--force');

console.log('Generating TypeScript types from FastAPI OpenAPI schema...');

try {
  // Check if the API is available
  console.log(`Checking API availability at ${API_URL}...`);

  try {
    execSync(`curl -s --max-time 30 ${API_URL}/openapi.json > /dev/null`, {
      stdio: 'ignore',
    });
    console.log('API is available');
  } catch (error) {
    if (FORCE_MODE) {
      console.error(
        'API is not available. Please make sure the FastAPI server is running.',
      );
      console.error(`   Try: cd .. && python -m src.server.server`);
      process.exit(1);
    } else {
      console.warn('API is not available. Skipping type generation for now.');
      console.warn(
        `   The API will be checked again when you run: npm run sync-types`,
      );
      console.warn(`   To start the API: cd .. && python -m src.server.server`);
      process.exit(0); // Exit successfully without generating types
    }
  }

  // Generate new types
  console.log('Generating new types...');
  execSync(
    `npx openapi-typescript ${API_URL}/openapi.json --output ${OUTPUT_FILE}`,
    {
      stdio: 'inherit',
    },
  );

  // Verify the generated file
  if (fs.existsSync(OUTPUT_FILE)) {
    const stats = fs.statSync(OUTPUT_FILE);
    console.log(`Types generated successfully!`);
    console.log(`   File: ${OUTPUT_FILE}`);
    console.log(`   Size: ${(stats.size / 1024).toFixed(2)} KB`);
  } else {
    throw new Error('Generated types file not found');
  }

  console.log('Type generation completed successfully!');
} catch (error) {
  console.error('Error generating types:', error.message);

  process.exit(1);
}
