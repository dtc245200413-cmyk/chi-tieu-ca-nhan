import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .forms import LoginForm, RegistrationForm
from .models import Category, Transaction, User

main = Blueprint("main", __name__)
logger = logging.getLogger(__name__)
TRANSACTION_KINDS = {"income", "expense"}
MAX_AMOUNT = Decimal("99999999999999")
DEMO_NOTE_PREFIX = "DEMO:"
DEFAULT_CATEGORIES = {
    "income": ("Lương", "Thưởng", "Đầu tư", "Thu nhập khác"),
    "expense": ("Ăn uống", "Di chuyển", "Nhà ở", "Hóa đơn", "Mua sắm", "Sức khỏe", "Giải trí", "Khác"),
}


def _today() -> date:
    return datetime.now(ZoneInfo(current_app.config["TIMEZONE"])).date()


def _categories(kind: str | None = None):
    query = Category.query.filter_by(owner_id=current_user.id)
    if kind in TRANSACTION_KINDS:
        query = query.filter_by(kind=kind)
    return query.order_by(Category.kind, Category.name).all()


def _sum_amount(kind: str, start: date | None = None, end: date | None = None) -> Decimal:
    query = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter_by(
        owner_id=current_user.id, kind=kind
    )
    if start:
        query = query.filter(Transaction.happened_on >= start)
    if end:
        query = query.filter(Transaction.happened_on < end)
    return Decimal(query.scalar() or 0)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _parse_transaction(form_data, existing: Transaction | None = None):
    kind = (form_data.get("kind") or "").strip()
    if kind not in TRANSACTION_KINDS:
        raise ValueError("Vui lòng chọn loại giao dịch hợp lệ.")

    try:
        amount = Decimal((form_data.get("amount") or "").strip())
    except InvalidOperation:
        raise ValueError("Số tiền phải là số nguyên dương tính theo VND.") from None
    if not amount.is_finite() or amount <= 0 or amount > MAX_AMOUNT or amount != amount.to_integral_value():
        raise ValueError("Số tiền phải là số nguyên dương, tối đa 99.999.999.999.999 ₫.")

    happened_on = _parse_date(form_data.get("happened_on"))
    if happened_on is None:
        raise ValueError("Vui lòng nhập ngày giao dịch hợp lệ.")

    try:
        category_id = int(form_data.get("category_id", ""))
    except (TypeError, ValueError):
        raise ValueError("Vui lòng chọn danh mục.") from None
    category = Category.query.filter_by(
        id=category_id, owner_id=current_user.id, kind=kind
    ).first()
    if category is None:
        raise ValueError("Danh mục không hợp lệ hoặc không thuộc loại giao dịch đã chọn.")

    note = (form_data.get("note") or "").strip()
    if len(note) > 500:
        raise ValueError("Ghi chú không được dài quá 500 ký tự.")

    transaction = existing or Transaction(owner_id=current_user.id)
    transaction.kind = kind
    transaction.category_id = category.id
    transaction.amount = amount
    transaction.happened_on = happened_on
    transaction.note = note
    return transaction


@main.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("Email này đã được đăng ký.", "error")
            return render_template("register.html", form=form)
        user = User(name=form.name.data.strip(), email=email)
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.flush()
            for kind, names in DEFAULT_CATEGORIES.items():
                db.session.add_all(Category(owner_id=user.id, name=name, kind=kind) for name in names)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Không thể tạo tài khoản với email này. Hãy thử lại.", "error")
            return render_template("register.html", form=form)
        logger.info("auth_register_success", extra={"event": "auth_register_success", "user_id": user.id})
        flash("Tài khoản đã sẵn sàng. Hãy đăng nhập để tiếp tục.", "success")
        return redirect(url_for("main.login"))
    return render_template("register.html", form=form)


@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(form.password.data):
            logger.warning("auth_login_failed", extra={"event": "auth_login_failed"})
            flash("Email hoặc mật khẩu chưa chính xác.", "error")
            return render_template("login.html", form=form)
        session.clear()
        session.permanent = True
        login_user(user, remember=False, fresh=True)
        logger.info("auth_login_success", extra={"event": "auth_login_success", "user_id": user.id})
        flash("Đăng nhập thành công.", "success")
        return redirect(url_for("main.index"))
    return render_template("login.html", form=form)


@main.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Bạn đã đăng xuất.", "success")
    return redirect(url_for("main.login"))


@main.get("/")
@login_required
def index():
    today = _today()
    month_start = today.replace(day=1)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    monthly_income = _sum_amount("income", month_start, next_month)
    monthly_expense = _sum_amount("expense", month_start, next_month)
    total_income = _sum_amount("income")
    total_expense = _sum_amount("expense")

    months = []
    month_names = ["Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
                   "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"]
    for offset in reversed(range(6)):
        month_index = today.year * 12 + today.month - 1 - offset
        year, month_zero = divmod(month_index, 12)
        month = month_zero + 1
        start = date(year, month, 1)
        end = date(year + (month == 12), month % 12 + 1, 1)
        income = _sum_amount("income", start, end)
        expense = _sum_amount("expense", start, end)
        months.append({
            "label": month_names[month - 1],
            "income": income,
            "expense": expense,
        })
    chart_max = max((max(row["income"], row["expense"]) for row in months), default=Decimal(0)) or Decimal(1)
    for row in months:
        row["income_pct"] = int(row["income"] * 100 / chart_max)
        row["expense_pct"] = int(row["expense"] * 100 / chart_max)

    recent = (Transaction.query.filter_by(owner_id=current_user.id)
              .order_by(Transaction.happened_on.desc(), Transaction.id.desc()).limit(6).all())
    return render_template(
        "index.html",
        today=today,
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        monthly_balance=monthly_income - monthly_expense,
        overall_balance=total_income - total_expense,
        months=months,
        recent=recent,
        has_demo_data=Transaction.query.filter_by(owner_id=current_user.id)
        .filter(Transaction.note.like(f"{DEMO_NOTE_PREFIX}%")).first() is not None,
    )


@main.post("/demo-data/create")
@login_required
def create_demo_data():
    demo_query = Transaction.query.filter_by(owner_id=current_user.id).filter(
        Transaction.note.like(f"{DEMO_NOTE_PREFIX}%")
    )
    if demo_query.first() is not None:
        flash("Tài khoản đã có dữ liệu mẫu.", "info")
        return redirect(url_for("main.index"))

    income_categories = Category.query.filter_by(
        owner_id=current_user.id, kind="income"
    ).order_by(Category.id).all()
    expense_categories = Category.query.filter_by(
        owner_id=current_user.id, kind="expense"
    ).order_by(Category.id).all()
    if not income_categories or not expense_categories:
        flash("Hãy tạo ít nhất một danh mục thu và một danh mục chi trước.", "error")
        return redirect(url_for("main.index"))

    today = _today()
    sample_rows = []
    for offset in reversed(range(6)):
        month_index = today.year * 12 + today.month - 1 - offset
        year, month_zero = divmod(month_index, 12)
        month = month_zero + 1
        current_month = offset == 0
        dates = (
            date(year, month, 1),
            date(year, month, min(8, today.day) if current_month else 8),
            date(year, month, min(20, today.day) if current_month else 20),
        )
        sample_rows.extend((
            Transaction(
                owner_id=current_user.id,
                category_id=income_categories[offset % len(income_categories)].id,
                kind="income",
                amount=Decimal("15000000") + Decimal(offset * 150000),
                happened_on=dates[0],
                note=f"{DEMO_NOTE_PREFIX} Thu nhập mô phỏng {year}-{month:02d}",
            ),
            Transaction(
                owner_id=current_user.id,
                category_id=expense_categories[offset % len(expense_categories)].id,
                kind="expense",
                amount=Decimal("1250000") + Decimal(offset * 20000),
                happened_on=dates[1],
                note=f"{DEMO_NOTE_PREFIX} Sinh hoạt {year}-{month:02d}",
            ),
            Transaction(
                owner_id=current_user.id,
                category_id=expense_categories[(offset + 1) % len(expense_categories)].id,
                kind="expense",
                amount=Decimal("680000") + Decimal(offset * 10000),
                happened_on=dates[2],
                note=f"{DEMO_NOTE_PREFIX} Mua sắm {year}-{month:02d}",
            ),
        ))

    db.session.add_all(sample_rows)
    db.session.commit()
    flash("Đã tạo 18 giao dịch mẫu trong 6 tháng. Bạn có thể xóa bất cứ lúc nào.", "success")
    return redirect(url_for("main.index"))


@main.post("/demo-data/delete")
@login_required
def delete_demo_data():
    deleted = (Transaction.query.filter_by(owner_id=current_user.id)
               .filter(Transaction.note.like(f"{DEMO_NOTE_PREFIX}%"))
               .delete(synchronize_session=False))
    db.session.commit()
    if deleted:
        flash(f"Đã xóa {deleted} giao dịch mẫu.", "success")
    else:
        flash("Tài khoản không có giao dịch mẫu để xóa.", "info")
    return redirect(url_for("main.index"))


@main.get("/transactions")
@login_required
def transactions():
    query = Transaction.query.filter_by(owner_id=current_user.id)
    kind = request.args.get("kind", "")
    category_id = request.args.get("category_id", "")
    start_value = request.args.get("start", "")
    end_value = request.args.get("end", "")
    start = _parse_date(start_value)
    end = _parse_date(end_value)
    if kind in TRANSACTION_KINDS:
        query = query.filter_by(kind=kind)
    else:
        kind = ""
    if category_id.isdigit():
        query = query.filter_by(category_id=int(category_id))
    else:
        category_id = ""
    if start_value and start is None:
        flash("Ngày bắt đầu không hợp lệ.", "error")
        start_value = ""
    if end_value and end is None:
        flash("Ngày kết thúc không hợp lệ.", "error")
        end_value = ""
    if start:
        query = query.filter(Transaction.happened_on >= start)
    if end:
        query = query.filter(Transaction.happened_on <= end)
    if start and end and start > end:
        flash("Ngày bắt đầu cần trước hoặc trùng ngày kết thúc.", "error")
        query = Transaction.query.filter_by(owner_id=current_user.id)
        start_value = end_value = ""
    rows = query.order_by(Transaction.happened_on.desc(), Transaction.id.desc()).limit(500).all()
    return render_template(
        "transactions.html", transactions=rows, categories=_categories(),
        selected_kind=kind, selected_category=category_id, start_value=start_value, end_value=end_value,
        today=_today(),
    )


@main.post("/transactions/new")
@login_required
def create_transaction():
    try:
        transaction = _parse_transaction(request.form)
        db.session.add(transaction)
        db.session.commit()
        flash("Đã lưu giao dịch.", "success")
        return redirect(url_for("main.transactions"))
    except ValueError as exc:
        flash(str(exc), "error")
    except IntegrityError:
        db.session.rollback()
        flash("Không thể lưu giao dịch. Hãy kiểm tra danh mục và thử lại.", "error")
    return redirect(url_for("main.transactions"))


@main.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id: int):
    transaction = Transaction.query.filter_by(id=transaction_id, owner_id=current_user.id).first_or_404()
    if request.method == "POST":
        try:
            _parse_transaction(request.form, existing=transaction)
            db.session.commit()
            flash("Đã cập nhật giao dịch.", "success")
            return redirect(url_for("main.transactions"))
        except ValueError as exc:
            flash(str(exc), "error")
        except IntegrityError:
            db.session.rollback()
            flash("Không thể cập nhật giao dịch. Hãy thử lại.", "error")
    return render_template("edit_transaction.html", transaction=transaction, categories=_categories())


@main.post("/transactions/<int:transaction_id>/delete")
@login_required
def delete_transaction(transaction_id: int):
    transaction = Transaction.query.filter_by(id=transaction_id, owner_id=current_user.id).first_or_404()
    db.session.delete(transaction)
    db.session.commit()
    flash("Đã xóa giao dịch.", "success")
    return redirect(url_for("main.transactions"))


@main.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        kind = (request.form.get("kind") or "").strip()
        if not name or len(name) > 80 or kind not in TRANSACTION_KINDS:
            flash("Tên danh mục hoặc loại danh mục chưa hợp lệ.", "error")
        elif Category.query.filter_by(owner_id=current_user.id, name=name, kind=kind).first():
            flash("Danh mục cùng loại này đã tồn tại.", "error")
        else:
            db.session.add(Category(owner_id=current_user.id, name=name, kind=kind))
            try:
                db.session.commit()
                flash("Đã tạo danh mục.", "success")
                return redirect(url_for("main.categories"))
            except IntegrityError:
                db.session.rollback()
                flash("Không thể tạo danh mục. Hãy thử lại.", "error")
    return render_template("categories.html", categories=_categories())


@main.post("/categories/<int:category_id>/edit")
@login_required
def edit_category(category_id: int):
    category = Category.query.filter_by(id=category_id, owner_id=current_user.id).first_or_404()
    name = (request.form.get("name") or "").strip()
    kind = (request.form.get("kind") or "").strip()
    if not name or len(name) > 80 or kind not in TRANSACTION_KINDS:
        flash("Tên hoặc loại danh mục chưa hợp lệ.", "error")
    elif category.transactions and category.kind != kind:
        flash("Không thể đổi loại danh mục đã được giao dịch sử dụng.", "error")
    elif Category.query.filter(
        Category.owner_id == current_user.id, Category.name == name, Category.kind == kind,
        Category.id != category.id,
    ).first():
        flash("Danh mục cùng loại này đã tồn tại.", "error")
    else:
        category.name = name
        category.kind = kind
        try:
            db.session.commit()
            flash("Đã cập nhật danh mục.", "success")
            return redirect(url_for("main.categories"))
        except IntegrityError:
            db.session.rollback()
            flash("Không thể cập nhật danh mục. Hãy thử lại.", "error")
    return redirect(url_for("main.categories"))


@main.post("/categories/<int:category_id>/delete")
@login_required
def delete_category(category_id: int):
    category = Category.query.filter_by(id=category_id, owner_id=current_user.id).first_or_404()
    if category.transactions:
        flash("Danh mục đang có giao dịch nên chưa thể xóa.", "error")
    else:
        db.session.delete(category)
        db.session.commit()
        flash("Đã xóa danh mục.", "success")
    return redirect(url_for("main.categories"))


@main.get("/reports")
@login_required
def reports():
    today = _today()
    default_start = today.replace(day=1)
    start_value = request.args.get("start", default_start.isoformat())
    end_value = request.args.get("end", today.isoformat())
    start = _parse_date(start_value)
    end = _parse_date(end_value)
    if start is None or end is None or start > end:
        flash("Khoảng thời gian không hợp lệ. Đang hiển thị tháng hiện tại.", "error")
        start, end = default_start, today
        start_value, end_value = start.isoformat(), end.isoformat()
    end_exclusive = end + timedelta(days=1)
    income = _sum_amount("income", start, end_exclusive)
    expense = _sum_amount("expense", start, end_exclusive)
    grouped = (db.session.query(Category.name, Transaction.kind, func.sum(Transaction.amount))
               .join(Transaction, Transaction.category_id == Category.id)
               .filter(Transaction.owner_id == current_user.id,
                       Transaction.happened_on >= start,
                       Transaction.happened_on < end_exclusive)
               .group_by(Category.name, Transaction.kind)
               .order_by(func.sum(Transaction.amount).desc()).all())
    category_rows = [{"name": name, "kind": kind, "amount": Decimal(amount)}
                     for name, kind, amount in grouped]
    max_category = max((row["amount"] for row in category_rows), default=Decimal(1)) or Decimal(1)
    for row in category_rows:
        row["pct"] = int(row["amount"] * 100 / max_category)
    return render_template(
        "reports.html", start_value=start_value, end_value=end_value,
        income=income, expense=expense, balance=income - expense, category_rows=category_rows,
    )
