"""Notion API integration module."""

from notion_client import Client
from typing import List, Dict, Any
from datetime import datetime
from config import Config
from utils import chunk_text


class NotionClient:
    """Handles Notion API operations for meeting minutes."""
    
    def __init__(self):
        """Initialize the Notion client."""
        if not Config.NOTION_TOKEN:
            raise ValueError("NOTION_TOKEN is not configured")
        
        if not Config.NOTION_PAGE_ID:
            raise ValueError("NOTION_PAGE_ID is not configured")
        
        self.client = Client(auth=Config.NOTION_TOKEN)
        self.page_id = Config.NOTION_PAGE_ID

    def find_today_minutes(self) -> str | None:
        """Check if today's meeting minutes page already exists. Returns URL if found."""
        from datetime import date
        today = date.today().isoformat()

        results = self.client.databases.query(
            database_id=self.page_id,
            filter={"property": "날짜", "date": {"equals": today}}
        )

        if results.get("results"):
            return results["results"][0].get("url")
        return None
    
    def create_meeting_minutes(
        self,
        summary: str,
        key_updates: str,
        discussion_log: str,
        action_items: str
    ) -> str:
        """
        Create meeting minutes as a new page in Notion.
        
        Args:
            summary: Meeting summary
            key_updates: Key updates section
            discussion_log: Discussion log section
            action_items: Action items section
            
        Returns:
            URL of the created page
        """
        try:
            # Windows strftime() can't handle emojis, so format separately
            timestamp = datetime.now().strftime("%Y-%m-%d")
            title = f"팀 주간 회의 {timestamp}"

            new_page = self.client.pages.create(
                parent={"database_id": self.page_id},
                icon={
                    "type": "emoji",
                    "emoji": "🧐"
                },
                properties={
                    "제목": {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    },
                    "날짜": {
                        "date": {
                            "start": timestamp
                        }
                    },
                    "유형": {
                        "select": {
                            "name": "팀 주간 회의"
                        }
                    }
                },
                children=self._build_blocks(summary, key_updates, discussion_log, action_items)
            )
            
            return new_page["url"]
            
        except Exception as e:
            raise RuntimeError(f"Failed to create Notion page: {str(e)}")
    
    def _build_blocks(
        self,
        summary: str,
        key_updates: str,
        discussion_log: str,
        action_items: str
    ) -> List[Dict[str, Any]]:
        """
        Build Notion blocks for the meeting minutes.
        
        Args:
            summary: Meeting summary
            key_updates: Key updates section
            discussion_log: Discussion log section
            action_items: Action items section
            
        Returns:
            List of Notion block objects
        """
        blocks = []

        blocks.append(self._heading_block("요약", level=2))
        blocks.extend(self._text_to_blocks(summary))

        blocks.append(self._heading_block("업데이트", level=2))
        blocks.extend(self._text_to_blocks(key_updates))

        blocks.append(self._heading_block("논의사항", level=2))
        blocks.extend(self._text_to_blocks(discussion_log))

        blocks.append(self._heading_block("할 일", level=2))
        blocks.extend(self._action_items_to_blocks(action_items))
        
        return blocks
    
    def _heading_block(self, text: str, level: int = 2) -> Dict[str, Any]:
        """
        Create a heading block.
        
        Args:
            text: Heading text
            level: Heading level (1, 2, or 3)
            
        Returns:
            Notion heading block
        """
        heading_type = f"heading_{level}"
        return {
            "object": "block",
            "type": heading_type,
            heading_type: {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": text
                        }
                    }
                ]
            }
        }
    
    def _parse_hierarchical_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse hierarchical text into a tree structure.

        Args:
            text: Text with indentation representing hierarchy

        Returns:
            List of dictionaries with content, level, and children
        """
        if not text or not text.strip():
            return []

        lines = text.split('\n')
        items = []

        for line in lines:
            if not line.strip():
                continue

            # Count leading spaces to determine indent level
            stripped = line.lstrip()
            indent_count = len(line) - len(stripped)

            # Determine indent level (0, 1, 2+)
            # Typically: 0 spaces = level 0, 4 spaces = level 1, 8+ spaces = level 2
            if indent_count == 0:
                level = 0
            elif indent_count <= 4:
                level = 1
            else:
                level = 2

            # Detect item type and extract content
            content = stripped
            item_type = "paragraph"

            # Remove list markers
            if content.startswith('•') or content.startswith('-'):
                content = content[1:].strip()
                item_type = "bulleted_list_item"
            elif content and content[0].isdigit() and '.' in content[:4]:
                # Numbered list: "1. ", "2. ", etc.
                idx = content.index('.')
                content = content[idx+1:].strip()
                item_type = "numbered_list_item"
            elif len(content) >= 2 and content[0].isalpha() and content[1] == '.':
                # Lettered list: "a. ", "b. ", etc.
                content = content[2:].strip()
                item_type = "bulleted_list_item"

            # Strip markdown bold
            content = self._strip_markdown_bold(content)

            items.append({
                "content": content,
                "level": level,
                "type": item_type,
                "children": []
            })

        return items

    def _build_hierarchy(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build parent-child hierarchy from flat list with levels.

        Args:
            items: Flat list of items with level information

        Returns:
            Hierarchical list with children nested
        """
        if not items:
            return []

        root = []
        stack = []  # Stack of (item, level) tuples

        for item in items:
            current_level = item["level"]

            # Pop items from stack that are not ancestors
            while stack and stack[-1]["level"] >= current_level:
                stack.pop()

            # If stack is empty, this is a root item
            if not stack:
                root.append(item)
                stack.append(item)
            else:
                # Add as child of the last item in stack
                parent = stack[-1]
                parent["children"].append(item)
                stack.append(item)

        return root

    def _text_to_blocks(self, text: str) -> List[Dict[str, Any]]:
        """
        Convert text to Notion paragraph/bulleted list blocks with hierarchy.

        Args:
            text: Text to convert

        Returns:
            List of Notion blocks
        """
        if not text or not text.strip():
            return self._paragraph_block("(No content)")

        # Parse hierarchical structure
        items = self._parse_hierarchical_text(text)
        if not items:
            return self._paragraph_block("(No content)")

        # Build hierarchy
        hierarchy = self._build_hierarchy(items)

        # Convert to Notion blocks
        blocks = self._build_nested_blocks(hierarchy)

        return blocks if blocks else self._paragraph_block("(No content)")

    def _build_nested_blocks(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Recursively build Notion blocks with nested children.

        Args:
            items: Hierarchical items with children

        Returns:
            List of Notion block objects with children
        """
        blocks = []

        for item in items:
            content = item["content"]
            item_type = item["type"]
            children = item.get("children", [])

            # Build children blocks recursively
            children_blocks = []
            if children:
                children_blocks = self._build_nested_blocks(children)

            # Create the appropriate block type
            if item_type == "bulleted_list_item":
                blocks.extend(self._bulleted_list_block(content, children_blocks))
            elif item_type == "numbered_list_item":
                blocks.extend(self._numbered_list_block(content, children_blocks))
            else:
                blocks.extend(self._paragraph_block(content, children_blocks))

        return blocks

    def _action_items_to_blocks(self, text: str) -> List[Dict[str, Any]]:
        """
        Convert action items to Notion to-do blocks.
        
        Args:
            text: Action items text
            
        Returns:
            List of Notion to-do blocks
        """
        if not text or not text.strip():
            return self._paragraph_block("No action items")
        
        blocks = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            content = line
            for prefix in ['-', '•', '[ ]', '[x]', '[]']:
                if content.startswith(prefix):
                    content = content[len(prefix):].strip()
            
            blocks.extend(self._todo_block(content))
        
        return blocks if blocks else self._paragraph_block("No action items")

    def _strip_markdown_bold(self, text: str) -> str:
        """
        Remove **bold** markdown from text.

        Args:
            text: Text potentially containing **bold** markdown

        Returns:
            Text with bold markdown removed
        """
        import re
        # Remove **text** pattern
        return re.sub(r'\*\*(.+?)\*\*', r'\1', text)

    def _paragraph_block(self, text: str, children: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Create paragraph block(s), chunking if necessary."""
        chunks = chunk_text(text)
        blocks = []

        for i, chunk in enumerate(chunks):
            block = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": chunk
                            }
                        }
                    ]
                }
            }
            # Only add children to the first chunk
            if i == 0 and children:
                block["paragraph"]["children"] = children
            blocks.append(block)
        return blocks
    
    def _bulleted_list_block(self, text: str, children: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Create bulleted list block(s), chunking if necessary."""
        chunks = chunk_text(text)
        blocks = []

        for i, chunk in enumerate(chunks):
            block = {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": chunk
                            }
                        }
                    ]
                }
            }
            # Only add children to the first chunk
            if i == 0 and children:
                block["bulleted_list_item"]["children"] = children
            blocks.append(block)
        return blocks

    def _numbered_list_block(self, text: str, children: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Create numbered list block(s), chunking if necessary."""
        chunks = chunk_text(text)
        blocks = []

        for i, chunk in enumerate(chunks):
            block = {
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": chunk
                            }
                        }
                    ]
                }
            }
            # Only add children to the first chunk
            if i == 0 and children:
                block["numbered_list_item"]["children"] = children
            blocks.append(block)
        return blocks
    
    def create_soomgo_minutes(
        self,
        content: str,
        client_name: str,
        meeting_type: str,
        industry: str,
        user_name: str,
        ai_summary: str = "",
    ) -> str:
        """Create Soomgo client meeting minutes page in Notion.

        Args:
            content: Full markdown content from LLM
            client_name: Client company name
            meeting_type: Meeting type (초기 상담/후속 미팅/계약 미팅)
            industry: Client industry
            user_name: User who created this
            ai_summary: One-line AI summary

        Returns:
            URL of the created Notion page
        """
        from config import Config

        if not Config.SOOMGO_NOTION_DB_ID:
            raise ValueError("SOOMGO_NOTION_DB_ID is not configured")

        timestamp = datetime.now().strftime("%Y-%m-%d")
        title = f"{client_name} · {timestamp}"

        properties = {
            "제목": {"title": [{"text": {"content": title}}]},
            "클라이언트명": {"select": {"name": client_name}},
            "미팅 날짜": {"date": {"start": timestamp}},
            "미팅 유형": {"select": {"name": meeting_type}},
            "담당자": {"select": {"name": user_name}},
            "업종": {"select": {"name": industry}},
            "상태": {"select": {"name": "진행 중"}},
        }

        if ai_summary:
            properties["AI 요약"] = {
                "rich_text": [{"text": {"content": ai_summary[:2000]}}]
            }

        # Convert markdown content to Notion blocks
        blocks = self._markdown_to_blocks(content)

        new_page = self.client.pages.create(
            parent={"database_id": Config.SOOMGO_NOTION_DB_ID},
            icon={"type": "emoji", "emoji": "🤝"},
            properties=properties,
            children=blocks,
        )
        return new_page["url"]

    def _clean_text(self, text: str) -> str:
        """Strip markdown bold and HTML tags from text."""
        text = self._strip_markdown_bold(text)
        text = text.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
        return text

    def _callout_block(self, text: str, icon: str = "📌", color: str = "gray_background") -> dict:
        """Create a callout block with icon and background color."""
        return {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": self._clean_text(text)}}],
                "icon": {"emoji": icon},
                "color": color,
            }
        }

    def _divider_block(self) -> dict:
        """Create a divider block."""
        return {"object": "block", "type": "divider", "divider": {}}

    def _markdown_to_blocks(self, markdown_text: str) -> list:
        """Convert markdown text to Notion blocks with visual design.

        Design pattern:
        - Divider before each ## heading (section separation)
        - > quote lines become callout blocks
        - ## headings, ### subheadings preserved
        - Bullet/numbered lists, todo items preserved
        - Markdown bold and HTML tags cleaned
        """
        blocks = []
        markdown_text = markdown_text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
        lines = markdown_text.split("\n")
        i = 0
        has_content = False

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                i += 1
                continue

            # Heading 2 — add divider before (except first section)
            if stripped.startswith("## "):
                text = stripped[3:].strip()
                if has_content:
                    blocks.append(self._divider_block())
                blocks.append(self._heading_block(text, level=2))
                has_content = True
                i += 1
                continue

            # Heading 3
            if stripped.startswith("### "):
                text = stripped[4:].strip()
                blocks.append(self._heading_block(text, level=3))
                has_content = True
                i += 1
                continue

            # Quote/callout — > lines become callout blocks
            if stripped.startswith("> "):
                text = stripped[2:].strip()
                text = self._clean_text(text)
                # Detect icon hint from content
                icon = "📌"
                color = "gray_background"
                if "⚠️" in text or "경고" in text or "주의" in text:
                    icon = "⚠️"
                    color = "yellow_background"
                elif "📋" in text or "개요" in text:
                    icon = "📋"
                    color = "blue_background"
                elif "🏃" in text or "브릿지" in text or "우리" in text:
                    icon = "🏃"
                    color = "green_background"
                elif "🤝" in text or "고객" in text:
                    icon = "🤝"
                    color = "orange_background"
                elif "💡" in text:
                    icon = "💡"
                    color = "yellow_background"
                # Remove icon from text if it's at the start
                for emoji in ["⚠️", "📋", "🏃", "🤝", "💡", "📌"]:
                    if text.startswith(emoji):
                        text = text[len(emoji):].strip()
                blocks.append(self._callout_block(text, icon=icon, color=color))
                has_content = True
                i += 1
                continue

            # Todo item
            if stripped.startswith("- [ ] ") or stripped.startswith("- [x] "):
                checked = stripped.startswith("- [x] ")
                text = stripped[6:].strip()
                blocks.extend(self._todo_block(text))
                if blocks:
                    blocks[-1]["to_do"]["checked"] = checked
                has_content = True
                i += 1
                continue

            # Bullet list
            if stripped.startswith("- ") or stripped.startswith("• "):
                text = stripped[2:].strip()
                text = self._clean_text(text)
                blocks.extend(self._bulleted_list_block(text))
                has_content = True
                i += 1
                continue

            # Numbered list
            if len(stripped) >= 3 and stripped[0].isdigit() and "." in stripped[:4]:
                idx = stripped.index(".")
                text = stripped[idx + 1 :].strip()
                text = self._clean_text(text)
                blocks.extend(self._numbered_list_block(text))
                has_content = True
                i += 1
                continue

            # Markdown horizontal rule
            if stripped in ("---", "***", "___"):
                blocks.append(self._divider_block())
                i += 1
                continue

            # Table separator lines (e.g., :--- :----)
            if stripped.startswith(":") or (stripped.startswith("|") and all(c in "|-: " for c in stripped)):
                i += 1
                continue

            # Table rows (| delimited)
            if stripped.startswith("|") and stripped.endswith("|"):
                text = stripped.replace("|", " ").strip()
                text = self._clean_text(text)
                if text:
                    blocks.extend(self._paragraph_block(text))
                has_content = True
                i += 1
                continue

            # Regular paragraph
            text = self._clean_text(stripped)
            blocks.extend(self._paragraph_block(text))
            i += 1

        return blocks

    def _todo_block(self, text: str) -> List[Dict[str, Any]]:
        """Create to-do block(s), chunking if necessary."""
        chunks = chunk_text(text)
        blocks = []
        
        for chunk in chunks:
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": chunk
                            }
                        }
                    ],
                    "checked": False
                }
            })
        return blocks
