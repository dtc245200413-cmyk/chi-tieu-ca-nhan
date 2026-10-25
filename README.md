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
- Nginx reverse proxy chạy bằng image unprivileged và bổ sung các security headers cơ bản.
- Loki lưu log; Grafana Alloy đọc log container Docker và gửi log đến Loki.
- Grafana và Prometheus chạy riêng trong Ubuntu VMware; dự án không tạo thêm hai dịch vụ này.
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
nginx/
  default.conf         # reverse proxy tới Flask và security headers
monitoring/
  loki-config.yaml     # cấu hình Loki single-binary
  alloy/config.alloy   # chỉ thu log nginx, web, db và pgadmin của dự án
docker-compose.yml
.env.example
```

## Giám sát log

Grafana và Prometheus hiện có tiếp tục chạy ở stack riêng. Grafana sẽ đọc log từ Loki qua URL `http://loki:3100`. Loki không publish cổng 3100 ra máy Ubuntu hoặc Internet. Hai container Loki và Alloy dùng Docker network nội bộ `expense-monitoring` cùng với container Grafana.

Alloy chỉ thu log của các container có nhãn Compose project `expense-tracker-project` và service `nginx`, `web`, `db`, `pgadmin`. Tên này được xác nhận từ Ubuntu VM; bộ lọc không lấy log WordPress, Loki, Alloy hoặc project khác.

Alloy cần truy cập Docker socket để đọc log và metadata container. Socket được gắn vào container ở chế độ bind chỉ đọc và không publish ra mạng; hãy giữ Alloy trên Ubuntu VM và không mở Docker socket ra ngoài máy.

## Đồng bộ tệp từ Windows sang Ubuntu VM

Ứng dụng chạy trên Ubuntu VMware còn mã nguồn được chỉnh sửa trong VS Code trên Windows. Sau khi chỉnh sửa, chép các tệp dưới đây vào cùng thư mục dự án trên Ubuntu trước khi chạy Compose. Không chép `.env` từ Windows.

1. Trong Ubuntu Terminal, vào thư mục dự án (nơi có `docker-compose.yml`) và tạo thư mục cấu hình nếu chưa có:

   ```bash
   cd ~/expense-tracker-project
   mkdir -p nginx monitoring/alloy
   ```

   Nếu dự án ở đường dẫn khác, dùng đường dẫn thực tế đó.

2. Lấy IP VM bằng `hostname -I`. Ubuntu VM hiện báo `192.168.151.128`.

3. Mở PowerShell tại thư mục dự án trên Windows. Thay `TEN_NGUOI_DUNG` và `IP_VM` bằng tài khoản Ubuntu và IP thực tế, rồi chép các tệp đã sửa/tạo:

   ```powershell
   scp docker-compose.yml README.md .env.example TEN_NGUOI_DUNG@IP_VM:~/expense-tracker-project/
   scp nginx/default.conf TEN_NGUOI_DUNG@IP_VM:~/expense-tracker-project/nginx/
   scp monitoring/loki-config.yaml TEN_NGUOI_DUNG@IP_VM:~/expense-tracker-project/monitoring/
   scp monitoring/alloy/config.alloy TEN_NGUOI_DUNG@IP_VM:~/expense-tracker-project/monitoring/alloy/
   ```

   Cách này chép cả `.env.example` mẫu nhưng không sao chép `.env` hay mật khẩu. Nếu SSH/SCP chưa bật, có thể dùng thư mục chia sẻ VMware hoặc VS Code Remote - SSH.

## Tạo `.env` trên Ubuntu

Compose cần các biến sau. Không điền giá trị bí mật vào `.env.example`, không gửi nội dung `.env` qua chat và không commit `.env`:

   ```bash
   cd ~/expense-tracker-project
   [ -f .env ] || cp .env.example .env
   nano .env
   ```

Chạy lệnh trong thư mục làm việc của project hiện tại, không chạy ở `~`. Ảnh kiểm tra cho thấy project có hai tệp Compose ở hai thư mục; trước khi tạo hoặc sửa `.env`, xác nhận thư mục làm việc bằng lệnh inspect bên dưới. Không tạo một `.env` mới trong home và không ghi đè tệp `.env` đang được stack dùng.

   ```dotenv
   POSTGRES_DB=expense_tracker
   POSTGRES_USER=expense_app
   POSTGRES_PASSWORD=<chuỗi-ngẫu-nhiên-riêng>
   APP_SECRET_KEY=<chuỗi-ngẫu-nhiên-riêng>
   PGADMIN_DEFAULT_EMAIL=admin@example.local
   PGADMIN_DEFAULT_PASSWORD=<chuỗi-ngẫu-nhiên-riêng>
   ```

Chạy `openssl rand -hex 32` ba lần để tạo ba giá trị khác nhau cho PostgreSQL, Flask và pgAdmin; điền trực tiếp các kết quả vào `.env` trên VM. Nếu `.env` đã tồn tại, hãy sửa tệp đó thay vì ghi đè bằng bản mẫu.

## Kiểm tra Grafana và Docker network trên Ubuntu VM

Trước khi chạy Compose, mở Terminal trong Ubuntu và kiểm tra IP, container Grafana, network hiện có và tên project:

   ```bash
   hostname -I
   docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
   docker inspect grafana --format '{{json .NetworkSettings.Networks}}'
   docker network ls
   docker compose ls
   ```

Nếu container không tên `grafana`, dùng tên thực tế xuất hiện trong `docker ps` ở lệnh `docker inspect` và `docker network connect`. Nếu `docker compose ls` hiện project có tên khác tên thư mục, cập nhật regex trong `monitoring/alloy/config.alloy` và thay tên trong truy vấn LogQL bên dưới. Khi chạy Compose, thêm `-p TEN_PROJECT` với đúng tên đang có (ví dụ `docker compose -p TEN_PROJECT config --quiet`) để tiếp tục dùng project hiện tại, không tạo một nhóm container khác.

VM hiện báo project `expense-tracker-project` với hai tệp cấu hình `/home/ubuntu/chi-tieu-ca-nhan/docker-compose.yml` và `/home/ubuntu/expense-tracker-project/docker-compose.yml`. Xác nhận thư mục làm việc và danh sách tệp của container đang chạy bằng lệnh chỉ đọc này; hãy giữ đúng các tệp và thứ tự đó khi chạy lại Compose:

   ```bash
   docker inspect expense-tracker-project-web-1 --format 'working_dir={{index .Config.Labels "com.docker.compose.project.working_dir"}} config_files={{index .Config.Labels "com.docker.compose.project.config_files"}}'
   ```

Tạo Docker bridge chỉ dùng nội bộ cho Grafana và Loki. Nếu `expense-monitoring` đã tồn tại, kiểm tra bằng `docker network inspect expense-monitoring --format '{{.Driver}} {{.Internal}}'`; chỉ dùng lại nếu kết quả là `bridge true`. Nếu chưa có:

   ```bash
   docker network create --driver bridge --internal expense-monitoring
   ```

Nếu network cùng tên đã tồn tại nhưng kết quả không phải `bridge true`, hãy chọn một tên mới chưa dùng, thay giá trị `name` trong cuối `docker-compose.yml` và dùng tên mới đó trong các lệnh `docker network` bên dưới.

Kiểm tra kết quả `docker inspect grafana`. Nếu Grafana chưa có network `expense-monitoring`, kết nối nó (thay tên nếu container mang tên khác):

   ```bash
   docker network connect expense-monitoring grafana
   ```

## Chạy Compose trên Ubuntu VM

Đảm bảo `.env` đã được điền trên Ubuntu và hoàn thành phần network phía trên. Sau đó chạy:

   ```bash
   docker compose -p expense-tracker-project \
     -f /home/ubuntu/chi-tieu-ca-nhan/docker-compose.yml \
     -f /home/ubuntu/expense-tracker-project/docker-compose.yml config --quiet
   docker compose -p expense-tracker-project \
     -f /home/ubuntu/chi-tieu-ca-nhan/docker-compose.yml \
     -f /home/ubuntu/expense-tracker-project/docker-compose.yml up -d --build
   docker compose -p expense-tracker-project \
     -f /home/ubuntu/chi-tieu-ca-nhan/docker-compose.yml \
     -f /home/ubuntu/expense-tracker-project/docker-compose.yml ps
   ```

Ảnh Ubuntu hiện hiển thị hai tệp Compose trên. Nếu lệnh inspect cho thấy danh sách khác, thay bằng đúng các tệp đó và giữ nguyên thứ tự; chạy lệnh từ `working_dir` đã xác nhận. `config --quiet` kiểm tra cú pháp mà không in giá trị bí mật vào Terminal. `up` thêm Loki và Alloy vào project hiện tại; không chạy `docker compose down -v`.

Xem log khi cần chẩn đoán:

   ```bash
   docker compose -p expense-tracker-project \
     -f /home/ubuntu/chi-tieu-ca-nhan/docker-compose.yml \
     -f /home/ubuntu/expense-tracker-project/docker-compose.yml \
     logs --tail=100 nginx web db pgadmin loki alloy
   ```

Trong VM, Nginx reverse proxy mở tại `http://localhost:8081` và thêm `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` và `Permissions-Policy`. Ứng dụng Flask vẫn giữ cổng `8000`; pgAdmin ở `http://localhost:5050`; Grafana hiện có ở `http://localhost:3000`. Từ Windows thay `localhost` bằng IP VM thực tế. Loki chỉ mở nội bộ tại `http://loki:3100` trong network `expense-monitoring`; PostgreSQL không publish cổng ra host.

Để dừng dịch vụ mà không xóa container hoặc volume:

   ```bash
   docker compose -p expense-tracker-project \
     -f /home/ubuntu/chi-tieu-ca-nhan/docker-compose.yml \
     -f /home/ubuntu/expense-tracker-project/docker-compose.yml stop
   ```

Các volume `postgres_data`, `loki_data` và `alloy_data` lần lượt giữ dữ liệu PostgreSQL, log Loki và vị trí đọc log của Alloy.

## Thêm Loki trong Grafana và xem log

Grafana đã có vẫn giữ nguyên nguồn Prometheus. Sau khi Loki và Alloy chạy khỏe:

1. Mở `http://<IP_VM>:3000` và đăng nhập Grafana hiện có.
2. Chọn **Connections** → **Add new connection**, tìm và chọn **Loki**, rồi chọn **Add new data source**. Cần quyền Organization Admin để thêm nguồn dữ liệu.
3. Ở ô **URL**, nhập `http://loki:3100` (không dùng `localhost`).
4. Chọn **Save & test**. Nếu kết nối lỗi, kiểm tra Grafana có nằm trong network `expense-monitoring` không.
5. Mở **Explore**, chọn nguồn **Loki** và thử các truy vấn LogQL sau:

   ```logql
   {project="expense-tracker-project", service="web"}
   {project="expense-tracker-project", service="nginx"}
   {project="expense-tracker-project", service=~"web|db|pgadmin|nginx"} |~ "(?i)(error|exception|failed)"
   ```

Truy vấn đầu xem log ứng dụng; truy vấn thứ hai xem log reverse proxy Nginx; truy vấn thứ ba tìm dòng có lỗi trong bốn dịch vụ. Có thể đổi nhãn `service` để xem một dịch vụ khác. Chỉ log mới sau khi bộ thu log chạy mới được thu thập; log cũ không được nhập ngược tự động.

## Tính năng đã được xây dựng trong Giai đoạn 1

- Đăng ký, đăng nhập và đăng xuất; mật khẩu được băm và biểu mẫu có CSRF token.
- Mỗi người dùng có bộ danh mục thu/chi riêng; có thể tạo, sửa và xóa danh mục chưa được sử dụng.
- Tạo, sửa, xóa và lọc giao dịch theo loại, danh mục và khoảng ngày.
- Tổng quan thu, chi, số dư tích lũy và biểu đồ thu/chi sáu tháng.
- Báo cáo tổng thu/chi và phân nhóm theo danh mục cho khoảng ngày được chọn.
- PostgreSQL có volume lưu bền; schema được quản lý bằng Flask-Migrate.

Danh mục mặc định được tạo khi người dùng đăng ký; không có giao dịch mẫu được tự chèn. Ảnh minh chứng cần được chụp sau khi dịch vụ thật chạy trong VM.

## Trạng thái triển khai

| Yêu cầu trong đề | Trạng thái trong dự án |
| --- | --- |
| Mã nguồn và cấu hình có README | Đã có trong repository cục bộ; theo yêu cầu, chưa push lên GitHub. |
| Web, database và công cụ quản lý DB | Flask, PostgreSQL và pgAdmin đã có; các container đang chạy theo ảnh Ubuntu. |
| Nginx reverse proxy và bảo mật cơ bản | Đã thêm cấu hình Nginx unprivileged, reverse proxy và security headers; chờ chạy trên VM để xác nhận. |
| Prometheus và Grafana | Đã có trong stack riêng trên Ubuntu; không tạo bản trùng. Việc scrape ứng dụng/database cần xác minh trong cấu hình Prometheus hiện có. |
| Loki và truy vấn LogQL | Loki đã thêm; cấu hình hiện dùng Alloy và có ba truy vấn mẫu. Đề thi ghi Promtail, nên cần chốt bộ thu log trước khi đồng bộ. |
| Hardening | Flask và Nginx chạy bằng user không phải root; database không publish cổng; network quan sát nội bộ. Các biện pháp còn lại cần rà soát sau khi xác nhận stack đang chạy. |
| Báo cáo từ 10 trang có hình minh họa | Chưa tạo; cần ảnh kết quả Nginx, Prometheus/Grafana, Loki/Explore từ lần chạy thực tế để báo cáo không ghi nhận kết quả chưa kiểm chứng. |

Trước khi chạy lại Compose, đồng bộ tệp sang Ubuntu VM và xác nhận thư mục làm việc cùng danh sách hai tệp Compose của project hiện tại. Dùng đúng project `expense-tracker-project`; không xóa container hoặc volume, không chạy `docker compose down -v`.
