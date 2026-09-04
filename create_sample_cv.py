from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font('Arial', 'B', 16)
pdf.cell(0, 10, 'John Doe', ln=True)
pdf.set_font('Arial', '', 12)
pdf.cell(0, 10, 'Email: john@example.com | Phone: +92-300-1234567', ln=True)
pdf.ln(5)

pdf.set_font('Arial', 'B', 14)
pdf.cell(0, 10, 'Summary', ln=True)
pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 8, 'Software engineer with 3 years experience in Python, Flutter, and machine learning. Passionate about building scalable apps.')

pdf.set_font('Arial', 'B', 14)
pdf.cell(0, 10, 'Experience', ln=True)
pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 8, 'Software Engineer at TechCorp (2021-2024). Developed mobile apps using Flutter and Firebase. Built REST APIs with FastAPI and integrated payment gateways.')

pdf.set_font('Arial', 'B', 14)
pdf.cell(0, 10, 'Education', ln=True)
pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 8, 'BS Computer Science, FAST NUCES, 2021')

pdf.set_font('Arial', 'B', 14)
pdf.cell(0, 10, 'Skills', ln=True)
pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 8, 'Python, Flutter, Dart, Firebase, FastAPI, Machine Learning, Git, SQL')

pdf.set_font('Arial', 'B', 14)
pdf.cell(0, 10, 'Projects', ln=True)
pdf.set_font('Arial', '', 12)
pdf.multi_cell(0, 8, 'E-commerce App: Built a Flutter e-commerce app with Firebase backend and Stripe payments. Interview Coach Bot: Created an AI chatbot for interview practice using Python and HuggingFace.')

pdf.output('sample_cv.pdf')
print('Created sample_cv.pdf')
