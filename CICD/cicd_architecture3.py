from diagrams import Diagram, Edge
from diagrams.aws.devtools import Codepipeline, Codebuild 
from diagrams.aws.compute import ECS, ECR
from diagrams.aws.general import User
from diagrams.onprem.vcs import Github

with Diagram(
    "AWS Django CI/CD Architecture\n"
    "1. 개발자가 GitHub에 코드 Push\n"
    "2. CodePipeline이 변경 감지 후 파이프라인 실행\n"
    "3. CodeBuild가 소스 체크아웃 → Docker 이미지 빌드 → ECR에 푸시\n"
    "4. ECS가 새 이미지를 감지, 서비스에 배포\n"
    "5. 사용자는 새 버전의 웹서비스에 접속",
    show=False,
    direction="LR"  # 좌→우(가로) 방향
):
    github = Github("GitHub\n(Repo)")
    pipeline = Codepipeline("CodePipeline")
    build = Codebuild("CodeBuild")
    ecr = ECR("ECR")
    ecs = ECS("ECS/Fargate")
    user = User("User")

    github >> Edge(label="1. Push") >> pipeline
    pipeline >> Edge(label="2. Trigger") >> build
    build >> Edge(label="3. Docker build/push") >> ecr
    ecr >> Edge(label="4. Deploy") >> ecs
    ecs >> Edge(label="5. Web Access") >> user