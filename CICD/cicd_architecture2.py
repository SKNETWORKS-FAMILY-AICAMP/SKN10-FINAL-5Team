from diagrams import Diagram, Edge
from diagrams.aws.devtools import Codepipeline, Codebuild
from diagrams.aws.compute import ECS
from diagrams.aws.general import User
from diagrams.aws.storage import S3
from diagrams.onprem.vcs import Github

with Diagram("AWS Django CI/CD Architecture (with S3)", show=False, direction="TB"):
    user = User("User")
    github = Github("GitHub\n(Repo)")
    pipeline = Codepipeline("CodePipeline")
    build = Codebuild("CodeBuild")
    s3 = S3("S3 (Artifact)")
    ecs = ECS("ECS/Fargate")

    github >> Edge(label="Push/PR") >> pipeline
    pipeline >> Edge(label="Trigger") >> build
    build >> Edge(label="Artifact upload") >> s3
    s3 >> Edge(label="Deploy") >> ecs
    ecs >> Edge(label="Web Access") >> user