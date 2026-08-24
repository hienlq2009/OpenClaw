# Mở quyền truy cập giakelongquyen.com cho phiên tự động

Phiên ngày 2026-08-24 **không quét được site**. Có hai lớp chặn độc lập,
phải xử lý cả hai thì quy trình 5 bước mới chạy được.

## Chặn 1 — WordPress MCP không dùng được cho site này

`wpcom-user-sites` trả về cho blog ID `62155248` (giakelongquyen.com):

```
platform: jetpack
mcp_access.status: unavailable
reason_code: jetpack_paid_plan_required
```

Gọi thử `pages.list` và `settings.get` đều trả lỗi:
*"This action requires a paid Jetpack plan."*

Đây là site self-hosted nối qua Jetpack. Công cụ MCP theo site chỉ mở khi có
**Jetpack AI** hoặc **Jetpack Complete**.

### Cách xử lý (chọn một)

| Cách | Việc cần làm | Ưu / nhược |
|---|---|---|
| A. Nâng cấp Jetpack | Mua Jetpack AI hoặc Complete tại jetpack.com/pricing, sau đó bật MCP access trong màn hình Jetpack AI | Dùng ngay bộ công cụ MCP có sẵn, không phải cấu hình thêm. Tốn phí thuê bao |
| B. Application Password | Trong `wp-admin → Users → Profile → Application Passwords`, tạo mật khẩu ứng dụng, cấp cho phiên làm việc | Miễn phí, đi thẳng qua WordPress REST API (`/wp-json/wp/v2/`). Cần Chặn 2 được gỡ trước |

**Đã chốt: cách B (Application Password).** Tài khoản `LongQuyenAuto` đã được
cấp mật khẩu ứng dụng ngày 2026-08-24. Bộ công cụ `scripts/wp.py` trong repo đi
theo hướng này.

### Cách nạp thông tin xác thực

Mật khẩu **chỉ truyền qua biến môi trường**, không bao giờ ghi vào file trong
repo (`.gitignore` đã chặn, nhưng vẫn phải cẩn thận):

```bash
export WP_BASE="https://giakelongquyen.com"
export WP_USER="LongQuyenAuto"
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"

python3 scripts/wp.py check
```

Lưu ý bảo mật: mật khẩu ứng dụng đã từng được gửi dưới dạng văn bản thuần trong
cửa sổ chat. Sau khi mọi thứ chạy ổn định, nên thu hồi và cấp lại một mật khẩu
mới trong `wp-admin → Users → Profile → Application Passwords`. Mật khẩu ứng
dụng có thể thu hồi riêng lẻ mà không ảnh hưởng mật khẩu đăng nhập chính.

## Chặn 2 — Tường lửa mạng của phiên chặn tên miền

Mọi kết nối ra `giakelongquyen.com:443` đều bị egress proxy trả về 403:

```
kind: connect_rejected
detail: gateway answered 403 to CONNECT (policy denial or upstream failure)
host: giakelongquyen.com:443
```

Cả `curl` lẫn `WebFetch` đều hỏng. Đây là chính sách mạng của môi trường, không
phải lỗi site — và **không được đi vòng**.

### Cách xử lý

Thêm các tên miền sau vào danh sách cho phép của môi trường:

```
giakelongquyen.com
www.giakelongquyen.com
```

Nếu muốn đối chiếu chéo hệ thống site vệ tinh, thêm cả:
`kelongquyen.com`, `khogiake.com`, `wikirack.com`, `racking.longquyen.info`.

## Kiểm tra sau khi gỡ

```bash
# 1. Mạng đã thông chưa
curl -sS -o /dev/null -w "%{http_code}\n" https://giakelongquyen.com/

# 2. Xác thực đã chạy chưa
python3 scripts/wp.py check

# 3. Quét thử
python3 scripts/audit.py --base https://giakelongquyen.com --out reports/ --check-images
```

Bước 1 trả về `200`, bước 2 in ra tên người dùng và danh sách quyền, bước 3
sinh được báo cáo trong `reports/` là đã thông cả hai lớp.

## Chặn 3 — SiteGround chặn IP trung tâm dữ liệu bằng CAPTCHA

Sau khi gỡ xong hai lớp trên, mọi request tới site đều trả về một trang 169 byte:

```
HTTP/2 202
sg-captcha: challenge
x-sg-cdn: 1
x-robots-tag: noindex

<meta http-equiv="refresh" content="0;/.well-known/sgcaptcha/?r=%2F&y=ipc:160.79.106.137...">
```

Anti-Bot AI của SiteGround chặn IP trung tâm dữ liệu. Đã kiểm tra và loại trừ:

| Thử nghiệm | Kết quả |
|---|---|
| User-Agent Chrome thật | vẫn `202`, vẫn CAPTCHA |
| `robots.txt`, `sitemap.xml`, `/wp-json/` | cả ba đều bị chặn |
| REST API có xác thực | bị chặn *trước* bước xác thực |
| Theo redirect kèm cookie jar | không đi được — `meta refresh` cần JavaScript |

IP của phiên **không cố định**: hai request cách nhau 30 giây cho hai IP khác
nhau (`160.79.106.137` rồi `160.79.106.133`). Whitelist một IP đơn lẻ sẽ hỏng
ngay ở phiên sau.

### Cách xử lý — đã chọn

**Chạy quét tại máy người dùng.** Trình quét chỉ dùng thư viện chuẩn Python nên
chạy được ở bất cứ đâu; IP nhà mạng Việt Nam không bị chặn. Xem
`docs/CHAY-TAI-MAY.md`.

Hai cách còn lại đã cân nhắc và không chọn: tắt Anti-Bot AI (hạ thấp bảo mật
site) hoặc whitelist dải IP (không bền vì IP xoay theo pool).

## Trạng thái ngày 2026-08-24

| Lớp chặn | Trạng thái |
|---|---|
| Quyền ghi WordPress | ✅ đã gỡ — Application Password cho `LongQuyenAuto` |
| Tường lửa mạng môi trường | ✅ đã gỡ — allowlist `giakelongquyen.com` |
| Chống bot SiteGround | ⚠️ còn — xử lý bằng cách chạy quét tại máy người dùng |
