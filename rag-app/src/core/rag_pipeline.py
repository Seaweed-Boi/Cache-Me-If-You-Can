class RAGPipeline:
    def __init__(self, document_loader, retriever, generator):
        self.document_loader = document_loader
        self.retriever = retriever
        self.generator = generator

    def load_documents(self, file_path):
        documents = self.document_loader.load(file_path)
        self.index_documents(documents)

    def index_documents(self, documents):
        for doc in documents:
            self.retriever.index(doc)

    def query(self, user_query):
        relevant_docs = self.retriever.retrieve(user_query)
        response = self.generator.generate(relevant_docs, user_query)
        return response