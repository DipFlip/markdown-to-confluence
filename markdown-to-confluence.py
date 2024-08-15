import requests
import json
import re
import os
import mimetypes
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse

def read_markdown_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read()

def convert_markdown_to_confluence(markdown_content, base_url, space_key):
    # Convert [[Page Name]] to [Page Name]
    content = re.sub(r'\[\[(.*?)\]\]', lambda m: f'[{m.group(1)}|{base_url}/display/{space_key}/{m.group(1).replace(" ", "+")}]', markdown_content)
    
    # Convert [[Page Name|Display Text]] to [Display Text|Page Name]
    content = re.sub(r'\[\[(.*?)\|(.*?)\]\]', lambda m: f'[{m.group(2)}|{base_url}/display/{space_key}/{m.group(1).replace(" ", "+")}]', content)
    
    # Convert numbered lists
    content = re.sub(r'^\d+\.\s', '# ', content, flags=re.MULTILINE)
    
    # Convert links (but not image links)
    content = re.sub(r'\[([^\]!]+)\]\(([^)]+)\)', r'[\1|\2]', content)
    
    # Convert image links
    content = re.sub(r'!\[\[([^\]]+)\]\]', lambda m: f'!{m.group(1)}!', content)
    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', lambda m: f'!{m.group(2)}|alt={m.group(1)}!', content)
    
    return content

def upload_image(base_url, auth, space_key, page_id, image_path):
    api_endpoint = f"{base_url}/rest/api/content/{page_id}/child/attachment"
    
    image_filename = os.path.basename(image_path)
    mime_type, _ = mimetypes.guess_type(image_path)
    
    with open(image_path, 'rb') as file:
        files = {'file': (image_filename, file, mime_type)}
        data = {'minorEdit': 'true'}
        
        response = requests.post(
            api_endpoint,
            auth=auth,
            files=files,
            data=data,
            headers={'X-Atlassian-Token': 'no-check'}
        )
        
    if response.status_code == 200:
        print(f"Successfully uploaded {image_filename}")
        return True
    else:
        print(f"Failed to upload {image_filename}. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def create_confluence_page(base_url, username, password, space_key, title, content, image_dir):
    auth = HTTPBasicAuth(username, password)
    api_endpoint = f"{base_url}/rest/api/content"

    page_data = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": content,
                "representation": "wiki"
            }
        }
    }

    try:
        response = requests.post(
            api_endpoint,
            auth=auth,
            headers={"Content-Type": "application/json"},
            data=json.dumps(page_data),
            verify=False  # Only use this for testing with self-signed certificates
        )

        response.raise_for_status()

        print("Page created successfully!")
        page_id = response.json()['id']
        page_url = f"{base_url}/pages/viewpage.action?pageId={page_id}"
        print(f"View the page at: {page_url}")

        # Upload images
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)|!\[\[([^\]]+)\]\]'
        for match in re.finditer(image_pattern, content):
            image_filename = match.group(2) or match.group(3)
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

# Confluence details
base_url = "http://localhost:8090"
username = "admin"
password = "your_password"  # Replace with your actual password
space_key = "TEST"

# Markdown file and image directory
base_dir = "/home/emil/repos/anp-wiki/content"
markdown_file = "Folder/Polaris-LAMP.md"  # Replace with your actual filename
image_dir = os.path.join(base_dir, "Images")

# Read and process the Markdown file
markdown_content = read_markdown_file(os.path.join(base_dir, markdown_file))
confluence_content = convert_markdown_to_confluence(markdown_content, base_url, space_key)

# Use the filename (without .md) as the title
title = os.path.splitext(os.path.basename(markdown_file))[0]

# Create the Confluence page and upload images
create_confluence_page(base_url, username, password, space_key, title, confluence_content, image_dir, base_dir)