"""文档处理部分"""

from  langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentProcessing:

    def __init__(self,path,chunk_size,chunk_overlap):
        self.encoding = "utf-8"
        self.path = path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
    def text_processing(self):
        loader = TextLoader(self.path,encoding=self.encoding)

        texts = list(loader.lazy_load())

        splitter = RecursiveCharacterTextSplitter(
            chunk_size = self.chunk_size,
            chunk_overlap = self.chunk_overlap,
            separators = ["\n\n","\n",".","。","!","?","！","？"," ",""],
            length_function = len
        )

        split_docs = splitter.split_documents(texts)

        return split_docs

