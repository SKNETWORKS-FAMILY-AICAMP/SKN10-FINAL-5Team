from diagrams import Diagram, Edge
from diagrams.aws.devtools import Codepipeline, Codebuild 
from diagrams.aws.compute import ECS, ECR
from diagrams.aws.general import User
from diagrams.aws.management import SystemsManagerParameterStore
from diagrams.aws.network import Route53
from diagrams.onprem.vcs import Github

# 설명은 주석으로!
# 1. 개발자가 GitHub에 코드 Push
# 2. CodePipeline이 변경 감지 후 파이프라인 실행
# 3. CodeBuild가 소스 체크아웃 → Docker 이미지 빌드 → ECR에 푸시
# 4. ECS가 새 이미지를 감지, 서비스에 배포
# 5. ECS Task가 SSM Parameter Store에서 환경변수(비밀키 등) 로드
# 6. CodeBuild가 ECS로 인해 변경된 퍼블릭IP를 route53에 등록된 도메인 네임에 업데이트함.
# 7. 사용자는 새 버전의 웹서비스에 접속

with Diagram(
    "aws_cicd_architecture",  # 파일명으로 사용될 짧은 제목
    show=False,
    direction="LR"
):
    github = Github("GitHub\n(Repo)")
    pipeline = Codepipeline("CodePipeline")
    build = Codebuild("CodeBuild\n(Docker Build/Push)")
    ecr = ECR("ECR")
    ecs = ECS("ECS/Fargate")
    ssm = SystemsManagerParameterStore("SSM\nParameter Store")
    route53 = Route53("Route53\n(DNS)")
    build_ip = Codebuild("CodeBuild\n(Route53 Update)")
    user = User("User")

    github >> Edge(label="1. Push") >> pipeline
    pipeline >> Edge(label="2. Trigger") >> build
    build >> Edge(label="3. Docker build/push") >> ecr
    ecr >> Edge(label="4. Deploy") >> ecs
    ecs >> Edge(label="5. 환경변수 로드") >> ssm
    ecs >> Edge(label="퍼블릭IP 변경 감지") >> build_ip
    build_ip >> Edge(label="6. 도메인 IP 업데이트") >> route53
    user >> Edge(label="7. 접속 (도메인)") >> route53
    route53 >> Edge(label="트래픽 라우팅") >> ecs