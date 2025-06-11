#!/usr/bin/env python3
"""
AWS RDS PostgreSQL 인스턴스 생성 스크립트
퍼블릭 접근 가능한 RDS 인스턴스를 생성합니다.
"""

import boto3
import json
import time
import logging
from botocore.exceptions import ClientError

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RDSManager:
    def __init__(self, region_name='ap-northeast-2'):
        """AWS RDS 클라이언트 초기화"""
        self.region = region_name
        self.rds_client = boto3.client('rds', region_name=region_name)
        self.ec2_client = boto3.client('ec2', region_name=region_name)
        
    def create_security_group(self, group_name='youth-policy-rds-sg'):
        """RDS용 보안 그룹 생성 (퍼블릭 접근 허용)"""
        try:
            # VPC 정보 가져오기
            vpcs = self.ec2_client.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
            if not vpcs['Vpcs']:
                raise Exception("기본 VPC를 찾을 수 없습니다.")
            
            vpc_id = vpcs['Vpcs'][0]['VpcId']
            logger.info(f"기본 VPC 사용: {vpc_id}")
            
            # 보안 그룹 생성
            response = self.ec2_client.create_security_group(
                GroupName=group_name,
                Description='Security group for Youth Policy PostgreSQL RDS',
                VpcId=vpc_id
            )
            
            security_group_id = response['GroupId']
            logger.info(f"보안 그룹 생성됨: {security_group_id}")
            
            # PostgreSQL 포트(5432) 인바운드 규칙 추가 - 모든 IP에서 접근 허용
            self.ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 5432,
                        'ToPort': 5432,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'PostgreSQL access from anywhere'}]
                    }
                ]
            )
            
            logger.info("PostgreSQL 포트(5432)에 대한 퍼블릭 접근 규칙 추가됨")
            return security_group_id
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidGroup.Duplicate':
                # 이미 존재하는 보안 그룹 찾기
                groups = self.ec2_client.describe_security_groups(GroupNames=[group_name])
                security_group_id = groups['SecurityGroups'][0]['GroupId']
                logger.info(f"기존 보안 그룹 사용: {security_group_id}")
                return security_group_id
            else:
                logger.error(f"보안 그룹 생성 실패: {str(e)}")
                raise
    
    def create_db_subnet_group(self, subnet_group_name='youth-policy-subnet-group'):
        """DB 서브넷 그룹 생성"""
        try:
            # 모든 서브넷 조회
            subnets = self.ec2_client.describe_subnets()
            
            # 서로 다른 가용영역의 서브넷들 선택
            subnet_ids = []
            availability_zones = set()
            
            for subnet in subnets['Subnets']:
                az = subnet['AvailabilityZone']
                if az not in availability_zones and len(subnet_ids) < 3:
                    subnet_ids.append(subnet['SubnetId'])
                    availability_zones.add(az)
            
            if len(subnet_ids) < 2:
                raise Exception("최소 2개의 서로 다른 가용영역 서브넷이 필요합니다.")
            
            logger.info(f"서브넷 사용: {subnet_ids}")
            
            # DB 서브넷 그룹 생성
            response = self.rds_client.create_db_subnet_group(
                DBSubnetGroupName=subnet_group_name,
                DBSubnetGroupDescription='Subnet group for Youth Policy PostgreSQL RDS',
                SubnetIds=subnet_ids[:2],  # 최소 2개 사용
                Tags=[
                    {'Key': 'Name', 'Value': 'youth-policy-subnet-group'},
                    {'Key': 'Project', 'Value': 'YouthPolicy'}
                ]
            )
            
            logger.info(f"DB 서브넷 그룹 생성됨: {subnet_group_name}")
            return subnet_group_name
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'DBSubnetGroupAlreadyExistsFault':
                logger.info(f"기존 DB 서브넷 그룹 사용: {subnet_group_name}")
                return subnet_group_name
            else:
                logger.error(f"DB 서브넷 그룹 생성 실패: {str(e)}")
                raise
    
    def create_rds_instance(self, 
                          db_instance_identifier='youth-policy-postgres',
                          db_name='youth_policy',
                          master_username='postgres',
                          master_password='YouthPolicy2024!',
                          security_group_id=None,
                          subnet_group_name=None):
        """RDS PostgreSQL 인스턴스 생성 (퍼블릭 접근 가능)"""
        try:
            response = self.rds_client.create_db_instance(
                DBInstanceIdentifier=db_instance_identifier,
                DBInstanceClass='db.t3.micro',  # 프리 티어
                Engine='postgres',
                # EngineVersion='15.4',  # 기본 버전 사용 (자동으로 최신 안정 버전 선택)
                MasterUsername=master_username,
                MasterUserPassword=master_password,
                AllocatedStorage=20,  # 20GB (프리 티어 최대)
                StorageType='gp2',
                StorageEncrypted=True,
                VpcSecurityGroupIds=[security_group_id] if security_group_id else [],
                DBSubnetGroupName=subnet_group_name,
                BackupRetentionPeriod=7,  # 7일 백업 보관
                MultiAZ=False,  # 프리 티어는 Multi-AZ 불가
                PubliclyAccessible=True,  # 퍼블릭 접근 허용
                AutoMinorVersionUpgrade=True,
                DeletionProtection=False,  # 개발용이므로 삭제 보호 비활성화
                DBName=db_name,
                Port=5432,
                Tags=[
                    {'Key': 'Name', 'Value': 'youth-policy-postgres'},
                    {'Key': 'Project', 'Value': 'YouthPolicy'},
                    {'Key': 'Environment', 'Value': 'development'}
                ]
            )
            
            logger.info(f"RDS 인스턴스 생성 시작: {db_instance_identifier}")
            logger.info("인스턴스 생성 완료까지 약 5-10분 소요됩니다...")
            
            return response['DBInstance']
            
        except ClientError as e:
            logger.error(f"RDS 인스턴스 생성 실패: {str(e)}")
            raise
    
    def wait_for_db_available(self, db_instance_identifier):
        """RDS 인스턴스가 사용 가능할 때까지 대기"""
        logger.info("RDS 인스턴스가 사용 가능할 때까지 대기 중...")
        
        waiter = self.rds_client.get_waiter('db_instance_available')
        waiter.wait(
            DBInstanceIdentifier=db_instance_identifier,
            WaiterConfig={
                'Delay': 30,  # 30초마다 확인
                'MaxAttempts': 20  # 최대 10분 대기
            }
        )
        
        logger.info("RDS 인스턴스가 사용 가능한 상태가 되었습니다!")
    
    def get_db_endpoint(self, db_instance_identifier):
        """RDS 인스턴스 엔드포인트 정보 조회"""
        try:
            response = self.rds_client.describe_db_instances(
                DBInstanceIdentifier=db_instance_identifier
            )
            
            db_instance = response['DBInstances'][0]
            endpoint = db_instance['Endpoint']['Address']
            port = db_instance['Endpoint']['Port']
            
            logger.info(f"RDS 엔드포인트: {endpoint}:{port}")
            return endpoint, port
            
        except ClientError as e:
            logger.error(f"엔드포인트 조회 실패: {str(e)}")
            raise
    
    def create_full_setup(self):
        """전체 RDS 설정 생성"""
        try:
            logger.info("=== AWS RDS PostgreSQL 인스턴스 생성 시작 ===")
            
            # 1. 보안 그룹 생성
            security_group_id = self.create_security_group()
            
            # 2. DB 서브넷 그룹 생성
            subnet_group_name = self.create_db_subnet_group()
            
            # 3. RDS 인스턴스 생성
            db_instance = self.create_rds_instance(
                security_group_id=security_group_id,
                subnet_group_name=subnet_group_name
            )
            
            # 4. 인스턴스 사용 가능할 때까지 대기
            self.wait_for_db_available('youth-policy-postgres')
            
            # 5. 엔드포인트 정보 조회
            endpoint, port = self.get_db_endpoint('youth-policy-postgres')
            
            # 6. 연결 정보 출력
            logger.info("=== RDS 인스턴스 생성 완료 ===")
            logger.info(f"엔드포인트: {endpoint}")
            logger.info(f"포트: {port}")
            logger.info(f"데이터베이스: youth_policy")
            logger.info(f"사용자명: postgres")
            logger.info(f"비밀번호: YouthPolicy2024!")
            
            # 7. 환경 설정 파일 생성
            self.create_env_file(endpoint, port)
            
            return {
                'endpoint': endpoint,
                'port': port,
                'database': 'youth_policy',
                'username': 'postgres',
                'password': 'YouthPolicy2024!'
            }
            
        except Exception as e:
            logger.error(f"RDS 설정 생성 실패: {str(e)}")
            raise
    
    def create_env_file(self, endpoint, port):
        """환경 설정 파일 생성"""
        env_content = f"""# AWS RDS 연결 설정
# 실제 운영 환경에서 사용할 RDS 설정

# RDS 엔드포인트
DB_HOST={endpoint}

# RDS 포트
DB_PORT={port}

# RDS 마스터 사용자명
DB_USER=postgres

# RDS 마스터 비밀번호
DB_PASSWORD=YouthPolicy2024!

# 생성된 데이터베이스명
DB_NAME=youth_policy

# AWS 관련 설정
AWS_REGION=ap-northeast-2
AWS_ENVIRONMENT=true
"""
        
        with open('scripts/rds_config.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        logger.info("환경 설정 파일이 생성되었습니다: scripts/rds_config.env")

def main():
    """메인 실행 함수"""
    try:
        rds_manager = RDSManager()
        connection_info = rds_manager.create_full_setup()
        
        print("\n" + "="*50)
        print("AWS RDS PostgreSQL 인스턴스가 성공적으로 생성되었습니다!")
        print("="*50)
        print(f"엔드포인트: {connection_info['endpoint']}")
        print(f"포트: {connection_info['port']}")
        print(f"데이터베이스: {connection_info['database']}")
        print(f"사용자명: {connection_info['username']}")
        print(f"비밀번호: {connection_info['password']}")
        print("\n다음 단계:")
        print("1. scripts/rds_config.env 파일이 생성되었습니다")
        print("2. dump_migrate_data.py를 실행하여 데이터를 마이그레이션하세요")
        print("3. 애플리케이션 설정을 업데이트하세요")
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        print("AWS 자격 증명과 권한을 확인해주세요.")

if __name__ == "__main__":
    main()