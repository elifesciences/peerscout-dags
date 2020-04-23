from peerscout.utils.html import (
    strip_tags
)


class TestStripTags:
    def test_strip_tags(self):
        assert strip_tags('<i>italic</i>') == 'italic'

    def test_resolve_char_refs(self):
        assert strip_tags('&gt;') == '>'

    def test_not_fail_on_unescaped_greater_sign(self):
        assert strip_tags('1 > 0') == '1 > 0'
