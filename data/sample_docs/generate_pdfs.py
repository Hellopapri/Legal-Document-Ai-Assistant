import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

def create_ai_assessment(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    content = []
    content.append(Paragraph("AI Engineer - Assessment", styles['Title']))
    content.append(Spacer(1, 12))
    
    text = ("This document outlines the assessment and requirements for the AI Engineer position. "
            "The candidate should possess strong skills in Python, Machine Learning, and Large Language Models. "
            "Key responsibilities include developing and deploying scalable AI solutions, optimizing model performance, "
            "and staying updated with the latest research in the field. Evaluation will be based on technical proficiency, "
            "problem-solving abilities, and communication skills. The role requires experience with frameworks such as "
            "PyTorch or TensorFlow, and exposure to vector databases and RAG architectures is highly desirable. "
            "Candidates will be tested on their ability to design robust data pipelines and their understanding of "
            "model evaluation metrics.")
    
    content.append(Paragraph(text * 5, styles['Normal'])) # Multiplied to ensure substantial content
    doc.build(content)

def create_legal_notice(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    content = []
    
    legal_text = ("This is a formal legal notice. Please be advised that the following terms and conditions apply "
                  "to the use of the services provided by this entity. Failure to comply with these terms may result "
                  "in legal action. The user agrees to indemnify and hold harmless the provider from any claims arising "
                  "from misuse of the information provided herein. This document serves as a standard multi-page "
                  "extraction test file. Legal documents often contain dense text and specific formatting requirements. "
                  "Accuracy in data extraction is critical for compliance and risk management. "
                  "This section is repeated to ensure the document spans at least five pages for testing purposes. " * 4)

    for i in range(1, 6):
        content.append(Paragraph(f"Legal Notice - Page {i}", styles['Heading1']))
        content.append(Spacer(1, 12))
        content.append(Paragraph(legal_text, styles['Normal']))
        content.append(PageBreak())
        
    doc.build(content)

if __name__ == "__main__":
    os.makedirs("data/sample_docs", exist_ok=True)
    create_ai_assessment("data/sample_docs/AI Engineer - Assessment.pdf")
    create_legal_notice("data/sample_docs/legal_sample_notice.pdf")
    print("PDFs generated successfully.")
