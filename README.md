# Hệ thống Quản lý Chi tiêu (Expense Tracker)

## Thông tin đề tài

- **Sinh viên:** Nguyễn Thị Hồng Nhung
- **MSSV:** DTC245200413
- **Đề tài số:** 38 — Hệ thống Quản lý Chi tiêu (Expense Tracker)
- **Môn học:** Triển khai và Quản trị Hệ thống Phần mềm
- **Lớp/khóa:** CNTT K23E

## Mục tiêu

Ứng dụng giúp cá nhân ghi nhận thu nhập và chi tiêu, quản lý danh mục, lọc giao dịch, xem tổng quan theo tháng và lập báo cáo theo thời gian. Mỗi tài khoản chỉ xem và thay đổi dữ liệu do chính tài khoản đó tạo.

## Công nghệ

- Python, Flask, Flask-Login, Flask-WTF, SQLAlchemy và Flask-Migrate.
- PostgreSQL lưu dữ liệu; Docker Compose quản lý ứng dụng, cơ sở dữ liệu và pgAdmin.
- Giao diện HTML/CSS/JavaScript tiếng Việt, hiển thị tiền theo VND.

## Cấu trúc hiện tại

```text
backend/
  app/                 # cấu hình, models, routes, forms và extensions
  migrations/          # migration schema PostgreSQL
  Dockerfile
  requirements.txt
  run.py
frontend/
  css/style.css
  js/app.js
  *.html               # giao diện Jinja được Flask phục vụ
docker-compose.yml
.env.example
```

## Chạy trên Ubuntu VM

Mở **Ubuntu VM Terminal**, chuyển đến thư mục dự án (thư mục có `docker-compose.yml`), rồi tạo tệp cấu hình riêng:

```bash
cp .env.example .env
nano .env
```

Trong `.env`, điền `POSTGRES_PASSWORD`, `APP_SECRET_KEY` và `PGADMIN_DEFAULT_PASSWORD` bằng ba chuỗi ngẫu nhiên khác nhau, mỗi chuỗi tối thiểu 32 ký tự. Trên VM có thể tạo chuỗi hex bằng `openssl rand -hex 32`; không chụp hoặc gửi nội dung `.env` lên chat, không commit tệp này.

Kiểm tra cấu hình và khởi động dịch vụ:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Xem log khi cần chẩn đoán:

```bash
docker compose logs --tail=100 web db pgadmin
```

Ở Giai đoạn 1, ứng dụng được mở qua `http://localhost:8000` trong VM; pgAdmin tại `http://localhost:5050`. Từ Windows, dùng `http://<IP_VM>:8000` và `http://<IP_VM>:5050` nếu mạng VM cho phép truy cập. Lấy địa chỉ VM bằng `hostname -I`. PostgreSQL không công bố cổng ra máy host; khi đăng ký server trong pgAdmin, dùng hostname `db`, cổng `5432` và thông tin kết nối trong `.env`.

Để dừng các container mà giữ nguyên dữ liệu:

```bash
docker compose down
```

Không dùng `docker compose down -v`; lệnh đó xóa volume PostgreSQL.

## Tính năng đã được xây dựng trong Giai đoạn 1

- Đăng ký, đăng nhập và đăng xuất; mật khẩu được băm và biểu mẫu có CSRF token.
- Mỗi người dùng có bộ danh mục thu/chi riêng; có thể tạo, sửa và xóa danh mục chưa được sử dụng.
- Tạo, sửa, xóa và lọc giao dịch theo loại, danh mục và khoảng ngày.
- Tổng quan thu, chi, số dư tích lũy và biểu đồ thu/chi sáu tháng.
- Báo cáo tổng thu/chi và phân nhóm theo danh mục cho khoảng ngày được chọn.
- PostgreSQL có volume lưu bền; schema được quản lý bằng Flask-Migrate.

Danh mục mặc định được tạo khi người dùng đăng ký; không có giao dịch mẫu được tự chèn. Ảnh minh chứng cần được chụp sau khi dịch vụ thật chạy trong VM.

## Trạng thái triển khai

Giai đoạn 0 đã khảo sát bộ khung hiện có. Giai đoạn 1 đã được chuẩn bị trong mã nguồn; cần khởi động và kiểm tra bằng Docker Compose trên Ubuntu VM để xác nhận trước khi chuyển sang Nginx. Nginx, giám sát Prometheus/Grafana, Loki/Promtail, cảnh báo, hardening và báo cáo tổng hợp sẽ được triển khai ở các giai đoạn tiếp theo.
