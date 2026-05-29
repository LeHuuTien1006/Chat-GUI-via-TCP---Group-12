"""
Task 1.1 - Tìm kiếm tin nhắn cục bộ (Message Search)
Nhóm 12 - Lê Hữu Tiến
Nhận QTextBrowser / list tin nhắn từ Quỳnh Anh, tìm kiếm theo từ khóa,
highlight kết quả trả về.
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Message:
    """Cấu trúc một tin nhắn trong chat."""
    msg_id: int
    sender: str
    content: str
    timestamp: str
    room: str = "general"


@dataclass
class SearchResult:
    """Kết quả tìm kiếm một tin nhắn."""
    message: Message
    highlighted_content: str      # Nội dung với từ khóa được đánh dấu
    match_positions: List[tuple]  # [(start, end), ...] vị trí match trong content


# ─────────────────────────────────────────────────────────────
#  CÁC HÀM LÕI
# ─────────────────────────────────────────────────────────────

def search_messages(
    messages: List[Message],
    keyword: str,
    case_sensitive: bool = False
) -> List[SearchResult]:
    """
    Duyệt mảng tin nhắn và lọc theo từ khóa.

    Args:
        messages      : Danh sách Message nhận từ Quỳnh Anh
        keyword       : Từ khóa cần tìm
        case_sensitive: Phân biệt hoa/thường (mặc định không)

    Returns:
        Danh sách SearchResult có đính kèm vị trí match và nội dung highlighted
    """
    if not keyword.strip():
        return []

    results: List[SearchResult] = []
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(keyword), flags)

    for msg in messages:
        matches = list(pattern.finditer(msg.content))
        if not matches:
            continue

        positions = [(m.start(), m.end()) for m in matches]
        highlighted = _highlight_text(msg.content, positions)
        results.append(SearchResult(
            message=msg,
            highlighted_content=highlighted,
            match_positions=positions
        ))

    return results


def _highlight_text(text: str, positions: List[tuple]) -> str:
    """
    Chèn thẻ [HIGHLIGHT]...[/HIGHLIGHT] quanh các đoạn match.
    Quỳnh Anh có thể parse cặp thẻ này để tô màu trên QTextBrowser.
    """
    result = []
    prev_end = 0
    for start, end in positions:
        result.append(text[prev_end:start])
        result.append(f"[HIGHLIGHT]{text[start:end]}[/HIGHLIGHT]")
        prev_end = end
    result.append(text[prev_end:])
    return "".join(result)


def highlight_for_qt(text: str, positions: List[tuple], color: str = "yellow") -> str:
    """
    Sinh HTML để dùng trực tiếp với QTextBrowser.setHtml().
    Quỳnh Anh gọi hàm này, truyền kết quả vào widget.
    """
    result = []
    prev_end = 0
    for start, end in positions:
        result.append(text[prev_end:start])
        result.append(
            f'<span style="background-color:{color}; font-weight:bold;">'
            f'{text[start:end]}</span>'
        )
        prev_end = end
    result.append(text[prev_end:])
    return "".join(result)


def print_search_results(results: List[SearchResult], keyword: str) -> None:
    """In kết quả tìm kiếm ra console (dùng khi test)."""
    if not results:
        print(f'[SEARCH] Không tìm thấy kết quả nào cho từ khóa: "{keyword}"')
        return

    print(f'\n[SEARCH] Tìm thấy {len(results)} tin nhắn chứa "{keyword}":')
    print("─" * 60)
    for i, r in enumerate(results, 1):
        msg = r.message
        print(f"  [{i}] ID={msg.msg_id} | {msg.sender} | {msg.timestamp}")
        print(f"       Phòng: {msg.room}")
        print(f"       Nội dung: {r.highlighted_content}")
        print(f"       Vị trí match: {r.match_positions}")
        print()


# ─────────────────────────────────────────────────────────────
#  TEST THỦ CÔNG
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Dữ liệu mẫu (thực tế nhận từ Quỳnh Anh qua list/QTextBrowser)
    sample_messages = [
        Message(1,  "Quân",      "Mọi người họp lúc 9h nhé",                     "09:00", "general"),
        Message(2,  "QuỳnhAnh",  "OK anh Quân, em sẽ họp đúng giờ",              "09:01", "general"),
        Message(3,  "Tiến",      "Anh Quân ơi server bị lỗi khi gửi ảnh",        "09:05", "general"),
        Message(4,  "Quân",      "Tiến kiểm tra lại phần header nhị phân nhé",   "09:06", "general"),
        Message(5,  "QuỳnhAnh",  "Em đang fix bug UI của nhóm chat group",       "09:10", "group-12"),
        Message(6,  "Tiến",      "Header đã fix xong, test gửi ảnh lại đi Quân", "09:15", "group-12"),
        Message(7,  "Quân",      "Good job Tiến! Merge vào main đi",             "09:20", "general"),
        Message(8,  "QuỳnhAnh",  "Anh Quân review PR của em với nhé",            "09:25", "general"),
    ]

    # Test 1: Tìm tên "Quân"
    results = search_messages(sample_messages, "Quân")
    print_search_results(results, "Quân")

    # Test 2: Tìm từ "header" không phân biệt hoa thường
    results = search_messages(sample_messages, "header")
    print_search_results(results, "header")

    # Test 3: Sinh HTML highlight để Quỳnh Anh dùng cho QTextBrowser
    print("[QT HTML] Ví dụ HTML highlight cho QTextBrowser:")
    test_msg = sample_messages[2]
    html = highlight_for_qt(
        test_msg.content,
        [(test_msg.content.lower().find("server"), test_msg.content.lower().find("server") + 6)],
        color="#FFEB3B"
    )
    print(f"  {html}\n")

    # Test 4: Từ khóa không tồn tại
    results = search_messages(sample_messages, "xyz123")
    print_search_results(results, "xyz123")
