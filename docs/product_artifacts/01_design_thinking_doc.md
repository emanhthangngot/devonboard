# Design Thinking Document

*Purpose: This document is the foundational step. It shifts the focus away from "what features can we build?" to "what human problem are we solving?" It ensures the product is rooted in actual user needs rather than assumptions.*

## Empathize
*   **Who the users are:** 
    *   **Kỹ sư IT mới tốt nghiệp / Junior tại Việt Nam:** Thường gia nhập các dự án lớn nhưng gặp rào cản lớn về năng lực thực chiến (do đào tạo học thuật nặng lý thuyết - theo báo cáo của Navigos). Họ đối mặt với codebase phức tạp, tài liệu nội bộ sơ sài hoặc đã lạc hậu.
    *   **Senior Engineer / Tech Lead tại Việt Nam:** Chịu áp lực hướng dẫn liên tục cho nhân sự mới trong bối cảnh các Senior có trình độ cao thường xuyên luân chuyển công việc hoặc nhận làm remote cho nước ngoài (Mỹ, Singapore, Anh), dẫn đến đứt gãy tri thức hệ thống.
*   **Daily environment:** Sống trong môi trường phát triển tốc độ cao, thường xuyên trao đổi qua các kênh không chính thức như Zalo/Slack, mã nguồn thay đổi liên tục nhưng tài liệu (Wiki, README) không được cập nhật kịp thời.
*   **Feelings:** Junior cảm thấy lo lắng, ngợp trước hàng vạn dòng code và sợ làm hỏng hệ thống khi refactor. Senior cảm thấy kiệt quệ (burnout) vì phải trả lời lặp đi lặp lại những câu hỏi "Tại sao đoạn code này được viết như vậy?".
*   **Workarounds:** Junior tự mò mẫm qua `git blame`, tìm kiếm thủ công trong Slack/Zalo cũ, hoặc hỏi trực tiếp Senior gây gián đoạn công việc của cả hai.

## Define
*   **Problem Statement:** 
    *   **Đoạn tóm tắt:** Các kỹ sư phần mềm mới (đặc biệt là Junior ở Việt Nam chịu ảnh hưởng bởi khoảng cách kỹ năng) gặp khó khăn trong việc hiểu sâu cấu trúc và lịch sử thiết kế của codebase phức tạp, trong khi các doanh nghiệp công nghệ Việt Nam phải đối mặt với nguy cơ mất mát tri thức hệ thống khi nhân sự Senior liên tục dịch chuyển sang làm remote cho thị trường quốc tế.
    *   **Nhu cầu cốt lõi:** Một hệ thống lưu trữ và truy xuất "tri thức ngầm" của codebase một cách tự động, có trích dẫn nguồn chứng cứ xác thực (commit, PR, issue) để bất kỳ ai cũng có thể tự onboard nhanh chóng mà không cần làm phiền Senior.

## Ideate
*   **Ý tưởng cốt lõi:** DevOnboard kết nối cấu trúc code hiện tại với lịch sử Git/GitHub để xây dựng một bản đồ tri thức nội bộ (Knowledge Graph), hỗ trợ hỏi đáp kèm trích dẫn nguồn chứng cứ cụ thể.
*   **Các ý tưởng chi tiết:**
    1.  *Ý tưởng 1 (Được chọn):* Bản đồ tri thức codebase cục bộ kết nối cấu trúc mã nguồn (file, class, function) với bằng chứng lịch sử (commit, PR, issue, review comment). Cung cấp giao diện Hỏi đáp (Cited Q&A) và Bảng thông tin "Lịch sử & Lý do" (History/Why Panel) chủ động.
    2.  *Ý tưởng 2:* Công cụ tự động vẽ sơ đồ luồng dữ liệu thời gian thực (real-time data flow) và liên kết với cuộc hội thoại trên Zalo/Slack của nhóm để tìm lý do quyết định. (Bị loại do rủi ro bảo mật thông tin và khó tích hợp cấu trúc).
    3.  *Ý tưởng 3:* Chatbot AI đọc mã nguồn đơn thuần. (Bị loại vì dễ ảo giác và thiếu bối cảnh lịch sử "tại sao").

## Prototype
*   **What will be built:** Bản thử nghiệm chạy local, áp dụng cho một codebase mẫu đã chuẩn bị sẵn (`nextlevelbuilder/goclaw`).
*   **Core Flow:** Người dùng chọn một hàm/module trên giao diện -> DevOnboard hiển thị bảng thông tin lịch sử và trích dẫn lý do thiết kế (claims) -> Người dùng nhập câu hỏi dạng "Tại sao ProviderAdapter lại dùng cơ chế load bất đồng bộ?" -> AI trả về câu trả lời kèm trích dẫn chi tiết các PR và commit tương ứng -> Người dùng xuất "Evidence Pack" để đính kèm vào PR review.

## Test
*   **Đối tượng kiểm thử:** 5 kỹ sư Junior/Mới gia nhập tại một startup công nghệ Việt Nam.
*   **Câu hỏi/Phản hồi cần tìm kiếm:** 
    *   Liệu các trích dẫn commit/PR có đủ độ tin cậy để họ tự tin thực hiện thay đổi mã nguồn không?
    *   Thời gian để họ tìm ra nguyên nhân một thiết kế lạ là bao lâu so với cách tự mò mẫm hoặc hỏi Senior?
*   **Chỉ số đo lường thành công:**
    *   **Time-to-Value (TTV):** Người dùng tìm được câu trả lời và xác minh được tính đúng đắn của thiết kế trong vòng **60 giây**.
    *   **Tỷ lệ tự giải quyết:** Junior tự hoàn thành 80% nhiệm vụ tìm hiểu luồng nghiệp vụ cơ bản mà không cần gián đoạn công việc của Senior.
