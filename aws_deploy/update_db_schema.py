#!/usr/bin/env python3
"""
Lambda4 중복/삭제 관리를 위한 데이터베이스 스키마 업데이트 스크립트
실행일: 2025-06-26
"""

import psycopg2
import sys
import os

def update_database_schema():
    """데이터베이스 스키마를 업데이트합니다."""
    
    # 데이터베이스 연결 설정
    db_config = {
        'host': 'youth-policy-api-postgres.czoqimai8z0n.ap-northeast-2.rds.amazonaws.com',
        'port': 5432,
        'database': 'postgres',
        'user': 'postgres',
        'password': 'postgres'
    }
    
    # 스키마 업데이트 SQL
    schema_updates = [
        # 1. data_hash 컬럼 추가
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_name = 'policies' AND column_name = 'data_hash') THEN
                ALTER TABLE policies ADD COLUMN data_hash VARCHAR(32);
                RAISE NOTICE 'Added data_hash column';
            ELSE
                RAISE NOTICE 'data_hash column already exists';
            END IF;
        END $$;
        """,
        
        # 2. is_active 컬럼 추가
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_name = 'policies' AND column_name = 'is_active') THEN
                ALTER TABLE policies ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
                RAISE NOTICE 'Added is_active column';
            ELSE
                RAISE NOTICE 'is_active column already exists';
            END IF;
        END $$;
        """,
        
        # 3. last_checked_at 컬럼 추가
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_name = 'policies' AND column_name = 'last_checked_at') THEN
                ALTER TABLE policies ADD COLUMN last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                RAISE NOTICE 'Added last_checked_at column';
            ELSE
                RAISE NOTICE 'last_checked_at column already exists';
            END IF;
        END $$;
        """,
        
        # 4. deactivated_at 컬럼 추가
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_name = 'policies' AND column_name = 'deactivated_at') THEN
                ALTER TABLE policies ADD COLUMN deactivated_at TIMESTAMP;
                RAISE NOTICE 'Added deactivated_at column';
            ELSE
                RAISE NOTICE 'deactivated_at column already exists';
            END IF;
        END $$;
        """,
        
        # 5. 인덱스 생성
        "CREATE INDEX IF NOT EXISTS idx_policies_is_active ON policies(is_active);",
        "CREATE INDEX IF NOT EXISTS idx_policies_data_hash ON policies(data_hash);",
        "CREATE INDEX IF NOT EXISTS idx_policies_last_checked ON policies(last_checked_at);",
        "CREATE INDEX IF NOT EXISTS idx_policies_deactivated ON policies(deactivated_at) WHERE deactivated_at IS NOT NULL;",
        
        # 6. 기존 데이터 초기화
        "UPDATE policies SET is_active = TRUE WHERE is_active IS NULL;",
        
        # 7. 컬럼 코멘트 추가
        "COMMENT ON COLUMN policies.data_hash IS '데이터 변경 감지용 MD5 해시값';",
        "COMMENT ON COLUMN policies.is_active IS '정책 활성 상태 (FALSE: 논리적 삭제)';",
        "COMMENT ON COLUMN policies.last_checked_at IS '마지막 데이터 확인 시간';",
        "COMMENT ON COLUMN policies.deactivated_at IS '정책 비활성화 시간';"
    ]
    
    try:
        print("🔧 데이터베이스 연결 중...")
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ 데이터베이스 연결 성공!")
        
        # 스키마 업데이트 실행
        for i, sql in enumerate(schema_updates, 1):
            try:
                print(f"📝 SQL 실행 중... ({i}/{len(schema_updates)})")
                cursor.execute(sql)
                print(f"✅ SQL {i} 실행 완료")
            except Exception as e:
                print(f"⚠️ SQL {i} 실행 경고: {e}")
                continue
        
        # 업데이트 결과 확인
        print("\n🔍 업데이트된 컬럼 확인:")
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'policies' 
                AND column_name IN ('data_hash', 'is_active', 'last_checked_at', 'deactivated_at')
            ORDER BY column_name;
        """)
        
        results = cursor.fetchall()
        if results:
            print("컬럼명 | 데이터타입 | NULL허용 | 기본값")
            print("-" * 60)
            for row in results:
                print(f"{row[0]} | {row[1]} | {row[2]} | {row[3] or 'None'}")
        else:
            print("❌ 새로운 컬럼을 찾을 수 없습니다.")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 데이터베이스 스키마 업데이트 완료!")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 스키마 업데이트 실패: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Lambda4 데이터베이스 스키마 업데이트")
    print("=" * 50)
    
    success = update_database_schema()
    sys.exit(0 if success else 1) 