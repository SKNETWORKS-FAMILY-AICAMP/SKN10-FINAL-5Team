import boto3
import os

def load_parameters_from_aws(prefix="/youth_main3/"):
    """
    AWS SSM Parameter Store에서 환경변수 로드
    prefix: 파라미터 이름 앞에 붙는 경로 (예: /youth_main3/)
    """
    ssm = boto3.client('ssm', region_name=os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2"))
    next_token = None
    params = {}
    while True:
        kwargs = {
            "Path": prefix,
            "WithDecryption": True,
            "Recursive": True,
            "MaxResults": 10
        }
        if next_token:
            kwargs["NextToken"] = next_token
        response = ssm.get_parameters_by_path(**kwargs)
        for param in response["Parameters"]:
            key = param["Name"].replace(prefix, "")
            params[key] = param["Value"]
            os.environ[key] = param["Value"]
        next_token = response.get("NextToken")
        if not next_token:
            break
    return params