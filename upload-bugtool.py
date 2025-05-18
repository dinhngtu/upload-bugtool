#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import getpass
import os
import shutil
import subprocess
import sys
import tempfile

try:
    import urllib.parse as urlparse
    from urllib.parse import quote as urlquote
except ImportError:
    import urlparse
    from urllib import quote as urlquote

try:
    xrange
except NameError:
    xrange = range


# Ported from openssh misc.c


def cleanhostname(host):
    if host.startswith("[") and host.endswith("]"):
        return host[1:-1]
    return host


def colon(s):
    if not s:
        return None
    if s[0] == ":":
        return None
    flag = 0
    if s[0] == "[":
        flag = 1
    for i in xrange(len(s)):
        if s[i] == "@" and i + 1 < len(s) and s[i + 1] == "[":
            flag = 1
        elif s[i] == "]":
            if i + 1 < len(s) and s[i + 1] == ":" and flag:
                return i + 1
        elif s[i] == ":":
            if not flag:
                return i
        elif s[i] == "/":
            return None
    return None


def parse_user_host_path(s):
    colon_pos = colon(s)
    if colon_pos is None:
        raise ValueError("invalid SCP path")
    host_part = s[:colon_pos]
    path_part = s[colon_pos + 1 :]
    # if not path_part:
    # path_part = "."
    at_pos = host_part.rfind("@")
    if at_pos != -1:
        user_candidate = host_part[:at_pos]
        host_candidate = host_part[at_pos + 1 :]
        user = user_candidate if user_candidate else None
    else:
        user = None
        host_candidate = host_part
    host = cleanhostname(host_candidate)
    return (user, host, path_part)


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


def upload(*, base_url, folder_token, password, file, scp=False, tmpdir=None):
    if scp:
        assert tmpdir is not None
        print("Downloading %s" % file, file=sys.stderr)
        subprocess.check_call(
            ["scp", file, tmpdir], stdout=sys.stdout, stderr=sys.stderr
        )

        if "://" in file:
            scp_uri = urlparse.urlparse(file)
            scp_path = scp_uri.path
        else:
            (_, _, scp_path) = parse_user_host_path(file)
        if scp_path is None:
            raise ValueError("invalid SCP path")

        file = os.path.join(tmpdir, os.path.basename(scp_path))
        if not os.path.exists(file):
            raise FileNotFoundError("scp failed to download the file.")

    print("Uploading %s" % file, file=sys.stderr)

    upload_filename = urlquote(os.path.basename(file))
    target_url = "%s/public.php/webdav/%s" % (base_url, upload_filename)
    cred = "%s:%s" % (folder_token, password)

    curl_args = [
        "curl",
        "-S",
        "-f",
        "-T",
        file,
        "-u",
        cred,
        "-H",
        "X-Requested-With: XMLHttpRequest",
        target_url,
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


def main():
    parser = argparse.ArgumentParser(
        description="Uploads a file to a Nextcloud/Owncloud shared drop folder."
    )
    parser.add_argument(
        "-p", action="store_true", help="Prompt for password for the share link."
    )
    parser.add_argument(
        "--scp", action="store_true", help="Treat input file paths as SCP locations."
    )
    parser.add_argument("share_link", help="The Nextcloud/Owncloud share link URL.")
    parser.add_argument("files", nargs="+", help="Files to upload.")

    args = parser.parse_args()

    if not args.scp and any(
        "://" in file and not os.path.exists(file) for file in args.files
    ):
        print(
            "Error: Given file path looks like a URL and does not exist locally, did you mix up the syntax or forget --scp?",
            file=sys.stderr,
        )
        sys.exit(1)

    password = ""
    if args.p:
        if sys.stdin.isatty():
            password = getpass.getpass("Enter password for share link: ")
        else:
            print(
                "Error: Cannot prompt for password when not on a TTY.", file=sys.stderr
            )
            sys.exit(1)

    base_url, folder_token = parse_share_link(args.share_link)

    tmpdir = None
    if args.scp:
        tmpdir = tempfile.mkdtemp()

    try:
        for file in args.files:
            upload(
                base_url=base_url,
                folder_token=folder_token,
                password=password,
                file=file,
                scp=args.scp,
                tmpdir=tmpdir,
            )
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    main()
