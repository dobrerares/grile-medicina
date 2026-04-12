import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    sessions = relationship("QuizSession", back_populates="user")


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    filters = Column(Text, nullable=True)  # JSON string of filters used
    session_type = Column(String, nullable=False, default="practice")  # "practice" or "review"

    user = relationship("User", back_populates="sessions")
    questions = relationship("QuizSessionQuestion", back_populates="session", order_by="QuizSessionQuestion.position")


class QuizSessionQuestion(Base):
    __tablename__ = "quiz_session_questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id"), nullable=False, index=True)
    question_id = Column(String, nullable=False)  # references grile.json question id
    position = Column(Integer, nullable=False)

    session = relationship("QuizSession", back_populates="questions")
    answers = relationship("QuizAnswer", back_populates="session_question")


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_question_id = Column(Integer, ForeignKey("quiz_session_questions.id"), nullable=False, index=True)
    user_answer = Column(String, nullable=False)
    time_spent_ms = Column(Integer, nullable=True)
    answered_at = Column(DateTime, default=datetime.datetime.utcnow)

    session_question = relationship("QuizSessionQuestion", back_populates="answers")


class BugReport(Base):
    __tablename__ = "bug_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String, nullable=True)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    screenshot_path = Column(String, nullable=True)
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
