from flask import Blueprint, render_template, redirect, request, url_for, flash, abort
from flask_login import login_required, current_user
from models import User, Subject, Chapter, Quiz, Question, Score, db
from datetime import datetime
from functools import wraps

admin = Blueprint('admin', __name__, url_prefix='/admin')

# Admin access decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page.')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin.before_request
def check_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash('You must be an admin to access this page.')
        return redirect(url_for('auth.login'))

@admin.route('/')
@login_required
def dashboard():
    subjects = Subject.query.all()
    chapters = Chapter.query.all()
    quizzes = Quiz.query.all()
    questions = Question.query.all()
    users = User.query.filter_by(is_admin=False).all()
    scores = Score.query.all()
    recent_scores = Score.query.order_by(Score.time_stamp.desc()).limit(5).all()
    
    # Calculate statistics
    stats = {
        'subjects': len(subjects),
        'chapters': len(chapters),
        'quizzes': len(quizzes),
        'questions': len(questions),
        'users': len(users),
        'scores': len(scores),
        'recent_scores': recent_scores,
        'recent_users': User.query.order_by(User.id.desc()).limit(5).all()
    }
    
    return render_template('admin/dashboard.html', stats=stats, subjects=subjects)

# Subject Management
@admin.route('/subjects')
@login_required
def subjects():
    subjects = Subject.query.all()
    return render_template('admin/subjects.html', subjects=subjects)

@admin.route('/subjects/add', methods=['POST'])
@login_required
def add_subject():
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('Subject name is required', 'danger')
        return redirect(url_for('admin.subjects'))
    
    new_subject = Subject(name=name, description=description)
    db.session.add(new_subject)
    db.session.commit()
    
    flash('Subject added successfully', 'success')
    return redirect(url_for('admin.subjects'))

@admin.route('/subjects/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_subject(id):
    subject = Subject.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Subject name is required', 'danger')
            return redirect(url_for('admin.edit_subject', id=id))
        
        subject.name = name
        subject.description = description
        db.session.commit()
        
        flash('Subject updated successfully', 'success')
        return redirect(url_for('admin.subjects'))
    
    return render_template('admin/edit_subject.html', subject=subject)

@admin.route('/subjects/delete/<int:id>')
@login_required
def delete_subject(id):
    subject = Subject.query.get_or_404(id)
    
    # Check if the subject has chapters
    if subject.chapters:
        flash('Cannot delete subject with chapters. Delete chapters first.', 'danger')
        return redirect(url_for('admin.subjects'))
    
    db.session.delete(subject)
    db.session.commit()
    
    flash('Subject deleted successfully', 'success')
    return redirect(url_for('admin.subjects'))

# Chapter Management
@admin.route('/subjects/<int:subject_id>/chapters')
@login_required
def chapters(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    chapters = Chapter.query.filter_by(subject_id=subject_id).all()
    return render_template('admin/chapters.html', subject=subject, chapters=chapters)

@admin.route('/subjects/<int:subject_id>/chapters/add', methods=['POST'])
@login_required
def add_chapter(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    name = request.form.get('name')
    description = request.form.get('description')
    
    if not name:
        flash('Chapter name is required', 'danger')
        return redirect(url_for('admin.chapters', subject_id=subject_id))
    
    new_chapter = Chapter(name=name, description=description, subject_id=subject_id)
    db.session.add(new_chapter)
    db.session.commit()
    
    flash('Chapter added successfully', 'success')
    return redirect(url_for('admin.chapters', subject_id=subject_id))

@admin.route('/chapters/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_chapter(id):
    chapter = Chapter.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Chapter name is required', 'danger')
            return redirect(url_for('admin.edit_chapter', id=id))
        
        chapter.name = name
        chapter.description = description
        db.session.commit()
        
        flash('Chapter updated successfully', 'success')
        return redirect(url_for('admin.chapters', subject_id=chapter.subject_id))
    
    return render_template('admin/edit_chapter.html', chapter=chapter)

@admin.route('/chapters/delete/<int:id>')
@login_required
def delete_chapter(id):
    chapter = Chapter.query.get_or_404(id)
    subject_id = chapter.subject_id
    
    # Check if the chapter has quizzes
    if chapter.quizzes:
        flash('Cannot delete chapter with quizzes. Delete quizzes first.', 'danger')
        return redirect(url_for('admin.chapters', subject_id=subject_id))
    
    db.session.delete(chapter)
    db.session.commit()
    
    flash('Chapter deleted successfully', 'success')
    return redirect(url_for('admin.chapters', subject_id=subject_id))

# Quiz Management
@admin.route('/chapters/<int:chapter_id>/quizzes')
@login_required
def quizzes(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    quizzes = Quiz.query.filter_by(chapter_id=chapter_id).all()
    return render_template('admin/quizzes.html', chapter=chapter, quizzes=quizzes)

@admin.route('/chapters/<int:chapter_id>/quizzes/add', methods=['POST'])
@login_required
def add_quiz(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    date_str = request.form.get('date')
    duration = request.form.get('duration')
    remarks = request.form.get('remarks')
    
    if not date_str or not duration:
        flash('Date and duration are required', 'danger')
        return redirect(url_for('admin.quizzes', chapter_id=chapter_id))
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
        duration_str = duration
    except ValueError:
        flash('Invalid date format', 'danger')
        return redirect(url_for('admin.quizzes', chapter_id=chapter_id))
    
    new_quiz = Quiz(
        chapter_id=chapter_id,
        date_of_quiz=date,
        time_duration=duration_str,
        remarks=remarks
    )
    db.session.add(new_quiz)
    db.session.commit()
    
    flash('Quiz added successfully', 'success')
    return redirect(url_for('admin.quizzes', chapter_id=chapter_id))

@admin.route('/quizzes/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_quiz(id):
    quiz = Quiz.query.get_or_404(id)
    
    if request.method == 'POST':
        date_str = request.form.get('date_of_quiz')
        duration = request.form.get('time_duration')
        remarks = request.form.get('remarks')
        
        if not date_str or not duration:
            flash('Date and duration are required', 'danger')
            return redirect(url_for('admin.edit_quiz', id=id))
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
            duration_str = duration
        except ValueError:
            flash('Invalid date format', 'danger')
            return redirect(url_for('admin.edit_quiz', id=id))
        
        quiz.date_of_quiz = date
        quiz.time_duration = duration_str
        quiz.remarks = remarks
        db.session.commit()
        
        flash('Quiz updated successfully', 'success')
        return redirect(url_for('admin.quizzes', chapter_id=quiz.chapter_id))
    
    return render_template('admin/edit_quiz.html', quiz=quiz)

@admin.route('/quizzes/delete/<int:id>')
@login_required
def delete_quiz(id):
    quiz = Quiz.query.get_or_404(id)
    chapter_id = quiz.chapter_id
    
    # Check if the quiz has questions
    if quiz.questions:
        flash('Cannot delete quiz with questions. Delete questions first.', 'danger')
        return redirect(url_for('admin.quizzes', chapter_id=chapter_id))
    
    # Check if the quiz has been taken by users
    if quiz.scores:
        flash('Cannot delete quiz with scores. Delete scores first.', 'danger')
        return redirect(url_for('admin.quizzes', chapter_id=chapter_id))
    
    db.session.delete(quiz)
    db.session.commit()
    
    flash('Quiz deleted successfully', 'success')
    return redirect(url_for('admin.quizzes', chapter_id=chapter_id))

# Question Management
@admin.route('/quizzes/<int:quiz_id>/questions')
@login_required
def questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    return render_template('admin/questions.html', quiz=quiz, questions=questions)

@admin.route('/quizzes/<int:quiz_id>/questions/add', methods=['POST'])
@login_required
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    statement = request.form.get('statement')
    option1 = request.form.get('option1')
    option2 = request.form.get('option2')
    option3 = request.form.get('option3')
    option4 = request.form.get('option4')
    correct_option = request.form.get('correct_option')
    
    if not statement or not option1 or not option2 or not option3 or not option4 or not correct_option:
        flash('All fields are required', 'danger')
        return redirect(url_for('admin.questions', quiz_id=quiz_id))
    
    try:
        correct_option_int = int(correct_option)
        if correct_option_int < 1 or correct_option_int > 4:
            raise ValueError
    except ValueError:
        flash('Correct option must be a number between 1 and 4', 'danger')
        return redirect(url_for('admin.questions', quiz_id=quiz_id))
    
    new_question = Question(
        quiz_id=quiz_id,
        question_statement=statement,
        option1=option1,
        option2=option2,
        option3=option3,
        option4=option4,
        correct_option=correct_option_int
    )
    db.session.add(new_question)
    db.session.commit()
    
    flash('Question added successfully', 'success')
    return redirect(url_for('admin.questions', quiz_id=quiz_id))

@admin.route('/questions/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_question(id):
    question = Question.query.get_or_404(id)
    
    if request.method == 'POST':
        statement = request.form.get('statement')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3')
        option4 = request.form.get('option4')
        correct_option = request.form.get('correct_option')
        
        if not statement or not option1 or not option2 or not option3 or not option4 or not correct_option:
            flash('All fields are required', 'danger')
            return redirect(url_for('admin.edit_question', id=id))
        
        try:
            correct_option_int = int(correct_option)
            if correct_option_int < 1 or correct_option_int > 4:
                raise ValueError
        except ValueError:
            flash('Correct option must be a number between 1 and 4', 'danger')
            return redirect(url_for('admin.edit_question', id=id))
        
        question.question_statement = statement
        question.option1 = option1
        question.option2 = option2
        question.option3 = option3
        question.option4 = option4
        question.correct_option = correct_option_int
        db.session.commit()
        
        flash('Question updated successfully', 'success')
        return redirect(url_for('admin.questions', quiz_id=question.quiz_id))
    
    return render_template('admin/edit_question.html', question=question)

@admin.route('/questions/delete/<int:id>')
@login_required
def delete_question(id):
    question = Question.query.get_or_404(id)
    quiz_id = question.quiz_id
    
    db.session.delete(question)
    db.session.commit()
    
    flash('Question deleted successfully', 'success')
    return redirect(url_for('admin.questions', quiz_id=quiz_id))

# User Management
@admin.route('/users')
@login_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin.route('/users/toggle_admin/<int:id>')
@login_required
def toggle_admin(id):
    # Admin functionality has been disabled
    flash('Admin management functionality has been disabled', 'info')
    return redirect(url_for('admin.users'))

@admin.route('/users/delete/<int:id>')
@login_required
def delete_user(id):
    # Don't allow admin to delete themselves
    if id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin.users'))
    
    user = User.query.get_or_404(id)
    
    # Delete all associated scores
    Score.query.filter_by(user_id=id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User and associated data deleted successfully', 'success')
    return redirect(url_for('admin.users'))

# Reports and Analytics
@admin.route('/reports')
@login_required
@admin_required
def reports():
    recent_scores = Score.query.order_by(Score.time_stamp.desc()).limit(10).all()
    subjects = Subject.query.all()
    
    # Prepare data for subject-wise score chart
    subject_scores = {}
    for subject in subjects:
        total_score = 0
        count = 0
        for chapter in subject.chapters:
            for quiz in chapter.quizzes:
                for score in quiz.scores:
                    total_score += score.get_percentage()
                    count += 1
        
        if count > 0:
            subject_scores[subject.name] = round(total_score / count, 1)
    
    # Prepare data for user attempts by subject
    subject_attempts = {}
    for subject in subjects:
        subject_attempts[subject.name] = 0
        for chapter in subject.chapters:
            for quiz in chapter.quizzes:
                subject_attempts[subject.name] += len(quiz.scores)
    
    return render_template('admin/reports.html', 
                           recent_scores=recent_scores,
                           subject_scores=subject_scores,
                           subject_attempts=subject_attempts)


@admin.route('/search')
@login_required
@admin_required
def search():
    query = request.args.get('query', '')
    
    if not query:
        return redirect(url_for('admin.dashboard'))
    
    users = User.query.filter(User.full_name.ilike(f'%{query}%')).all()
    subjects = Subject.query.filter(Subject.name.ilike(f'%{query}%')).all()
    chapters = Chapter.query.filter(Chapter.name.ilike(f'%{query}%')).all()
    quizzes = Quiz.query.filter(Quiz.remarks.ilike(f'%{query}%')).all()
    
    return render_template('admin/search.html', 
                           query=query,
                           users=users,
                           subjects=subjects,
                           chapters=chapters,
                           quizzes=quizzes)

@admin.route('/all-quizzes')
@login_required
@admin_required
def all_quizzes():
    quizzes = Quiz.query.all()
    return render_template('admin/search.html', 
                          query="All Quizzes",
                          users=[],
                          subjects=[],
                          chapters=[],
                          quizzes=quizzes) 