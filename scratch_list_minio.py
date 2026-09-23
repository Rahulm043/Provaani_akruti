import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://minio:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="46f14446fe9983cc8e77edcf854bcf523766003b737c2684",
)

res = s3.list_objects_v2(Bucket="voice-audio")
print("Objects matching 148:")
for o in res.get("Contents", []):
    if "148" in o["Key"]:
        print(" ", o["Key"], f"({o['Size']} bytes)")
