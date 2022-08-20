import shutil
from processing import handle_event, read_output
from utilities import calculate_age


def validate_input(min_age, max_age):
    if min_age >= 0 and min_age <= max_age and max_age <= 150:
        return (min_age, max_age)
    else:
        return False


# reads the DB and returns the filtered data in JSON format
def get_data(client, dest_bucket, tmp_dir, out_file, fieldnames, min_age, max_age, is_image_exists, stats=False):
    """
    Collects info from output file on GET request to /data and /stats endpoints.
    Downloads the output file, creates a list of dicts, filters the records.
    Creates a new list of filtered records for /data requests.
    And a list of user age records for /stats requests. 
    """
    # download output file from the bucket
    try:
        client.fget_object(dest_bucket, out_file, tmp_dir + out_file)
    except Exception as e:
        print(e)
    # read the output file into temp DB
    temp_db = read_output(tmp_dir, out_file, fieldnames)
    # remove temp dir
    try:
        shutil.rmtree(tmp_dir)
    except Exception as e:
        print(e)
    res = []
    ages = []
    # if age within the range check if img="on" and img_path is empty str
    for entry in temp_db:
        # age will be returned to calculate average age if stats=True
        if entry["birthts"]:
            age = calculate_age(entry["birthts"])
            if age >= min_age and age <= max_age:
                if is_image_exists == "on" and not entry["img_path"]: 
                    continue
                else:
                    ages.append(age)
                    res.append(entry)
    if stats:
        return ages
    return res


def handle_webhook(client, paths, out_file, fieldnames, key, content_type, event):
    """
    On POST requests to /webhook endpoint runs the event handler.
    On S3 Put, Post, Copy events runs the handler for the Edit event. 
    On S3 Delete event runs the handler for the Remove event. 
    """
    # modify the existing record in the output csv
    if event == "Put" or event == "Post" or event == "Copy":
        handle_event(
            client=client,
            paths=paths,
            out_file=out_file,
            fieldnames=fieldnames,
            key=key,
            content_type=content_type,
            event="edit")
    # remove the existing record from the output csv
    elif event == "Delete":
        handle_event(
            client=client,
            paths=paths,
            out_file=out_file,
            fieldnames=fieldnames,
            key=key,
            content_type=content_type,
            event="remove")