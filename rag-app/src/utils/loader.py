from pathlib import Path
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document


def load_documents(data_path: str) -> List[Document]:
    """
    Load PDF documents from a specified directory.
    
    Args:
        data_path: Path to the directory containing PDF files
        
    Returns:
        List of Document objects loaded from all PDF files in the directory
        
    Raises:
        FileNotFoundError: If the data_path does not exist
        ValueError: If the data_path is not a directory
    """
    path = Path(data_path)
    
    # Validate the path
    if not path.exists():
        raise FileNotFoundError(f"Data path does not exist: {data_path}")
    
    if not path.is_dir():
        raise ValueError(f"Data path is not a directory: {data_path}")
    
    documents = []
    
    # Find all PDF files in the directory
    pdf_files = list(path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"Warning: No PDF files found in {data_path}")
        return documents
    
    # Load each PDF file
    for pdf_file in pdf_files:
        try:
            print(f"Loading: {pdf_file.name}")
            loader = PyPDFLoader(str(pdf_file))
            docs = loader.load()
            documents.extend(docs)
            print(f"  Loaded {len(docs)} pages from {pdf_file.name}")
        except Exception as e:
            print(f"Error loading {pdf_file.name}: {str(e)}")
            continue
    
    print(f"\nTotal documents loaded: {len(documents)}")
    return documents
