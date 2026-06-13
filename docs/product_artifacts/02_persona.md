# Persona

*Purpose: A persona is a fictional but data-driven representation of your target user. It humanizes abstract data, ensuring the entire product team (from engineers to marketers) is designing for a specific, realistic human rather than an abstract demographic.*

---

## 1. Primary Persona: Trần Minh Đức (Junior Software Engineer)

### Descriptive
*   **Narrative:** Đức (23 tuổi) vừa tốt nghiệp Đại học Công nghệ tại TP.HCM và gia nhập một startup fintech với vai trò Junior Developer. Đây là dự án lớn đầu tiên của cậu với hàng trăm module đan xen phức tạp.
*   **Demographic:** 23 tuổi, sống tại TP.HCM, thu nhập 15-18 triệu VNĐ/tháng, tốt nghiệp Cử nhân CNTT.
*   **Psychographic:** Năng động, tự tin về khả năng tiếp thu công nghệ mới nhưng thiếu kỹ năng thực chiến (nằm trong nhóm 70% sinh viên cần đào tạo lại). Rất sợ bị đánh giá là "thiếu năng lực" nếu liên tục hỏi các câu hỏi cơ bản.

### Motivations
*   **Ngắn hạn:** Onboard nhanh chóng, hoàn thành task đầu tiên đúng hạn mà không gây lỗi hệ thống.
*   **Dài hạn:** Thăng tiến lên Mid-level trong vòng 2 năm, học hỏi các pattern thiết kế chuẩn từ hệ thống thực tế.
*   **Mong muốn cốt lõi:** Có một trợ lý tin cậy giúp cậu tự tìm hiểu cấu trúc hệ thống mà không phải làm phiền Senior.

### Interactions
*   **Thiết bị & Công cụ:** Sử dụng Laptop Ubuntu, IDE VS Code, Git, GitHub.
*   **Kênh giao tiếp:** Slack cho công việc chính thức, Zalo cho các trao đổi nhanh của nhóm.
*   **Thói quen dùng AI:** Thường xuyên dùng AI hỗ trợ viết code nhanh nhưng lo ngại ảo giác (hallucination) và thiếu bối cảnh thực tế của dự án doanh nghiệp.

### Pain Points
*   **Codebase quá lớn và thiếu tài liệu:** README của dự án viết sơ sài từ 1 năm trước và không cập nhật.
*   **Sự bận rộn của Senior:** Các anh Senior thường xuyên bận họp hoặc làm việc từ xa, không có thời gian hướng dẫn chi tiết.
*   **Lịch sử code bị phân mảnh:** `git blame` chỉ chỉ ra ai viết code chứ không giải thích "Tại sao hệ thống lại dùng cơ chế adapter này thay vì connector trực tiếp".

### Moments that Matter
*   **Khoảnh khắc nhận task đầu tiên:** Nhận task sửa đổi một shared interface nhạy cảm nhưng không biết những module nào đang phụ thuộc vào nó.
*   **5 phút trước khi gửi PR (Pull Request):** Căng thẳng vì không chắc chắn liệu thay đổi của mình có vi phạm các quyết định thiết kế lịch sử của hệ thống hay không.

---

## 2. Secondary Persona: Nguyễn Việt Hùng (Tech Lead / Architect)

### Descriptive
*   **Narrative:** Anh Hùng (32 tuổi) là Tech Lead chịu trách nhiệm về kiến trúc hệ thống và quy trình code review của nhóm. Anh đang chịu áp lực lớn khi công ty mở rộng quy mô nhân sự nhưng chất lượng đầu ra bị giảm sút.
*   **Demographic:** 32 tuổi, sống tại Hà Nội, thu nhập 50-60 triệu VNĐ/tháng, có vợ và một con nhỏ.
*   **Psychographic:** Đề cao tính kỷ luật, cấu trúc code sạch và an toàn bảo mật. Gặp áp lực lớn về mặt thời gian (sandwich generation) khi vừa quản lý đội ngũ vừa lo cho gia đình.

### Motivations
*   **Ngắn hạn:** Giảm thời gian onboard cho nhân viên mới từ 4 tuần xuống 1 tuần.
*   **Dài hạn:** Bảo toàn tri thức hệ thống (institutional memory) kể cả khi các Senior chủ chốt chuyển đi làm remote cho nước ngoài.
*   **Mong muốn cốt lõi:** Quy trình code review tự động hóa bối cảnh lịch sử, giúp ngăn chặn rủi ro refactor sai trước khi code được merge.

### Interactions
*   **Thiết bị & Công cụ:** Macbook Pro, GitHub Enterprise, Zalo, Slack.
*   **Thói quen:** Đọc code trực tiếp trên GitHub PR review screen, viết tài liệu kiến trúc bằng Markdown lưu trữ trong repo.

### Pain Points
*   **Lặp lại giải thích:** Dành 2-3 tiếng mỗi ngày chỉ để giải thích cho Junior về các quyết định thiết kế cũ.
*   **Tri thức bị mất mát:** Khi các kỹ sư kỳ cựu nghỉ việc, bối cảnh thiết kế của nhiều module cốt lõi biến mất hoàn toàn, không ai dám refactor vì sợ sập hệ thống.

### Moments that Matter
*   **Khi review PR của Junior:** Phát hiện Junior thay đổi cấu trúc DB hoặc interface chung vì nghĩ "đơn giản", suýt gây lỗi nghiêm trọng cho luồng thanh toán chính.
