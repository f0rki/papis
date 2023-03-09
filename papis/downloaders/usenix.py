import re
from urllib.parse import urlparse
from typing import Optional

import papis.downloaders.base


class Downloader(papis.downloaders.Downloader):

    def __init__(self, url: str):
        papis.downloaders.Downloader.__init__(self, url, name="usenix")
        self.expected_document_extension = 'pdf'
        self._raw_data : Optional[str] = None

    @classmethod
    def match(cls, url: str) -> Optional[papis.downloaders.Downloader]:
        if re.match(r".*usenix.org/.*", url):
            return Downloader(url)
        else:
            return None

    def get_identifier(self) -> Optional[str]:
        """
        >>> d = Downloader("https://www.usenix.org/conference/usenixsecurity22/presentation/bulekov")
        >>> d.get_identifier()
        'usenixsecurity22-bulekov'
        >>> d = Downloader("https://www.usenix.org/conference/nsdi23/presentation/liu-tianfeng")
        >>> d.get_identifier()
        'nsdi23-liu-tianfeng'
        """
        o = urlparse(self.uri)
        path = o.path
        path_components = list(path.split("/"))
        if len(path_components) < 4:
            return None
        return path_components[1] + "-" + path_components[3]

    def get_document_url(self) -> Optional[str]:
        """
        >>> d = Downloader("https://www.usenix.org/conference/usenixsecurity22/presentation/bulekov")
        >>> d.get_document_url()
        'https://www.usenix.org/system/files/sec22-bulekov.pdf'
        >>> d = Downloader("https://www.usenix.org/conference/nsdi23/presentation/liu-tianfeng")
        >>> d.get_document_url()
        None
        """

        import bs4

        if not self._raw_data:
            self._raw_data = self.session.get(self.uri).content.decode('utf-8')
        soup = bs4.BeautifulSoup(self._raw_data, "html.parser")
        a = list(filter(
            lambda t: t.get("name", "") == 'citation_pdf_url' and t.get("content", "").endswith(self.expected_document_extension),
            soup.find_all('meta')
        ))

        if not a:
            self.logger.warn('No citation_pdf_url url in this usenix page')
            return None

        return str(a[0])

    def get_bibtex_url(self) -> Optional[str]:
        """
        >>> d = Downloader("https://www.usenix.org/conference/usenixsecurity22/presentation/bulekov")
        >>> d.get_document_url()
        'https://www.usenix.org/system/files/sec22-bulekov.pdf'
        >>> d.get_bibtex_url()
        'https://www.usenix.org/biblio/export/bibtex/277148'
        """
        o = urlparse(self.uri)
        import bs4

        if not self._raw_data:
            self._raw_data = self.session.get(self.uri).content.decode('utf-8')
        soup = bs4.BeautifulSoup(self._raw_data, "html.parser")

        a = list(filter(
            lambda t: re.match(r'/biblio/export/bibtex/([0-9]+)$', t.get('href', '')),
            soup.find_all('a')
        ))

        if not a:
            self.logger.warn('No bibtex export url in this usenix page')
            return None

        bib_path = a[0]
        return str(o._replace(path=bib_path))
