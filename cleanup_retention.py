import sys
import os
sys.path.append("/app")

import asyncio
import asyncpg
import aioboto3

from api.constants import (
    DATABASE_URL,
    ENABLE_AWS_S3,
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
    S3_BUCKET,
    S3_ENDPOINT_URL,
    S3_REGION,
)

async def main():
    print("Starting 30-day retention cleanup...")
    
    # 1. Resolve DB URL
    db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    # 2. Query old runs
    try:
        rows = await conn.fetch(
            "SELECT id, recording_url, transcript_url FROM workflow_runs WHERE created_at < NOW() - INTERVAL '30 days'"
        )
        print(f"Found {len(rows)} runs older than 30 days.")
    except Exception as e:
        print(f"Error querying old runs: {e}")
        await conn.close()
        return

    if not rows:
        print("No old runs to clean up. Exiting.")
        await conn.close()
        return

    # 3. Resolve storage settings
    is_aws = ENABLE_AWS_S3
    if is_aws:
        bucket = S3_BUCKET
        endpoint_url = S3_ENDPOINT_URL
        region = S3_REGION
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    else:
        bucket = MINIO_BUCKET or "voice-audio"
        endpoint_url = MINIO_ENDPOINT
        if endpoint_url and not endpoint_url.startswith("http://") and not endpoint_url.startswith("https://"):
            endpoint_url = f"http://{endpoint_url}"
        region = "us-east-1"
        aws_access_key = MINIO_ACCESS_KEY
        aws_secret_key = MINIO_SECRET_KEY

    print(f"Using S3/MinIO bucket: {bucket} at {endpoint_url}")

    # 4. Perform S3 deletion
    session = aioboto3.Session()
    client_kwargs = {"region_name": region}
    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url
    if aws_access_key and aws_secret_key:
        client_kwargs["aws_access_key_id"] = aws_access_key
        client_kwargs["aws_secret_access_key"] = aws_secret_key

    run_ids = []
    async with session.client("s3", **client_kwargs) as s3_client:
        for row in rows:
            run_id = row["id"]
            rec_url = row["recording_url"]
            trans_url = row["transcript_url"]
            
            # Delete recording file
            if rec_url:
                try:
                    await s3_client.delete_object(Bucket=bucket, Key=rec_url)
                    print(f"Deleted recording from storage: {rec_url}")
                except Exception as e:
                    print(f"Error deleting recording {rec_url}: {e}")

            # Delete transcript file
            if trans_url:
                try:
                    await s3_client.delete_object(Bucket=bucket, Key=trans_url)
                    print(f"Deleted transcript from storage: {trans_url}")
                except Exception as e:
                    print(f"Error deleting transcript {trans_url}: {e}")

            run_ids.append(run_id)

    # 5. Delete DB records
    if run_ids:
        try:
            await conn.execute(
                "DELETE FROM workflow_runs WHERE id = ANY($1)",
                run_ids
            )
            print(f"Deleted {len(run_ids)} records from workflow_runs table.")
        except Exception as e:
            print(f"Error deleting database records: {e}")

    await conn.close()
    print("Cleanup completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
