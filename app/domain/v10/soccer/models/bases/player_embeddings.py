from sqlalchemy import Column, BigInteger, Text, ForeignKey, TIMESTAMP, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector import Vector

Base = declarative_base()

class PlayerEmbedding(Base):
    """임베딩 레코드 모델.

    Attributes:
        id: 임베딩 레코드 고유 식별자 (PK, BigInt, autoincrement)
        player_id: 선수 ID (FK -> Player.id)
        content: 원본 텍스트 데이터
        embedding: KoElectra 기반 768차원 벡터 임베딩
        created_at: 레코드 생성 시간
    """
    __tablename__ = "players_embeddings"

    # 기본 키
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="임베딩 레코드 고유 식별자"
    )

    # 외래 키
    player_id = Column(
        BigInteger,
        ForeignKey("players.id"),
        nullable=False,
        comment="선수 ID"
    )

    # 원본 텍스트 데이터
    content = Column(
        Text,
        nullable=False,
        comment="임베딩 생성에 사용된 원본 텍스트"
    )

    # 768차원 KoElectra 벡터 임베딩
    embedding = Column(
        Vector('768'),
        nullable=False,
        comment='768차원 KoElectra 임베딩 벡터'
    )

    # 생성 시간
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment='레코드 생성 시간'
    )

    # 관계 설정
    player = relationship(
        "Player",
        back_populates="embeddings"
    )

# 예시 엔진 생성 및 연결 (실제 사용 시 필요에 따라 수정)
engine = create_engine('postgresql://user:password@localhost:5432/yourdatabase')
Base.metadata.create_all(engine)