# Product Requirements Document (PRD)

*Purpose: The PRD is the "contract" between Product Management, Design, and Engineering. It details exactly *what* needs to be built and *why*, serving as the single source of truth during the development cycle. It bridges the gap between high-level strategy and actual code.*

---

## 1. Objective (Mục tiêu)
Xây dựng phiên bản **DevOnboard MVP** dưới dạng hệ thống chạy local, giúp trích xuất cấu trúc mã nguồn và lịch sử phát triển để tạo lập đồ thị tri thức codebase. Hệ thống cho phép kỹ sư mới hỏi đáp có trích dẫn nguồn chứng cứ xác thực (commit, PR, issue) và giúp Tech Lead đánh giá rủi ro refactor, chuẩn bị bối cảnh review Pull Request nhanh chóng.

---

## 2. Target Audience (Khách hàng mục tiêu)
*   **Trần Minh Đức (Primary Persona - Junior Developer tại Việt Nam):** Kỹ sư mới gia nhập dự án, cần hiểu nhanh luồng nghiệp vụ phức tạp của codebase lớn mà không cần hỏi dồn dập các đàn anh Senior.
*   **Nguyễn Việt Hùng (Secondary Persona - Tech Lead tại Việt Nam):** Đang quản lý đội ngũ trong bối cảnh tỷ lệ nhảy việc cao (turnover), cần một giải pháp bảo lưu tri thức hệ thống và đẩy nhanh tốc độ code review.
*   **AI-Agent Power User (Secondary Persona):** Kỹ sư sử dụng các tác nhân AI (AI Coding Agents) muốn cung cấp bối cảnh mã nguồn và lịch sử thiết kế được trích lọc an toàn, chính xác cao cho agent.

---

## 3. Value Proposition (Tuyên ngôn giá trị)
**DevOnboard biến mã nguồn tĩnh và lịch sử Git rời rạc thành tri thức hệ thống có trích dẫn cụ thể.**
*   **Đối với kỹ sư:** Tiết kiệm 1-2 tiếng mỗi ngày mò mẫm trong các commit cũ, giảm thiểu rủi ro khi sửa code ở các module lạ nhờ cảnh báo rủi ro refactor chủ động.
*   **Đối với doanh nghiệp:** Đóng vai trò là gói **"Bảo hiểm tri thức"**, lưu trữ các quyết định thiết kế cốt lõi (design rationale) trực tiếp trong dự án, ngăn chặn việc thất thoát tri thức khi các Senior chuyển đi nơi khác.

---

## 4. User Stories / Requirements (Yêu cầu người dùng)

### US-01 — Structural Query (Hỏi đáp Cấu trúc)
*   **As a** Junior Developer (Đức),  
    **I want to** hỏi "Luồng xử lý từ cổng thanh toán đối tác đi qua adapter nào?"  
    **So that** tôi có thể hiểu luồng thực thi mà không phải đọc từng dòng code.
*   **Acceptance Criteria:**
    *   Câu trả lời trích dẫn chính xác file, function, module cụ thể trong codebase.
    *   Hiển thị sơ đồ luồng gọi (call/dependency path) liên quan.
    *   Phân biệt rõ ràng giữa bằng chứng trực tiếp và suy luận kiến trúc của AI.
    *   Nếu không có dữ liệu cấu trúc, hệ thống phải thông báo rõ những gì đang thiếu.

### US-02 — Historical Query (Hỏi đáp Lịch sử Thiết kế)
*   **As a** Junior Developer (Đức),  
    **I want to** hỏi "Tại sao chúng ta lại dùng cấu trúc Single-Threaded Event Loop cho module này?"  
    **So that** tôi hiểu bối cảnh thiết kế trước khi thay đổi logic hoạt động.
*   **Acceptance Criteria:**
    *   Câu trả lời trích dẫn các commit, PR, review comment, issue hoặc claim thiết kế cụ thể.
    *   Phần câu trả lời tách biệt rõ "Code làm gì" và "Tại sao code được thiết kế như vậy".
    *   Nếu không tìm thấy lý do lịch sử, hệ thống hiển thị trạng thái trống (empty state) và không được tự bịa ra lý do.

### US-03 — Hybrid Refactor-Risk Query (Đánh giá rủi ro Refactor kết hợp)
*   **As a** Tech Lead (Hùng),  
    **I want to** hỏi "Có an toàn khi refactor module ProviderAdapter không?"  
    **So that** tôi biết được các ảnh hưởng cấu trúc kèm theo lịch sử lỗi/bug của module này.
*   **Acceptance Criteria:**
    *   Phần cấu trúc: Liệt kê tất cả các file/hàm chịu ảnh hưởng trực tiếp (blast radius).
    *   Phần lịch sử: Liệt kê các commit liên quan đến bug cũ, các PR liên quan, và các lựa chọn thiết kế từng bị bác bỏ.
    *   Phân loại rõ rệt giữa "Rủi ro cấu trúc" và "Ẩn số lịch sử".

### US-04 — History/Why Panel (Bảng Lịch sử & Lý do Zero-Click)
*   **As a** Kỹ sư,  
    **I want to** click vào một file/hàm trên giao diện đồ thị và xem ngay bối cảnh lịch sử của nó  
    **So that** tôi có bối cảnh tức thì mà không cần tự viết câu prompt dài dòng.
*   **Acceptance Criteria:**
    *   Bảng điều khiển hiển thị danh sách commit, tác giả, PR, issue liên quan trực tiếp.
    *   Các liên kết chứng cứ có thể click để mở trực tiếp trong trình duyệt hoặc IDE.
    *   Trạng thái trống (empty state) hiển thị rõ ràng nếu node code chưa có lịch sử.

### US-05 — Ingest Pipeline (Đường ống nạp dữ liệu)
*   **As a** Kỹ sư,  
    **I want to** làm mới dữ liệu codebase và lịch sử Git theo yêu cầu  
    **So that** câu trả lời luôn cập nhật các thay đổi code mới nhất.
*   **Acceptance Criteria:**
    *   Hiển thị mốc thời gian cập nhật dữ liệu gần nhất.
    *   Việc nạp lại dữ liệu không tạo ra trùng lặp trong biểu đồ tri thức.
    *   Cho phép người dùng cấu hình loại trừ (exclude) các file rác, file sinh tự động, hoặc thư mục vendor.

### US-06 — Benchmark Dashboard (Bảng so sánh đối chứng)
*   **As a** Lập trình viên thử nghiệm,  
    **I want to** so sánh câu trả lời của DevOnboard với câu trả lời của AI thông thường  
    **So that** kiểm chứng được giá trị của việc trích dẫn nguồn lịch sử.
*   **Acceptance Criteria:**
    *   Sử dụng cùng một bộ câu hỏi cố định (5 câu hỏi chuẩn trong demo).
    *   Đo lường các chỉ số: Thời gian phản hồi, Tỷ lệ trích dẫn (citation coverage), Độ tin cậy và Điểm đánh giá của lập trình viên.

### US-07 — PR Review Preparation (Đóng gói chứng cứ review)
*   **As a** Tech Lead (Hùng) / Reviewer,  
    **I want to** xuất một gói dữ liệu chứng cứ (Evidence Pack) cho các file thay đổi trong PR  
    **So that** tôi có đủ bối cảnh lịch sử thiết kế của các module bị ảnh hưởng để review an toàn.
*   **Acceptance Criteria:**
    *   Gói dữ liệu liệt kê các file thay đổi, lịch sử chỉnh sửa gần nhất, các cảnh báo rủi ro thiết kế.
    *   Cho phép sao chép nhanh để paste vào phần bình luận PR trên GitHub/Zalo.

### US-08 — AI-Agent Context Pack (Xuất bối cảnh cho AI Agent)
*   **As a** Lập trình viên sử dụng AI Agent,  
    **I want to** xuất bối cảnh mã nguồn và các ràng buộc lịch sử dạng tóm tắt gọn nhẹ  
    **So that** tôi nạp trực tiếp cho AI Agent làm việc chính xác hơn.
*   **Acceptance Criteria:**
    *   Định dạng xuất gọn nhẹ, bảo mật, loại bỏ hoàn toàn mã độc, secrets hoặc thư viện vendor.
    *   Cho phép chạy chế độ "Evidence-only" (chỉ xuất bối cảnh lịch sử, không xuất code) để bảo mật IP.

---

## 5. Scope (Phạm vi sản phẩm)

### In Scope (Có trong phiên bản MVP V1)
*   Ứng dụng chạy local dưới dạng Web UI (Next.js) được backend FastAPI hỗ trợ.
*   Chỉ hỗ trợ quét đơn repository (Single-repo) của dự án demo `nextlevelbuilder/goclaw`.
*   Trích xuất dữ liệu từ các file mã nguồn nội bộ và lịch sử Git commit local. Metadata từ GitHub (PR, issue) là tùy chọn và có cơ chế fallback về commit lịch sử khi không có token mạng.
*   Hỗ trợ 5 câu hỏi truy vấn cố định để kiểm nghiệm benchmark trong `docs/AI.md`.

### Out of Scope (Không phát triển trong MVP)
*   Không xây dựng hệ thống đa người dùng, phân quyền (RBAC) hay lưu trữ đám mây (SaaS).
*   Không hỗ trợ nhiều repository liên kết chéo trong bản V1.
*   Không phát triển public CLI trong MVP; các thao tác scan, ingest, query, evidence pack và benchmark được thực hiện qua Web UI gọi REST API.
*   Không tích hợp tính năng tự động chỉnh sửa/ghi đè mã nguồn của dự án.
*   Không gửi bất kỳ thông tin mã nguồn nào lên máy chủ AI nếu người dùng không cấu hình khóa API hoặc chọn dịch vụ đám mây (mặc định ưu tiên local LLM hoặc API bảo mật cao).

---

## 6. Dependencies & Assumptions (Phụ thuộc & Giả định)

### Phụ thuộc kỹ thuật (Dependencies)
*   **Git CLI:** Máy chạy thử nghiệm phải được cài đặt Git để truy xuất log lịch sử.
*   **Mô hình LLM:** Phụ thuộc vào tính sẵn sàng của LLM API (OpenAI/Gemini/Anthropic) hoặc hạ tầng máy local của lập trình viên nếu chạy qua Ollama.
*   **AST Parser:** Thư viện `tree-sitter` phải phân tích chính xác mã nguồn Go của dự án demo.

### Giả định kinh doanh (Assumptions)
*   Các nhà phát triển sẵn sàng chạy quy trình quét cục bộ để đổi lấy sự bảo mật tuyệt đối về mặt IP mã nguồn.
*   Codebase có lịch sử Git tương đối sạch (các commit ghi chép đầy đủ nội dung mô tả) để AI có thể trích xuất lý do thiết kế (design claims) chất lượng.
