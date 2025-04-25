# sybig-r-morph

## SyBig-r-Morph: Greek Pseudoword Generator Tool

A Flask-based web application that generates well-formed Greek pseudowords from real Greek syllables, using phonological constraints, lexical filters, and frequency data.

## Requirements
- Python 3.7+
- Install dependencies from requirements.txt (see below)

# Web Framework
Flask==2.3.3

# Data Processing
pandas==2.1.0
numpy==1.25.2

# String Comparison
jellyfish==1.0.0

# Greek Language Processing
greek-accentuation==1.2.0

# Excel File Support
openpyxl==3.1.2
xlrd==2.0.1

# WSGI Server (for production)
gunicorn==21.2.0

## Installation
1. Clone this repository:
git clone https://github.com/revith71/sybig-r-morph.git
cd sybig-r-morph

2. Create and activate a virtual environment:
python3 -m venv venv
source venv/bin/activate     # On Windows: venv\Scripts\activate

3. Install the required packages:
pip install -r requirements.txt

4. Download the required lexicons and place them in the data/ folder:
🔹 Greek Lexicon 1
Download all_num_clean_ns.xls from ILSP
(Ignores stress; compressed Excel file)

🔹 GreekLex2
Download from the GreekLex 2 website
Inside the ZIP file, locate GreekLex2.xlsx

📁 Place both GreekLex2.xlsx and all_num_clean_ns.xls in the data/ folder.

5. Run the application:
python3 app.py

💡 Note for macOS users: Use python3 instead of python if your system defaults to Python 2.x

6. Open your browser and go to:
http://127.0.0.1:5000

