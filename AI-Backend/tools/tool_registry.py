from tools.calculator import calculator
from tools.file_tools import read_text_file
from tools.data_tools import analyze_dataset
from tools.document_tool import create_docx
from tools.excel_tool import create_excel
from tools.pptx_tool import create_pptx
from tools.pdf_tool import create_pdf
# from tools.image_tool import analyze_image
from tools.rag_tool import search_knowledge_base
from tools.index_tool import index_document


TOOLS = [
    calculator,
    index_document,
    read_text_file,
    search_knowledge_base,
    analyze_dataset,
    create_docx,
    create_excel,
    create_pptx,
    create_pdf
]