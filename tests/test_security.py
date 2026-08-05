from __future__ import annotations

import unittest

from agent_memory.security import find_sensitive_content


class SecurityScannerTests(unittest.TestCase):
    def test_detects_common_secret_values(self) -> None:
        content = "password=not-a-real-test-secret\nAuthorization: Bearer fake-test-token-value"

        findings = find_sensitive_content(content)

        self.assertEqual([finding.label for finding in findings], ["secret assignment", "authorization bearer token"])
        self.assertEqual([finding.line_number for finding in findings], [1, 2])

    def test_allows_policy_text_without_values(self) -> None:
        content = "Do not store passwords, API keys, access tokens, private keys, or protected personal data."

        self.assertEqual(find_sensitive_content(content), [])


if __name__ == "__main__":
    unittest.main()
