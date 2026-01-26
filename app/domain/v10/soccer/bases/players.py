"""선수(Player) SQLAlchemy 모델."""

from sqlalchemy import Column, String, Integer, BigInteger, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.domain.shared.bases import Base


class Player(Base):
    """선수 정보를 저장하는 SQLAlchemy 모델.

    Attributes:
        id: 선수 고유 식별자 (PK, BigInt)
        team_id: 팀 ID (FK -> teams.id)
        player_name: 선수명
        e_player_name: 영문 선수명
        nickname: 별명
        join_yyyy: 입단년도
        position: 포지션
        back_no: 등번호
        nation: 국적
        birth_date: 생년월일
        solar: 양력/음력 구분
        height: 키 (cm)
        weight: 몸무게 (kg)
    """

    __tablename__ = "players"

    # 기본 키
    id = Column(
        BigInteger,
        primary_key=True,
        comment="선수 고유 식별자"
    )

    # 외래 키
    team_id = Column(
        BigInteger,
        ForeignKey("teams.id"),
        nullable=True,
        comment="팀 ID"
    )

    # 선수 정보
    player_name = Column(
        String(20),
        nullable=True,
        comment="선수명"
    )

    e_player_name = Column(
        String(40),
        nullable=True,
        comment="영문 선수명"
    )

    nickname = Column(
        String(30),
        nullable=True,
        comment="별명"
    )

    join_yyyy = Column(
        String(10),
        nullable=True,
        comment="입단년도"
    )

    position = Column(
        String(10),
        nullable=True,
        comment="포지션"
    )

    back_no = Column(
        Integer,
        nullable=True,
        comment="등번호"
    )

    nation = Column(
        String(20),
        nullable=True,
        comment="국적"
    )

    birth_date = Column(
        Date,
        nullable=True,
        comment="생년월일"
    )

    solar = Column(
        String(10),
        nullable=True,
        comment="양력/음력 구분"
    )

    height = Column(
        Integer,
        nullable=True,
        comment="키 (cm)"
    )

    weight = Column(
        Integer,
        nullable=True,
        comment="몸무게 (kg)"
    )

    # 관계
    team = relationship(
        "Team",
        back_populates="players"
    )
