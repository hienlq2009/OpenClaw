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

Khuyến nghị: **cách B** nếu chỉ cần đọc/sửa nội dung — rẻ hơn và đủ quyền cho
toàn bộ Bước 1–4. Chọn cách A nếu muốn dùng luôn các công cụ MCP dựng sẵn.

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
curl -sS -o /dev/null -w "%{http_code}\n" https://giakelongquyen.com/
python3 scripts/audit.py --base https://giakelongquyen.com --out reports/ --check-images
```

Trả về `200` và sinh được báo cáo trong `reports/` là đã thông.
