"""경기장(Stadium) SQLAlchemy 모델."""

from sqlalchemy import Column, Integer, BigInteger, String
from sqlalchemy.orm import relationship

from app.domain.shared.bases import Base


class Stadium(Base):
    """경기장 정보를 저장하는 SQLAlchemy 모델.

    Attributes:
        id: 경기장 고유 식별자 (PK, BigInt)
        stadium_code: 경기장 코드
        statdium_name: 경기장 이름 (오타 포함, ERD 기준)
        hometeam_code: 홈팀 코드
        seat_count: 좌석 수
        address: 주소
        ddd: 지역번호
        tel: 전화번호
    """

    __tablename__ = "stadiums"

    # 기본 키
    id = Column(
        BigInteger,
        primary_key=True,
        comment="경기장 고유 식별자"
    )

    # 경기장 정보
    stadium_code = Column(
        String(10),
        nullable=True,
        comment="경기장 코드"
    )

    statdium_name = Column(
        String(40),
        nullable=True,
        comment="경기장 이름"
    )

    hometeam_code = Column(
        String(10),
        nullable=True,
        comment="홈팀 코드"
    )

    seat_count = Column(
        Integer,
        nullable=True,
        comment="좌석 수"
    )

    address = Column(
        String(60),
        nullable=True,
        comment="주소"
    )

    ddd = Column(
        String(10),
        nullable=True,
        comment="지역번호"
    )

    tel = Column(
        String(20),
        nullable=True,
        comment="전화번호"
    )

    # 관계
    teams = relationship(
        "Team",
        back_populates="stadium"
    )

    schedules = relationship(
        "Schedule",
        back_populates="stadium"
    )
