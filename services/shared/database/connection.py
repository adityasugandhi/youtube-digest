from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import logging
from typing import Generator

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection manager"""
    
    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20):
        self.database_url = database_url
        
        # Create engine
        self.engine = create_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            echo=False  # Set to True for SQL logging
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()


# Global database manager instance (to be initialized in main app)
db_manager: DatabaseManager = None


def init_database(database_url: str, pool_size: int = 10, max_overflow: int = 20):
    """Initialize database manager"""
    global db_manager
    db_manager = DatabaseManager(database_url, pool_size, max_overflow)
    return db_manager


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session"""
    if not db_manager:
        raise RuntimeError("Database not initialized")
    
    yield from db_manager.get_session()