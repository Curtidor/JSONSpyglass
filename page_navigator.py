from loaders.config_loader import ConfigLoader


class PageNavigator:
    def __init__(self, config: ConfigLoader):
        self.config = config
        self.page_nav_data = self.config.get_raw_page_nav()

        self.allowed_domains = []
        self.sleep_time = 0
        self.url_pattern = ""
        self.target_elements = []

    def __repr__(self):
        return f"PageNavigator(allowed_domains={self.allowed_domains}, " \
               f"sleep_time={self.sleep_time}, " \
               f"url_pattern={self.url_pattern}, " \
               f"target_elements={self.target_elements})"
