import unittest
from security import hash_password, verify_password


class PasswordTests(unittest.TestCase):
    def test_correct_and_wrong_password(self):
        value = hash_password('ТестPassword123')
        self.assertTrue(verify_password('ТестPassword123', value))
        self.assertFalse(verify_password('wrong', value))

    def test_unique_salt(self):
        self.assertNotEqual(hash_password('same12345'), hash_password('same12345'))

    def test_malformed_hash(self):
        for value in ('plaintext', 'pbkdf2_sha256$x$salt$digest',
                      'pbkdf2_sha256$999999999$salt$digest'):
            self.assertFalse(verify_password('anything', value))
