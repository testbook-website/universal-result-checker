from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    exam_name = Column(String, index=True)
    tier = Column(String)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    roll_numbers = relationship("RollNumber", back_populates="exam", cascade="all, delete-orphan")

class RollNumber(Base):
    __tablename__ = "roll_numbers"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    roll_number = Column(String, index=True)

    exam = relationship("Exam", back_populates="roll_numbers")
