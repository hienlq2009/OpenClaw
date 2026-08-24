# OpenClaw — Bộ công cụ tối ưu giakelongquyen.com

Công cụ quét, chẩn đoán và tối ưu SEO / AIO / AEO cho website
[giakelongquyen.com](https://giakelongquyen.com) — Công ty TNHH Sản xuất và
Thương mại Long Quyền, nhà sản xuất giá kệ kho hàng công nghiệp tại Hà Nội.

## Nội dung

| Đường dẫn | Mục đích |
|---|---|
| `scripts/audit.py` | Trình quét SEO/AEO, chỉ dùng thư viện chuẩn Python |
| `scripts/wp.py` | Client WordPress REST API để sửa lỗi an toàn (chạy thử mặc định, tự sao lưu, hoàn tác được) |
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

Phiên 2026-08-24 **chưa quét được site**. Còn đúng một việc chặn:

| Lớp chặn | Trạng thái |
|---|---|
| Quyền ghi WordPress | đã gỡ — dùng Application Password |
| Tường lửa mạng của môi trường | **còn chặn** `giakelongquyen.com:443` |

Chi tiết và cách xử lý nằm trong `docs/ACCESS.md`.

Cả hai công cụ đã kiểm thử end-to-end: `audit.py` chạy trên site giả lập có lỗi
cài sẵn và bắt đúng toàn bộ; `wp.py` chạy trên máy chủ REST giả lập, xác nhận
đủ vòng ghi → sao lưu → hoàn tác. Sẵn sàng chạy ngay khi tên miền được mở.
