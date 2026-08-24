# Quy trình vận hành hàng ngày - giakelongquyen.com

Tài liệu thao tác cho phiên tối ưu tự động. Trước khi chạy, kiểm tra
`docs/ACCESS.md` để chắc chắn hai lớp chặn đã được gỡ.

## Bước 1 — Quét

```bash
python3 scripts/audit.py \
  --base https://giakelongquyen.com \
  --out reports/ \
  --max-urls 40 \
  --check-images
```

Trình quét lấy URL từ `sitemap.xml`. Muốn chỉ định danh sách trang cố định
(trang chủ + 10 trang sản phẩm chính + 5 bài mới nhất) thì tạo file danh sách
và truyền `--paths`:

```bash
python3 scripts/audit.py --base https://giakelongquyen.com --paths docs/priority-urls.txt
```

Kết quả ra hai file trong `reports/`: bản `.md` để đọc, bản `.json` để so sánh
với phiên trước.

### Trình quét kiểm tra những gì

| Nhóm | Nội dung kiểm tra |
|---|---|
| Truy cập | mã HTTP, chuỗi chuyển hướng, robots.txt, sitemap.xml |
| Chỉ mục | thẻ meta robots `noindex`, thẻ canonical |
| Thẻ meta | thiếu/quá ngắn/quá dài title và description |
| Cấu trúc | thiếu H1, trùng H1, nhảy cấp heading |
| Hình ảnh | thiếu alt, thiếu width/height, dung lượng > 200KB / > 500KB |
| Hiệu năng | script chặn render trong `<head>`, HTML nặng > 1MB |
| Chuyển đổi | cú pháp `tel:` và link Zalo, thiếu meta viewport |
| AEO | có/không JSON-LD, JSON-LD sai cú pháp, liệt kê các `@type` |
| Liên kết | link nội bộ và link ngoài trả về 4xx/5xx |

## Bước 2 — Chẩn đoán

Trình quét đã tự phân loại sẵn ba mức:

- **CRITICAL** — mất chuyển đổi hoặc chặn chỉ mục: hỏng `tel:`/Zalo, thiếu
  viewport, `noindex` ngoài ý muốn, link nội bộ gãy, HTTP lỗi
- **MEDIUM** — ảnh hưởng SEO: thiếu title/description/canonical/alt, trùng H1,
  thiếu schema, script chặn render
- **LOW** — tối ưu thêm: độ dài title/description chưa tối ưu, nhảy cấp heading,
  ảnh thiếu kích thước

Với mỗi lỗi, truy nguyên nhân gốc trước khi sửa: lỗi lặp trên nhiều trang
thường xuất phát từ template của theme, không phải từ nội dung từng trang. Sửa
ở template thì hết một lượt; sửa từng trang thì lỗi quay lại sau mỗi bài mới.

## Bước 3 — Sửa

### Được sửa tự động

- Bổ sung meta title / description còn thiếu
- Bổ sung alt cho ảnh
- Sửa link nội bộ gãy
- Sửa lỗi chính tả
- Sửa cấu trúc heading sai (H1 trùng, nhảy cấp)

### Phải chờ duyệt

- Xóa trang
- Đổi permalink
- Sửa code theme hoặc plugin
- Thay đổi cấu trúc menu
- Đụng tới hệ thống tên miền vệ tinh

Mọi thay đổi nội dung lớn: lưu bản nháp, không xuất bản thẳng.

### Công cụ sửa: `scripts/wp.py`

Nạp thông tin xác thực trước (xem `docs/ACCESS.md`):

```bash
export WP_BASE="https://giakelongquyen.com"
export WP_USER="LongQuyenAuto"
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
```

| Lệnh | Việc |
|---|---|
| `wp.py check` | Kiểm tra kết nối và quyền |
| `wp.py seo-detect` | Nhận diện plugin SEO và các khóa meta đọc được |
| `wp.py media-no-alt` | Liệt kê ảnh thiếu alt |
| `wp.py set-alt --id N --alt "..."` | Đặt alt cho ảnh |
| `wp.py find-link --url URL` | Tìm trang nào đang chứa một URL |
| `wp.py replace-link --old A --new B` | Thay URL trong nội dung |
| `wp.py backup --type all` | Sao lưu toàn bộ bài viết/trang |
| `wp.py restore --file ...` | Hoàn tác từ bản sao lưu |

### Ba lớp bảo vệ đã dựng sẵn

1. **Mặc định chạy thử.** Mọi lệnh ghi đều chỉ in ra dự định. Phải thêm
   `--apply` mới thực sự ghi lên site.
2. **Sao lưu trước khi ghi.** Bản gốc lưu vào `backups/<ngày>/<loại>-<id>.json`
   trước mỗi thao tác ghi.
3. **Nhật ký thay đổi.** Mỗi thay đổi ghi một dòng vào
   `backups/<ngày>/changes.jsonl` kèm giá trị cũ, giá trị mới và đường dẫn bản
   sao lưu.

Hoàn tác một thay đổi:

```bash
python3 scripts/wp.py restore --file backups/2026-08-24/post-11.json --apply
```

Công cụ **không có** lệnh xóa trang và **không có** lệnh đổi permalink — cố ý
thiết kế như vậy để một lỗi thao tác không thể gây hậu quả không hồi phục
được.

## Bước 4 — Tối ưu SEO + AIO/AEO

### Schema JSON-LD

Template nằm trong `schema/`, mọi giá trị cần điền đều ở dạng `{{TÊN_TRƯỜNG}}`:

| File | Đặt ở đâu |
|---|---|
| `organization.jsonld` | toàn site (thường nhúng ở footer hoặc header) |
| `localbusiness.jsonld` | trang chủ, trang liên hệ |
| `product.jsonld` | mỗi trang sản phẩm |
| `faqpage.jsonld` | trang có mục FAQ |
| `breadcrumblist.jsonld` | mọi trang có phân cấp |

Điền giá trị từ `docs/entity-profile.md` — không lấy từ nguồn khác, không đoán.
Thông số kỹ thuật (tải trọng, kích thước, vật liệu) **chỉ lấy từ catalogue
chính thức**. Thà để trống một trường còn hơn ghi sai một con số tải trọng: sai
thông số kỹ thuật giá kệ là rủi ro an toàn kho hàng, không chỉ là lỗi SEO.

Kiểm tra cú pháp trước khi dán lên site:

```bash
python3 -c "import json,sys; json.load(open(sys.argv[1]))" schema/product.jsonld
```

Sau khi lên site, đối chiếu bằng Google Rich Results Test.

### Viết câu trả lời trực tiếp (AEO)

Mỗi trang sản phẩm mở đầu bằng một đoạn 40–60 từ trả lời thẳng câu hỏi chính,
đặt ngay dưới H1, trước mọi nội dung marketing. Đây là đoạn AI trích dẫn.

Cấu trúc: **định nghĩa → đặc điểm phân biệt → dùng cho trường hợp nào**.

Các truy vấn cần có câu trả lời trực tiếp:

- kệ selective là gì
- kệ drive-in khác kệ selective thế nào
- giá kệ kho hàng bao nhiêu tiền
- nên chọn kệ nào cho kho lạnh / kho hàng luân chuyển nhanh
- sàn mezzanine chịu được tải trọng bao nhiêu
- kệ trung tải dùng cho mặt hàng nào

Nguyên tắc viết: câu đầu trả lời xong câu hỏi. Không mở bài, không "trong bối
cảnh hiện nay", không nhắc lại câu hỏi.

### Từ khóa thương mại

Nhóm chính: `giá kệ kho hàng`, `kệ selective`, `kệ drive-in`, `giá kệ công
nghiệp Hà Nội`, `kệ trung tải`, `kệ siêu thị`, `sàn mezzanine`.

Biến thể theo địa phương: ghép với Hà Nội, Bắc Ninh, Hưng Yên, Hải Phòng, Vĩnh
Phúc, Hải Dương — chỉ tạo trang riêng cho tỉnh nào thực sự có nội dung khác
biệt (dự án đã làm, kho thực tế). Trang địa phương rỗng ruột chỉ đổi tên tỉnh
là nội dung mỏng, có hại nhiều hơn lợi.

### Liên kết nội bộ

Trang sản phẩm ↔ bài viết liên quan, dùng anchor text tự nhiên theo ngữ cảnh.
Không dùng "xem thêm tại đây". Không nhồi cùng một anchor text vào mọi trang.

## Bước 5 — Báo cáo

Mẫu báo cáo cuối phiên:

| Mục | Kết quả |
|---|---|
| Số trang đã quét | |
| Lỗi phát hiện (CRITICAL / MEDIUM / LOW) | |
| Lỗi đã tự sửa | liệt kê kèm link trang |
| Việc chờ duyệt | liệt kê kèm lý do cần duyệt |
| Tối ưu đã thực hiện | |
| Đề xuất cho ngày mai | 1–3 việc ưu tiên |

So sánh với báo cáo phiên trước để thấy xu hướng:

```bash
python3 -c "
import json,glob
fs=sorted(glob.glob('reports/audit-*.json'))[-2:]
for f in fs:
    d=json.load(open(f))
    n=sum(len(p['issues']) for p in d['pages'])
    print(d['date'], 'trang:', len(d['pages']), 'loi:', n)
"
```

## Thứ tự ưu tiên

1. Lỗi làm mất chuyển đổi (nút gọi, Zalo, form báo giá hỏng)
2. Lỗi chặn chỉ mục (`noindex`, robots.txt chặn nhầm, canonical sai)
3. Link gãy nội bộ
4. Thiếu schema trên trang sản phẩm
5. Thiếu meta / alt
6. Tối ưu nội dung và liên kết nội bộ
