# Markdown to Confluence

This script converts Markdown files to Confluence pages and uploads them to a specified Confluence space. It also handles image uploads and converts Markdown links and headings to Confluence format.

## Features

- Converts Markdown files to Confluence pages.
- Handles image uploads.
- Converts Markdown links and headings to Confluence format.
- Supports nested folders by creating parent pages for each folder.
- Takes #tags and adds as confluence labels.

## Prerequisites

- Python 3.x
- `requests` library
- `python-dotenv` library

## Setup

1. Clone the repository:
    ```bash
    git clone https://github.com/DipFlip/markdown-to-confluence.git
    cd markdown-to-confluence
    ```

2. Install the required Python libraries:
    ```bash
    pip install -r requirements.txt
    ```

3. Create a `.env` file in the root directory of the project and add the following environment variables:
    ```env
    BASE_URL=http://localhost:8090
    CONFLUENCE_USERNAME=your_username
    CONFLUENCE_PASSWORD=your_password
    SPACE_KEY=NAMEOFSPACE
    BASE_DIR=/abssolute/path/to/your/wiki/content
    IMAGE_DIR=relative/from/base_dir/to/image/dir
    ```

4. Ensure your Confluence instance is running and accessible at the `BASE_URL` specified in the `.env` file.

## Usage

1. To convert and upload all Markdown files in the specified `BASE_DIR`, run:
    ```bash
    python markdown-to-confluence.py
    ```

2. To convert and upload a specific Markdown file, provide the relative path to the file as an argument:
    ```bash
    python markdown-to-confluence.py path/to/your/file.md
    ```

## Notes

- The script will create parent pages for each folder in the `BASE_DIR` and add the Markdown files as child pages.
- The script removes YAML front matter and lines containing `--------------TAGS-----------------` from the Markdown files before conversion.
- Ensure that the `BASE_DIR` and `IMAGE_DIR` paths in the `.env` file are correct and accessible.

## Contributing

Feel free to submit issues or pull requests if you have any improvements or bug fixes.

## License

This project is licensed under the MIT License.
