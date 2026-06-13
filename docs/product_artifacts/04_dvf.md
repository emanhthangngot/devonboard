# DVF Framework Assessment

*Purpose: The DVF (Desirability, Viability, Feasibility) framework acts as a reality check for any product idea. It ensures that a product is not only loved by users (Desirable) but also makes financial sense for the company (Viable) and can actually be built by the engineering team (Feasible). An idea must hit the intersection of all three to succeed.*

---

## 1. Desirable (for users)
*   **Giá trị mang lại cho kỹ sư (Junior & Senior):** 
    *   Junior có thể tự tin sửa code và onboard nhanh chóng nhờ câu trả lời có trích dẫn nguồn chứng cứ xác thực (commit, PR, issue). Họ không còn cảm giác e ngại hay lo lắng làm hỏng hệ thống.
    *   Senior Tech Lead được giải phóng khỏi các câu hỏi lặp đi lặp lại về kiến trúc cũ, giúp họ tập trung vào công việc lập trình chuyên sâu và các bài toán kinh doanh.
*   **Chứng cứ từ nghiên cứu người dùng:** Các lập trình viên thường có mức độ hoài nghi rất cao đối với các chatbot AI sinh chữ chung chung (như ChatGPT). Khả năng truy xuất chứng cứ và kiểm chứng trực tiếp (provenance) là tính năng cốt lõi được yêu cầu nhiều nhất để họ tin tưởng áp dụng AI vào mã nguồn thực tế.

## 2. Viable (for businesses)
*   **Hiệu quả kinh tế cho doanh nghiệp:**
    *   **Giảm chi phí onboarding:** Rút ngắn thời gian onboard kỹ sư mới (đặc biệt trong bối cảnh khoảng cách năng lực của lập trình viên Việt Nam) từ 4 tuần xuống 1 tuần. Ước tính tiết kiệm hàng ngàn USD chi phí lương và năng suất cho mỗi nhân sự mới.
    *   **Bảo hiểm mất mát tri thức (Knowledge Retention):** Giảm thiểu tối đa rủi ro gián đoạn vận hành khi các nhân sự Senior chủ chốt rời công ty (vấn đề rất phổ biến ở thị trường IT Việt Nam khi Senior chuyển sang làm remote cho nước ngoài).
*   **Mô hình doanh thu:**
    *   **Bản Local MVP:** Miễn phí cho nhà phát triển cá nhân và các dự án mã nguồn mở nhỏ.
    *   **Bản Enterprise (Lộ trình tương lai):** Thu phí thuê bao (SaaS hoặc Self-hosted) theo số lượng seats và số lượng repository tích hợp, đi kèm các tính năng bảo mật nâng cao và phân quyền truy cập.
*   **Kiểm soát rủi ro IP/Security:** Thiết lập chế độ "Evidence-only" hoạt động hoàn toàn local để đáp ứng các tiêu chuẩn bảo mật khắt khe của doanh nghiệp, cam kết không gửi mã nguồn của khách hàng lên máy chủ AI bên thứ ba khi chưa có sự cho phép.

## 3. Feasible (for engineers)
*   **Tính khả thi về mặt kỹ thuật:**
    *   **Công nghệ cốt lõi:** Sử dụng các thư viện phân tích cú pháp tĩnh (AST) nhẹ như `tree-sitter` để trích xuất cấu trúc code và các API Git chuẩn để quét lịch sử commit/PR.
    *   **Lưu trữ dữ liệu:** Đồ thị tri thức (knowledge graph) được biểu diễn và lưu trữ dưới dạng file JSON cục bộ (`knowledge-graph.json`), không đòi hỏi hạ tầng cơ sở dữ liệu đồ thị phức tạp cho phiên bản MVP.
    *   **Tích hợp AI:** Sử dụng các mô hình ngôn ngữ lớn (LLM) thông qua API (như Gemini 1.5 Pro, Anthropic Claude 3.5 Sonnet) hoặc chạy local thông qua Ollama để tổng hợp câu trả lời từ dữ liệu đồ thị đã được lọc sạch.
    *   **Môi trường thử nghiệm cố định:** Sử dụng repo `nextlevelbuilder/goclaw` tại branch `dev` làm dữ liệu mẫu (fixture) cố định bằng biến môi trường `TARGET_REPO_COMMIT` để đảm bảo kết quả kiểm chứng (benchmarking) có thể tái lập 100%.
