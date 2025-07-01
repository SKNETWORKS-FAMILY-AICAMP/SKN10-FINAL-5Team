from diagrams import Diagram, Edge
from diagrams.aws.devtools import Codepipeline, Codebuild 
from diagrams.aws.compute import ECS, ECR
from diagrams.aws.general import User
from diagrams.onprem.vcs import Github

with Diagram("AWS Django CI/CD Architecture", show=False, direction="TB"):
    user = User("User")
    github = Github("GitHub\n(Repo)")
    pipeline = Codepipeline("CodePipeline")
    build = Codebuild("CodeBuild")
    ecr = ECR("ECR")
    ecs = ECS("ECS/Fargate")

    github >> Edge(label="Push/PR") >> pipeline
    pipeline >> Edge(label="Trigger") >> build
    build >> Edge(label="Docker build/push") >> ecr
    ecr >> Edge(label="Deploy") >> ecs
    ecs >> Edge(label="Web Access") >> user