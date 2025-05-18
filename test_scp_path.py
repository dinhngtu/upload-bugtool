import unittest

import importlib

upload_bugtool = importlib.import_module("upload-bugtool")
parse_user_host_path = upload_bugtool.parse_user_host_path

# Ported from openssh test_parse.c


class TestParseFunctions(unittest.TestCase):
    def test_misc_parse_user_host_path(self):
        user, host, path = parse_user_host_path("someuser@some.host:some/path")
        self.assertEqual(user, "someuser")
        self.assertEqual(host, "some.host")
        self.assertEqual(path, "some/path")

    def test_misc_parse_user_ipv4_path(self):
        user, host, path = parse_user_host_path("someuser@1.22.33.144:some/path")
        self.assertEqual(user, "someuser")
        self.assertEqual(host, "1.22.33.144")
        self.assertEqual(path, "some/path")

    def test_misc_parse_user_ipv4_bracketed_path(self):
        user, host, path = parse_user_host_path("someuser@[1.22.33.144]:some/path")
        self.assertEqual(user, "someuser")
        self.assertEqual(host, "1.22.33.144")
        self.assertEqual(path, "some/path")

    def test_misc_parse_user_ipv4_bracketed_nopath(self):
        user, host, path = parse_user_host_path("someuser@[1.22.33.144]:")
        self.assertEqual(user, "someuser")
        self.assertEqual(host, "1.22.33.144")
        self.assertEqual(path, ".")

    def test_misc_parse_user_ipv6_path(self):
        user, host, path = parse_user_host_path("someuser@[::1]:some/path")
        self.assertEqual(user, "someuser")
        self.assertEqual(host, "::1")
        self.assertEqual(path, "some/path")


if __name__ == "__main__":
    unittest.main()
