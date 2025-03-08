import os

def get_created_files_dir():
    """Get the path to the Created Files directory."""
    # Get the absolute path to the project root directory
    # The file_creation.py is in the project root, so we just need the directory of this file
    project_root = os.path.dirname(os.path.abspath(__file__))
    created_files_dir = os.path.join(project_root, "Created Files")
    os.makedirs(created_files_dir, exist_ok=True)
    return created_files_dir

def create_text_file(content, filename):
    """Create a plain text file with the given content"""
    try:
        # If filename is not an absolute path, place it in the Created Files directory
        if not os.path.isabs(filename):
            created_files_dir = get_created_files_dir()
            filename = os.path.join(created_files_dir, filename)
        
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, f"Created text file: {filename}"
    except Exception as e:
        return False, f"Error creating text file: {str(e)}"

def create_csv_file(content, filename):
    """Create a CSV file with the given content"""
    try:
        # If filename is not an absolute path, place it in the Created Files directory
        if not os.path.isabs(filename):
            created_files_dir = get_created_files_dir()
            filename = os.path.join(created_files_dir, filename)
        
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, f"Created CSV file: {filename}"
    except Exception as e:
        return False, f"Error creating CSV file: {str(e)}"

def create_docx_file(content, filename):
    """Create a Word document with the given content"""
    try:
        # If filename is not an absolute path, place it in the Created Files directory
        if not os.path.isabs(filename):
            created_files_dir = get_created_files_dir()
            filename = os.path.join(created_files_dir, filename)
        
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        import docx
        doc = docx.Document()
        
        # Split content by double newlines to create paragraphs
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                doc.add_paragraph(para)
                
        doc.save(filename)
        return True, f"Created Word document: {filename}"
    except ImportError:
        return False, "python-docx library not installed. Install with: pip install python-docx"
    except Exception as e:
        return False, f"Error creating Word document: {str(e)}"

def create_excel_file(content, filename):
    """Create an Excel file with the given content"""
    try:
        # If filename is not an absolute path, place it in the Created Files directory
        if not os.path.isabs(filename):
            created_files_dir = get_created_files_dir()
            filename = os.path.join(created_files_dir, filename)
        
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        import pandas as pd
        import io
        
        # Try to parse the content as CSV data
        csv_data = io.StringIO(content)
        # Use on_bad_lines instead of error_bad_lines (which is deprecated)
        df = pd.read_csv(csv_data, sep=',', on_bad_lines='skip')
        
        # Save as Excel file
        if filename.endswith('.xlsx'):
            df.to_excel(filename, index=False, engine='openpyxl')
        else:  # .xls
            df.to_excel(filename, index=False, engine='xlwt')
            
        return True, f"Created Excel file: {filename}"
    except ImportError:
        return False, "pandas or openpyxl library not installed. Install with: pip install pandas openpyxl xlwt"
    except Exception as e:
        return False, f"Error creating Excel file: {str(e)}"

def create_pdf_file(content, filename):
    """Create a PDF file with the given content"""
    try:
        # If filename is not an absolute path, place it in the Created Files directory
        if not os.path.isabs(filename):
            created_files_dir = get_created_files_dir()
            filename = os.path.join(created_files_dir, filename)
        
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        from weasyprint import HTML
        import tempfile
        
        # Convert content to HTML
        html_content = f"<html><body><pre>{content}</pre></body></html>"
        
        # Create PDF using WeasyPrint
        HTML(string=html_content).write_pdf(filename)
        return True, f"Created PDF file: {filename}"
    except ImportError:
        return False, "weasyprint library not installed. Install with: pip install weasyprint"
    except Exception as e:
        return False, f"Error creating PDF file: {str(e)}"

def create_file(content, filename):
    """Create a file with the given content based on file extension"""
    # Ensure the filename has an extension
    if '.' not in filename:
        return False, "Filename must have an extension (e.g., .txt, .docx, .xlsx, .pdf)"
    
    # Get the file extension
    ext = filename.lower().split('.')[-1]
    
    # Create the file based on extension
    if ext == 'txt':
        return create_text_file(content, filename)
    elif ext == 'csv':
        return create_csv_file(content, filename)
    elif ext in ['doc', 'docx']:
        return create_docx_file(content, filename)
    elif ext in ['xls', 'xlsx']:
        return create_excel_file(content, filename)
    elif ext == 'pdf':
        return create_pdf_file(content, filename)
    else:
        return False, f"Unsupported file extension: .{ext}"
