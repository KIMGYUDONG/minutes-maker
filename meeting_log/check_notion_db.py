"""Check Notion database structure and properties."""

from notion_client import Client
from config import Config
import json

def main():
    print("=== Notion Database Structure Checker ===\n")

    try:
        # Initialize Notion client
        print("1. Initializing Notion Client...")
        client = Client(auth=Config.NOTION_TOKEN)
        print("✅ Notion Client initialized\n")

        # Retrieve database info
        print(f"2. Fetching database structure for ID: {Config.NOTION_PAGE_ID}...")
        database = client.databases.retrieve(database_id=Config.NOTION_PAGE_ID)
        print("✅ Database info retrieved\n")

        # Check for data sources
        data_sources = database.get("data_sources", [])
        if data_sources:
            print(f"⚠️ This database uses data sources!")
            print(f"   Data Source ID: {data_sources[0].get('id')}\n")

            # Try to fetch the actual data source database
            data_source_id = data_sources[0].get('id')
            print(f"3. Fetching actual data source database...")
            try:
                database = client.databases.retrieve(database_id=data_source_id)
                print("✅ Data source database retrieved\n")
            except Exception as e:
                print(f"❌ Could not retrieve data source: {e}\n")

        # Print database title
        if "title" in database:
            title_list = database["title"]
            if title_list:
                db_title = "".join([t.get("plain_text", "") for t in title_list])
                print(f"📚 Database Title: {db_title}\n")

        # Print full database JSON for debugging
        print("=" * 60)
        print("FULL DATABASE JSON:")
        print("=" * 60)
        print(json.dumps(database, indent=2, ensure_ascii=False))
        print()

        # Print properties
        print("=" * 60)
        print("DATABASE PROPERTIES:")
        print("=" * 60)

        properties = database.get("properties", {})

        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get("type", "unknown")
            prop_id = prop_info.get("id", "")

            print(f"\n🔹 Property: {prop_name}")
            print(f"   Type: {prop_type}")
            print(f"   ID: {prop_id}")

            # Highlight title property
            if prop_type == "title":
                print(f"   ⭐ THIS IS THE TITLE PROPERTY - Use this in code!")

        print("\n" + "=" * 60)
        print("RECOMMENDED CODE:")
        print("=" * 60)

        # Find title property name
        title_prop_name = None
        for prop_name, prop_info in properties.items():
            if prop_info.get("type") == "title":
                title_prop_name = prop_name
                break

        if title_prop_name:
            print(f'\nIn notion_integration.py line 50, use:')
            print(f'"{title_prop_name}": {{')
            print(f'    "title": [')
            print(f'        {{')
            print(f'            "text": {{')
            print(f'                "content": title')
            print(f'            }}')
            print(f'        }}')
            print(f'    ]')
            print(f'}}')
        else:
            print("\n⚠️ No title property found!")

        print("\n✅ Check completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
