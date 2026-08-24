# Hồ sơ thực thể - Nguồn dữ liệu chuẩn (E-E-A-T)

File này là **nguồn duy nhất đúng** cho thông tin doanh nghiệp. Mọi trang, mọi
khối schema, mọi hồ sơ mạng xã hội đều phải khớp file này từng ký tự. Sai lệch
thông tin thực thể là một trong những nguyên nhân hàng đầu khiến AI và công cụ
trả lời không dám trích dẫn website.

## Cần điền trước khi dùng

Các trường dưới đây **chưa được xác minh** vì phiên làm việc không truy cập
được site. Không được đoán — điền từ giấy đăng ký kinh doanh và catalogue chính
thức của công ty.

| Trường | Giá trị chuẩn | Trạng thái |
|---|---|---|
| Tên pháp lý đầy đủ | Công ty TNHH Sản xuất và Thương mại Long Quyền | cần xác minh |
| Tên thương hiệu | Giá Kệ Long Quyền | cần xác minh |
| Năm thành lập | `{{NAM_THANH_LAP}}` | **mâu thuẫn — xem bên dưới** |
| Địa chỉ nhà máy | `{{DIA_CHI_DAY_DU}}` | cần điền |
| Địa chỉ văn phòng | `{{DIA_CHI_VAN_PHONG}}` | cần điền |
| Mã số thuế | `{{MA_SO_THUE}}` | cần điền |
| Hotline | `{{SDT}}` (hiển thị) / `{{SDT_E164}}` (dùng trong `tel:`) | cần điền |
| Zalo OA | `{{URL_ZALO}}` | cần điền |
| Email | `{{EMAIL}}` | cần điền |
| Giờ làm việc | `{{GIO_LAM_VIEC}}` | cần điền |

## Mâu thuẫn cần chốt gấp: năm thành lập

Ba nguồn công khai đang nói ba con số khác nhau:

| Nguồn | Tuổi doanh nghiệp công bố |
|---|---|
| Yêu cầu công việc (khách hàng cung cấp) | gần 30 năm |
| Tiêu đề `giakelongquyen.com/en/` trên kết quả tìm kiếm | "30 Năm Sản Xuất & Lắp Đặt" |
| kelongquyen.com | "hơn 25 năm kinh nghiệm" |

Chênh lệch 5 năm giữa các tài sản số của cùng một doanh nghiệp. Cần chốt **một
năm thành lập duy nhất**, rồi thống nhất trên toàn bộ site, schema
`foundingDate`, Google Business Profile và fanpage.

Cách viết được khuyến nghị: ghi thẳng năm thành lập ("thành lập năm 1996") thay
vì "gần 30 năm" — câu chữ tính theo mốc tương đối sẽ tự sai sau mỗi năm, và AI
trích dẫn lại con số cũ.

## Quy tắc dùng số điện thoại

- Hiển thị cho người đọc: định dạng Việt Nam, ví dụ `0912 345 678`
- Trong thuộc tính `href`: **phải** ở dạng E.164 liền không dấu cách —
  `tel:+84912345678`
- Trong schema `telephone`: dùng dạng E.164

Khoảng trắng trong `tel:` làm hỏng nút gọi trên một số trình duyệt Android.
`scripts/audit.py` tự động bắt lỗi này (mã `contact_link_broken`).

## Hệ thống tên miền vệ tinh

Tài khoản đang giữ khoảng 20 tên miền cùng chủ đề giá kệ, phần lớn **đã ngắt
kết nối Jetpack** và không còn được cập nhật:

```
khogiake.com          1000giake.com        wikirack.com
giachuahang.com       giabayhang.com       khotanglung.com
noithatcongnghiep.info  racking.longquyen.info  khoxeday.com
santanglung.com       bansanxuat.com       bangchuyen.net
congnghiep.biz        quickrack.net        nhalaprap.com
giakecongnghiep.wordpress.com              go.longquyen.com
```

Rủi ro: nội dung trùng lặp và tự cạnh tranh từ khóa với site chính. Cơ hội: nếu
các tên miền này còn backlink, chuyển hướng 301 về trang tương ứng trên
giakelongquyen.com sẽ dồn được sức mạnh liên kết.

**Cần khảo sát trước khi động vào** — chưa có dữ liệu nên chưa đề xuất hành động
cụ thể. Việc này cần quyền duyệt của chủ site vì đụng tới cấu trúc tên miền.
