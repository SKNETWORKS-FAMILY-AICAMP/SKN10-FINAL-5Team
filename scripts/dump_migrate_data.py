#!/usr/bin/env python3
"""
Docker PostgreSQL에서 AWS RDS로 데이터 마이그레이션 스크립트
"""

import subprocess
import psycopg2
import os
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataMigration:
    def __init__(self):
        """환경 설정 로드"""
        # RDS 환경 설정 로드
        load_dotenv('scripts/rds_config.env')
        
        # Docker PostgreSQL 설정 (로컬)
        self.docker_config = {
            "host": "localhost",
            "port": "5432",
            "user": "postgres",
            "password": "postgres",
            "database": "youth_policy"
        }
        
        # AWS RDS 설정
        self.rds_config = {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT", "5432"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_NAME", "youth_policy")
        }
        
        # 덤프 파일 경로
        self.dump_file = f"youth_policy_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
    def test_docker_connection(self):
        """Docker PostgreSQL 연결 테스트"""
        try:
            conn = psycopg2.connect(
                host=self.docker_config["host"],
                port=self.docker_config["port"],
                user=self.docker_config["user"],
                password=self.docker_config["password"],
                database=self.docker_config["database"],
                connect_timeout=10
            )
            
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM policies")
            count = cur.fetchone()[0]
            
            cur.close()
            conn.close()
            
            logger.info(f"Docker PostgreSQL 연결 성공! 정책 데이터: {count}개")
            return True, count
            
        except Exception as e:
            logger.error(f"Docker PostgreSQL 연결 실패: {str(e)}")
            return False, 0
    
    def test_rds_connection(self):
        """AWS RDS 연결 테스트"""
        try:
            conn = psycopg2.connect(
                host=self.rds_config["host"],
                port=self.rds_config["port"],
                user=self.rds_config["user"],
                password=self.rds_config["password"],
                database="postgres",  # 먼저 기본 DB에 연결
                connect_timeout=10
            )
            conn.close()
            
            logger.info("AWS RDS 연결 성공!")
            return True
            
        except Exception as e:
            logger.error(f"AWS RDS 연결 실패: {str(e)}")
            return False
    
    def create_database_if_not_exists(self):
        """RDS에 youth_policy 데이터베이스가 없으면 생성"""
        try:
            # postgres 데이터베이스에 연결
            conn = psycopg2.connect(
                host=self.rds_config["host"],
                port=self.rds_config["port"],
                user=self.rds_config["user"],
                password=self.rds_config["password"],
                database="postgres",
                connect_timeout=10
            )
            conn.autocommit = True
            cur = conn.cursor()
            
            # youth_policy 데이터베이스 존재 확인
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.rds_config["database"],))
            exists = cur.fetchone()
            
            if not exists:
                # 데이터베이스 생성
                cur.execute(f'CREATE DATABASE "{self.rds_config["database"]}"')
                logger.info(f"RDS에 {self.rds_config['database']} 데이터베이스 생성됨")
            else:
                logger.info(f"RDS에 {self.rds_config['database']} 데이터베이스가 이미 존재함")
            
            cur.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"데이터베이스 생성 중 오류: {str(e)}")
            raise
    
    def dump_docker_data(self):
        """Docker PostgreSQL에서 데이터 덤프"""
        try:
            logger.info("Docker PostgreSQL에서 데이터 덤프 시작...")
            
            # pg_dump 명령어 구성
            dump_cmd = [
                "pg_dump",
                "-h", self.docker_config["host"],
                "-p", self.docker_config["port"],
                "-U", self.docker_config["user"],
                "-d", self.docker_config["database"],
                "-f", self.dump_file,
                "--clean",  # DROP 문 포함
                "--if-exists",  # IF EXISTS 사용
                "--verbose"
            ]
            
            # 환경변수로 비밀번호 설정
            env = os.environ.copy()
            env["PGPASSWORD"] = self.docker_config["password"]
            
            # 덤프 실행
            result = subprocess.run(
                dump_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )
            
            if result.returncode == 0:
                logger.info(f"데이터 덤프 완료: {self.dump_file}")
                
                # 덤프 파일 크기 확인
                size = os.path.getsize(self.dump_file) / 1024 / 1024  # MB
                logger.info(f"덤프 파일 크기: {size:.2f} MB")
                
                return True
            else:
                logger.error(f"덤프 실패: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("덤프 작업이 타임아웃되었습니다.")
            return False
        except Exception as e:
            logger.error(f"덤프 중 오류: {str(e)}")
            return False
    
    def restore_to_rds(self):
        """AWS RDS로 데이터 복원"""
        try:
            logger.info("AWS RDS로 데이터 복원 시작...")
            
            # psql 명령어 구성
            restore_cmd = [
                "psql",
                "-h", self.rds_config["host"],
                "-p", self.rds_config["port"],
                "-U", self.rds_config["user"],
                "-d", self.rds_config["database"],
                "-f", self.dump_file,
                "--quiet"
            ]
            
            # 환경변수로 비밀번호 설정
            env = os.environ.copy()
            env["PGPASSWORD"] = self.rds_config["password"]
            
            # 복원 실행
            result = subprocess.run(
                restore_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10분 타임아웃
            )
            
            if result.returncode == 0:
                logger.info("AWS RDS로 데이터 복원 완료!")
                return True
            else:
                logger.error(f"복원 실패: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("복원 작업이 타임아웃되었습니다.")
            return False
        except Exception as e:
            logger.error(f"복원 중 오류: {str(e)}")
            return False
    
    def verify_migration(self):
        """마이그레이션 결과 검증"""
        try:
            # RDS 연결 및 데이터 확인
            conn = psycopg2.connect(
                host=self.rds_config["host"],
                port=self.rds_config["port"],
                user=self.rds_config["user"],
                password=self.rds_config["password"],
                database=self.rds_config["database"],
                connect_timeout=10
            )
            
            cur = conn.cursor()
            
            # 테이블 존재 확인
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            if 'policies' not in tables:
                logger.error("policies 테이블이 RDS에 생성되지 않았습니다.")
                return False
            
            # 데이터 개수 확인
            cur.execute("SELECT COUNT(*) FROM policies")
            rds_count = cur.fetchone()[0]
            
            # 인덱스 확인
            cur.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'policies'
            """)
            indexes = [row[0] for row in cur.fetchall()]
            
            cur.close()
            conn.close()
            
            logger.info(f"RDS 마이그레이션 검증 완료:")
            logger.info(f"- 정책 데이터: {rds_count}개")
            logger.info(f"- 인덱스: {len(indexes)}개")
            
            if rds_count > 0:
                logger.info("✅ 마이그레이션이 성공적으로 완료되었습니다!")
                return True
            else:
                logger.error("❌ 데이터가 마이그레이션되지 않았습니다.")
                return False
                
        except Exception as e:
            logger.error(f"검증 중 오류: {str(e)}")
            return False
    
    def cleanup(self):
        """임시 파일 정리"""
        try:
            if os.path.exists(self.dump_file):
                os.remove(self.dump_file)
                logger.info(f"덤프 파일 삭제됨: {self.dump_file}")
        except Exception as e:
            logger.warning(f"덤프 파일 삭제 실패: {str(e)}")
    
    def run_migration(self):
        """전체 마이그레이션 프로세스 실행"""
        try:
            logger.info("=== PostgreSQL → AWS RDS 마이그레이션 시작 ===")
            
            # 1. 연결 테스트
            logger.info("1. 연결 테스트 중...")
            docker_ok, data_count = self.test_docker_connection()
            if not docker_ok:
                raise Exception("Docker PostgreSQL 연결 실패")
            
            rds_ok = self.test_rds_connection()
            if not rds_ok:
                raise Exception("AWS RDS 연결 실패")
            
            # 2. RDS 데이터베이스 생성
            logger.info("2. RDS 데이터베이스 확인/생성 중...")
            self.create_database_if_not_exists()
            
            # 3. 데이터 덤프
            logger.info("3. Docker PostgreSQL 데이터 덤프 중...")
            if not self.dump_docker_data():
                raise Exception("데이터 덤프 실패")
            
            # 4. 데이터 복원
            logger.info("4. AWS RDS로 데이터 복원 중...")
            if not self.restore_to_rds():
                raise Exception("데이터 복원 실패")
            
            # 5. 검증
            logger.info("5. 마이그레이션 결과 검증 중...")
            if not self.verify_migration():
                raise Exception("마이그레이션 검증 실패")
            
            # 6. 정리
            logger.info("6. 임시 파일 정리 중...")
            self.cleanup()
            
            logger.info("=== 마이그레이션 성공적으로 완료! ===")
            print("\n" + "="*50)
            print("마이그레이션이 성공적으로 완료되었습니다!")
            print("="*50)
            print(f"RDS 엔드포인트: {self.rds_config['host']}")
            print(f"데이터베이스: {self.rds_config['database']}")
            print(f"이전된 정책 데이터: {data_count}개")
            print("\n다음 단계:")
            print("1. 애플리케이션 환경 변수를 RDS로 업데이트")
            print("2. Docker PostgreSQL 컨테이너 중지 가능")
            print("3. DBeaver 등으로 RDS 연결 테스트")
            
            return True
            
        except Exception as e:
            logger.error(f"마이그레이션 실패: {str(e)}")
            self.cleanup()
            return False

def main():
    """메인 실행 함수"""
    migration = DataMigration()
    
    if not migration.rds_config["host"]:
        print("❌ RDS 설정이 없습니다.")
        print("먼저 scripts/create_rds_instance.py를 실행하여 RDS 인스턴스를 생성하세요.")
        return
    
    success = migration.run_migration()
    
    if success:
        print("\n🎉 마이그레이션이 완료되었습니다!")
    else:
        print("\n❌ 마이그레이션이 실패했습니다. 로그를 확인해주세요.")

if __name__ == "__main__":
    main()