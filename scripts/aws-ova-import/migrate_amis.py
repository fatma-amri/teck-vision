import boto3
import time

ec2 = boto3.client('ec2', region_name='eu-west-3')
dynamodb = boto3.resource('dynamodb', region_name='eu-west-3')
table = dynamodb.Table('ctf-ova-imports')

SUBNET_ID = "subnet-0ef9bef6cbe3b556b"
SECURITY_GROUP_ID = "sg-00926707e3e049019"
INSTANCE_PROFILE_ARN = "arn:aws:iam::853169228413:instance-profile/teck-vision-beanstalk-ec2-profile"

USER_DATA = """#!/bin/bash
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting Golden AMI Setup"

# Wait a bit for network
sleep 10

# Disable apt-daily timers to prevent apt-get lock errors
if [ -f /etc/debian_version ]; then
    systemctl stop apt-daily.timer || true
    systemctl stop apt-daily-upgrade.timer || true
    systemctl kill --kill-who=all apt-daily.service || true
    while fuser /var/lib/dpkg/lock >/dev/null 2>&1 ; do
        echo "Waiting for other software managers to finish..."
        sleep 5
    done
fi

# Install CloudWatch Agent
if [ -f /etc/redhat-release ]; then
    yum update -y
    yum install -y amazon-cloudwatch-agent
elif [ -f /etc/debian_version ]; then
    apt-get update
    apt-get install -y wget
    wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
    dpkg -i -E ./amazon-cloudwatch-agent.deb
fi

echo "Setup complete. Shutting down in 5 seconds."
sleep 5
shutdown -h now
"""

def migrate():
    response = table.scan()
    items = response.get('Items', [])
    completed_items = [i for i in items if i.get('import_status') == 'completed' and i.get('ami_id') and not str(i.get('ami_id')).startswith('ami-new')]
    
    print(f"Found {len(completed_items)} completed AMIs to migrate.")
    
    for item in completed_items:
        challenge_id = item['challenge_id']
        old_ami_id = item['ami_id']
        
        if 'old_ami_id' in item:  # Skip if already migrated
            print(f"Skipping {challenge_id}, already migrated.")
            continue
            
        print(f"\nProcessing {challenge_id} with old AMI {old_ami_id}...")
        
        try:
            run_resp = ec2.run_instances(
                ImageId=old_ami_id,
                InstanceType='t3.micro',
                MinCount=1,
                MaxCount=1,
                UserData=USER_DATA,
                IamInstanceProfile={'Arn': INSTANCE_PROFILE_ARN},
                NetworkInterfaces=[{
                    'DeviceIndex': 0,
                    'SubnetId': SUBNET_ID,
                    'Groups': [SECURITY_GROUP_ID],
                    'AssociatePublicIpAddress': True
                }],
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': f'GoldenAMIBuilder-{challenge_id}'}]
                }]
            )
            instance_id = run_resp['Instances'][0]['InstanceId']
            print(f"  Launched instance {instance_id}. Waiting for it to stop...")
            
            attempts = 0
            while attempts < 60:
                res = ec2.describe_instances(InstanceIds=[instance_id])
                state = res['Reservations'][0]['Instances'][0]['State']['Name']
                if state == 'stopped':
                    break
                if state in ['terminated', 'shutting-down']:
                    raise Exception(f"Instance terminated unexpectedly")
                time.sleep(15)
                attempts += 1
            if attempts >= 60:
                 raise Exception("Timed out waiting for instance to stop")
                 
            print(f"  Instance {instance_id} stopped. Creating image...")
            
            image_resp = ec2.create_image(
                InstanceId=instance_id,
                Name=f"Monitored-{challenge_id}-{int(time.time())}",
                Description=f"Golden AMI for {challenge_id} with CloudWatch Agent"
            )
            new_ami_id = image_resp['ImageId']
            print(f"  Creating image {new_ami_id}. Waiting to be available...")
            
            image_waiter = ec2.get_waiter('image_available')
            image_waiter.wait(ImageIds=[new_ami_id], WaiterConfig={'Delay': 15, 'MaxAttempts': 60})
            print(f"  Image {new_ami_id} is available.")
            
            table.update_item(
                Key={'challenge_id': challenge_id},
                UpdateExpression="SET ami_id = :new_ami, updated_at = :now, old_ami_id = :old_ami",
                ExpressionAttributeValues={
                    ':new_ami': new_ami_id,
                    ':old_ami': old_ami_id,
                    ':now': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            )
            print(f"  DynamoDB updated for {challenge_id}.")
            
            ec2.terminate_instances(InstanceIds=[instance_id])
            print(f"  Terminated builder instance {instance_id}.")
            
        except Exception as e:
            print(f"  Error processing {challenge_id}: {e}")

if __name__ == "__main__":
    migrate()
