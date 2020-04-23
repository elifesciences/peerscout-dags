from peerscout.utils.html import (
    strip_tags
)


class TestStripTags:
    def test_strip_tags(self):
        assert strip_tags('<i>italic</i>') == 'italic'

    def test_resolve_char_refs(self):
        assert strip_tags('&gt;') == '>'
