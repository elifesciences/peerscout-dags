from html.parser import HTMLParser


class MarkupStrippingHtmlParser(HTMLParser):
    def __init__(self, convert_charrefs: bool = True):
        super().__init__(convert_charrefs=convert_charrefs)
        self._collected_data: list = []

    def handle_data(self, data):
        self._collected_data.append(data)

    def get_data(self):
        return ''.join(self._collected_data)

    def error(self, message):
        # override ParserBase.error, which otherwise raises NotImplementedError
        raise message


def strip_tags(text: str) -> str:
    stripper = MarkupStrippingHtmlParser()
    stripper.feed(text)
    return stripper.get_data()
