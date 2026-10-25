# Hệ thống Quản lý Chi tiêu (Expense Tracker)

## Thông tin đề tài

| Thông tin | Nội dung |
|---|---|
| Sinh viên | Nguyễn Thị Hồng Nhung |
| MSSV | DTC245200413 |
| Đề tài | Số 38 — Hệ thống Quản lý Chi tiêu (Expense Tracker) |
| Môn học | Triển khai và Quản trị Hệ thống Phần mềm |
| Lớp/khóa | CNTT K23E |

## Mục tiêu

Expense Tracker giúp người dùng ghi nhận thu nhập và chi tiêu, quản lý danh mục, lọc giao dịch, xem tổng quan theo tháng và lập báo cáo theo khoảng thời gian. Mỗi tài khoản chỉ được xem và thay đổi dữ liệu do chính tài khoản đó tạo.

## Công nghệ

- **Backend:** Python, Flask, Flask-Login, Flask-WTF, SQLAlchemy và Flask-Migrate.
- **Cơ sở dữ liệu:** PostgreSQL.
- **Triển khai:** Docker Compose.
- **Giám sát:** Prometheus, Grafana, cAdvisor, Node Exporter, PostgreSQL Exporter và Nginx Prometheus Exporter.
- **Thu thập log:** Loki và Promtail.
- **Reverse proxy:** Nginx unprivileged.
- **Giao diện:** HTML, CSS và JavaScript; tiếng Việt, hiển thị tiền theo VND.

## Tính năng

- Đăng ký, đăng nhập và đăng xuất; mật khẩu được băm, biểu mẫu có CSRF token.
- Quản lý danh mục thu và chi riêng theo tài khoản.
- Tạo, sửa, xóa và lọc giao dịch theo loại, danh mục và khoảng ngày.
- Xem tổng thu, tổng chi, số dư tích lũy và biểu đồ thu/chi sáu tháng.
- Xem báo cáo tổng thu/chi và phân nhóm theo danh mục trong khoảng ngày được chọn.
- PostgreSQL lưu dữ liệu bằng Docker volume; schema được quản lý bằng Flask-Migrate.

Danh mục mặc định được tạo khi người dùng đăng ký. Ứng dụng không tự chèn giao dịch mẫu.

## Cấu trúc dự án

```text
backend/
  app/                         # cấu hình, models, routes, forms và extensions
  migrations/                  # migration schema PostgreSQL
  Dockerfile
  requirements.txt
  run.py

frontend/
  css/
  js/
  *.html                       # giao diện Jinja được Flask phục vụ

monitoring/
  prometheus/
    docker-compose.yml
    prometheus.yml
  promtail/
    promtail-config.yml
  loki-config.yaml

nginx/
  default.conf

docker-compose.yml
.env.example
```

## Triển khai trên Ubuntu VM

### 1. Chuẩn bị tệp môi trường

Mở Ubuntu VM Terminal, chuyển đến thư mục dự án có `docker-compose.yml`, rồi chạy:

```bash
cd ~/chi-tieu-ca-nhan
cp .env.example .env
nano .env
```

Điền các biến được khai báo trong `.env.example`, gồm thông tin PostgreSQL, khóa bí mật của ứng dụng và tài khoản pgAdmin. Dùng các chuỗi bí mật khác nhau; có thể tạo chuỗi ngẫu nhiên bằng:

```bash
openssl rand -hex 32
```

Nếu cấu hình PostgreSQL Exporter yêu cầu thêm `POSTGRES_EXPORTER_USER` và `POSTGRES_EXPORTER_PASSWORD`, hãy tạo giá trị riêng cho hai biến này.

Không chụp hoặc gửi nội dung `.env` lên chat và không commit tệp `.env` lên GitHub.

### 2. Kiểm tra và khởi động ứng dụng

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Xem log khi cần chẩn đoán:

```bash
docker compose logs --tail=100 web db pgadmin nginx loki promtail
```

### 3. Địa chỉ truy cập

Trong Ubuntu VM:

| Dịch vụ | Địa chỉ |
|---|---|
| Ứng dụng qua Nginx | `http://localhost:8081` |
| Flask backend truy cập trực tiếp | `http://localhost:8000` |
| pgAdmin | `http://localhost:5050` |
| Grafana | `http://localhost:3000` |
| Prometheus | `http://localhost:9090` |

Từ Windows, thay `localhost` bằng địa chỉ IP của VM nếu mạng VM và tường lửa cho phép truy cập. Xem IP VM bằng:

```bash
hostname -I
```

PostgreSQL sử dụng cổng `5432` bên trong Docker network và không công bố cổng ra máy host. Khi đăng ký server trong pgAdmin, dùng hostname `db`, cổng `5432` và thông tin kết nối trong `.env`.

Loki sử dụng cổng `3100` nội bộ Docker; không cần mở cổng này ra máy host. Grafana truy vấn Loki qua Docker network.

## Prometheus và Grafana

Prometheus thu thập metrics từ các target:

- `prometheus`
- `node_exporter`
- `postgres_exporter`
- `cadvisor`
- `nginx`

Trên Prometheus, có thể xem trạng thái target tại `http://localhost:9090/targets`. Trong lần kiểm tra trên Ubuntu VM, tất cả các target trên đều ở trạng thái `up`.

Grafana được dùng để xem dữ liệu giám sát và truy vấn log trong **Explore**.

## Loki, Promtail và truy vấn LogQL

Promtail thu thập log từ các Docker container và gửi đến Loki. Trong Grafana, mở **Explore**, chọn nguồn dữ liệu **Loki**, rồi chạy các truy vấn:

```logql
{project="expense-tracker-project", service="nginx"}
```

```logql
{project="expense-tracker-project", service="web"}
```

```logql
{project="expense-tracker-project", service=~"nginx|web"}
```

Ba truy vấn trên đã được chạy trong Grafana Explore và trả về log trong lần kiểm tra trên Ubuntu VM.

## Các biện pháp bảo mật

- Nginx chạy bằng image unprivileged và tắt thông tin phiên bản qua `server_tokens off`.
- Nginx trả về các security headers như `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` và `Permissions-Policy`.
- PostgreSQL không công bố cổng ra máy host.
- Khóa bí mật và mật khẩu được lưu trong `.env`; không đưa `.env` lên GitHub.
- Backend chạy bằng người dùng không phải root trong container.
- Mật khẩu người dùng được băm; biểu mẫu có CSRF token và các truy vấn dữ liệu được giới hạn theo tài khoản.

## Trạng thái triển khai

Các dịch vụ đã được khởi động và kiểm tra trên Ubuntu VM:

- Web Flask được truy cập qua Nginx tại `http://localhost:8081`; yêu cầu chưa đăng nhập được chuyển hướng đến trang đăng nhập.
- Nginx trả về các security headers đã cấu hình.
- PostgreSQL và pgAdmin đã chạy.
- Prometheus có các target `cadvisor`, `nginx`, `node_exporter`, `postgres_exporter` và `prometheus` ở trạng thái `up`.
- Loki ở trạng thái healthy và Promtail đang chạy.
- Ba truy vấn LogQL trong Grafana Explore đã trả về log.

## Dừng ứng dụng

Để dừng các container thuộc Compose project hiện tại mà giữ dữ liệu trong volume:

```bash
docker compose down
```

Không dùng `docker compose down -v` nếu muốn giữ dữ liệu PostgreSQL, vì tùy chọn `-v` sẽ xóa volume.