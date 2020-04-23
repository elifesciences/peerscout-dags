from html.parser import HTMLParser


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.strict = False
        self.convert_charrefs = True
        self._collected_data = []

    def handle_data(self, data):
        self._collected_data.append(data)

    def get_data(self):
        return ''.join(self._collected_data)

    def error(self, message):
        # override ParserBase.error, which otherwise raises NotImplementedError
        raise message


def strip_tags(text: str) -> str:
    stripper = MLStripper()
    stripper.feed(text)
    return stripper.get_data()
