from flask_login import UserMixin
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(100), nullable=True)
    dob = db.Column(db.String(20), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

    scores = db.relationship('Score', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def get_average_score(self):
        if not self.scores:
            return 0
        
        total_percentage = 0
        for score in self.scores:
            total_percentage += score.get_percentage()
        
        return round(total_percentage / len(self.scores), 1)
    
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    chapters = db.relationship('Chapter', backref='subject', lazy=True, cascade="all, delete-orphan")
    
    def get_total_quizzes(self):
        count = 0
        for chapter in self.chapters:
            count += len(chapter.quizzes)
        return count
    
    def get_total_students(self):
        student_ids = set()
        for chapter in self.chapters:
            for quiz in chapter.quizzes:
                for score in quiz.scores:
                    student_ids.add(score.user_id)
        return len(student_ids)
    
class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    
    quizzes = db.relationship('Quiz', backref='chapter', lazy=True, cascade="all, delete-orphan")

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    date_of_quiz = db.Column(db.String(20), nullable=False)
    time_duration = db.Column(db.String(10), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade="all, delete-orphan")
    scores = db.relationship('Score', backref='quiz', lazy=True, cascade="all, delete-orphan")

    def get_status(self,user):
        for score in self.scores:
            if score.user_id == user.id:
                return "Taken"
            
        return "Open"
    

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_statement = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(200), nullable=False)
    option2 = db.Column(db.String(200), nullable=False)
    option3 = db.Column(db.String(200), nullable=False)
    option4 = db.Column(db.String(200), nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)  # 1, 2, 3, or 4

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score_id = db.Column(db.Integer, db.ForeignKey('score.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option = db.Column(db.Integer, nullable=False)  # The option (1-4) selected by the user

      # Relationships
    score = db.relationship('Score', backref=db.backref('answers', lazy=True, cascade="all, delete-orphan"))
    question = db.relationship('Question', backref=db.backref('answers', lazy=True, cascade="all, delete-orphan"))
    
    # Helper method to check if answer is correct
    def is_correct(self):
        return self.selected_option == self.question.correct_option


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time_stamp = db.Column(db.DateTime, default=datetime.utcnow)
    correct_answers = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    
    def get_percentage(self):
        if self.total_questions == 0:
            return 0
        return round((self.correct_answers / self.total_questions) * 100, 1)
    
    def get_grade(self):
        percentage = self.get_percentage()
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"
    
    def get_status(self):
        percentage = self.get_percentage()
        if percentage >= 60:
            return "Passed"
        else:
            return "Failed" 