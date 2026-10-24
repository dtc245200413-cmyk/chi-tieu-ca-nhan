from datetime import date

from app.extensions import db
from app.models import Category, Transaction, User


def registration_data(email="tester@example.com", name="Test User", password="TestPassword!2026"):
    return {
        "name": name,
        "email": email,
        "password": password,
        "confirm": password,
    }


def register_and_login(client, email="tester@example.com", name="Test User", password="TestPassword!2026"):
    response = client.post("/register", data=registration_data(email, name, password))
    assert response.status_code == 302
    response = client.post("/login", data={"email": email, "password": password}, follow_redirects=True)
    assert response.status_code == 200
    return response


def category_for(app, email, kind):
    user = User.query.filter_by(email=email).one()
    return Category.query.filter_by(owner_id=user.id, kind=kind).first()


def create_transaction(client, category_id, kind, amount, note, happened_on=None):
    return client.post(
        "/transactions/new",
        data={
            "category_id": str(category_id),
            "kind": kind,
            "amount": str(amount),
            "happened_on": (happened_on or date.today()).isoformat(),
            "note": note,
        },
    )


def test_health_and_public_pages(client):
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json == {"status": "ok", "database": "ok"}
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200
    assert client.get("/css/style.css").status_code == 200
    assert client.get("/js/app.js").status_code == 200


def test_private_pages_redirect_when_logged_out(client):
    for path in ("/", "/transactions", "/categories", "/reports"):
        response = client.get(path)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_registration_creates_default_categories_and_login(client, app):
    response = register_and_login(client)
    assert b"aria-current=\"page\"" in response.data
    with app.app_context():
        user = User.query.filter_by(email="tester@example.com").one()
        assert user.check_password("TestPassword!2026")
        assert Category.query.filter_by(owner_id=user.id).count() == 12


def test_registration_rejects_short_password(client, app):
    response = client.post(
        "/register",
        data=registration_data(password="short", email="short@example.com"),
    )
    assert response.status_code == 200
    with app.app_context():
        assert User.query.filter_by(email="short@example.com").count() == 0


def test_duplicate_registration_and_invalid_login(client, app):
    register_and_login(client)
    client.post("/logout")
    duplicate = client.post("/register", data=registration_data())
    assert duplicate.status_code == 200
    bad_login = client.post(
        "/login",
        data={"email": "tester@example.com", "password": "wrong-password"},
    )
    assert bad_login.status_code == 200
    with app.app_context():
        assert User.query.filter_by(email="tester@example.com").count() == 1


def test_navigation_marks_the_current_section(client):
    register_and_login(client)
    for path, label in (
        ("/", "Tổng quan"),
        ("/transactions", "Giao dịch"),
        ("/categories", "Danh mục"),
        ("/reports", "Báo cáo"),
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert response.data.count(b"aria-current=\"page\"") == 1
        assert label.encode() in response.data


def test_transaction_create_filter_edit_delete_and_reports(client, app):
    register_and_login(client)
    with app.app_context():
        expense = category_for(app, "tester@example.com", "expense")
        income = category_for(app, "tester@example.com", "income")
        expense_id, income_id = expense.id, income.id

    today = date.today()
    assert create_transaction(client, income_id, "income", 2_000_000, "test-income", today).status_code == 302
    assert create_transaction(client, expense_id, "expense", 500_000, "test-expense", today).status_code == 302

    page = client.get("/transactions")
    assert page.status_code == 200
    assert b"test-income" in page.data and b"test-expense" in page.data
    assert client.get("/transactions?kind=income").status_code == 200
    filtered = client.get("/transactions?kind=expense")
    assert b"test-expense" in filtered.data and b"test-income" not in filtered.data
    dated = client.get(f"/transactions?start={today.isoformat()}&end={today.isoformat()}")
    assert b"test-income" in dated.data and b"test-expense" in dated.data

    with app.app_context():
        expense_row = Transaction.query.filter_by(note="test-expense").one()
        expense_tx_id = expense_row.id
    edit_page = client.get(f"/transactions/{expense_tx_id}/edit")
    assert edit_page.status_code == 200
    edited = client.post(
        f"/transactions/{expense_tx_id}/edit",
        data={
            "category_id": str(expense_id),
            "kind": "expense",
            "amount": "750000",
            "happened_on": today.isoformat(),
            "note": "test-expense-edited",
        },
    )
    assert edited.status_code == 302
    assert b"test-expense-edited" in client.get("/transactions").data

    report = client.get(f"/reports?start={today.isoformat()}&end={today.isoformat()}")
    assert report.status_code == 200
    assert b"2.000.000" in report.data and b"750.000" in report.data

    deleted = client.post(f"/transactions/{expense_tx_id}/delete")
    assert deleted.status_code == 302
    remaining = client.get("/transactions")
    assert b"test-expense-edited" not in remaining.data
    assert b"test-income" in remaining.data


def test_invalid_transaction_is_not_saved(client, app):
    register_and_login(client)
    with app.app_context():
        expense = category_for(app, "tester@example.com", "expense")
        expense_id = expense.id

    response = create_transaction(client, expense_id, "expense", -1, "invalid-amount")
    assert response.status_code == 302
    with app.app_context():
        assert Transaction.query.count() == 0


def test_category_create_edit_and_delete(client, app):
    register_and_login(client)
    added = client.post("/categories", data={"name": "Test Category", "kind": "expense"})
    assert added.status_code == 302
    page = client.get("/categories")
    assert b"Test Category" in page.data

    with app.app_context():
        user = User.query.filter_by(email="tester@example.com").one()
        category = Category.query.filter_by(owner_id=user.id, name="Test Category").one()
        category_id = category.id
    edited = client.post(
        f"/categories/{category_id}/edit",
        data={"name": "Updated Category", "kind": "income"},
    )
    assert edited.status_code == 302
    assert b"Updated Category" in client.get("/categories").data

    deleted = client.post(f"/categories/{category_id}/delete")
    assert deleted.status_code == 302
    assert b"Updated Category" not in client.get("/categories").data


def test_category_in_use_cannot_change_type_or_be_deleted(client, app):
    register_and_login(client)
    client.post("/categories", data={"name": "Used Category", "kind": "expense"})
    with app.app_context():
        user = User.query.filter_by(email="tester@example.com").one()
        category = Category.query.filter_by(owner_id=user.id, name="Used Category").one()
        category_id = category.id
    create_transaction(client, category_id, "expense", 1000, "use-category")

    client.post(
        f"/categories/{category_id}/edit",
        data={"name": "Used Category", "kind": "income"},
    )
    client.post(f"/categories/{category_id}/delete")
    with app.app_context():
        category = db.session.get(Category, category_id)
        assert category is not None
        assert category.kind == "expense"
        assert Transaction.query.filter_by(category_id=category_id).count() == 1


def test_user_data_is_isolated(client, app):
    register_and_login(client, "first@example.com", "First User")
    with app.app_context():
        user = User.query.filter_by(email="first@example.com").one()
        expense = Category.query.filter_by(owner_id=user.id, kind="expense").first()
        category_id = expense.id
    create_transaction(client, category_id, "expense", 1234, "private-first-user-note")
    with app.app_context():
        transaction_id = Transaction.query.filter_by(note="private-first-user-note").one().id

    second = app.test_client()
    register_and_login(second, "second@example.com", "Second User")
    assert b"private-first-user-note" not in second.get("/transactions").data
    assert second.get(f"/transactions/{transaction_id}/edit").status_code == 404


def test_invalid_report_dates_render_safely(client):
    register_and_login(client)
    response = client.get("/reports?start=not-a-date&end=also-invalid")
    assert response.status_code == 200
    assert b"B\xc3\xa1o c\xc3\xa1o" in response.data
