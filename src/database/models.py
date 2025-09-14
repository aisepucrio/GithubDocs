import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    repository_name = Column(String, index=True)
    
    results = relationship("RepoAnalysisResult", back_populates="run")

class RepoAnalysisResult(Base):
    __tablename__ = "repo_analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"))
    plugin_name = Column(String, index=True)
    data = Column(JSON)

    run = relationship("AnalysisRun", back_populates="results")
