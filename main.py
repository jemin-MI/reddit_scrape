import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

async def process_comment(comment_div):
    # Get the text content of the main comment
    comment_box = comment_div.locator('div[slot="comment"]').nth(0)
    p_tags = comment_box.locator('p')
    p_count = await p_tags.count()

    replied_comment = ''
    for i in range(p_count):
        replied_comment += await p_tags.nth(i).text_content()

    # Extract meta information
    meta_data_div = comment_div.locator('div[slot="commentMeta"]')
    author_tracker = meta_data_div.locator('faceplate-tracker[noun="comment_author"] a').nth(0)
    comment_author_name = await author_tracker.text_content()
    link = await author_tracker.get_attribute('href')
    time_div = meta_data_div.locator('time').nth(0)
    time = await time_div.get_attribute('title')

    comment_data = {
        "author": comment_author_name.strip(),
        "link": link.strip(),
        "time": time.strip(),
        "body": replied_comment.strip(),
        "replies": []
    }

    # Process nested comments (replies)
    sub_comment_box = comment_div.locator('> shreddit-comment')
    sub_comment_count = await sub_comment_box.count()

    if sub_comment_count > 0:
        for p in range(sub_comment_count):
            sub_comment_div = sub_comment_box.nth(p)
            reply_data = await process_comment(sub_comment_div)
            comment_data["replies"].append(reply_data)

    return comment_data


async def page_loader(url, page, context):
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # Expand any dynamically loaded comments
    expand_buttons = page.locator('faceplate-partial[loading="action"]')
    count_buttons = await expand_buttons.count()
    for i in range(count_buttons):
        await expand_buttons.nth(i).click()
    await asyncio.sleep(2)

    # Extract main post details
    main_container = page.locator('div.main-container')
    heading_div = main_container.locator('shreddit-post')
    title = await heading_div.get_attribute('post-title')
    article_language = await heading_div.get_attribute('post-language')
    auther_id = await heading_div.get_attribute('author-id')
    auther_name = await heading_div.get_attribute('author')
    body_text = (await heading_div.locator('div[slot="text-body"] p').text_content()).strip()

    # Extract comments
    main_comment_div = page.locator('#comment-tree')
    comment_tree_divs = main_comment_div.locator('> shreddit-comment')
    count = await comment_tree_divs.count()
    all_comments = []

    for i in range(count):
        comment_div = comment_tree_divs.nth(i)
        comment_data = await process_comment(comment_div)
        all_comments.append(comment_data)

    # Structure the JSON
    data_dict = {
        "Title": title,
        "Body Text": body_text,
        "Article Language": article_language,
        "Author ID": auther_id,
        "Author Name": auther_name,
        "Comments": all_comments
    }

    # Save to a JSON file
    with open("data.json", 'w') as file:
        json.dump(data_dict, file, indent=4)

    print("Data written to JSON file successfully!")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        url = 'https://www.reddit.com/r/Gta5Modding/comments/1hp563d/is_kiddions_safe_against_battleye/'
        await page_loader(url, page, context)
        await browser.close()


asyncio.run(main())
