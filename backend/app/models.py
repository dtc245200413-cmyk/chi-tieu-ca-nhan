from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(254), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    categories = db.relationship("Category", back_populates="owner", cascade="all, delete-orphan")
    transactions = db.relationship("Transaction", back_populates="owner", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = (
        db.UniqueConstraint("owner_id", "name", "kind", name="uq_category_owner_name_kind"),
        db.CheckConstraint("kind IN ('income', 'expense')", name="ck_category_kind"),
    )

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    kind = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    owner = db.relationship("User", back_populates="categories")
    transactions = db.relationship("Transaction", back_populates="category")


class Transaction(db.Model):
    __tablename__ = "transactions"
    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_transaction_amount_positive"),
        db.CheckConstraint("kind IN ('income', 'expense')", name="ck_transaction_kind"),
        db.Index("ix_transaction_owner_date", "owner_id", "happened_on"),
    )

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    kind = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Numeric(14, 0), nullable=False)
    happened_on = db.Column(db.Date, nullable=False, index=True)
    note = db.Column(db.String(500), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    owner = db.relationship("User", back_populates="transactions")
    category = db.relationship("Category", back_populates="transactions")
