import os
from datetime import datetime
from statistics import mean


def is_bucket_empty(client, bucket):
    """
    Checks if provided bucket contains objects.
    """
    try:
        objects = client.list_objects(bucket)
        try:
            next(objects)
        except StopIteration:
            return True
    except Exception as e:
        print(e)
    return False


def upload(client, src_dir, bucket):
    """
    Uploads contents of local directory to MinIO bucket.
    """
    try:
        files = os.listdir(src_dir)
        # create a new bucket
        if not client.bucket_exists(bucket):
            try:
                client.make_bucket(bucket)
            except Exception as e:
                print(e)
        # upload files from a local dir to a bucket
        if files:
            for src_file in files:
                src_file_path = src_dir + src_file
                try:
                    client.fput_object(bucket, src_file, src_file_path)
                    print(f"{src_file} successfully uploaded to {bucket}")
                except Exception as e:
                    print(e)
        else:
            print(f"{src_dir} directory is empty")
    except Exception as e:
        print(e)

def download(client, src_bucket, tmp_dir):
    """
    Downloads contents MinIO bucket to local directory.
    """
    try:
        objects = client.list_objects(src_bucket, recursive=True)
        for object in objects:
            filename = object.object_name.encode("utf-8").__str__()
            filename = filename[2:-1]
            file_path = f"{tmp_dir}{filename}"
            try:
                client.fget_object(src_bucket, object.object_name.encode("utf-8"), file_path)
            except Exception as e:
                print(e)
    except Exception as e:
        print(e)


# timestamp is divided by 1000
def calculate_age(timestamp):
    now = datetime.now()
    birthdate = datetime.fromtimestamp(int(timestamp) / 1000)
    diff = now - birthdate
    return (round(diff.days / 365))


# data is a filtered list of numbers
def calculate_mean_age(data):
    return (round(mean(data)))