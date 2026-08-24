# OpenClaw — Bộ công cụ tối ưu giakelongquyen.com

Công cụ quét, chẩn đoán và tối ưu SEO / AIO / AEO cho website
[giakelongquyen.com](https://giakelongquyen.com) — Công ty TNHH Sản xuất và
Thương mại Long Quyền, nhà sản xuất giá kệ kho hàng công nghiệp tại Hà Nội.

## Nội dung

| Đường dẫn | Mục đích |
|---|---|
| `scripts/audit.py` | Trình quét SEO/AEO, chỉ dùng thư viện chuẩn Python |
| `docs/RUNBOOK.md` | Quy trình vận hành 5 bước hàng ngày |
| `docs/ACCESS.md` | Cách gỡ hai lớp chặn truy cập (bắt buộc đọc trước) |
| `docs/entity-profile.md` | Nguồn dữ liệu chuẩn về doanh nghiệp (E-E-A-T) |
| `docs/priority-urls.txt` | Danh sách trang ưu tiên quét mỗi phiên |
| `schema/*.jsonld` | Template JSON-LD: Organization, LocalBusiness, Product, FAQPage, BreadcrumbList |

## Bắt đầu

```bash
# 1. Gỡ chặn truy cập theo docs/ACCESS.md, sau đó kiểm tra
curl -sS -o /dev/null -w "%{http_code}\n" https://giakelongquyen.com/

# 2. Chạy quét
python3 scripts/audit.py --base https://giakelongquyen.com --out reports/ --check-images

# 3. Đọc báo cáo
cat reports/audit-$(date +%F).md
```

Không cần cài đặt gì thêm — trình quét chỉ dùng thư viện chuẩn của Python 3.

## Trạng thái hiện tại

Phiên 2026-08-24 **chưa quét được site**: công cụ WordPress MCP bị khóa sau gói
Jetpack trả phí, và tường lửa mạng của phiên chặn tên miền. Chi tiết và cách xử
lý nằm trong `docs/ACCESS.md`.

Bộ công cụ trong repo đã được kiểm thử end-to-end trên site giả lập có lỗi cài
sẵn và bắt đúng toàn bộ, sẵn sàng chạy ngay khi có quyền truy cập.
