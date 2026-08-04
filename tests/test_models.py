from __future__ import annotations

import unittest

from agent_memory.models import content_sha256, normalize_content, normalize_tags, serialize_tags


class ModelHelperTests(unittest.TestCase):
    def test_tag_normalization_is_deterministic(self) -> None:
        tags = normalize_tags(("QueryDSL", " jpa ", "DTO", "querydsl", ""))

        self.assertEqual(tags, ("dto", "jpa", "querydsl"))
        self.assertEqual(serialize_tags(tags), "dto,jpa,querydsl")

    def test_comma_separated_tags_are_split_safely(self) -> None:
        self.assertEqual(normalize_tags(("one,two", "Two", " three ")), ("one", "three", "two"))

    def test_content_hash_normalizes_line_endings(self) -> None:
        self.assertEqual(normalize_content("one\r\ntwo\rthree"), "one\ntwo\nthree")
        self.assertEqual(content_sha256("one\r\ntwo"), content_sha256("one\ntwo"))


if __name__ == "__main__":
    unittest.main()
