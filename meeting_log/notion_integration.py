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
    
    def _text_to_blocks(self, text: str) -> List[Dict[str, Any]]:
        """
        Convert text to Notion paragraph/bulleted list blocks.
        
        Args:
            text: Text to convert
            
        Returns:
            List of Notion blocks
        """
        if not text or not text.strip():
            return self._paragraph_block("(No content)")
        
        blocks = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('-') or line.startswith('•'):
                content = line[1:].strip()
                blocks.extend(self._bulleted_list_block(content))
            else:
                blocks.extend(self._paragraph_block(line))
        
        return blocks if blocks else self._paragraph_block("(No content)")
    
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
    def _paragraph_block(self, text: str) -> List[Dict[str, Any]]:
        """Create paragraph block(s), chunking if necessary."""
        chunks = chunk_text(text)
        blocks = []
        
        for chunk in chunks:
            blocks.append({
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
            })
        return blocks
    
    def _bulleted_list_block(self, text: str) -> List[Dict[str, Any]]:
        """Create bulleted list block(s), chunking if necessary."""
        chunks = chunk_text(text)
        blocks = []
        
        for chunk in chunks:
            blocks.append({
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
            })
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
