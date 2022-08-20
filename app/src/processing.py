import os
import re
import csv
import shutil
from utilities import upload, download


def get_paths(path):
    """
    Creates a list of paths to source files
    """
    files = os.listdir(path)
    files.sort()
    return files


def readline_csv(path, filename):
    """
    Reads user info from a csv file and returns it as a dict
    """
    entry = {}
    try:
        with open(path, "r") as csv_file:
            reader = csv.DictReader(csv_file, skipinitialspace=True)
            for line in reader:
                entry = {"user_id": filename, **line}
        return entry
    except Exception as e:
        print(e)


def aggregate(src_dir, src_bucket):
    """
    Creates a list of dicts from source files.
    [{user_id: {user_id:"", first_name:"", last_name:"", birthts:"", img_path:""}, ...}]
    """
    # get the paths of source files
    files = get_paths(src_dir)
    entry = {}
    temp_db = []
    for file in files:
        user_id, extension = os.path.splitext(file)
        if user_id not in entry:
            entry[user_id] = {}
        if extension == ".csv":
            # read user info from a csv file
            user_info = readline_csv(src_dir + "/" + user_id + extension, user_id)
            entry[user_id].update(user_info)
        elif re.match(r".png|.jpg|.jpeg|.gif", extension):
            # image path in the datalake 
            entry[user_id].update({"img_path": f"{src_bucket}/{user_id}{extension}"})
    temp_db = [v for v in entry.values()]
    return temp_db


def write_output(dest_dir, out_file, data, fieldnames):
    """
    Writes aggregated data to output file on disk
    """
    try:
        if not os.path.exists(os.path.dirname(dest_dir)):
            os.mkdir(os.path.dirname(dest_dir))
    except Exception as e:
        print(e)
    try:
        with open(dest_dir + out_file, "w") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    except Exception as e:
        print(e)


def read_output(tmp_dir, out_file, fieldnames):
    """
    Reads aggregated data from output file on disk
    """
    try:
        with open(f"{tmp_dir}{out_file}", "r") as csv_file:
            reader = csv.DictReader(csv_file, fieldnames)
            next(reader)
            temp_db = []
            for line in reader:
                temp_db.append(line)
        return temp_db
    except Exception as e:
        print(e)


def handle_edit(entry, data, content_type):
    """
    Modifies an existing record or adds an image path to a record 
    """
    if content_type == "text/csv":
        entry.update(
            first_name=data["first_name"],
            last_name=data["last_name"],
            birthts=data["birthts"])
    elif content_type == "image/png":
            entry.update(img_path=data["img_path"])


def handle_remove(temp_db, entry, content_type):
    """
    Removes user info or the image path of an existing record.
    If no file with the ID is left, the record is removed completely.
    """
    if content_type == "csv":
        if entry["img_path"]:
            entry.pop("first_name", "No such key")
            entry.pop("last_name", "No such key")
            entry.pop("birthts", "No such key")
        else:
            temp_db.remove(entry)
    elif content_type == "png":
        if entry["first_name"]:
            entry.pop("img_path")
        else:
            temp_db.remove(entry)
    else:
        temp_db.remove(entry)


def handle_new_record(temp_db, data, content_type):
    """
    Appends a new record containing user info or image path.
    """
    new_entry = {}
    if content_type == "text/csv":
        new_entry = {
            "user_id": data["user_id"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "birthts": data["birthts"]
        }
    elif content_type == "image/png":
        new_entry = {"user_id": data["user_id"], "img_path": data["img_path"]}
    temp_db.append(new_entry)


def modify(data, tmp_dir, out_file, fieldnames, content_type, event):
    """
    Calls handlers based on an event and modifies the output file.
    Updates user info or image path.
    Removes fields from the record or removes the whole record.
    Creates a new record if user ID is not found.
    """
    temp_db = read_output(tmp_dir, out_file, fieldnames)
    try:
        for entry in temp_db:
            if entry["user_id"] == data["user_id"]:
                if event == "remove":
                    handle_remove(temp_db, entry, content_type)
                elif event == "edit":
                    handle_edit(entry, data, content_type)
                break
        else:
            handle_new_record(temp_db, data, content_type)
    except Exception as e:
        temp_db = {}
        print(e)
    return temp_db


def handle_event(client, paths=[], out_file="output.csv", fieldnames=[], key=None, content_type="text/csv", event="update"):
    """
    Downloads the necessary files, process or modify them, writes a new file and uploads it to a bucket.
    On Update button click: loads the files from the datalake into a temp dir and aggregates them into a list of dicts.
    For other events prepares necessary data and downloads the output file.
    On Edit event: downloads the source file to be merged with the output file.
    Prepares the necessary info and gets a processed list of dicts to be written to output file.
    On Remove event: passes the filetype and user_id of the record to remove the fields from.
    Gets back a list of dicts with removed data.
    For ALL events: writes the processed db to the output file and uploads it to its bucket. 
    """ 
    dest_dir, src_bucket, dest_bucket, tmp_dir = paths
    processed = ""
    data = {}
    extension = ""

    if event == "update":
        # download all source files to temp dir
        download(client, src_bucket, tmp_dir)
        # aggregate files and get the temp db with all records
        processed = aggregate(tmp_dir, src_bucket)
    else:
        obj_path = key.rsplit("/", 1)
        src_bucket = obj_path[0]
        obj_name = obj_path[1]
        user_id, extension = obj_name.split(".")
        # download output file to temp dir
        try:
            client.fget_object(dest_bucket, out_file, tmp_dir + out_file)
        except Exception as e:
            print("output file:", e)

        if event == "edit":
            # download new or updated source file to temp dir
            try:
                client.fget_object(src_bucket, obj_name, tmp_dir + obj_name)
            except Exception as e:
                print("source files:", e)
            # data contains user info
            if content_type == "text/csv":
                data = readline_csv(tmp_dir + obj_name, user_id)
            elif content_type == "image/png":
                data = {"user_id": user_id, "img_path": src_bucket + "/" + obj_name}
            # append the new or update the existing record
            processed = modify(data, tmp_dir, out_file, fieldnames, content_type, event)
        elif event == "remove":
            data = {"user_id": user_id}
            # extension as content_type
            processed = modify(data, tmp_dir, out_file, fieldnames, extension, event)

    # write processed db to disk
    write_output(dest_dir, out_file, processed, fieldnames)
    # upload output file to processed_data bucket
    upload(client, dest_dir, dest_bucket)
    # remove temporary directories
    try:
        shutil.rmtree(tmp_dir)
    except Exception as e:
        print(e)
    try:
        shutil.rmtree(dest_dir)
    except Exception as e:
        print(e)


