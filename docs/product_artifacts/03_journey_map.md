# User Journey Map

*Purpose: A Journey Map visualizes the end-to-end experience a user has with a product, from the moment they realize they have a problem to long-term advocacy. It breaks down silos, forcing the team to see the product not as isolated features, but as a continuous narrative.*

---

## 1. Discover (Khám phá)
*   **User Action:** Đức nhận task đầu tiên sửa đổi luồng xác thực trong codebase lạ. Tài liệu wiki nội bộ trống rỗng. Đức lên Google, GitHub và các hội nhóm lập trình viên Việt Nam tìm kiếm công cụ tự động giải thích kiến trúc codebase kèm lịch sử Git.
*   **Pain Points:** 
    *   Các chatbot AI thông thường chỉ đọc hiểu code tĩnh, hay ảo giác (hallucinate) và không có bối cảnh lịch sử thiết kế.
    *   `git blame` chỉ hiện tên người commit gần nhất (thường là một người sửa format code) chứ không giải thích lý do thiết kế ban đầu.
*   **Emotional State:** Lo lắng, bối rối, sợ làm gián đoạn thời gian của các đàn anh Senior.
*   **Impact:** Giúp định hình chiến lược SEO của DevOnboard nhắm vào các từ khóa: "tìm kiếm lịch sử code", "codebase onboarding tool", "git rationale search".

## 2. Aware (Nhận thức)
*   **User Action:** Đức tìm thấy DevOnboard qua một bài viết kỹ thuật chia sẻ về giải pháp "Bảo toàn tri thức codebase doanh nghiệp". Đức truy cập trang landing page hoặc file README của sản phẩm để đánh giá.
*   **User Evaluation:** Đức tự hỏi: "Công cụ này có an toàn bảo mật không? Có gửi code dự án của mình lên máy chủ bên thứ ba không? Có chạy local được không?". Đức nhận ra DevOnboard ưu tiên thiết kế local-first và bảo mật mã nguồn (Evidence-only mode).
*   **Objections:** Nghi ngờ về khả năng hoạt động thực tế: "Liệu AI có trích dẫn chính xác không hay lại dẫn link commit sai?".
*   **Impact:** Landing page của DevOnboard phải hiển thị rõ cam kết bảo mật mã nguồn chạy local và tính năng xác thực trích dẫn (provenance graph).

## 3. Convert (Chuyển đổi)
*   **User Action:** Đức quyết định tải DevOnboard và chạy giao diện local về máy. Cậu cấu hình nhanh bằng lệnh `cp .env.example .env`, mở web workspace, và chạy quét thử codebase mẫu `nextlevelbuilder/goclaw`.
*   **Time-to-Value (TTV):** Trong vòng **60 giây**, giao diện local hiển thị cấu trúc codebase dạng đồ thị tri thức, và Đức nhận được câu trả lời đầu tiên có trích dẫn đầy đủ link PR/Commit thực tế.
*   **Pain Points:** Nếu quá trình cài đặt yêu cầu cài nhiều package phức tạp hoặc nhập API key rườm rà, Đức sẽ nản và từ bỏ.
*   **Impact:** Tối ưu quy trình khởi chạy local cực đơn giản thông qua `Makefile` và cung cấp bộ fixture sẵn để kiểm chứng giá trị ngay lập tức.

## 4. Retain (Duy trì)
*   **User Action:** Đức biến DevOnboard thành một phần trong thói quen lập trình hàng ngày. Mỗi khi mở một file code lạ, Đức click vào node code để xem bảng "History/Why Panel" chủ động cập nhật bối cảnh mà không cần gõ câu hỏi. Khi chuẩn bị sửa code, Đức chạy kiểm tra rủi ro (Refactor-Risk Check) và xuất gói dữ liệu chứng cứ (Evidence Pack).
*   **Why they stay:** Tiết kiệm được trung bình 1-2 tiếng mỗi ngày không phải tìm kiếm thông tin cũ và không bị Senior cằn nhằn.
*   **Why they might churn:** Nếu đồ thị tri thức bị lỗi thời (stale graph) do pipeline cập nhật chậm, hoặc AI đưa ra những trích dẫn không liên quan.
*   **Impact:** Cần có tính năng tự động phát hiện thay đổi trong Git để nhắc nhở cập nhật đồ thị tri thức và cơ chế đánh giá độ tin cậy của chứng cứ (evidence quality scoring).

## 5. Advocate (Lan tỏa)
*   **User Action:** Đức sao chép "PR Review Evidence Pack" đính kèm vào phần mô tả Pull Request gửi cho Tech Lead (anh Hùng). Hùng ngạc nhiên vì PR của một Junior mới vào lại cực kỳ đầy đủ bối cảnh, liệt kê chính xác các rủi ro hệ thống và trích dẫn các quyết định thiết kế từ 2 năm trước. Đức chia sẻ công cụ này trong buổi họp kỹ thuật tuần của công ty.
*   **Motivation to share:** Đức muốn chứng tỏ năng lực tự nghiên cứu và nhận được sự công nhận từ đồng nghiệp.
*   **Business Outcome:** Công ty quyết định mua hoặc tích hợp DevOnboard vào quy trình onboarding bắt buộc cho toàn bộ lập trình viên mới gia nhập.
