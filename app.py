from flask import Flask, render_template, request, session, redirect, url_for
import requests
import random
from html import unescape
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
import firebase_admin
from flask import flash, get_flashed_messages
from firebase_admin import credentials, auth
from dotenv import load_dotenv
load_dotenv()
import os
import json



app = Flask(__name__)


app.secret_key = os.getenv('FLASK_SECRET_KEY')


# Use the path to the file from the environment variable
cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if cred_path is None:
    raise ValueError("Missing GOOGLE_APPLICATION_CREDENTIALS environment variable")

cred = credentials.Certificate(cred_path)


firebase_admin.initialize_app(cred)


TOTAL_QUESTIONS = 50  # Total number of questions for the quiz

def fetch_question():
    """Fetch a new question and answers from the API."""
    #response = requests.get('https://opentdb.com/api.php?amount=1&category=11&type=multiple')
    response = requests.get('https://opentdb.com/api.php?amount=50&category=27&type=multiple')
    data = response.json()
    question_info = data['results'][0]
    question = unescape(question_info['question'])
    correct_answer = unescape(question_info['correct_answer'])
    incorrect_answers = [unescape(ans) for ans in question_info['incorrect_answers']]
    all_answers = incorrect_answers + [correct_answer]
    random.shuffle(all_answers)
    return question, correct_answer, all_answers


# Forms
class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
    
    
class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')
    

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        try:
            user = auth.create_user(
                email=email,
                password=password
            )
            # User created successfully, flash message
            flash('You have successfully registered!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            # Handle exceptions or show error messages
    return render_template('register.html', form=form)




@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        try:
            user = auth.get_user_by_email(email)
            # Assume user is authenticated for demonstration
            session['user_id'] = user.uid            
            flash('You have successfully logged in!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
             flash('Login failed. Please check your credentials and try again.', 'danger')
            #flash('Login failed. Please check your credentials and try again.', 'error')
    return render_template('login.html', form=form)


def check_auth():
    user_id = session.get('user_id')
    if not user_id:
        return False
    try:
        auth.get_user(user_id)
        return True
    except:
        return False
        

@app.route('/index', methods=['GET', 'POST'])
def index():
    if not check_auth():
        return redirect(url_for('login'))
    
    session.setdefault('attempted_count', 0)
    session.setdefault('correct_count', 0)

    if session['attempted_count'] >= TOTAL_QUESTIONS:
        return render_template('quiz_completed.html', correct_count=session['correct_count'], total_questions=TOTAL_QUESTIONS)
    
    if request.method == 'POST':
        user_answer = request.form.get('answers')
        correct_answer = session.get('correct_answer')
        if user_answer == correct_answer:
            session['correct_count'] += 1
            message = "Correct!"
        else:
            message = f"Incorrect! The correct answer was {correct_answer}."
    else:
        message = None
    
    # Fetch a new question if needed
    if request.method == 'GET' or session.get('fetch_new', True):
        question, correct_answer, all_answers = fetch_question()
        session['correct_answer'] = correct_answer
        session['current_question'] = question
        session['current_answers'] = all_answers
        session['fetch_new'] = False
    else:
        question = session['current_question']
        all_answers = session['current_answers']
    
    return render_template('index.html', question=question, answers=all_answers, message=message, correct_count=session['correct_count'], attempted_count=session['attempted_count'], total_questions=TOTAL_QUESTIONS)

@app.route('/next')
def next_question():
    if session.get('attempted_count', 0) < TOTAL_QUESTIONS:
        session['attempted_count'] += 1
        session['fetch_new'] = True
    return redirect(url_for('index'))

@app.route('/restart')
def restart_quiz():
    session['attempted_count'] = 0
    session['correct_count'] = 0
    session['fetch_new'] = True
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()  # This clears all data in the session
    return redirect(url_for('home'))


 
@app.route('/request-password-reset', methods=['GET'])
def request_password_reset():
    # Just render the template without passing a form since it's not used
    return render_template('password_reset_request.html')







if __name__ == '__main__':
    app.run(debug=True)
