import json
import mimetypes
import os
import re
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# Load environment variables from .env file
load_dotenv()


def read_markdown_file(filename):
    with open(filename, "r", encoding="utf-8") as file:
        content = file.read()
        if content.startswith("---"):
            end_index = content.find("---", 3)
            if end_index != -1:
                content = content[end_index + 3 :].strip()
        # Remove the line '--------------TAGS-----------------'
        content = re.sub(
            r"^--------------TAGS-----------------\s*", "", content, flags=re.MULTILINE
        )
        return content


def convert_markdown_to_confluence(markdown_content, base_url, space_key):
    images_to_upload = []

    # Convert image links and store them in images_to_upload
    content = re.sub(
        r"(?:!\[.*?\])\((.*?)\)",
        lambda m: images_to_upload.append(m.group(1)) or f"!{m.group(1)}!",
        markdown_content,
    )
    content = re.sub(
        r"(?:!\[.*?\])\((.*?)\)", lambda m: f"!{m.group(1)}!", markdown_content
    )

    content = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f"!{m.group(2)}|alt={m.group(1)}!",
        content,
    )

    def process_page_name(page_name):
        return re.sub(r"[^\w\s()]", "", page_name).replace(" ", "+")

    # Convert [[Page Name|Display Text]] to [Display Text|Page Name]
    content = re.sub(
        r"\[\[(.*?)\|(.*?)\]\]",
        lambda m: f"[{m.group(2)}|{base_url}/display/{space_key}/{process_page_name(m.group(1))}]",
        content,
    )
    # Convert [[Page Name]] to [Page Name]
    content = re.sub(
        r"\[\[(.*?)\]\]",
        lambda m: f"[{m.group(1)}|{base_url}/display/{space_key}/{process_page_name(m.group(1))}]",
        content,
    )

    # Convert tags to labels
    labels = re.findall(r"#(\S+)", content)
    content = re.sub(r"#(\S+)", "", content)
    content = re.sub(r"^\d+\.\s", "# ", content, flags=re.MULTILINE)

    # Convert headings
    content = re.sub(r"^(#{7,})\s*(.*)", r"\2", content, flags=re.MULTILINE)
    content = re.sub(r"^(#{6})\s*(.*)", r"h6. \2", content, flags=re.MULTILINE)
    content = re.sub(r"^(#{5})\s*(.*)", r"h5. \2", content, flags=re.MULTILINE)
    content = re.sub(r"^(#{4})\s*(.*)", r"h4. \2", content, flags=re.MULTILINE)
    content = re.sub(r"^(#{3})\s*(.*)", r"h3. \2", content, flags=re.MULTILINE)
    content = re.sub(r"^(#{2})\s*(.*)", r"h2. \2", content, flags=re.MULTILINE)
    content = re.sub(r"^(#{1})\s*(.*)", r"h1. \2", content, flags=re.MULTILINE)

    # Convert links (but not image links)
    content = re.sub(r"\[([^\]!]+)\]\(([^)]+)\)", r"[\1|\2]", content)

    # Convert image links
    content = re.sub(r"!\[\[([^\]]+)\]\]", lambda m: f"!{m.group(1)}!", content)

    content = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f"!{m.group(2)}|alt={m.group(1)}!",
        content,
    )

    return content, images_to_upload, labels


def upload_image(base_url, auth, space_key, page_id, image_path):
    api_endpoint = f"{base_url}/rest/api/content/{page_id}/child/attachment"

    image_filename = os.path.basename(image_path)
    mime_type, _ = mimetypes.guess_type(image_path)

    # Check if the image already exists
    if isinstance(auth, HTTPBasicAuth):
        existing_attachments = requests.get(api_endpoint, auth=auth).json()
    elif isinstance(auth, str):
        existing_attachments = requests.get(
            api_endpoint, headers={"Authorization": "Bearer " + auth}
        ).json()
    else:
        raise Exception

    for attachment in existing_attachments.get("results", []):
        if attachment["title"] == image_filename:
            print(f"Image {image_filename} already exists. Skipping upload.")
            return True

    with open(image_path, "rb") as file:
        files = {"file": (image_filename, file, mime_type)}
        data = {"minorEdit": "true"}

        if isinstance(auth, HTTPBasicAuth):
            response = requests.post(
                api_endpoint,
                auth=auth,
                files=files,
                data=data,
                headers={"X-Atlassian-Token": "no-check"},
            )
        elif isinstance(auth, str):
            response = requests.post(
                api_endpoint,
                files=files,
                data=data,
                headers={
                    "Authorization": "Bearer " + auth,
                    "X-Atlassian-Token": "no-check",
                },
            )
        else:
            raise Exception

    if response.status_code == 200:
        print(f"Successfully uploaded {image_filename}")
        return True
    else:
        print(f"Failed to upload {image_filename}. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return False


def get_page_id(base_url, auth, space_key, title):
    api_endpoint = f"{base_url}/rest/api/content"
    params = {"type": "page", "spaceKey": space_key, "title": title}
    if isinstance(auth, HTTPBasicAuth):
        response = requests.get(api_endpoint, auth=auth, params=params)
    elif isinstance(auth, str):
        response = requests.get(
            api_endpoint, headers={"Authorization": "Bearer " + auth}, params=params
        )
    else:
        raise Exception
    if response.status_code == 200 and response.json()["results"]:
        return response.json()["results"][0]["id"]
    return None


def create_confluence_page(
    base_url,
    auth,
    space_key,
    title,
    content,
    image_dir,
    images_to_upload,
    labels,
    parent_id=None,
):
    api_endpoint = f"{base_url}/rest/api/content"

    page_data = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {"storage": {"value": content, "representation": "wiki"}},
    }

    if parent_id:
        page_data["ancestors"] = [{"id": parent_id}]

    try:
        # Check if the page already exists
        page_id = get_page_id(base_url, auth, space_key, title)
        if page_id:
            # Update the existing page
            api_endpoint = f"{base_url}/rest/api/content/{page_id}"
            # Fetch the current version number of the existing page
            if isinstance(auth, HTTPBasicAuth):
                version_response = requests.get(api_endpoint, auth=auth)
            elif isinstance(auth, str):
                version_response = requests.get(
                    api_endpoint, headers={"Authorization": "Bearer " + auth}
                )
            else:
                raise Exception
            version_response.raise_for_status()
            current_version = version_response.json()["version"]["number"]

            # Update the page with the new content
            page_data["version"] = {"number": current_version + 1}
            if isinstance(auth, HTTPBasicAuth):
                response = requests.put(
                    api_endpoint,
                    auth=auth,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(page_data),
                    verify=True,  # Only use this for testing with self-signed certificates
                )
            elif isinstance(auth, str):
                response = requests.put(
                    api_endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + auth,
                    },
                    data=json.dumps(page_data),
                    verify=True,  # Only use this for testing with self-signed certificates
                )
            else:
                raise Exception
            response.raise_for_status()
            print("Page updated successfully!")
        else:
            # Create a new page
            if isinstance(auth, HTTPBasicAuth):
                response = requests.post(
                    api_endpoint,
                    auth=auth,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(page_data),
                    verify=True,  # Only use this for testing with self-signed certificates
                )
            elif isinstance(auth, str):
                response = requests.post(
                    api_endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + auth,
                    },
                    data=json.dumps(page_data),
                    verify=True,  # Only use this for testing with self-signed certificates
                )
            else:
                raise Exception
            response.raise_for_status()
            print("Page created successfully!")
            page_id = response.json()["id"]

        # Add labels to the page
        if labels:
            label_endpoint = f"{base_url}/rest/api/content/{page_id}/label"
            label_data = [{"prefix": "global", "name": label} for label in labels]
            if isinstance(auth, HTTPBasicAuth):
                label_response = requests.post(
                    label_endpoint,
                    auth=auth,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(label_data),
                    verify=True,  # Only use this for testing with self-signed certificates
                )
            elif isinstance(auth, str):
                label_response = requests.post(
                    label_endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + auth,
                    },
                    data=json.dumps(label_data),
                    verify=True,  # Only use this for testing with self-signed certificates
                )
            else:
                raise Exception
            if label_response.status_code == 200:
                print("Labels added successfully!")
            else:
                print(
                    f"Failed to add labels. Status code: {label_response.status_code}"
                )
                print(f"Response: {label_response.text}")

        page_url = f"{base_url}/pages/viewpage.action?pageId={page_id}"
        print(f"View the page at: {page_url}")

        # Upload images from images_to_upload list
        for image_filename in images_to_upload:
            image_path = os.path.join(image_dir, image_filename)
            print(f"Trying to upload image: {image_path}")
            if os.path.exists(image_path):
                upload_image(base_url, auth, space_key, page_id, image_path)
            else:
                print(f"Warning: Image file not found: {image_path}")

    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error occurred: {err}")
        print(f"Response content: {err.response.content}")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred while making the request: {err}")
    except json.JSONDecodeError:
        print("Failed to parse the JSON response.")
        print(f"Response content: {response.text}")
    except Exception as err:
        print(f"An unexpected error occurred: {err}")


if __name__ == "__main__":
    import sys

    # Confluence details
    base_url = os.getenv("BASE_URL")
    username = os.getenv("CONFLUENCE_USERNAME")
    password = os.getenv("CONFLUENCE_PASSWORD")
    token = os.getenv("CONFLUENCE_TOKEN")
    space_key = os.getenv("SPACE_KEY")

    # Markdown file and image directory
    base_dir = os.getenv("BASE_DIR")
    image_dir = os.getenv("IMAGE_DIR")

    def find_markdown_files(base_dir):
        markdown_files = []
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith(".md"):
                    markdown_files.append(os.path.join(root, file))
        return markdown_files

    if len(sys.argv) > 1:
        # Process the specific file provided as an argument
        markdown_file = os.path.join(base_dir, sys.argv[1])
        markdown_files = [markdown_file]
    else:
        # Process all markdown files in the base_dir
        markdown_files = find_markdown_files(base_dir)

    for markdown_file in markdown_files:
        # Read and process the Markdown file
        markdown_content = read_markdown_file(markdown_file)
        confluence_content, images_to_upload, labels = convert_markdown_to_confluence(
            markdown_content, base_url, space_key
        )

        # Use the filename (without .md) as the title
        title = os.path.splitext(os.path.basename(markdown_file))[0]

        # Create the Confluence page and upload images
        if token != "":
            auth = token
        else:
            auth = HTTPBasicAuth(username, password)
        folder_name = os.path.dirname(markdown_file).replace(base_dir, "").strip("/")
        if folder_name:
            parent_id = get_page_id(base_url, auth, space_key, folder_name)
            if not parent_id:
                print(f"Creating parent page: {folder_name}")
                create_confluence_page(
                    base_url, auth, space_key, folder_name, "", image_dir, [], []
                )
                parent_id = get_page_id(base_url, auth, space_key, folder_name)
            create_confluence_page(
                base_url,
                auth,
                space_key,
                title,
                confluence_content,
                image_dir,
                images_to_upload,
                labels,
                parent_id,
            )
        else:
            create_confluence_page(
                base_url,
                auth,
                space_key,
                title,
                confluence_content,
                image_dir,
                images_to_upload,
                labels,
            )
