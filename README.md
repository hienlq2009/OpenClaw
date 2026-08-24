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
| `docs/CHAY-TAI-MAY.md` | **Hướng dẫn chạy quét tại máy anh** — quy trình đang dùng |
| `docs/ACCESS.md` | Lịch sử ba lớp chặn truy cập và cách xử lý từng lớp |
| `docs/entity-profile.md` | Nguồn dữ liệu chuẩn về doanh nghiệp (E-E-A-T) |
| `docs/priority-urls.txt` | Danh sách trang ưu tiên quét mỗi phiên |
| `schema/*.jsonld` | Template JSON-LD: Organization, LocalBusiness, Product, FAQPage, BreadcrumbList |

## Bắt đầu

Chạy từ **máy của anh** (xem `docs/CHAY-TAI-MAY.md` để biết vì sao):

```bash
# 1. Kiểm tra mạng tới được site
curl -sS -o /dev/null -w "%{http_code}\n" https://giakelongquyen.com/   # cần 200

# 2. Chạy quét
python3 scripts/audit.py --base https://giakelongquyen.com --out reports/ --check-images

# 3. Đẩy báo cáo lên để phân tích
git add reports/ && git commit -m "Báo cáo quét $(date +%F)" && git push
```

Không cần cài đặt gì thêm — trình quét chỉ dùng thư viện chuẩn của Python 3.

## Trạng thái hiện tại

| Lớp chặn | Trạng thái |
|---|---|
| Quyền ghi WordPress | ✅ đã gỡ — Application Password |
| Tường lửa môi trường | ✅ đã gỡ — allowlist tên miền |
| Chống bot SiteGround | ⚠️ chặn IP trung tâm dữ liệu bằng CAPTCHA |

Vì lớp thứ ba, quy trình chia đôi: **anh chạy quét tại máy** rồi đẩy báo cáo
lên repo, phiên tự động lo phần phân tích và viết bản sửa. Cách này không phải
hạ thấp lớp chống bot của site. Chi tiết trong `docs/CHAY-TAI-MAY.md`.

Cả hai công cụ đã kiểm thử end-to-end: `audit.py` chạy trên site giả lập có lỗi
cài sẵn và bắt đúng toàn bộ; `wp.py` chạy trên máy chủ REST giả lập, xác nhận
đủ vòng ghi → sao lưu → hoàn tác.
