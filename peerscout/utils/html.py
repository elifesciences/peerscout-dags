from html.parser import HTMLParser


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, data):
        self.fed.append(data)

    def get_data(self):
        return ''.join(self.fed)

    def error(self, message):
        raise message


def strip_tags(text: str) -> str:
    stripper = MLStripper()
    stripper.feed(text)
    return stripper.get_data()
