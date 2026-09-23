import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://minio:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="46f14446fe9983cc8e77edcf854bcf523766003b737c2684",
)
resp = s3.get_object(Bucket="voice-audio", Key="transcripts/148.txt")
print("=== TRANSCRIPT 148 ===")
print(resp["Body"].read().decode("utf-8"))
