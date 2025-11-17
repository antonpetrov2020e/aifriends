-- Migration: Add interactive tour fields to users table
-- Date: 2025-11-17
-- Description: Adds onboarding_step and tour_completed fields for new interactive onboarding

-- Add onboarding_step column (tracks current step in onboarding)
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_step VARCHAR(50) DEFAULT 'start';

-- Add tour_completed column (tracks if user completed interactive tour)
ALTER TABLE users ADD COLUMN IF NOT EXISTS tour_completed BOOLEAN DEFAULT FALSE;

-- Update existing users to have default values
UPDATE users SET onboarding_step = 'start' WHERE onboarding_step IS NULL;
UPDATE users SET tour_completed = FALSE WHERE tour_completed IS NULL;
