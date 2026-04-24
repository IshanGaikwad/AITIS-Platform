
def generate_playwright(story, test):
    return {
        "id": test.id.replace("TC", "AUTO"),
        "title": test.title,
        "framework": story.framework,
        "language": "TypeScript",
        "file_name": f"{test.id}.spec.ts",
        "content": f"test('{test.title}', async () => {{ /* TODO */ }});",
    }
