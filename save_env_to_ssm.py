import boto3
import os

def parse_env_file(env_path):
    params = {}
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            params[key] = value
    return params

def save_to_ssm(params, prefix="/youth_main3/"):
    ssm = boto3.client("ssm", region_name=params.get("AWS_DEFAULT_REGION", "ap-northeast-2"))
    for key, value in params.items():
        param_name = f"{prefix}{key}"
        param_type = "SecureString" if "KEY" in key or "PASSWORD" in key or "SECRET" in key else "String"
        print(f"Saving {param_name} ...")
        ssm.put_parameter(
            Name=param_name,
            Value=value,
            Type=param_type,
            Overwrite=True
        )

if __name__ == "__main__":
    env_path = ".env"
    if not os.path.exists(env_path):
        print(".env 파일이 없습니다.")
        exit(1)
    params = parse_env_file(env_path)
    save_to_ssm(params)
    print("모든 값을 SSM 파라미터 스토어에 저장 완료.")