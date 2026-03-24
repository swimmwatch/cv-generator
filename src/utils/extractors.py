import abc
from io import BytesIO

import docx
import pymupdf


class TextExtractor(abc.ABC):
    @abc.abstractmethod
    def extract(self, file_data: bytes) -> str:
        raise NotImplementedError


class PdfTextExtractor(TextExtractor):
    def extract(self, file_data: bytes) -> str:
        text_parts: list[str] = []
        with pymupdf.open(stream=file_data, filetype="pdf") as doc:
            for page in doc:
                text_parts.append(page.get_text())

        return "\n\n".join(text_parts).strip()


class DocxTextExtractor(TextExtractor):
    def extract(self, file_data: bytes) -> str:
        doc = docx.Document(BytesIO(file_data))
        text_parts = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
        return "\n\n".join(text_parts).strip()


EXTRACTORS: dict[str, TextExtractor] = {
    ".pdf": PdfTextExtractor(),
    ".doc": DocxTextExtractor(),
    ".docx": DocxTextExtractor(),
}


class TextExtractorFactory:
    _extractors: dict[str, TextExtractor] = EXTRACTORS

    @classmethod
    def get(cls, file_name: str) -> TextExtractor:
        ext = ""
        if "." in file_name:
            ext = "." + file_name.rsplit(".", 1)[-1].lower()

        extractor = cls._extractors.get(ext)
        if extractor is None:
            msg = f"Unsupported file extension: {ext}"
            raise ValueError(msg)

        return extractor
