# Pitch Deck Outline

*Purpose: The Pitch Deck is a storytelling tool. Whether pitching to venture capitalists for funding or to internal executives for budget approval, it condenses all product research, strategy, and design into a compelling, persuasive narrative. It must convince the audience that the problem is real, the solution is brilliant, and the business case is sound.*

---

## 1. Presenting (Giới thiệu & Hook)
*   **Presenter:** Trình bày bởi Product Lead của dự án DevOnboard.
*   **The Hook (Điểm lôi cuốn đầu tiên):**
    > **"70% kỹ sư IT mới ra trường tại Việt Nam cần đào tạo lại và mất ít nhất 1-2 tháng để hiểu một codebase phức tạp. Đồng thời, doanh nghiệp công nghệ Việt đang đối mặt với nguy cơ mất trắng hàng tỷ đồng tri thức hệ thống mỗi khi các Senior kỹ sư chuyển đi làm remote cho công ty nước ngoài."**
*   **Vision Statement:** DevOnboard - Nền tảng tự động số hóa lịch sử phát triển phần mềm thành tri thức hệ thống có trích dẫn, giúp quá trình onboarding diễn ra tức thì và bảo toàn tri thức doanh nghiệp trọn đời.

## 2. Problem Statement (Mô tả bài toán)
*   **Bản chất vấn đề:** Mã nguồn hiện tại chỉ trả lời câu hỏi **CÁI GÌ (What)** được viết, chứ không trả lời được **TẠI SAO (Why)** thiết kế như vậy. 
*   **Sự phân mảnh thông tin:** Các quyết định kiến trúc, lựa chọn thiết kế nhạy cảm bị phân mảnh trên hàng ngàn PR, commit log, issue và các đoạn chat không chính thức trên Zalo/Slack.
*   **Hậu quả:** 
    *   Junior mất hàng giờ mò mẫm code cũ, tạo ra các PR lỗi do vi phạm các ràng buộc thiết kế lịch sử.
    *   Senior Tech Lead bị gián đoạn liên tục để giải thích những câu hỏi lặp đi lặp lại.
    *   Các công cụ AI Chatbot thông thường thường xuyên ảo giác (hallucinate), đưa ra lời khuyên thiết kế thiếu căn cứ lịch sử, gây nguy hiểm khi áp dụng vào codebase thực tế.

## 3. Solutions (Giải pháp)
*   **DevOnboard Knowledge Graph:** Công cụ cục bộ tự động kết nối cấu trúc code tĩnh (AST) với lịch sử Git/PR để tạo lập một đồ thị chứng cứ (Provenance Graph) hoàn chỉnh.
*   **Các tính năng cốt lõi trong demo:**
    *   *Cited Q&A:* Hỏi đáp thông minh về codebase, mọi câu trả lời đều đính kèm thẻ trích dẫn commit/PR cụ thể để lập trình viên đối chiếu nhanh.
    *   *History/Why Panel:* Click vào bất kỳ hàm/module nào để xem ngay lịch sử sửa đổi và các khẳng định lý do thiết kế (claims) liên quan mà không cần viết prompt.
    *   *Refactor-Risk Checker:* Cảnh báo chủ động các khu vực có rủi ro cao hoặc có nhiều bug lịch sử trước khi kỹ sư sửa code.
    *   *PR Evidence Packs:* Tự động đóng gói bối cảnh thiết kế của phần code thay đổi trong PR để phục vụ khâu code review an toàn.

## 4. Desirability (Tính khả thi từ góc độ người dùng - Sự mong đợi)
*   **Lập trình viên tin bằng chứng hơn tin AI nói suông:** DevOnboard giải quyết sự hoài nghi của giới công nghệ bằng cách cung cấp cơ chế trích dẫn nguồn gốc chứng cứ rõ ràng (Provenance).
*   **Giúp Junior tự lập hơn:** Đức (Junior) có thể tự tin sửa code mà không có cảm giác sợ sệt hay liên tục phải gõ cửa đàn anh Senior để hỏi lý do lịch sử.
*   **Giải phóng Senior:** Anh Hùng (Tech Lead) tiết kiệm được 75% thời gian onboard nhân viên mới, giảm thiểu số lượng PR lỗi phải review lại từ đầu.

## 5. Viability (Tính khả thi từ góc độ kinh doanh - Hiệu quả kinh tế)
*   **Bài toán ROI (Lợi nhuận trên đầu tư):**
    *   Rút ngắn thời gian onboarding từ 4 tuần xuống còn 1 tuần. Với một đội ngũ 20 kỹ sư thường xuyên có sự biến động nhân sự, DevOnboard giúp tiết kiệm tương đương hàng chục ngàn USD chi phí lương lãng phí mỗi năm.
    *   **Bảo hiểm tri thức ngầm:** Ngăn chặn việc mất sạch tài liệu kiến trúc khi nhân sự chủ chốt nghỉ việc.
*   **Bảo mật IP tuyệt đối:** Mô hình chạy local-first (Evidence-only mode) đảm bảo mã nguồn doanh nghiệp không bao giờ bị rò rỉ ra internet - điều kiện bắt buộc để các doanh nghiệp tài chính, fintech hoặc startup tại Việt Nam đồng ý áp dụng.

## 6. Feasibility (Tính khả thi từ góc độ kỹ thuật - Thực thi)
*   **Đơn giản & Nhẹ nhàng:** Hệ thống hoạt động hoàn toàn cục bộ trên máy lập trình viên, lưu trữ đồ thị tri thức dưới dạng file JSON đơn giản (`knowledge-graph.json`), phân tích cú pháp tĩnh qua `tree-sitter`.
*   **Đồng bộ quy trình:** Dễ dàng tích hợp vào IDE (VS Code) và quy trình Git thông qua các hook tự động nạp lịch sử.
*   **Thử nghiệm kiểm chứng độc lập (Benchmark):** Bản MVP đã được tích hợp bộ đo lường benchmark trên repo mẫu `nextlevelbuilder/goclaw` (branch `dev`), đảm bảo kết quả trích dẫn có thể tái lập và đánh giá khách quan bởi các chuyên gia workshop.
