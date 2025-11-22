# SPEC-004: Notion Integration

**Status**: Implemented
**Version**: 1.0
**Last Updated**: 2025-11-22
**Owner**: Meeting Minutes Team
**Dependencies**: SPEC-001 (Architecture), SPEC-003 (LLM Integration)

---

## Overview

The Notion Integration module (`notion_integration.py`) publishes structured meeting minutes to a Notion database using the Notion API. It handles Korean content, hierarchical formatting, and text chunking for Notion's block size limits.

## Requirements

### Functional Requirements

**FR-001**: Create meeting minutes as a new page in a Notion database
**FR-002**: Format content with Korean section headers (요약, 업데이트, 논의사항, 할 일)
**FR-003**: Support hierarchical content structure (paragraphs, bulleted lists, to-dos)
**FR-004**: Chunk text to respect Notion's 2000-character limit per block
**FR-005**: Set page title with date format: "팀 주간 회의 YYYY-MM-DD"
**FR-006**: Add page icon (🧐 emoji)
**FR-007**: Return URL of created page

### Non-Functional Requirements

**NFR-001**: Create pages within 5 seconds
**NFR-002**: Handle Notion API errors gracefully
**NFR-003**: Support Korean characters (UTF-8) without corruption
**NFR-004**: Preserve text formatting (bold, italics) where possible

## Architecture

### Class: NotionClient

```python
class NotionClient:
    """Handles Notion API operations for meeting minutes."""

    def __init__(self)
    def create_meeting_minutes(
        self,
        summary: str,
        key_updates: str,
        discussion_log: str,
        action_items: str
    ) -> str

    # Private methods
    def _build_blocks(...) -> List[Dict[str, Any]]
    def _heading_block(text: str, level: int = 2) -> Dict[str, Any]
    def _text_to_blocks(text: str) -> List[Dict[str, Any]]
    def _action_items_to_blocks(text: str) -> List[Dict[str, Any]]
    def _paragraph_block(text: str) -> List[Dict[str, Any]]
    def _bulleted_list_block(text: str) -> List[Dict[str, Any]]
    def _todo_block(text: str) -> List[Dict[str, Any]]
```

### Component Diagram

```
NotionClient
├── Initialization
│   ├── Load Notion Token
│   ├── Load Database ID
│   └── Create Client Instance
│
├── Page Creation
│   ├── Title Generation: "팀 주간 회의 YYYY-MM-DD"
│   ├── Icon: 🧐
│   ├── Properties: 제목 (Korean)
│   └── Children: Blocks (content)
│
├── Block Building
│   ├── Section Headings (H2): 요약, 업데이트, 논의사항, 할 일
│   ├── Content Blocks: Paragraphs, Lists, To-dos
│   └── Text Chunking: Split > 2000 chars
│
└── Text Processing
    ├── Parse Line Prefixes: -, •, [ ], etc.
    ├── Determine Block Type: paragraph / list / todo
    ├── Chunk Long Text: Split into multiple blocks
    └── Create Rich Text: Notion format
```

## Detailed Specifications

### 1. Initialization

**Purpose**: Set up Notion client with authentication

```python
def __init__(self):
    """Initialize the Notion client."""
    if not Config.NOTION_TOKEN:
        raise ValueError("NOTION_TOKEN is not configured")

    if not Config.NOTION_PAGE_ID:
        raise ValueError("NOTION_PAGE_ID is not configured")

    self.client = Client(auth=Config.NOTION_TOKEN)
    self.page_id = Config.NOTION_PAGE_ID  # Actually database ID
```

**Configuration**:
- **Token**: Notion Integration Token (from workspace settings)
- **Database ID**: Target database for meeting minutes
- **Validation**: Raises error if either missing

**Error Handling**:
```python
# Missing token
ValueError: "NOTION_TOKEN is not configured"

# Missing database ID
ValueError: "NOTION_PAGE_ID is not configured"
```

### 2. Page Creation

**Purpose**: Create a new meeting minutes page in Notion database

**Implementation**: `create_meeting_minutes(...) -> str`

**Process**:
```python
1. Generate timestamp: datetime.now().strftime("%Y-%m-%d")
2. Create title: f"팀 주간 회의 {timestamp}"
3. Build blocks: _build_blocks(summary, key_updates, discussion_log, action_items)
4. Call Notion API: client.pages.create(...)
5. Return page URL
```

**API Call Structure**:
```python
new_page = self.client.pages.create(
    parent={"database_id": self.page_id},
    icon={"type": "emoji", "emoji": "🧐"},
    properties={
        "제목": {  # Korean property name
            "title": [
                {
                    "text": {
                        "content": title  # "팀 주간 회의 2025-11-22"
                    }
                }
            ]
        }
    },
    children=blocks  # List of block objects
)

return new_page["url"]  # https://notion.so/...
```

**Title Format**:
- **Pattern**: `팀 주간 회의 YYYY-MM-DD`
- **Example**: `팀 주간 회의 2025-11-22`
- **Note**: No emoji in title (previously had 📋, removed for compatibility)

**Page Icon**:
- **Emoji**: 🧐 (Monocle Face)
- **Type**: `emoji` (not image or external)

**Why Separate Timestamp Formatting?**
- Windows `strftime()` cannot handle emojis in format string
- Solution: Format timestamp first, then concatenate with Korean text

### 3. Block Building

**Purpose**: Convert meeting minutes sections into Notion blocks

**Implementation**: `_build_blocks(...) -> List[Dict[str, Any]]`

**Block Structure**:
```
┌─────────────────────────┐
│ ## 요약 (Heading 2)      │
├─────────────────────────┤
│ Paragraph blocks...     │
│ (summary content)       │
├─────────────────────────┤
│ ## 업데이트 (Heading 2)  │
├─────────────────────────┤
│ Paragraph / List blocks │
│ (key updates content)   │
├─────────────────────────┤
│ ## 논의사항 (Heading 2)  │
├─────────────────────────┤
│ Paragraph / List blocks │
│ (discussion content)    │
├─────────────────────────┤
│ ## 할 일 (Heading 2)     │
├─────────────────────────┤
│ To-do blocks...         │
│ (action items)          │
└─────────────────────────┘
```

**Code**:
```python
def _build_blocks(self, summary, key_updates, discussion_log, action_items):
    blocks = []

    # Section 1: 요약
    blocks.append(self._heading_block("요약", level=2))
    blocks.extend(self._text_to_blocks(summary))

    # Section 2: 업데이트
    blocks.append(self._heading_block("업데이트", level=2))
    blocks.extend(self._text_to_blocks(key_updates))

    # Section 3: 논의사항
    blocks.append(self._heading_block("논의사항", level=2))
    blocks.extend(self._text_to_blocks(discussion_log))

    # Section 4: 할 일 (special handling for to-dos)
    blocks.append(self._heading_block("할 일", level=2))
    blocks.extend(self._action_items_to_blocks(action_items))

    return blocks
```

### 4. Block Types

#### 4.1 Heading Block

**Purpose**: Create section headers (H2)

**Implementation**: `_heading_block(text, level=2) -> Dict`

**Notion Format**:
```python
{
    "object": "block",
    "type": "heading_2",  # or heading_1, heading_3
    "heading_2": {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": "요약"}
            }
        ]
    }
}
```

#### 4.2 Paragraph Block

**Purpose**: Regular text content

**Implementation**: `_paragraph_block(text) -> List[Dict]`

**Chunking Logic**:
```python
chunks = chunk_text(text)  # Split if > 2000 chars
blocks = []

for chunk in chunks:
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": chunk}
                }
            ]
        }
    })

return blocks
```

**Chunking Function** (`utils.py`):
```python
def chunk_text(text: str, max_length: int = 2000) -> List[str]:
    """Chunk text to respect Notion's 2000-character limit."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    while len(text) > max_length:
        # Find last space before max_length
        split_pos = text.rfind(' ', 0, max_length)
        if split_pos == -1:
            split_pos = max_length

        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip()

    if text:
        chunks.append(text)

    return chunks
```

#### 4.3 Bulleted List Block

**Purpose**: List items (for updates and discussions)

**Implementation**: `_bulleted_list_block(text) -> List[Dict]`

**Notion Format**:
```python
{
    "object": "block",
    "type": "bulleted_list_item",
    "bulleted_list_item": {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": chunk}
            }
        ]
    }
}
```

**Prefix Detection**:
- Detects lines starting with `-` or `•`
- Strips prefix and creates bulleted list item
- Chunks if content > 2000 characters

#### 4.4 To-Do Block

**Purpose**: Checklist items for action items

**Implementation**: `_todo_block(text) -> List[Dict]`

**Notion Format**:
```python
{
    "object": "block",
    "type": "to_do",
    "to_do": {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": chunk}
            }
        ],
        "checked": False  # Unchecked by default
    }
}
```

**Prefix Stripping**:
```python
# Remove common prefixes
for prefix in ['-', '•', '[ ]', '[x]', '[]']:
    if content.startswith(prefix):
        content = content[len(prefix):].strip()
```

### 5. Text Processing

**Purpose**: Convert plain text to appropriate Notion blocks

**Implementation**: `_text_to_blocks(text) -> List[Dict]`

**Process**:
```
1. Split text into lines
2. For each line:
    a. Check if starts with -, •
       → Create bulleted list item
    b. Otherwise:
       → Create paragraph
3. Chunk each block if > 2000 chars
4. Return list of blocks
```

**Edge Cases**:
- **Empty text**: Return `[paragraph_block("(No content)")]`
- **Only whitespace**: Skip line
- **Very long line**: Chunk into multiple blocks

**Example**:

**Input**:
```
이번 회의에서는 다음 사항을 논의했습니다.
- 신규 기능 A 완료
- 배포 일정 조정
```

**Output**:
```python
[
    paragraph_block("이번 회의에서는 다음 사항을 논의했습니다."),
    bulleted_list_block("신규 기능 A 완료"),
    bulleted_list_block("배포 일정 조정")
]
```

### 6. Action Items Processing

**Purpose**: Convert action items to to-do checkboxes

**Implementation**: `_action_items_to_blocks(text) -> List[Dict]`

**Process**:
```
1. Split text into lines
2. For each line:
    a. Strip common prefixes (-, •, [ ], [x])
    b. Create to-do block (unchecked)
3. Chunk if > 2000 chars
4. Return list of to-do blocks
```

**Example**:

**Input**:
```
1. **김개발:**
    • 배포 스크립트 작성
    • 테스트 환경 설정
2. **박기획:**
    - 문서 업데이트
```

**Output**:
```python
[
    todo_block("1. **김개발:**"),
    todo_block("배포 스크립트 작성"),
    todo_block("테스트 환경 설정"),
    todo_block("2. **박기획:**"),
    todo_block("문서 업데이트")
]
```

## Dependencies

### Python Packages
```
notion-client>=2.0.0  # Official Notion SDK
```

### External Services
- **Notion API**: Requires integration token and database access
- **Internet Connection**: Required for API calls

### Configuration
```bash
# .env file
NOTION_TOKEN=<your_integration_token>
NOTION_PAGE_ID=<database_id>  # Despite the name, this is a database ID
```

### Notion Setup
1. Create integration at notion.so/my-integrations
2. Get integration token (starts with `secret_`)
3. Create or select database for meeting minutes
4. Share database with integration
5. Get database ID from database URL

**Database ID from URL**:
```
https://notion.so/workspace/abc123def456?v=...
                          ^^^^^^^^^^^^^^^^
                          Database ID
```

## Error Handling

### Error Types

**1. Configuration Errors**
```python
ValueError: "NOTION_TOKEN is not configured"
ValueError: "NOTION_PAGE_ID is not configured"
```

**2. API Errors**
```python
# Invalid database ID
APIResponseError: Could not find database with ID: abc123

# Insufficient permissions
APIResponseError: This integration does not have permission to access this database

# Invalid property name
APIResponseError: Name is not a property that exists
```

**3. Text Encoding Errors**
```python
# Korean text corruption (rare with UTF-8)
UnicodeEncodeError: 'charmap' codec can't encode characters
```

### Error Recovery

| Error Type | Recovery Strategy |
|------------|-------------------|
| Missing config | Raise ValueError (user must fix) |
| Invalid database ID | Check database sharing and ID |
| Wrong property name | Update to match database schema |
| Text too long | Automatic chunking |
| API rate limit | Retry after delay (not implemented) |

### Common Issues

**Issue 1**: "제목 property not found"
**Solution**: Database must have a Title property named "제목" (Korean)

**Issue 2**: "Integration not shared with database"
**Solution**: In Notion, click "..." → "Connections" → Add integration

**Issue 3**: "Page vs Database confusion"
**Solution**: Use database ID, not page ID (despite variable name)

## Testing Strategy

### Unit Tests (`tests/unit/test_notion_integration.py`)
```python
def test_heading_block():
    """Test heading block creation"""

def test_paragraph_block_chunking():
    """Test text chunking for long paragraphs"""

def test_bulleted_list_detection():
    """Test - and • prefix detection"""

def test_todo_block_creation():
    """Test to-do checkbox creation"""

def test_korean_text_handling():
    """Test Korean character encoding"""
```

### Integration Tests (`test_notion_only.py`)
```python
def test_real_notion_page_creation():
    """Test actual Notion API page creation"""
```

### Mock Strategy (`tests/conftest.py`)
```python
@pytest.fixture
def mock_notion(mocker):
    """Mock Notion client for unit tests"""
    mock_client = mocker.patch('notion_integration.Client')
    mock_client.return_value.pages.create.return_value = {
        "id": "mock-page-id",
        "url": "https://notion.so/mock-page"
    }
    return mock_client
```

## Performance Metrics

### Response Time
- **Average**: 2-3 seconds
- **Max**: 5 seconds
- **Factors**: Block count, API latency

### Block Limits
- **Notion limit**: 100 blocks per API call
- **Current usage**: ~10-30 blocks per meeting
- **Chunked paragraphs**: Add extra blocks

### API Rate Limits
- **Notion rate limit**: 3 requests per second
- **Current usage**: 1 request per meeting (no retry logic)

## Configuration

### Database Schema

**Required Properties**:
```
┌────────────────────────────────┐
│ Property Name │ Type   │ Notes │
├───────────────┼────────┼───────┤
│ 제목          │ Title  │ Required, Korean name │
│ 생성 일시     │ Date   │ Optional (auto-filled) │
│ 태그          │ Multi-select │ Optional │
└────────────────────────────────┘
```

**Property Configuration**:
- **Title property**: Must be named "제목" (not "Name" or "Title")
- **Other properties**: Optional, not used by integration

### Text Chunking

**Configuration** (`utils.py`):
```python
MAX_NOTION_TEXT_LENGTH = 2000  # Notion's limit
```

**Chunking Strategy**:
1. If text ≤ 2000 chars: Single block
2. If text > 2000 chars: Split at word boundaries
3. Create multiple blocks (preserves formatting)

## Limitations

### Current Limitations
1. **No rich text**: Bold/italic formatting not preserved
2. **No nested blocks**: Flat structure only
3. **No images**: Cannot embed images
4. **No tables**: Cannot create table blocks
5. **No retry**: Single API call, no automatic retry
6. **No pagination**: Cannot handle very large meetings (>100 blocks)

### Workarounds
- **Rich text**: Use markdown syntax (** for bold, etc.)
- **Nested blocks**: Use indentation in text
- **Images**: Upload separately, link in text
- **Tables**: Use bulleted lists as workaround

## Future Enhancements

### Potential Improvements
1. **Rich text parsing**: Convert markdown to Notion rich text
2. **Nested blocks**: Support child blocks (indented lists)
3. **Image embedding**: Upload and embed screenshots
4. **Table support**: Parse and create table blocks
5. **Retry logic**: Automatic retry with exponential backoff
6. **Batch updates**: Update existing page instead of creating new
7. **Custom templates**: User-defined page structures
8. **Database selection**: Choose database from UI

### Technical Debt
- **Naming confusion**: `page_id` variable actually holds `database_id`
- **Error messages**: Generic errors, need more specific messages
- **No validation**: Doesn't verify block structure before API call
- **Hardcoded sections**: Should be configurable

---

**References**:
- [Notion API Documentation](https://developers.notion.com/)
- [Notion API Block Types](https://developers.notion.com/reference/block)
- [notion-client Python SDK](https://github.com/ramnes/notion-sdk-py)
- [Notion API Limits](https://developers.notion.com/reference/request-limits)
