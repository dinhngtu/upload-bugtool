#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import sys
import os
import subprocess
import getpass

try:
    import urllib.parse as urlparse
    from urllib.parse import quote as urlquote
except ImportError:
    import urlparse
    from urllib import quote as urlquote


def parse_share_link(share_link):
    """
    Parses the Nextcloud/Owncloud share link to extract the base URL and token.
    Args:
        share_link (str): The share link URL.
    Returns:
        tuple: A tuple containing (base_url, token).
    """
    parsed_url = urlparse.urlparse(share_link)

    # Determine the base URL
    if parsed_url.path.endswith("/index.php/s/" + parsed_url.path.split("/")[-1]):
        base_url = share_link.replace(
            "/index.php/s/" + parsed_url.path.split("/")[-1], ""
        )
    elif parsed_url.path.endswith("/s/" + parsed_url.path.split("/")[-1]):
        base_url = share_link.replace("/s/" + parsed_url.path.split("/")[-1], "")
    else:
        raise ValueError(
            "Invalid share link format. Could not determine base URL from: %s"
            % share_link
        )

    # Extract the token from the path segment after /s/ or /index.php/s/
    path_segments = parsed_url.path.split("/")
    if "index.php" in path_segments:
        token_index = path_segments.index("index.php") + 2
    else:
        token_index = path_segments.index("s") + 1

    token = path_segments[token_index]

    # Clean up the base URL for potential query parameters
    base_url = urlparse.urlparse(base_url)._replace(query="", fragment="").geturl()

    return base_url, token


def main():
    parser = argparse.ArgumentParser(
        description="Uploads a file to a Nextcloud/Owncloud shared drop folder."
    )
    parser.add_argument(
        "-p",
        "--password",
        action="store_true",
        help="Prompt for password for the share link (if required).",
    )
    parser.add_argument("file_to_upload", help="The path to the file to upload.")
    parser.add_argument("share_link", help="The Nextcloud/Owncloud share link URL.")

    args = parser.parse_args()

    # Check if file exists
    if not os.path.exists(args.file_to_upload):
        print("Error: File not found: %s" % args.file_to_upload, file=sys.stderr)
        sys.exit(1)

    # Password Handling
    password_val = ""
    if args.password:
        if sys.stdin.isatty():
            password_val = getpass.getpass("Enter password for share link: ")
        else:
            print(
                "Error: Cannot prompt for password when not on a TTY.", file=sys.stderr
            )
            sys.exit(1)

    # Parse Share Link
    base_url, folder_token = parse_share_link(args.share_link)

    # Prepare for Upload
    upload_filename_original = os.path.basename(args.file_to_upload)
    # urlquote will handle spaces, hashes, and other special characters
    upload_filename_escaped = urlquote(upload_filename_original)

    # Construct the target URL
    target_url_path = "%s/public.php/webdav/%s" % (base_url, upload_filename_escaped)

    curl_user_cred = "%s:%s" % (folder_token, password_val)

    curl_args = [
        "curl",
        "-S",
        "-f",
        "-T",
        args.file_to_upload,
        "-u",
        curl_user_cred,
        "-H",
        "X-Requested-With: XMLHttpRequest",
        target_url_path,
    ]
    # hack: imply that we're running on 8.2 if using python2
    if sys.version_info[0] == 2:
        curl_args += [
            "--ciphers",
            "ECDHE-RSA-AES256-SHA384,ECDHE-RSA-AES256-GCM-SHA384,AES256-SHA256,AES128-SHA256,ECDHE-ECDSA-AES128-GCM-SHA256",
        ]

    try:
        subprocess.check_call(curl_args, stdout=sys.stdout, stderr=sys.stderr)
    except:
        print("curl failed, see output above.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
