-- Migration: 004_add_withdrawal_system
-- Description: Add withdrawal system for X2C to SOL conversion

-- Create withdrawals table
CREATE TABLE IF NOT EXISTS withdrawals (
    withdrawal_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    sol_address VARCHAR(44) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    tx_hash VARCHAR(128) DEFAULT NULL,
    error_message TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_withdrawal_user ON withdrawals(user_id);
CREATE INDEX IF NOT EXISTS idx_withdrawal_status ON withdrawals(status);

-- Add sol_wallet field to users table if not exists
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS sol_wallet VARCHAR(44) DEFAULT NULL;

COMMENT ON TABLE withdrawals IS 'Records of X2C withdrawal requests';
COMMENT ON COLUMN withdrawals.status IS 'pending, processing, completed, failed';
