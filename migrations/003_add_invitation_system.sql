-- Migration: 003_add_invitation_system
-- Description: Add invitation system with referral tracking and rewards

-- Add invitation fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS invited_by BIGINT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS invitation_reward_received BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS invitation_reward_received_at TIMESTAMP DEFAULT NULL;

-- Create user_invitations table to track invitation relationships and rewards
CREATE TABLE IF NOT EXISTS user_invitations (
    invitation_id SERIAL PRIMARY KEY,
    inviter_id BIGINT NOT NULL,
    invitee_id BIGINT NOT NULL,
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_task_completed BOOLEAN DEFAULT FALSE,
    first_task_completed_at TIMESTAMP DEFAULT NULL,
    total_referral_rewards DECIMAL(10, 2) DEFAULT 0.00,
    FOREIGN KEY (inviter_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (invitee_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(invitee_id)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_inviter_id ON user_invitations(inviter_id);
CREATE INDEX IF NOT EXISTS idx_invitee_id ON user_invitations(invitee_id);

-- Create referral_rewards table to track each referral reward transaction
CREATE TABLE IF NOT EXISTS referral_rewards (
    reward_id SERIAL PRIMARY KEY,
    inviter_id BIGINT NOT NULL,
    invitee_id BIGINT NOT NULL,
    task_id INT NOT NULL,
    original_reward DECIMAL(10, 2) NOT NULL,
    referral_reward DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inviter_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (invitee_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES drama_tasks(task_id) ON DELETE CASCADE
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_referral_inviter ON referral_rewards(inviter_id);
CREATE INDEX IF NOT EXISTS idx_referral_invitee ON referral_rewards(invitee_id);
