-- Lambda4 중복/삭제 관리를 위한 스키마 업데이트
-- 실행일: 2025-06-26

-- 기존 policies 테이블에 새 컬럼들 추가
DO $$
BEGIN
    -- data_hash 컬럼 추가 (데이터 변경 감지용)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'policies' AND column_name = 'data_hash') THEN
        ALTER TABLE policies ADD COLUMN data_hash VARCHAR(32);
        RAISE NOTICE 'Added data_hash column';
    ELSE
        RAISE NOTICE 'data_hash column already exists';
    END IF;
    
    -- is_active 컬럼 추가 (논리적 삭제용)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'policies' AND column_name = 'is_active') THEN
        ALTER TABLE policies ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
        RAISE NOTICE 'Added is_active column';
    ELSE
        RAISE NOTICE 'is_active column already exists';
    END IF;
    
    -- last_checked_at 컬럼 추가 (마지막 확인 시간)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'policies' AND column_name = 'last_checked_at') THEN
        ALTER TABLE policies ADD COLUMN last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE 'Added last_checked_at column';
    ELSE
        RAISE NOTICE 'last_checked_at column already exists';
    END IF;
    
    -- deactivated_at 컬럼 추가 (비활성화 시간)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'policies' AND column_name = 'deactivated_at') THEN
        ALTER TABLE policies ADD COLUMN deactivated_at TIMESTAMP;
        RAISE NOTICE 'Added deactivated_at column';
    ELSE
        RAISE NOTICE 'deactivated_at column already exists';
    END IF;
END $$;

-- 새 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_policies_is_active ON policies(is_active);
CREATE INDEX IF NOT EXISTS idx_policies_data_hash ON policies(data_hash);
CREATE INDEX IF NOT EXISTS idx_policies_last_checked ON policies(last_checked_at);
CREATE INDEX IF NOT EXISTS idx_policies_deactivated ON policies(deactivated_at) WHERE deactivated_at IS NOT NULL;

-- 기존 데이터의 is_active 컬럼 초기화
UPDATE policies SET is_active = TRUE WHERE is_active IS NULL;

-- 컬럼 코멘트 추가
COMMENT ON COLUMN policies.data_hash IS '데이터 변경 감지용 MD5 해시값';
COMMENT ON COLUMN policies.is_active IS '정책 활성 상태 (FALSE: 논리적 삭제)';
COMMENT ON COLUMN policies.last_checked_at IS '마지막 데이터 확인 시간';
COMMENT ON COLUMN policies.deactivated_at IS '정책 비활성화 시간';

-- 스키마 업데이트 완료 확인
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'policies' 
    AND column_name IN ('data_hash', 'is_active', 'last_checked_at', 'deactivated_at')
ORDER BY column_name; 