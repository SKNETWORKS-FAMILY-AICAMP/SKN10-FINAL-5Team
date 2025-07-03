import boto3
import os

ECS_CLUSTER = os.getenv("ECS_CLUSTER_NAME")  # 예: 'your-ecs-cluster'
ECS_SERVICE = os.getenv("ECS_SERVICE_NAME")  # 예: 'your-ecs-service'
DOMAIN_NAME = "youthbot.click"

def get_ecs_public_ip(cluster, service):
    ecs = boto3.client('ecs')
    ec2 = boto3.client('ec2')

    tasks = ecs.list_tasks(cluster=cluster, serviceName=service, desiredStatus='RUNNING')
    if not tasks['taskArns']:
        raise Exception("No running tasks found.")
    task_arn = tasks['taskArns'][0]

    task_desc = ecs.describe_tasks(cluster=cluster, tasks=[task_arn])
    attachments = task_desc['tasks'][0]['attachments']
    eni_id = None
    for att in attachments:
        if att['type'] == 'ElasticNetworkInterface':
            for detail in att['details']:
                if detail['name'] == 'networkInterfaceId':
                    eni_id = detail['value']
                    break
    if not eni_id:
        raise Exception("ENI not found.")

    eni = ec2.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
    public_ip = eni['NetworkInterfaces'][0].get('Association', {}).get('PublicIp')
    if not public_ip:
        raise Exception("Public IP not found.")
    return public_ip

def get_hosted_zone_id(domain_name):
    route53 = boto3.client('route53')
    zones = route53.list_hosted_zones_by_name(DNSName=domain_name)
    for zone in zones['HostedZones']:
        if zone['Name'].rstrip('.') == domain_name:
            return zone['Id'].split('/')[-1]
    raise Exception("Hosted zone not found.")

def update_route53_record(domain_name, public_ip):
    route53 = boto3.client('route53')
    zone_id = get_hosted_zone_id(domain_name)
    response = route53.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            'Comment': 'Auto update by deployment pipeline',
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': domain_name,
                        'Type': 'A',
                        'TTL': 60,
                        'ResourceRecords': [{'Value': public_ip}]
                    }
                }
            ]
        }
    )
    return response

if __name__ == "__main__":
    cluster = ECS_CLUSTER
    service = ECS_SERVICE
    public_ip = get_ecs_public_ip(cluster, service)
    print(f"Updating {DOMAIN_NAME} to {public_ip}")
    update_route53_record(DOMAIN_NAME, public_ip)
    print("Route53 record updated.")