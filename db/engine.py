from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.config_loader import config
from core.logging_config import root_logger
from db.models import Base

engine = create_engine(
    f'postgresql://{config.db.user}:{config.db.password}@{config.db.host}/{config.db.db_name}'
)

session: Session = sessionmaker(engine, expire_on_commit=False)()


async def create_tables():
    Base.metadata.create_all(engine)
    root_logger('DB tables created or OK')
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    # session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
