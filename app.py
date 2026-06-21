from flask import Flask, render_template, request, redirect, session
from ai import analyze_resume
from db import Base, engine, SessionLocal
import models
import PyPDF2
import docx
import json


app = Flask(__name__)
app.secret_key = 'secret123'

Base.metadata.create_all(bind=engine)

#HOME PAGE

@app.route('/')
def home():
    if 'user' in session:
        return redirect('/dashboard')
    return redirect ('/login')


#----SIGN UP

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    db = SessionLocal()
    try:
        if request.method == 'POST':
            email= request.form.get('email')
            password = request.form.get('password')
            existing_user = db.query(models.User).filter_by(email=email).first()
            if existing_user:
                return "Email already registered. Please log in."
            user = models.User(email=email, password=password)
            db.add(user)
            db.commit()
            return redirect('/login')
        return render_template('signup.html')
    finally:
        db.close()


#----LOGIN

@app.route('/login', methods=['GET', 'POST'])
def login():
    db = SessionLocal()
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            user = db.query(models.User).filter_by(email=email, password=password).first()
            if user:
                session['user'] = user.email
                return redirect('/dashboard')
            else:
                return "Invalid credentials. Please try again."
        return render_template('login.html')
    finally:
        db.close()


#-------DASHBOARD

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    
    resume_text = None
    result = None

    if request.method == 'POST':
        user_goal = request.form.get('role')
        resume_text = request.form.get('text')

        file = request.files.get('file')
        # File handling
        if file and file.filename:
            if file.filename.lower().endswith('.pdf'):
                try:
                    pdf_reader = PyPDF2.PdfReader(file)
                    resume_text = ''
                    for page in pdf_reader.pages:
                        resume_text += page.extract_text() or ''
                except Exception as e:
                    result = {"error": f"Failed to process PDF: {str(e)}"}

            elif file.filename.lower().endswith('.docx'):
                try:
                    doc = docx.Document(file)
                    text = ""
                    for para in doc.paragraphs:
                        text += para.text + "\n"
                    resume_text = text
                except Exception as e:
                    result = {"error": f"Failed to process DOCX: {str(e)}"}
        if resume_text and user_goal:
            try:
                result = analyze_resume(resume_text, user_goal)
                
                #Save report to database
                db = SessionLocal()
                user = db.query(models.User).filter_by(email=session['user']).first()
                if not user:
                    db.close()
                    session.pop('user', None)
                    return redirect('/login')
                report = models.Reports(
                user_id=user.id, 
                resume_text=resume_text, 
                result=json.dumps(result)
                
                )

                db.add(report)
                db.commit()
                db.close()
                return render_template('dashboard.html', result=result, user=session['user'])
            except Exception as e:
                result = {"error": f"Failed to analyze resume: {str(e)}"}
                return render_template('dashboard.html', result=result, user=session["user"]) 
        else:
            if not result:
                result = {"error": "Please provide a resume (text or file) and a target role."}
            return render_template('dashboard.html', result=result, user=session['user'])

    return render_template('dashboard.html', result=result, user=session['user'])
            
# ---History

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/login')
    db = SessionLocal()
    user = db.query(models.User).filter_by(email=session['user']).first()
    if not user:
        db.close()
        session.pop('user', None)
        return redirect('/login')
    reports = db.query(models.Reports).filter_by(user_id=user.id).all()
    # convert JSON string -> dict
    parsed_reports = []
    for r in reports:
        try:
            parsed_result = json.loads(r.result)
        except Exception:
            parsed_result = {}

        parsed_reports.append({
            "resume": r.resume_text,
            "result": parsed_result
        })

    db.close()
    return render_template('history.html', reports=parsed_reports, user=session['user'])

#---LOGOUT
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

                    
if __name__ == '__main__':
    app.run(debug=True)
