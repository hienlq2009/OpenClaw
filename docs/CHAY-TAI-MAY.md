# Hướng dẫn chạy quét tại máy của anh

Máy chủ SiteGround chặn IP trung tâm dữ liệu của phiên làm việc tự động bằng
CAPTCHA, nên phần **quét** phải chạy từ máy anh (hoặc một VPS đặt tại Việt
Nam). Phần **phân tích và viết bản sửa** vẫn do phiên tự động làm.

Cách chia việc:

```
Anh chạy quét tại máy  ─────►  đẩy báo cáo lên GitHub  ─────►  em phân tích, viết bản sửa
```

Trình quét chỉ dùng thư viện chuẩn của Python, không phải cài thêm gói nào.

## Lần đầu: chuẩn bị

### 1. Kiểm tra Python

Mở Terminal (macOS/Linux) hoặc PowerShell (Windows), gõ:

```bash
python3 --version
```

Cần Python 3.8 trở lên. Nếu báo lỗi không tìm thấy lệnh, tải tại
[python.org/downloads](https://www.python.org/downloads/). Trên Windows, khi cài
nhớ **tích ô "Add Python to PATH"**.

### 2. Tải mã nguồn về

```bash
git clone https://github.com/hienlq2009/OpenClaw.git
cd OpenClaw
git checkout claude/wordpress-giakelongquyen-optimize-k891pa
```

Nếu đã tải về từ trước, chỉ cần cập nhật:

```bash
cd OpenClaw
git checkout claude/wordpress-giakelongquyen-optimize-k891pa
git pull origin claude/wordpress-giakelongquyen-optimize-k891pa
```

## Mỗi phiên: chạy quét

```bash
python3 scripts/audit.py \
  --base https://giakelongquyen.com \
  --out reports/ \
  --check-images
```

Quét khoảng 40 trang lấy từ `sitemap.xml`. Mất chừng 3–8 phút tùy tốc độ mạng,
màn hình sẽ hiện tiến độ từng trang.

Muốn nhanh hơn khi thử lần đầu, bỏ `--check-images` và giảm số trang:

```bash
python3 scripts/audit.py --base https://giakelongquyen.com --out reports/ --max-urls 10
```

### Nếu máy anh cũng bị chặn CAPTCHA

**Không được chỉ nhìn mã HTTP.** SiteGround trả về cả `200` lẫn `202` cho cùng
một trang CAPTCHA — đã gặp thực tế: cùng một URL, request này `202`, request
sau `200`, nhưng cả hai đều trả về đúng trang challenge 169 byte đó. Nhìn mã
HTTP thôi sẽ báo xanh nhầm.

Lệnh kiểm tra đúng — xem **header** và **dung lượng**:

```bash
curl -sS -D - -o /dev/null https://giakelongquyen.com/ | grep -iE "sg-captcha|content-length"
```

- Không thấy dòng `sg-captcha` nào → tốt, chạy quét được
- Thấy `sg-captcha: challenge` → IP của anh đang bị chặn

Cách xử lý khi bị chặn: thử từ mạng khác (4G điện thoại chẳng hạn), hoặc vào
Site Tools của SiteGround thêm IP của anh vào danh sách tin cậy.

Anh cũng không cần nhớ lệnh trên — **trình quét tự kiểm tra trước khi chạy**.
Nếu phát hiện bị chặn, nó dừng lại ngay và báo rõ, thay vì sinh ra một báo cáo
sai đầy lỗi giả (vì nó sẽ đọc trang CAPTCHA 169 byte thay vì nội dung thật).

## Gửi báo cáo cho em

Sau khi quét xong sẽ có hai file trong thư mục `reports/`.

### Cách 1 — đẩy lên GitHub (khuyến nghị)

```bash
git add reports/
git commit -m "Báo cáo quét ngày $(date +%F)"
git push origin claude/wordpress-giakelongquyen-optimize-k891pa
```

Xong thì nhắn em một câu, em tự đọc báo cáo trên repo và bắt tay vào phân tích.

### Cách 2 — gửi thẳng file

Mở file `reports/audit-<ngày>.md`, copy toàn bộ nội dung dán vào khung chat.
Hoặc đính kèm file trực tiếp.

## Đọc nhanh báo cáo

Phần **Tổng quan** ở đầu file cho biết ngay có bao nhiêu lỗi mỗi mức:

- **CRITICAL** — mất chuyển đổi hoặc chặn Google index. Sửa trước.
- **MEDIUM** — ảnh hưởng thứ hạng tìm kiếm.
- **LOW** — tối ưu thêm khi rảnh.

Anh không cần tự phân tích — cứ gửi em file, em đọc và đề xuất từng việc kèm
mức ưu tiên.

## Phần sửa lỗi

Sau khi em đề xuất, việc sửa có hai đường:

**Anh tự sửa** trong `wp-admin` theo hướng dẫn em viết. An toàn nhất, anh nhìn
thấy từng thay đổi trước khi lưu.

**Hoặc chạy công cụ sửa tại máy anh** — cùng lý do như trên, `scripts/wp.py`
chạy từ máy anh sẽ không bị SiteGround chặn:

```bash
export WP_BASE="https://giakelongquyen.com"
export WP_USER="LongQuyenAuto"
export WP_APP_PASSWORD="mật khẩu ứng dụng của anh"

python3 scripts/wp.py check          # kiểm tra kết nối trước
python3 scripts/wp.py media-no-alt   # xem danh sách ảnh thiếu alt
```

Trên Windows PowerShell, thay `export X="..."` bằng `$env:X="..."`.

Mọi lệnh ghi đều **mặc định chạy thử**, chỉ in ra dự định chứ chưa đụng vào
site. Phải thêm `--apply` mới thực sự ghi, và trước mỗi lần ghi công cụ tự lưu
bản gốc vào `backups/` để hoàn tác được.
