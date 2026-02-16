-- ============================================
-- Migration 003: customer_id 컬럼 추가 + admin_users 테이블 생성
-- ============================================

-- 1. consultations 테이블에 customer_id 컬럼 추가 (메디힘 플랫폼 ID)
ALTER TABLE consultations ADD COLUMN customer_id TEXT;
CREATE INDEX idx_consultations_customer_id ON consultations (customer_id);

-- 2. admin_users 테이블 생성
CREATE TABLE admin_users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trigger_admin_users_updated_at
    BEFORE UPDATE ON admin_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
