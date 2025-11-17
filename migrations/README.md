# Database Migrations

This directory contains SQL migration scripts for the database schema.

## How to apply migrations

### For SQLite (development)
```bash
sqlite3 data/aifriends.db < migrations/001_add_onboarding_tour.sql
```

### For PostgreSQL (production)
```bash
psql $DATABASE_URL -f migrations/001_add_onboarding_tour.sql
```

## Migration History

### 001_add_onboarding_tour.sql
- **Date**: 2025-11-17
- **Description**: Adds interactive tour support to onboarding
- **Changes**:
  - Added `onboarding_step` column to track current onboarding step
  - Added `tour_completed` column to track if user completed interactive tour
