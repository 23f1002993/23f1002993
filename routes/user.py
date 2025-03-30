from flask import Blueprint, render_template, redirect, request, url_for, flash, session, abort
from flask_login import login_required, current_user
from models import Subject, Chapter, Quiz, Question, Score, db, User, Answer
from datetime import datetime

user = Blueprint('user', __name__, url_prefix='/user')

@user.before_request
def check_regular_user():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

@user.route('/')
@login_required
def dashboard():
    subjects = Subject.query.all()
    quizzes_taken = Score.query.filter_by(user_id=current_user.id).count()
    scores = Score.query.filter_by(user_id=current_user.id).order_by(Score.time_stamp.desc()).limit(5).all()
    
    return render_template('user/dashboard.html', 
                         subjects=subjects,
                         quizzes_taken=quizzes_taken,
                         scores=scores)

@user.route('/subjects')
@login_required
def subjects():
    subjects = Subject.query.all()
    return render_template('user/subjects.html', subjects=subjects)

@user.route('/subjects/<int:subject_id>')
@login_required
def subject_detail(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    chapters = Chapter.query.filter_by(subject_id=subject_id).all()
    return render_template('user/chapters.html', subject=subject, chapters=chapters)

@user.route('/subjects/<int:subject_id>/chapters')
@login_required
def view_chapters(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    chapters = Chapter.query.filter_by(subject_id=subject_id).all()
    return render_template('user/chapters.html', subject=subject, chapters=chapters)

@user.route('/chapters/<int:chapter_id>')
@login_required
def chapter_detail(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    quizzes = Quiz.query.filter_by(chapter_id=chapter_id).all()
    return render_template('user/quizzes.html', chapter=chapter, quizzes=quizzes)

@user.route('/chapters/<int:chapter_id>/quizzes')
@login_required
def view_quizzes(chapter_id):
    try:
        chapter = Chapter.query.get_or_404(chapter_id)
        quizzes = Quiz.query.filter_by(chapter_id=chapter_id).all()
        return render_template('user/quizzes.html', chapter=chapter, quizzes=quizzes)
    except Exception as e:
        flash(f'An error occurred while trying to view quizzes: {str(e)}', 'danger')
        return redirect(url_for('user.dashboard'))

@user.route('/quizzes/<int:quiz_id>/take')
@login_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check if user has already taken this quiz
    user_score = Score.query.filter_by(quiz_id=quiz_id, user_id=current_user.id).first()
    if user_score:
        flash('You have already taken this quiz. View your score instead.', 'info')
        return redirect(url_for('user.view_score_detail', score_id=user_score.id))
    
    # Check if the quiz has questions
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    if not questions:
        flash('This quiz has no questions yet.', 'warning')
        return redirect(url_for('user.view_quizzes', chapter_id=quiz.chapter_id))
    
    return render_template('user/take_quiz.html', quiz=quiz, questions=questions)

@user.route('/quizzes/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check if user has already taken this quiz
    user_score = Score.query.filter_by(quiz_id=quiz_id, user_id=current_user.id).first()
    if user_score:
        flash('You have already taken this quiz. View your score instead.', 'info')
        return redirect(url_for('user.view_score_detail', score_id=user_score.id))
    
    # Get all questions for the quiz
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    if not questions:
        flash('This quiz has no questions.', 'warning')
        return redirect(url_for('user.view_quizzes', chapter_id=quiz.chapter_id))
    
    # Calculate score
    correct_count = 0
    total_questions = len(questions)
    
    # Create a new score record
    new_score = Score(
        user_id=current_user.id,
        quiz_id=quiz_id,
        correct_answers=0,  # Will update this after calculating
        total_questions=total_questions,
        time_stamp=datetime.now()
    )
    db.session.add(new_score)
    db.session.flush()  # Get the ID without committing
    
    # Process answers for each question
    for question in questions:
        selected_option = request.form.get(f'answer{question.id}')
        
        if selected_option:
            # Convert to integer
            selected_option = int(selected_option)
            
            # Create answer record
            answer = Answer(
                score_id=new_score.id,
                question_id=question.id,
                selected_option=selected_option
            )
            db.session.add(answer)
            
            # Count correct answers
            if selected_option == question.correct_option:
                correct_count += 1
    
    # Update the score value
    new_score.correct_answers = correct_count
    db.session.commit()
    
    flash(f'Quiz submitted successfully! Your score: {correct_count}/{total_questions}', 'success')
    return redirect(url_for('user.view_score_detail', score_id=new_score.id))

@user.route('/scores')
@login_required
def view_scores():
    scores = Score.query.filter_by(user_id=current_user.id).order_by(Score.time_stamp.desc()).all()
    subjects = Subject.query.all()
    
    # Calculate passing rate
    passed_quizzes = 0
    for score in scores:
        if score.get_status() == 'Passed':
            passed_quizzes += 1
    
    passing_rate = 0
    if scores:
        passing_rate = int((passed_quizzes / len(scores)) * 100)
    
    # Calculate best subject
    best_subject = "None"
    best_subject_score = 0
    subject_scores = {}
    
    for score in scores:
        subject_name = score.quiz.chapter.subject.name
        if subject_name not in subject_scores:
            subject_scores[subject_name] = {'total': 0, 'count': 0}
        
        subject_scores[subject_name]['total'] += score.get_percentage()
        subject_scores[subject_name]['count'] += 1
    
    for subject_name, data in subject_scores.items():
        avg_score = data['total'] / data['count']
        if avg_score > best_subject_score:
            best_subject_score = avg_score
            best_subject = subject_name
    
    # Get best individual score
    best_score = 0
    best_score_subject = "None"
    
    for score in scores:
        percentage = score.get_percentage()
        if percentage > best_score:
            best_score = percentage
            best_score_subject = f"{score.quiz.chapter.subject.name} - {score.quiz.chapter.name}"
    
    return render_template('user/scores.html', 
                         scores=scores, 
                         subjects=subjects,
                         passing_rate=passing_rate,
                         passed_quizzes=passed_quizzes,
                         best_subject=best_subject,
                         best_subject_score=round(best_subject_score) if best_subject_score else 0,
                         best_score=best_score,
                         best_score_subject=best_score_subject)

@user.route('/scores/<int:score_id>')
@login_required
def view_score_detail(score_id):
    score = Score.query.get_or_404(score_id)
    
    # Ensure the user can only view their own scores
    if score.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    return render_template('user/score_detail.html', score=score)

@user.route('/quizzes/<int:quiz_id>/view')
@login_required
def view_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    chapter = quiz.chapter
    subject = chapter.subject
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    # Check if the user has already taken this quiz
    user_score = Score.query.filter_by(quiz_id=quiz_id, user_id=current_user.id).first()
    
    return render_template('user/view_quiz.html', 
                          quiz=quiz, 
                          chapter=chapter, 
                          subject=subject,
                          questions=questions,
                          user_score=user_score)

@user.route('/search')
@login_required
def search():
    query = request.args.get('query', '')
    
    if not query:
        return render_template('user/search.html', subjects=[], chapters=[], quizzes=[], query=query)
    
    # Search for subjects that match the query
    subjects = Subject.query.filter(Subject.name.ilike(f'%{query}%')).all()
    
    # Search for chapters that match the query
    chapters = Chapter.query.filter(Chapter.name.ilike(f'%{query}%')).all()
    
    # Get the IDs of relevant subjects and chapters
    subject_ids = [subject.id for subject in subjects]
    chapter_ids = [chapter.id for chapter in chapters]
    
    # Retrieve chapters associated with matching subjects
    subject_chapters = Chapter.query.filter(Chapter.subject_id.in_(subject_ids)).all()
    all_chapter_ids = chapter_ids + [chapter.id for chapter in subject_chapters]
    
    # Retrieve quizzes for all relevant chapters
    quizzes = []
    if all_chapter_ids:
        quiz_objects = Quiz.query.filter(Quiz.chapter_id.in_(all_chapter_ids)).all()
        for quiz in quiz_objects:
            quizzes.append({
                'id': quiz.id,
                'chapter_id': quiz.chapter_id,
                'chapter_name': quiz.chapter.name,
                'subject_name': quiz.chapter.subject.name,
                'date': quiz.date_of_quiz
            })
    
    # If no chapters but we have matching subjects, get all chapters for those subjects
    if not all_chapter_ids and subject_ids:
        chapters_from_subjects = Chapter.query.filter(Chapter.subject_id.in_(subject_ids)).all()
        for chapter in chapters_from_subjects:
            quiz_objects = Quiz.query.filter_by(chapter_id=chapter.id).all()
            for quiz in quiz_objects:
                quizzes.append({
                    'id': quiz.id,
                    'chapter_id': quiz.chapter_id,
                    'chapter_name': chapter.name,
                    'subject_name': chapter.subject.name,
                    'date': quiz.date_of_quiz
                })
    
    return render_template('user/search.html', subjects=subjects, chapters=chapters, quizzes=quizzes, query=query)

@user.route('/charts')
@login_required
def charts():
    # Get all user scores
    scores = Score.query.filter_by(user_id=current_user.id).all()
    
    # Prepare data for subject-wise score chart
    subject_scores = {}
    for score in scores:
        subject_name = score.quiz.chapter.subject.name
        if subject_name not in subject_scores:
            subject_scores[subject_name] = {
                'total': score.get_percentage(),
                'count': 1
            }
        else:
            subject_scores[subject_name]['total'] += score.get_percentage()
            subject_scores[subject_name]['count'] += 1
    
    # Calculate average scores by subject
    avg_scores = {}
    for subject, data in subject_scores.items():
        avg_scores[subject] = round(data['total'] / data['count'], 1)
    
    # Calculate total attempts by subject
    subject_attempts = {}
    for score in scores:
        subject_name = score.quiz.chapter.subject.name
        if subject_name not in subject_attempts:
            subject_attempts[subject_name] = 1
        else:
            subject_attempts[subject_name] += 1
            
    return render_template('user/charts.html',
                           avg_scores=avg_scores,
                           subject_attempts=subject_attempts) 